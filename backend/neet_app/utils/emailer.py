import ssl
import smtplib
from email.message import EmailMessage as StdEmailMessage
from django.core.mail import EmailMessage
from django.conf import settings
from typing import Optional


def _build_body(name: str, reset_link: str) -> str:
    return (
        f"Hello {name or ''},\n\n"
        "You requested to reset your password.\n\n"
        "Click the link below to reset it (valid for 30 minutes):\n"
        f"{reset_link}\n\n"
        "If you didn’t request this, ignore this email.\n"
    )


def send_password_reset_email(to_email: str, to_name: str, reset_link: str) -> bool:
    """Send password reset email.

    Behavior:
    - If settings.EMAIL_PROVIDER == 'zeptomail' or 'smtp', use direct smtplib with settings EMAIL_HOST, EMAIL_PORT,
      EMAIL_HOST_USER and EMAIL_HOST_PASSWORD (read from env). This is useful for ZeptoMail integration.
    - Otherwise, fall back to Django's EmailMessage which uses EMAIL_BACKEND configured in settings.

    Credentials must be provided via environment variables / settings; do NOT commit secrets to git.
    """
    subject = "Reset your Inzighted password"
    body = _build_body(to_name, reset_link)

    provider = getattr(settings, 'EMAIL_PROVIDER', '').lower()

    if provider in ('zeptomail', 'smtp'):
        # Use smtplib directly (ZeptoMail sample)
        smtp_server = getattr(settings, 'EMAIL_HOST', 'smtp.zeptomail.in')
        port = int(getattr(settings, 'EMAIL_PORT', 587))
        username = getattr(settings, 'EMAIL_HOST_USER', None)
        password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', username or 'no-reply@inzighted.com')

        if not username or not password:
            # Missing credentials; do not attempt to send
            # In production log appropriately; here we return False
            print('Email credentials missing for ZeptoMail provider')
            return False

        msg = StdEmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        msg.set_content(body)

        try:
            if port == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
                    server.login(username, password)
                    server.send_message(msg)
            elif port == 587:
                with smtplib.SMTP(smtp_server, port, timeout=30) as server:
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                    server.login(username, password)
                    server.send_message(msg)
            else:
                # Unsupported port - return False (do not raise)
                print('Unsupported SMTP port configured for ZeptoMail:', port)
                return False
            return True
        except Exception as e:
            # In production, replace prints with proper logging. Avoid logging secrets.
            print('Failed to send email via ZeptoMail SMTP provider:', str(e))
            return False

    # Default: use Django's EmailMessage which respects EMAIL_BACKEND setting
    try:
        email = EmailMessage(subject=subject, body=body, to=[to_email])
        email.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print('Failed to send password reset email (Django backend):', str(e))
        return False
