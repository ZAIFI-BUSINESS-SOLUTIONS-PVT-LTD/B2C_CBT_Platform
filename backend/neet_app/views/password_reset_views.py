import secrets
import hashlib
import hmac
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.response import Response
from rest_framework import status

from ..models import StudentProfile, PasswordReset
from ..utils.emailer import send_password_reset_email
from ..serializers import (
    ForgotPasswordSerializer, VerifyTokenSerializer, ResetPasswordSerializer
)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


@api_view(['POST'])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def forgot_password(request):
    """POST /auth/forgot-password
    Always return generic response regardless of email existence.
    """
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email'].lower()

    # Generic response
    generic = {"detail": "If this email exists, we have sent reset instructions."}

    try:
        user = StudentProfile.objects.get(email=email)
    except StudentProfile.DoesNotExist:
        # Always return generic message to avoid enumeration
        return Response(generic, status=status.HTTP_200_OK)

    # Generate secure token and store only its hash
    raw_token = secrets.token_urlsafe(48)  # ~64 chars; cryptographically secure
    token_hash = _hash_token(raw_token)
    expires_at = timezone.now() + timedelta(minutes=30)

    # Store token record
    try:
        with transaction.atomic():
            PasswordReset.objects.create(
                user=user,
                reset_token_hash=token_hash,
                expires_at=expires_at,
                used=False
            )
    except Exception:
        # Do not reveal DB errors to caller
        return Response(generic, status=status.HTTP_200_OK)

    # Build reset link - FRONTEND_RESET_URL can be set in settings or env
    frontend_url = getattr(settings, 'FRONTEND_RESET_URL', 'https://inzighted.com/reset-password')
    reset_link = f"{frontend_url}?token={raw_token}&email={email}"

    # Send email (best-effort)
    send_password_reset_email(to_email=user.email, to_name=user.full_name or user.email, reset_link=reset_link)

    return Response(generic, status=status.HTTP_200_OK)


@api_view(['GET'])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def verify_reset_token(request):
    """GET /auth/verify-reset-token?email=...&token=..."""
    serializer = VerifyTokenSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email'].lower()
    token = serializer.validated_data['token']

    try:
        user = StudentProfile.objects.get(email=email)
    except StudentProfile.DoesNotExist:
        return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

    # Find candidate reset records that are not used and not expired
    now = timezone.now()
    candidates = PasswordReset.objects.filter(user=user, used=False, expires_at__gt=now).order_by('-created_at')
    token_hash = _hash_token(token)

    for cand in candidates:
        if hmac.compare_digest(cand.reset_token_hash, token_hash):
            return Response({"detail": "Token valid."}, status=status.HTTP_200_OK)

    return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def reset_password(request):
    """POST /auth/reset-password
    Body: { email, token, new_password }
    """
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email'].lower()
    token = serializer.validated_data['token']
    new_password = serializer.validated_data['new_password']

    # Basic server-side password strength check
    import re
    if len(new_password) < 8 or not re.search(r'[A-Z]', new_password) or not re.search(r'[a-z]', new_password) or not re.search(r'[0-9]', new_password) or not re.search(r'[^A-Za-z0-9]', new_password):
        return Response({"detail": "Password does not meet complexity requirements."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = StudentProfile.objects.get(email=email)
    except StudentProfile.DoesNotExist:
        return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    token_hash = _hash_token(token)

    # Perform selection, verification and update inside a single transaction
    try:
        with transaction.atomic():
            # Lock candidate rows so token can't be reused concurrently
            candidates = PasswordReset.objects.select_for_update().filter(
                user=user, used=False, expires_at__gt=now
            ).order_by('-created_at')

            matched = None
            for cand in candidates:
                if hmac.compare_digest(cand.reset_token_hash, token_hash):
                    matched = cand
                    break

            if not matched:
                return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

            # Update user's password and mark token as used within the same transaction
            user.set_password(new_password)
            user.password_changed_at = timezone.now()
            user.save(update_fields=['password_hash', 'password_changed_at'])

            matched.used = True
            matched.save(update_fields=['used'])

            # TODO: Invalidate existing sessions / JWTs for this user.
            # If using server sessions, delete session objects for this user.
            # If using JWTs, enforce a check on token issue timestamp vs user.password_changed_at.

    except Exception as e:
        return Response({"detail": "Failed to reset password."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"detail": "Password reset successful, please log in."}, status=status.HTTP_200_OK)
