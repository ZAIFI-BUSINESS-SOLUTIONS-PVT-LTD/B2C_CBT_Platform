import logging
import random
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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
    """
    queryset = TestSession.objects.all().order_by('-start_time')
    serializer_class = TestSessionSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return TestSessionCreateSerializer
        return TestSessionSerializer

    def create(self, request, *args, **kwargs):
        """
        Creates a new test session and provides questions.
        Replicates POST /api/test-sessions logic.
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data

            selected_topic_ids_str = validated_data.get('selected_topics')
            time_limit = validated_data.get('time_limit')
            requested_question_count = validated_data.get('question_count')

            try:
                topic_ids = [int(topic_id) for topic_id in selected_topic_ids_str]
            except (ValueError, TypeError):
                return Response(
                    {"error": "Selected topic IDs must be integers."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            all_questions = list(Question.objects.filter(topic_id__in=topic_ids))
            random.shuffle(all_questions)

            if requested_question_count is not None:
                selected_questions = all_questions[:requested_question_count]
            else:
                selected_questions = all_questions

            if not selected_questions:
                return Response(
                    {"error": "No questions found for the selected topics."}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            session = TestSession.objects.create(
                selected_topics=selected_topic_ids_str,
                time_limit=time_limit,
                question_count=requested_question_count,
                total_questions=len(selected_questions),
                start_time=timezone.now(),
                is_completed=False,
            )

            session_data = TestSessionSerializer(session).data
            questions_data = QuestionForTestSerializer(selected_questions, many=True).data

            return Response({
                'session': session_data,
                'questions': questions_data
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
        """
        session = get_object_or_404(TestSession, pk=pk)

        try:
            topic_ids = [int(topic_id) for topic_id in session.selected_topics]
        except ValueError:
            return Response(
                {"error": "Invalid topic IDs stored in session."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        all_questions_for_topics = list(Question.objects.filter(topic_id__in=topic_ids))
        random.shuffle(all_questions_for_topics)

        selected_questions = all_questions_for_topics[:session.total_questions]

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
        Replicates POST /api/test-sessions/:id/submit logic.
        """
        session = get_object_or_404(TestSession.objects.select_related(), pk=pk)

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

        question_map = {
            q.id: q for q in Question.objects.filter(topic_id__in=session_topic_ids).select_related('topic')
        }

        for answer in answers:
            question = question_map.get(answer.question.id)
            if not question:
                logger.warning(f"Question ID {answer.question.id} not found for answer {answer.id} in session {session.id}")
                continue

            is_correct = False
            if answer.selected_answer is not None:
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
        unanswered_questions_count += total_questions_in_session - answered_questions_count

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

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """
        Retrieves the results for a completed test session.
        Replicates GET /api/test-sessions/:id/results logic.
        """
        session = get_object_or_404(TestSession.objects.select_related(), pk=pk)

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

        question_map = {
            q.id: q for q in Question.objects.filter(topic_id__in=session_topic_ids).select_related('topic')
        }

        for answer in answers:
            question = question_map.get(answer.question.id)
            if not question:
                logger.warning(f"Question ID {answer.question.id} not found for answer {answer.id} in session {session.id}")
                continue

            is_correct = answer.is_correct

            if is_correct:
                correct_answers_count += 1
            elif answer.selected_answer is not None:
                incorrect_answers_count += 1
            else:
                unanswered_questions_count += 1

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
        unanswered_questions_count += total_questions_in_session - answered_questions_count

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
