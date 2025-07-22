import urllib.parse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import StudentProfile
from ..serializers import StudentProfileSerializer


class StudentProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing student profiles.
    Corresponds to /api/student-profile in Node.js.
    """
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer

    @action(detail=False, methods=['get'], url_path='email/(?P<email>.+)')
    def by_email(self, request, email=None):
        """
        Retrieves a student profile by email.
        Replicates GET /api/student-profile/email/:email logic.
        """
        # URL decode the email parameter to handle encoded @ symbols
        decoded_email = urllib.parse.unquote(email)
        
        profile = get_object_or_404(StudentProfile, email__iexact=decoded_email)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
