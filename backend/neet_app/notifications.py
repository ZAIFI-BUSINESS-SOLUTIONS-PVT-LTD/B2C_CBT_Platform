from typing import Dict, Optional
import threading
import logging

from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings

from .utils import emailer

logger = logging.getLogger(__name__)


def _render_welcome_templates(user, context: Dict) -> Dict[str, str]:
    """Render subject, html and text for welcome email. Falls back to simple text if templates missing."""
    try:
        subject = render_to_string('emails/welcome_subject.txt', context).strip()
    except Exception:
        subject = 'Welcome to Inzighted'

    try:
        html = render_to_string('emails/welcome.html', context)
    except Exception:
        html = None

    try:
        text = render_to_string('emails/welcome.txt', context)
    except Exception:
        # fallback simple text body
        text = (
            f"Hi {user.full_name},\n\n"
            "Welcome to Inzighted! We help you prepare with tests, analytics and an AI chatbot.\n\n"
            "Visit your dashboard to start a test and explore features.\n\n"
            "Thanks,\nThe Inzighted Team"
        )

    return {'subject': subject, 'html': html, 'text': text}


def _send_email_sync(to_email: str, subject: str, html: Optional[str], text: str) -> bool:
    """Use existing emailer functions to send an HTML-aware welcome email. If only text available, send via existing reset-email helper style."""
    # emailer currently only exposes send_password_reset_email; re-use Django EmailMessage path by calling send_password_reset_email when subject matches.
    # For simplicity and to avoid changing emailer, send plain text using SMTP/Django path via send_password_reset_email signature.
    try:
        # Use EmailMultiAlternatives which supports HTML alternatives
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        # text body first
        msg = EmailMultiAlternatives(subject=subject, body=text, from_email=from_email, to=[to_email])
        if html:
            msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.exception('Failed to send welcome email: %s', e)
        return False


def dispatch_welcome_email(user):
    """Render and dispatch welcome email to a StudentProfile instance.

    This function performs the send asynchronously on a background thread so it doesn't block
    the request / model save path. For production, replace with a Celery task or other worker.
    """
    if not getattr(user, 'email', None):
        return False

    # Use absolute frontend URL to avoid relative links like '/' which can render as invalid
    frontend_base = getattr(settings, 'FRONTEND_URL', None) or getattr(settings, 'FRONTEND_RESET_URL', None)
    if frontend_base:
        # If FRONTEND_RESET_URL contains a path (eg /reset-password) prefer base host only
        # attempt to use scheme+host only
        try:
            from urllib.parse import urlparse
            parsed = urlparse(frontend_base)
            if parsed.scheme and parsed.netloc:
                frontend_base = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass

    if not frontend_base:
        frontend_base = 'https://neet.inzighted.com'

    context = {
        'user': user,
        'full_name': user.full_name,
        'login_url': frontend_base + '/',
        'support_email': 'support@inzighted.com',
    }

    rendered = _render_welcome_templates(user, context)

    def _worker():
        try:
            success = _send_email_sync(user.email, rendered['subject'], rendered.get('html'), rendered['text'])
            if not success:
                logger.warning('Welcome email send returned False for %s', user.email)
        except Exception:
            logger.exception('Unhandled exception sending welcome email')

    try:
        # Enqueue Celery task to send welcome email
        from .tasks import send_welcome_email_task
        send_welcome_email_task.delay(user.student_id)
        logger.info(f'Welcome email task enqueued for user {user.student_id}')
        return True
    except ImportError:
        # Celery tasks not available, fallback to threading
        logger.warning('Celery tasks not available, falling back to threading for welcome email')
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return True
    except Exception as e:
        # Log the specific error but still try to send via Celery
        logger.error(f'Error enqueueing welcome email task for user {user.student_id}: {e}')
        # Re-raise to let Celery handle retries
        raise


def _render_test_result_templates(user, context: Dict) -> Dict[str, str]:
    """Render subject and text/html for test result email."""
    try:
        subject = render_to_string('emails/test_result_subject.txt', context).strip()
    except Exception:
        subject = f"Your test results"

    try:
        html = render_to_string('emails/test_result.html', context)
    except Exception:
        html = None

    try:
        text = render_to_string('emails/test_result.txt', context)
    except Exception:
        # fallback simple text body
        text = (
            f"Hi {user.full_name},\n\n"
            f"You have completed Test #{context.get('session_id')}\n\n"
            f"Correct answers: {context.get('correct_answers')}\n"
            f"Incorrect answers: {context.get('incorrect_answers')}\n"
            f"Unanswered questions: {context.get('unanswered_questions')}\n"
            f"Time taken (seconds): {context.get('time_taken')}\n\n"
            "Visit your dashboard for detailed results.\n\n"
            "Thanks,\nThe Inzighted Team"
        )

    return {'subject': subject, 'html': html, 'text': text}


def dispatch_test_result_email(user, results: Dict) -> bool:
    """Dispatch a test result email for a StudentProfile instance.

    This mirrors `dispatch_welcome_email` but uses test result templates.
    The send is performed on a background thread.
    """
    if not getattr(user, 'email', None):
        return False

    frontend_base = getattr(settings, 'FRONTEND_URL', None) or getattr(settings, 'FRONTEND_RESET_URL', None)
    if frontend_base:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(frontend_base)
            if parsed.scheme and parsed.netloc:
                frontend_base = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass

    if not frontend_base:
        frontend_base = 'https://neet.inzighted.com'

    context = {
        'user': user,
        'full_name': user.full_name,
        # include result fields expected by templates
        'session_id': results.get('session_id'),
        'total_questions': results.get('total_questions'),
        'correct_answers': results.get('correct_answers'),
        'incorrect_answers': results.get('incorrect_answers'),
        'unanswered_questions': results.get('unanswered_questions'),
        'time_taken': results.get('time_taken'),
        'score_percentage': results.get('score_percentage'),
        'results_url': f"{frontend_base}/results/{results.get('session_id')}",
        'support_email': 'support@inzighted.com',
    }

    rendered = _render_test_result_templates(user, context)

    def _worker():
        try:
            success = _send_email_sync(user.email, rendered['subject'], rendered.get('html'), rendered['text'])
            if not success:
                logger.warning('Test result email send returned False for %s', user.email)
        except Exception:
            logger.exception('Unhandled exception sending test result email')

    # First check if Celery workers are available to avoid Redis connection delays
    try:
        from .views.insights_views import is_celery_worker_available
        
        if not is_celery_worker_available():
            print(f"⚠️ No Celery workers available, using background thread for email to {user.student_id}")
            # Immediately fall back to background thread
            thread = threading.Thread(target=_worker, daemon=True)
            thread.start()
            print(f"🚀 Background email thread started for user {user.student_id}")
            return True
    except Exception as check_e:
        print(f"⚠️ Error checking Celery availability for email, using background thread: {str(check_e)}")
        # Fall back to background thread if worker check fails
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        print(f"🚀 Background email thread started for user {user.student_id}")
        return True

    # If workers are available, try Celery first
    try:
        from .tasks import send_test_result_email_task
        send_test_result_email_task.delay(user.student_id, results)
        logger.info(f'Test result email task enqueued for user {user.student_id}')
        return True
    except ImportError:
        # Celery tasks not available, fallback to threading
        logger.warning('Celery tasks not available, falling back to threading for test result email')
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return True
    except Exception as e:
        # Log the specific error and fallback to threading instead of failing
        logger.error(f'Error enqueueing test result email task for user {user.student_id}: {e}')
        logger.warning('Falling back to background thread for test result email')
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return True


def _render_inactivity_templates(user, context: Dict) -> Dict[str, str]:
    try:
        subject = render_to_string('emails/inactivity_subject.txt', context).strip()
    except Exception:
        subject = 'We miss you at Inzighted'

    try:
        html = render_to_string('emails/inactivity.html', context)
    except Exception:
        html = None

    try:
        text = render_to_string('emails/inactivity.txt', context)
    except Exception:
        text = (
            f"Hi {user.full_name},\n\n"
            "We noticed you haven't taken a test in a while. Regular practice helps a lot.\n\n"
            "Please log in and take a short test to keep your skills sharp.\n\n"
            "Thanks,\nThe Inzighted Team"
        )

    return {'subject': subject, 'html': html, 'text': text}


def dispatch_inactivity_reminder(user, last_test_date=None) -> bool:
    """Send an inactivity reminder email to a StudentProfile.

    last_test_date: optional datetime of last test to include in email.
    """
    if not getattr(user, 'email', None):
        return False

    frontend_base = getattr(settings, 'FRONTEND_URL', None) or getattr(settings, 'FRONTEND_RESET_URL', None)
    if frontend_base:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(frontend_base)
            if parsed.scheme and parsed.netloc:
                frontend_base = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass

    if not frontend_base:
        frontend_base = 'https://neet.inzighted.com'

    context = {
        'user': user,
        'full_name': user.full_name,
        'last_test_date': last_test_date,
        'dashboard_url': frontend_base + '/',
        'support_email': 'support@inzighted.com',
    }

    rendered = _render_inactivity_templates(user, context)

    def _worker():
        try:
            success = _send_email_sync(user.email, rendered['subject'], rendered.get('html'), rendered['text'])
            if not success:
                logger.warning('Inactivity reminder send returned False for %s', user.email)
        except Exception:
            logger.exception('Unhandled exception sending inactivity reminder')

    try:
        from .tasks import send_inactivity_reminder_task
        send_inactivity_reminder_task.delay(user.student_id, last_test_date)
        logger.info(f'Inactivity reminder task enqueued for user {user.student_id}')
        return True
    except ImportError:
        # Celery tasks not available, fallback to threading
        logger.warning('Celery tasks not available, falling back to threading for inactivity reminder')
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return True
    except Exception as e:
        # Log the specific error but still try to send via Celery
        logger.error(f'Error enqueueing inactivity reminder task for user {user.student_id}: {e}')
        # Re-raise to let Celery handle retries
        raise
