"""
Simple test views for validating the new authentication system
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from datetime import date

from ..models import StudentProfile, TestSession, Topic
from ..serializers import (
    StudentProfileCreateSerializer, 
    StudentLoginSerializer,
    TestSessionCreateSerializer
)
from ..utils.topic_utils import classify_topics_by_subject


@api_view(['POST'])
def create_test_student(request):
    """
    Quick endpoint to create a test student
    POST /api/test/create-student/
    """
    # Default test student data
    test_data = {
        'full_name': request.data.get('full_name', 'Test Student'),
        'email': request.data.get('email', f'test{timezone.now().timestamp()}@example.com'),
        'phone_number': request.data.get('phone_number', '+91-9999999999'),
        'date_of_birth': request.data.get('date_of_birth', '2005-01-15'),
        'school_name': request.data.get('school_name', 'Test School'),
        'target_exam_year': request.data.get('target_exam_year', 2025)
    }
    
    serializer = StudentProfileCreateSerializer(data=test_data)
    if serializer.is_valid():
        student = serializer.save()
        return Response({
            'message': 'Test student created successfully',
            'student_id': student.student_id,
            'generated_password': student.generated_password,
            'email': student.email,
            'full_name': student.full_name
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def test_login(request):
    """
    Test login endpoint
    POST /api/test/login/
    """
    serializer = StudentLoginSerializer(data=request.data)
    if serializer.is_valid():
        student = serializer.validated_data['student']
        
        # Return complete student profile as expected by frontend
        from ..serializers import StudentProfileSerializer
        student_data = StudentProfileSerializer(student).data
        
        return Response({
            'message': 'Login successful',
            'student': student_data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
def test_topic_classification(request):
    """
    Test topic classification
    GET /api/test/classify-topics/
    """
    classification = classify_topics_by_subject()
    
    summary = {}
    for subject, topics in classification.items():
        summary[subject] = {
            'count': len(topics),
            'examples': topics[:5]  # First 5 as examples
        }
    
    return Response({
        'message': 'Topic classification successful',
        'classification_summary': summary,
        'total_topics': sum(len(topics) for topics in classification.values())
    })


@api_view(['POST'])
def create_test_session(request):
    """
    Create a test session for testing
    POST /api/test/create-session/
    """
    # Get default data if not provided
    student_id = request.data.get('student_id')
    if not student_id:
        # Get first available student
        student = StudentProfile.objects.first()
        if not student:
            return Response({
                'error': 'No students available. Create a student first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        student_id = student.student_id
    
    # Get some topics if not provided
    selected_topics = request.data.get('selected_topics')
    if not selected_topics:
        topics = Topic.objects.all()[:10]  # Get first 10 topics
        selected_topics = [str(topic.id) for topic in topics]
    
    test_data = {
        'student_id': student_id,
        'selected_topics': selected_topics,
        'time_limit': request.data.get('time_limit', 60),
        'question_count': request.data.get('question_count', 10)
    }
    
    serializer = TestSessionCreateSerializer(data=test_data)
    if serializer.is_valid():
        session = serializer.save()
        
        return Response({
            'message': 'Test session created successfully',
            'session_id': session.id,
            'student_id': session.student_id,
            'total_questions': session.total_questions,
            'selected_topics_count': len(session.selected_topics),
            'physics_topics': len(session.physics_topics),
            'chemistry_topics': len(session.chemistry_topics),
            'botany_topics': len(session.botany_topics),
            'zoology_topics': len(session.zoology_topics)
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def system_status(request):
    """
    Get overall system status
    GET /api/test/status/
    """
    try:
        # Count existing data
        students_count = StudentProfile.objects.count()
        sessions_count = TestSession.objects.count()
        topics_count = Topic.objects.count()
        completed_sessions = TestSession.objects.filter(is_completed=True).count()
        
        # Test topic classification
        classification = classify_topics_by_subject()
        
        return Response({
            'message': 'System is operational',
            'database_status': {
                'students': students_count,
                'test_sessions': sessions_count,
                'completed_sessions': completed_sessions,
                'topics': topics_count
            },
            'topic_classification': {
                'physics': len(classification.get('Physics', [])),
                'chemistry': len(classification.get('Chemistry', [])),
                'botany': len(classification.get('Botany', [])),
                'zoology': len(classification.get('Zoology', [])),
                'unclassified': len(classification.get('Unclassified', []))
            },
            'features_status': {
                'student_authentication': True,
                'auto_id_generation': True,
                'topic_classification': True,
                'test_session_tracking': True,
                'subject_wise_analytics': True
            }
        })
    
    except Exception as e:
        return Response({
            'message': 'System error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
