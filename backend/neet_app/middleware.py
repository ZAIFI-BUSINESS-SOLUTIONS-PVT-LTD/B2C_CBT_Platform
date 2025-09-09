from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import UserActivity, StudentActivity, StudentProfile
import logging
logger = logging.getLogger(__name__)
try:
    # Import here so middleware still imports even if DRF/SimpleJWT are not installed
    from rest_framework_simplejwt.authentication import JWTAuthentication
except Exception:
    JWTAuthentication = None

class UpdateLastSeenMiddleware:
    """Middleware that updates UserActivity.last_seen for authenticated users.

    Add to settings.MIDDLEWARE after AuthenticationMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        # If user is not authenticated via session, try JWT auth (DRF) so token users are tracked
        jwt_user = None
        if (not user) or (getattr(user, 'is_authenticated', False) is False):
            if JWTAuthentication is not None:
                try:
                    result = JWTAuthentication().authenticate(request)
                    if result:
                        jwt_user = result[0]
                        # Do not override request.user if a session-based user exists and is authenticated
                        if not (user and getattr(user, 'is_authenticated', False)):
                            request.user = jwt_user
                            user = jwt_user
                except Exception:
                    logger.debug('JWT auth attempted in UpdateLastSeenMiddleware and failed')
                # If the simplejwt JWTAuthentication didn't yield a user, try the project's StudentJWTAuthentication
                if jwt_user is None:
                    try:
                        from .student_auth import StudentJWTAuthentication as ProjectStudentJWT
                        result = ProjectStudentJWT().authenticate(request)
                        if result:
                            jwt_user = result[0]
                            if not (user and getattr(user, 'is_authenticated', False)):
                                request.user = jwt_user
                                user = jwt_user
                    except Exception:
                        # Non-fatal; just skip if custom auth not available or fails
                        logger.debug('Project StudentJWTAuthentication attempt failed in middleware')

        if user and getattr(user, 'is_authenticated', False):
            # compute timestamp once for both UserActivity and StudentActivity
            now = timezone.now()
            # Update UserActivity only for real Django auth.User instances
            AuthUserModel = get_user_model()
            if isinstance(user, AuthUserModel):
                try:
                    now = timezone.now()
                    updated = UserActivity.objects.filter(user=user).update(
                        last_seen=now,
                        ip_address=request.META.get('REMOTE_ADDR') or None,
                        user_agent=request.META.get('HTTP_USER_AGENT') or None
                    )
                    if not updated:
                        # Attempt create if update didn't find a row
                        UserActivity.objects.create(user=user, last_seen=now,
                                                    ip_address=request.META.get('REMOTE_ADDR') or None,
                                                    user_agent=request.META.get('HTTP_USER_AGENT') or None)
                except Exception:
                    # Log failures so we can detect silent metric issues
                    logger.exception('UpdateLastSeenMiddleware failed to write UserActivity')
            # Additionally update StudentActivity when request belongs to a student
            try:
                # If request.user is a StudentProfile or has student_id attribute or student_profile
                student = None
                if isinstance(user, StudentProfile):
                    student = user
                else:
                    # support wrapper objects that hold StudentProfile under student_profile
                    sp = getattr(user, 'student_profile', None)
                    if isinstance(sp, StudentProfile):
                        student = sp
                    else:
                        sid = getattr(user, 'student_id', None)
                        if sid:
                            try:
                                student = StudentProfile.objects.get(student_id=sid)
                            except StudentProfile.DoesNotExist:
                                student = None

                if student:
                    logger.info(f'UpdateLastSeenMiddleware: updating StudentActivity for {student.student_id}')
                    updated = StudentActivity.objects.filter(student=student).update(
                        last_seen=now,
                        ip_address=request.META.get('REMOTE_ADDR') or None,
                        user_agent=request.META.get('HTTP_USER_AGENT') or None
                    )
                    if updated:
                        logger.info(f'UpdateLastSeenMiddleware: StudentActivity updated for {student.student_id}')
                    else:
                        logger.info(f'UpdateLastSeenMiddleware: creating StudentActivity for {student.student_id}')
                        StudentActivity.objects.create(student=student, last_seen=now,
                                                       ip_address=request.META.get('REMOTE_ADDR') or None,
                                                       user_agent=request.META.get('HTTP_USER_AGENT') or None)
                        logger.info(f'UpdateLastSeenMiddleware: StudentActivity created for {student.student_id}')
            except Exception:
                logger.exception('UpdateLastSeenMiddleware failed to write StudentActivity')
        return self.get_response(request)
