import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..models import Question, TestSession, TestAnswer

logger = logging.getLogger(__name__)


class TimeTrackingViewSet(viewsets.GenericViewSet):
    """
    API endpoint for tracking time spent on questions during test sessions.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def log_time(self, request):
        """
        Log time spent on a specific question during a test session.
        """
        try:
            # Extract data using correct snake_case field names
            data = request.data
            session_id = data['session_id']  # NOT 'sessionId'
            question_id = data['question_id']  # NOT 'questionId' 
            time_spent = int(data['time_spent'])  # NOT 'timeSpent'
            visit_start_time = data.get('visit_start_time')
            visit_end_time = data.get('visit_end_time')
            
            logger.info(f"✅ Successfully extracted: session_id={session_id}, question_id={question_id}, time_spent={time_spent}")
            
            # Validate required fields
            if not session_id or not question_id or time_spent is None:
                return Response(
                    {"error": "session_id, question_id, and time_spent are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get session and ensure it belongs to authenticated user
            try:
                session = TestSession.objects.get(
                    id=session_id,
                    student_id=request.user.student_id
                )
            except TestSession.DoesNotExist:
                return Response(
                    {"error": "Test session not found or access denied"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate question exists
            try:
                question = Question.objects.get(id=question_id)
            except Question.DoesNotExist:
                return Response(
                    {"error": "Question not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get or create TestAnswer record
            test_answer, created = TestAnswer.objects.get_or_create(
                session=session,
                question=question,
                defaults={
                    'selected_answer': None,
                    'is_correct': False,
                    'time_taken': 0,
                    'answered_at': None,
                    'marked_for_review': False,
                    'visit_count': 1  # Set to 1 for first visit
                }
            )
            
            # Update visit count - increment on each visit (including first time)
            if not created:
                # If the record already existed, increment visit count
                test_answer.visit_count = (test_answer.visit_count or 1) + 1
            # If created=True, visit_count is already set to 1 in defaults
            
            # Update time tracking - accumulate all visit times
            current_time = test_answer.time_taken or 0
            test_answer.time_taken = current_time + time_spent
            
            # Update answered_at if this is the first time logging for this question
            if not test_answer.answered_at and visit_end_time:
                try:
                    test_answer.answered_at = parse_datetime(visit_end_time)
                except (ValueError, TypeError):
                    test_answer.answered_at = timezone.now()
            elif not test_answer.answered_at:
                test_answer.answered_at = timezone.now()
            
            test_answer.save(update_fields=['time_taken', 'answered_at', 'visit_count'])
            
            logger.info(f"✅ Successfully logged {time_spent} seconds for question {question_id} in session {session_id}. Total time: {test_answer.time_taken}")
            
            return Response({
                "status": "success",
                "message": f"Logged {time_spent} seconds for question {question_id}",
                "totalTime": test_answer.time_taken,
                "visitCount": test_answer.visit_count,
                "questionId": question_id,
                "sessionId": session_id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in log_time: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
