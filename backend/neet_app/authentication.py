"""
Custom JWT Authentication for NEET Practice Platform
"""
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers, status
from rest_framework.response import Response
from django.contrib.auth.hashers import check_password
from .models import StudentProfile
from .serializers import StudentProfileSerializer


class StudentTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that works with StudentProfile model using email
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace username field with email
        self.fields['email'] = serializers.EmailField()
        self.fields['password'] = serializers.CharField()
        # Remove default username field if it exists
        if 'username' in self.fields:
            del self.fields['username']

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError('Both email and password are required.')
        
        try:
            # Get student by email
            student = StudentProfile.objects.get(email__iexact=email)
            
            # Check if student is active
            if not student.is_active:
                raise serializers.ValidationError('Student account is deactivated.')
            
            # Verify password
            if not student.check_password(password):
                raise serializers.ValidationError('Invalid credentials.')
            
            # Update last login
            from django.utils import timezone
            student.last_login = timezone.now()
            student.save(update_fields=['last_login'])
            
            # Create a dummy user object for JWT token generation
            # We'll use the student_id as the user identifier in the token
            class StudentUser:
                def __init__(self, student_profile):
                    self.id = student_profile.student_id  # Use student_id as the ID for the token
                    self.pk = student_profile.student_id  
                    self.student_profile = student_profile
                    self.username = student_profile.student_id  
                    self._is_authenticated = True
                    self._is_active = student_profile.is_active
                    self._is_anonymous = False
                
                @property
                def is_authenticated(self):
                    return self._is_authenticated
                
                @property
                def is_active(self):
                    return self._is_active
                
                @property
                def is_anonymous(self):
                    return self._is_anonymous
                
                def __str__(self):
                    return f"Student-{self.student_profile.student_id}"
            
            user = StudentUser(student)
            
            # Generate tokens with student_id as the user_id
            refresh = self.get_token(user)
            
            # Add student data to the token payload
            refresh['student_id'] = student.student_id
            refresh['email'] = student.email
            
            # Get student data and convert to camelCase
            student_data = StudentProfileSerializer(student).data
            
            # Convert snake_case keys to camelCase for consistency with frontend
            camel_case_student = {}
            for key, value in student_data.items():
                # Convert snake_case to camelCase
                if '_' in key:
                    parts = key.split('_')
                    camel_key = parts[0] + ''.join(word.capitalize() for word in parts[1:])
                    camel_case_student[camel_key] = value
                else:
                    camel_case_student[key] = value
            
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'student': camel_case_student
            }
            
        except StudentProfile.DoesNotExist:
            raise serializers.ValidationError('Invalid credentials.')
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims if needed
        return token


class StudentTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view for students
    Ensures proper camelCase response formatting
    """
    serializer_class = StudentTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        """Override post to ensure camelCase formatting"""
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            # Return validation errors in camelCase format
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the validated data (which includes student profile)
        validated_data = serializer.validated_data
        
        # Return response that will be processed by CamelCaseJSONRenderer
        return Response(validated_data)
