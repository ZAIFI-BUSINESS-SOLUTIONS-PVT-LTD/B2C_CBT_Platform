import urllib.parse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..errors import AppError, ValidationError as AppValidationError, NotFoundError
from ..error_codes import ErrorCodes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from ..models import StudentProfile
from ..serializers import (
    StudentProfileSerializer, 
    StudentProfileCreateSerializer,
    StudentLoginSerializer
)
from ..jwt_authentication import StudentJWTAuthentication


class StudentProfileViewSet(viewsets.ModelViewSet):
    """
    Enhanced API endpoint for managing student profiles with authentication.
    Supports student registration, login, and profile management.
    """
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    authentication_classes = [StudentJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions required for this view.
        Allow registration without authentication, but require authentication for other operations.
        """
        if self.action in ['create', 'register', 'login']:
            permission_classes = []
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter profiles by authenticated user for security"""
        if self.action in ['me'] and hasattr(self.request.user, 'student_id'):
            return StudentProfile.objects.filter(student_id=self.request.user.student_id)
        return super().get_queryset()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return StudentProfileCreateSerializer
        elif self.action == 'login':
            return StudentLoginSerializer
        return StudentProfileSerializer

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get current authenticated student profile.
        GET /api/students/me/
        """
        if not hasattr(request.user, 'student_id'):
            raise AppValidationError(code=ErrorCodes.AUTH_REQUIRED if hasattr(ErrorCodes, 'AUTH_REQUIRED') else ErrorCodes.INVALID_INPUT, message='User not properly authenticated')
        
        try:
            student = StudentProfile.objects.get(student_id=request.user.student_id)
            serializer = StudentProfileSerializer(student)
            return Response(serializer.data)
        except StudentProfile.DoesNotExist:
            raise NotFoundError(code=ErrorCodes.NOT_FOUND if hasattr(ErrorCodes, 'NOT_FOUND') else ErrorCodes.SERVER_ERROR, message='Student profile not found')

    @action(detail=False, methods=['put', 'patch'], url_path='update/(?P<student_id>[^/.]+)')
    def update_by_student_id(self, request, student_id=None):
        """
        Update student profile by student_id. Students can only update their own profile.
        PUT /api/student-profile/update/{student_id}/
        PATCH /api/student-profile/update/{student_id}/
        """
        if not hasattr(request.user, 'student_id'):
            raise AppValidationError(code=ErrorCodes.AUTH_REQUIRED if hasattr(ErrorCodes, 'AUTH_REQUIRED') else ErrorCodes.INVALID_INPUT, message='User not properly authenticated')
        
        # Ensure student can only update their own profile
        if student_id != request.user.student_id:
            raise AppError(code=ErrorCodes.FORBIDDEN if hasattr(ErrorCodes, 'FORBIDDEN') else ErrorCodes.INVALID_INPUT, message='You can only update your own profile')
        
        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            raise NotFoundError(code=ErrorCodes.NOT_FOUND if hasattr(ErrorCodes, 'NOT_FOUND') else ErrorCodes.SERVER_ERROR, message='Student profile not found')
        
        # Use partial=True for PATCH requests
        partial = request.method == 'PATCH'
        serializer = StudentProfileSerializer(student, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a new student with auto-generated student_id and password.
        POST /api/student-profile/register/
        """
        serializer = StudentProfileCreateSerializer(data=request.data)
        if serializer.is_valid():
            student = serializer.save()
            
            # Return student info including generated credentials
            response_data = {
                'student_id': student.student_id,
                'generated_password': student.generated_password,
                'full_name': student.full_name,
                'email': student.email,
                'message': 'Student registered successfully. Please save your credentials safely.'
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        raise AppValidationError(code=ErrorCodes.INVALID_INPUT, message='Invalid input for registration', details=serializer.errors)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Authenticate student with student_id and password.
        POST /api/student-profile/login/
        """
        serializer = StudentLoginSerializer(data=request.data)
        if serializer.is_valid():
            student = serializer.validated_data['student']
            
            # Update last login time
            StudentProfile.objects.filter(student_id=student.student_id).update(
                last_login=timezone.now()
            )
            
            # Return student profile data
            profile_serializer = StudentProfileSerializer(student)
            return Response({
                'message': 'Login successful',
                'student': profile_serializer.data
            }, status=status.HTTP_200_OK)
        raise AppValidationError(code=ErrorCodes.INVALID_INPUT, message='Invalid credentials provided', details=serializer.errors)

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """
        Change student password.
        POST /api/student-profile/{student_id}/change_password/
        """
        student = self.get_object()
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            raise AppValidationError(code=ErrorCodes.INVALID_INPUT, message='Both old_password and new_password are required')
        
        if not student.check_password(old_password):
            raise AppValidationError(code=ErrorCodes.INVALID_INPUT, message='Invalid current password')
        
        student.set_password(new_password)
        student.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='check-username')
    def check_username(self, request):
        """
        Check if a username (full_name) is available.
        GET /api/student-profile/check-username/?full_name=John%20Doe
        """
        full_name = request.query_params.get('full_name')
        
        if not full_name:
            raise AppValidationError(code=ErrorCodes.INVALID_INPUT, message='full_name parameter is required')
        
        from ..utils.password_utils import validate_full_name_uniqueness
        is_available, error_message = validate_full_name_uniqueness(full_name)
        
        return Response({
            'available': is_available,
            'message': error_message if not is_available else 'Username is available'
        })

    @action(detail=False, methods=['get'], url_path='email/(?P<email>.+)')
    def by_email(self, request, email=None):
        """
        Retrieves a student profile by email.
        GET /api/student-profile/email/{email}/
        """
        # URL decode the email parameter to handle encoded @ symbols
        decoded_email = urllib.parse.unquote(email)
        
        profile = get_object_or_404(StudentProfile, email__iexact=decoded_email)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        Get detailed statistics for a student.
        GET /api/student-profile/{student_id}/statistics/
        """
        student = self.get_object()
        
        test_sessions = student.get_test_sessions().filter(is_completed=True)
        
        # Calculate additional statistics (fields removed, so only best_score per subject)
        subject_stats = {
            'Physics': {
                'tests_taken': test_sessions.exclude(physics_score__isnull=True).count(),
                'best_score': test_sessions.exclude(physics_score__isnull=True).aggregate(
                    max_score=models.Max('physics_score')
                )['max_score']
            },
            'Chemistry': {
                'tests_taken': test_sessions.exclude(chemistry_score__isnull=True).count(),
                'best_score': test_sessions.exclude(chemistry_score__isnull=True).aggregate(
                    max_score=models.Max('chemistry_score')
                )['max_score']
            },
            'Botany': {
                'tests_taken': test_sessions.exclude(botany_score__isnull=True).count(),
                'best_score': test_sessions.exclude(botany_score__isnull=True).aggregate(
                    max_score=models.Max('botany_score')
                )['max_score']
            },
            'Zoology': {
                'tests_taken': test_sessions.exclude(zoology_score__isnull=True).count(),
                'best_score': test_sessions.exclude(zoology_score__isnull=True).aggregate(
                    max_score=models.Max('zoology_score')
                )['max_score']
            }
        }
        
        return Response({
            'student_info': StudentProfileSerializer(student).data,
            'subject_statistics': subject_stats,
            'recent_performance': test_sessions[:10].values(
                'id', 'start_time', 'total_questions', 'correct_answers',
                'physics_score', 'chemistry_score', 'botany_score', 'zoology_score'
            )
        }, status=status.HTTP_200_OK)
