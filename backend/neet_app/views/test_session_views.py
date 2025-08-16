import logging
import random
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..models import Question, TestSession, TestAnswer
from ..serializers import (
    QuestionForTestSerializer, TestSessionCreateSerializer, 
    TestSessionSerializer
)

logger = logging.getLogger(__name__)


class TestSessionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing test sessions.
    Corresponds to /api/test-sessions in Node.js.
    Only returns sessions for the authenticated user.
    """
    serializer_class = TestSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter test sessions by authenticated user"""
        logger.info(f"get_queryset - User: {self.request.user}")
        logger.info(f"User type: {type(self.request.user)}")
        logger.info(f"User authenticated: {self.request.user.is_authenticated}")
        
        if not hasattr(self.request.user, 'student_id'):
            logger.warning(f"User has no student_id attribute: {self.request.user}")
            return TestSession.objects.none()
            
        logger.info(f"Filtering by student_id: {self.request.user.student_id}")
        queryset = TestSession.objects.filter(
            student_id=self.request.user.student_id
        ).order_by('-start_time')
        
        logger.info(f"Queryset count: {queryset.count()}")
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return TestSessionCreateSerializer
        return TestSessionSerializer

    def create(self, request, *args, **kwargs):
        """
        Creates a new test session with student authentication.
        Enhanced version with time-based or count-based question selection.
        Backward compatible with existing question_count requests.
        """
        try:
            # Pass request context to serializer for authenticated user access
            serializer = self.get_serializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            
            # The serializer handles session creation with student validation
            # and question count calculation (either from direct input or time calculation)
            session = serializer.save()
            
            # Get questions for the session
            # session.question_count is now either:
            # 1. Direct question count (existing behavior)
            # 2. Calculated from time limit (new behavior - 1 question per minute)
            from .utils import generate_questions_for_topics
            selected_questions = generate_questions_for_topics(
                session.selected_topics, 
                session.question_count
            )

            # Create TestAnswer records for all assigned questions (initially unanswered)
            test_answers = []
            for question in selected_questions:
                test_answers.append(TestAnswer(
                    session=session,
                    question=question,
                    selected_answer=None,
                    is_correct=False,
                    marked_for_review=False,
                    time_taken=0
                ))
            TestAnswer.objects.bulk_create(test_answers)

            session_data = TestSessionSerializer(session).data
            questions_data = QuestionForTestSerializer(selected_questions, many=True).data

            return Response({
                'session': session_data,
                'questions': questions_data,
                'message': f'Test session created for student {session.student_id}'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating test session: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to create test session: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """
        Retrieves a test session and its questions.
        Replicates GET /api/test-sessions/:id logic.
        Only allows access to user's own sessions.
        """
        # Debug logging
        logger.info(f"Retrieve request - User: {request.user}, Session ID: {pk}")
        logger.info(f"User authenticated: {request.user.is_authenticated}")
        logger.info(f"User student_id: {getattr(request.user, 'student_id', 'No student_id')}")
        
        # Ensure only authenticated user's sessions are accessible
        try:
            session = get_object_or_404(
                self.get_queryset(), 
                pk=pk
            )
            logger.info(f"Session found: {session.id}, belongs to: {session.student_id}")
        except Exception as e:
            logger.error(f"Session retrieval failed: {e}")
            raise

        try:
            topic_ids = [int(topic_id) for topic_id in session.selected_topics]
        except ValueError:
            return Response(
                {"error": "Invalid topic IDs stored in session."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Get questions from TestAnswer table (the exact questions assigned to this session)
        test_answers = TestAnswer.objects.filter(session=session).select_related('question')
        selected_questions = [answer.question for answer in test_answers]

        session_data = TestSessionSerializer(session).data
        questions_data = QuestionForTestSerializer(selected_questions, many=True).data

        return Response({
            'session': session_data,
            'questions': questions_data
        })

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Submits a test session, marks it as complete, calculates results,
        and updates individual answer correctness.
        Only allows access to user's own sessions.
        """
        # Ensure only authenticated user's sessions are accessible
        session = get_object_or_404(
            self.get_queryset().select_related(), 
            pk=pk
        )

        session.is_completed = True
        session.end_time = timezone.now()
        session.save(update_fields=['is_completed', 'end_time'])

        answers = TestAnswer.objects.filter(session=session).select_related('question').prefetch_related('question__topic')

        total_questions_in_session = session.total_questions
        correct_answers_count = 0
        incorrect_answers_count = 0
        unanswered_questions_count = 0

        detailed_answers = []
        subject_performance = {}

        try:
            session_topic_ids = [int(tid) for tid in session.selected_topics]
        except ValueError:
            return Response(
                {"error": "Invalid topic IDs stored in session."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Get questions and ensure they are cleaned
        questions = Question.objects.filter(topic_id__in=session_topic_ids).select_related('topic')
        question_map = {}
        for q in questions:
            # Apply cleaning if LaTeX patterns or simple chemical notations are found
            needs_cleaning = any(pattern in q.question for pattern in ['\\', '$', '^{', '_{', '\\frac', '^ -', '^ +', '^-', '^+', 'x 10^'])
            if not needs_cleaning:
                # Also check options for patterns
                all_options = q.option_a + q.option_b + q.option_c + q.option_d
                needs_cleaning = any(pattern in all_options for pattern in ['\\', '$', '^{', '_{', '\\frac', '^ -', '^ +', '^-', '^+', 'x 10^'])
            if not needs_cleaning and q.explanation:
                # Also check explanation for patterns
                needs_cleaning = any(pattern in q.explanation for pattern in ['\\', '$', '^{', '_{', '\\frac', '^ -', '^ +', '^-', '^+', 'x 10^'])
            
            if needs_cleaning:
                from .utils import clean_mathematical_text
                q.question = clean_mathematical_text(q.question)
                q.option_a = clean_mathematical_text(q.option_a)
                q.option_b = clean_mathematical_text(q.option_b)
                q.option_c = clean_mathematical_text(q.option_c)
                q.option_d = clean_mathematical_text(q.option_d)
                if q.explanation:
                    q.explanation = clean_mathematical_text(q.explanation)
                q.save(update_fields=['question', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation'])
            question_map[q.id] = q

        # Process all TestAnswer objects (now includes all assigned questions)
        for answer in answers:
            question = answer.question
            is_correct = False
            if answer.selected_answer is not None and str(answer.selected_answer).strip() != '':
                if str(answer.selected_answer) == str(question.correct_answer):
                    correct_answers_count += 1
                    is_correct = True
                else:
                    incorrect_answers_count += 1
            else:
                unanswered_questions_count += 1

            answer.is_correct = is_correct
            answer.save(update_fields=['is_correct'])

            detailed_answers.append({
                'questionId': question.id,
                'question': question.question,
                'selectedAnswer': answer.selected_answer,
                'correctAnswer': question.correct_answer,
                'isCorrect': is_correct,
                'explanation': question.explanation,
                'optionA': question.option_a,
                'optionB': question.option_b,
                'optionC': question.option_c,
                'optionD': question.option_d,
                'markedForReview': answer.marked_for_review,
                'timeTaken': answer.time_taken
            })

            subject_name = question.topic.subject
            if subject_name not in subject_performance:
                subject_performance[subject_name] = {'correct': 0, 'total': 0}
            subject_performance[subject_name]['total'] += 1
            if is_correct:
                subject_performance[subject_name]['correct'] += 1

        answered_questions_count = len(answers)

        score_percentage = (correct_answers_count / total_questions_in_session) * 100 if total_questions_in_session > 0 else 0

        time_taken_seconds = 0
        if session.start_time and session.end_time:
            time_taken_seconds = int((session.end_time - session.start_time).total_seconds())

        formatted_subject_performance = []
        for subject_name, data in subject_performance.items():
            formatted_subject_performance.append({
                'subject': subject_name,
                'correct': data['correct'],
                'total': data['total'],
                'accuracy': (data['correct'] / data['total']) * 100 if data['total'] > 0 else 0
            })

        results = {
            'session_id': session.id,
            'total_questions': total_questions_in_session,
            'correct_answers': correct_answers_count,
            'incorrect_answers': incorrect_answers_count,
            'unanswered_questions': unanswered_questions_count,
            'score_percentage': round(score_percentage, 2),
            'time_taken': time_taken_seconds,
            'subject_performance': formatted_subject_performance,
            'detailed_answers': detailed_answers
        }

        return Response(results)

    @action(detail=True, methods=['post'])
    def quit(self, request, pk=None):
        """
        Quits a test session and marks it as incomplete.
        Only allows access to user's own sessions.
        """
        # Ensure only authenticated user's sessions are accessible
        session = get_object_or_404(
            self.get_queryset().select_related(), 
            pk=pk
        )

        # Check if the test is already completed
        if session.is_completed:
            return Response(
                {"error": "Cannot quit a completed test session."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark the session as incomplete and set end time
        session.is_completed = False  # Explicitly mark as incomplete
        session.end_time = timezone.now()
        session.save(update_fields=['is_completed', 'end_time'])

        logger.info(f"Test session {session.id} marked as incomplete (quit by user)")

        return Response({
            "message": "Test session has been marked as incomplete.",
            "session_id": session.id,
            "status": "incomplete"
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """
        Retrieves the results for a completed test session.
        Only allows access to user's own sessions.
        """
        # Ensure only authenticated user's sessions are accessible
        session = get_object_or_404(
            self.get_queryset().select_related(), 
            pk=pk
        )

        answers = TestAnswer.objects.filter(session=session).select_related('question').prefetch_related('question__topic')

        total_questions_in_session = session.total_questions
        correct_answers_count = 0
        incorrect_answers_count = 0
        unanswered_questions_count = 0

        detailed_answers = []
        subject_performance = {}

        try:
            session_topic_ids = [int(tid) for tid in session.selected_topics]
        except ValueError:
            return Response(
                {"error": "Invalid topic IDs stored in session."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Process all TestAnswer objects (now includes all assigned questions)
        for answer in answers:
            question = answer.question
            is_correct = answer.is_correct
            if answer.selected_answer is None or str(answer.selected_answer).strip() == '':
                unanswered_questions_count += 1
            elif is_correct:
                correct_answers_count += 1
            else:
                incorrect_answers_count += 1

            detailed_answers.append({
                'question_id': question.id,
                'question': question.question,
                'selected_answer': answer.selected_answer,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'explanation': question.explanation,
                'option_a': question.option_a,
                'option_b': question.option_b,
                'option_c': question.option_c,
                'option_d': question.option_d,
                'marked_for_review': answer.marked_for_review,
                'time_taken': answer.time_taken
            })

            subject_name = question.topic.subject
            if subject_name not in subject_performance:
                subject_performance[subject_name] = {'correct': 0, 'total': 0}
            subject_performance[subject_name]['total'] += 1
            if is_correct:
                subject_performance[subject_name]['correct'] += 1

        answered_questions_count = len(answers)

        score_percentage = (correct_answers_count / total_questions_in_session) * 100 if total_questions_in_session > 0 else 0

        time_taken_seconds = 0
        if session.start_time and session.end_time:
            time_taken_seconds = int((session.end_time - session.start_time).total_seconds())

        formatted_subject_performance = []
        for subject_name, data in subject_performance.items():
            formatted_subject_performance.append({
                'subject': subject_name,
                'correct': data['correct'],
                'total': data['total'],
                'accuracy': (data['correct'] / data['total']) * 100 if data['total'] > 0 else 0
            })

        results = {
            'session_id': session.id,
            'total_questions': total_questions_in_session,
            'correct_answers': correct_answers_count,
            'incorrect_answers': incorrect_answers_count,
            'unanswered_questions': unanswered_questions_count,
            'score_percentage': round(score_percentage, 2),
            'time_taken': time_taken_seconds,
            'subject_performance': formatted_subject_performance,
            'detailed_answers': detailed_answers
        }

        return Response(results)
