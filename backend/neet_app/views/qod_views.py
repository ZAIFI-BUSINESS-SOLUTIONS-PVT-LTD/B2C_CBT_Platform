"""
Question of the Day (QOD) Views

Handles endpoints for the daily question feature:
- GET /api/qod/ - Fetch today's question (or check if already attempted)
- POST /api/qod/submit/ - Submit answer for today's question
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta
import random

from ..models import QuestionOfTheDay, Question, TestAnswer, StudentProfile
from ..serializers import QuestionOfTheDaySerializer, QuestionOfTheDaySubmitSerializer, QuestionSerializer
from ..student_auth import StudentJWTAuthentication


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_question_of_the_day(request):
    """
    Get today's question for the authenticated student.
    
    Logic:
    1. Check if student has already attempted QOD today
    2. If yes, return the attempted question with result
    3. If no, select a new question avoiding previously attempted questions
    4. Question selection avoids:
       - Questions from Test Answer Table
       - Questions from Question of the Day Table
    """
    student = request.user
    today = date.today()
    
    # Check if student has already attempted (answered) QOD today
    # Only consider entries with a selected_option (i.e. answered)
    existing_qod = QuestionOfTheDay.objects.filter(
        student_id=student.student_id,
        date=today,
        selected_option__isnull=False,
    ).first()
    
    # Calculate QOD streak (consecutive days with an attempted QOD)
    def _calculate_streak(sid):
        streak = 0
        check_date = today
        while True:
            has_entry = QuestionOfTheDay.objects.filter(
                student_id=sid,
                date=check_date,
                selected_option__isnull=False,
            ).exists()
            if has_entry:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        return streak

    if existing_qod:
        # Student has already attempted today's question
        serializer = QuestionOfTheDaySerializer(existing_qod)
        return Response({
            'already_attempted': True,
            'qod': serializer.data,
            'streak': _calculate_streak(student.student_id),
        })
    
    # Get all question IDs the student has already attempted
    # 1. From Test Answer Table
    test_answered_question_ids = TestAnswer.objects.filter(
        session__student_id=student.student_id
    ).values_list('question_id', flat=True).distinct()
    
    # 2. From Question of the Day Table
    qod_question_ids = QuestionOfTheDay.objects.filter(
        student_id=student.student_id
    ).values_list('question_id', flat=True).distinct()
    
    # Combine both sets
    attempted_question_ids = set(test_answered_question_ids) | set(qod_question_ids)
    
    # Get questions not yet attempted
    available_questions = Question.objects.exclude(
        id__in=attempted_question_ids
    ).filter(
        institution__isnull=True  # Only global questions, not institution-specific
    )
    
    # Fallback: If all questions attempted, select from all questions
    if not available_questions.exists():
        available_questions = Question.objects.filter(
            institution__isnull=True
        )
    
    # Select a random question and return it to the client without persisting
    # a QuestionOfTheDay row. The QOD record will be created only when the
    # student submits an answer.
    if available_questions.exists():
        total_count = available_questions.count()
        random_index = random.randint(0, total_count - 1)
        selected_question = available_questions[random_index]

        # Use QuestionSerializer to build the question payload
        question_serialized = QuestionSerializer(selected_question).data

        # Construct a QOD-like response object (no DB record yet)
        qod_payload = {
            'id': None,
            'student': student.student_id,
            'question': selected_question.id,
            'question_data': question_serialized,
            'date': str(today),
            'selected_option': None,
            'is_correct': None,
            'created_at': None,
        }

        return Response({
            'already_attempted': False,
            'qod': qod_payload,
            'streak': _calculate_streak(student.student_id),
        })
    else:
        return Response(
            {'error': 'No questions available'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_question_of_the_day(request):
    """
    Submit answer for today's Question of the Day.
    
    Request body:
    {
        "selected_option": "A" | "B" | "C" | "D"
    }
    
    Response:
    {
        "is_correct": true/false,
        "correct_answer": "A",
        "explanation": "...",
        "qod": {...}
    }
    """
    student = request.user
    today = date.today()
    
    # Validate request data
    submit_serializer = QuestionOfTheDaySubmitSerializer(data=request.data)
    if not submit_serializer.is_valid():
        return Response(
            submit_serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    selected_option = submit_serializer.validated_data['selected_option']
    question_id = submit_serializer.validated_data.get('question_id')

    # Get today's QOD entry (if any)
    qod = QuestionOfTheDay.objects.filter(
        student_id=student.student_id,
        date=today
    ).first()

    # If no qod row exists (we no longer create on GET), create one now using
    # the question_id sent by the client. If question_id not provided, return
    # an error to avoid guessing which question was shown.
    if not qod:
        if not question_id:
            return Response(
                {'error': 'No question of the day found for today. Include question_id in submit payload.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Validate question exists
        try:
            question_obj = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response({'error': 'Invalid question_id provided.'}, status=status.HTTP_400_BAD_REQUEST)

        qod = QuestionOfTheDay.objects.create(
            student=student,
            question=question_obj,
            date=today
        )
    
    # Check if already answered
    if qod.selected_option is not None:
        return Response(
            {'error': 'You have already answered today\'s question.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check correctness
    correct_answer = qod.question.correct_answer
    is_correct = selected_option == correct_answer
    
    # Update QOD entry with the submitted answer
    qod.selected_option = selected_option
    qod.is_correct = is_correct
    qod.save()
    
    # Prepare response with question details
    serializer = QuestionOfTheDaySerializer(qod)
    
    return Response({
        'is_correct': is_correct,
        'correct_answer': correct_answer,
        'explanation': qod.question.explanation,
        'explanation_image': qod.question.explanation_image,
        'qod': serializer.data
    })
