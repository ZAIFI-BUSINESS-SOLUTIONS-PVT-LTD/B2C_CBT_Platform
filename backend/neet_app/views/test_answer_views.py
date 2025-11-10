from rest_framework import status, viewsets
from rest_framework.response import Response
from ..errors import AppError, ValidationError as AppValidationError
from ..error_codes import ErrorCodes
from rest_framework.permissions import IsAuthenticated

from ..models import TestAnswer
from ..serializers import TestAnswerCreateSerializer, TestAnswerSerializer


class TestAnswerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing individual test answers.
    Corresponds to /api/test-answers in Node.js.
    Only allows access to answers from user's own test sessions.
    """
    serializer_class = TestAnswerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter test answers by authenticated user's sessions"""
        if not hasattr(self.request.user, 'student_id'):
            return TestAnswer.objects.none()
        return TestAnswer.objects.filter(
            session__student_id=self.request.user.student_id
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return TestAnswerCreateSerializer
        return TestAnswerSerializer

    def create(self, request, *args, **kwargs):
        """
        Submits or updates a single test answer (upsert logic).
        Supports both MCQ (selected_answer) and NVT (text_answer) questions.
        """
        # Pass request context to serializer for authentication validation
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        session = validated_data.pop('session')
        question = validated_data.pop('question')
        
        # Determine question type
        question_type = getattr(question, 'question_type', None) or 'Blank'  # Default to MCQ

        # Prepare defaults for update_or_create
        defaults = {
            'marked_for_review': validated_data.get('marked_for_review', False),
        }
        
        # Handle answer based on question type
        if question_type == 'NVT':
            # NVT question - store text answer and evaluate
            text_answer = validated_data.get('text_answer')
            defaults['text_answer'] = text_answer
            defaults['selected_answer'] = None  # Clear MCQ answer for NVT
            
            # Auto-evaluate if enabled and answer provided
            if text_answer:
                from django.conf import settings
                auto_evaluate = settings.NEET_SETTINGS.get('NVT_AUTO_EVALUATE', True)
                if auto_evaluate and question.correct_answer:
                    is_correct = self._evaluate_nvt_answer(text_answer, question.correct_answer)
                    defaults['is_correct'] = is_correct
                else:
                    # Manual grading required or no correct answer set
                    defaults['is_correct'] = None
            else:
                # Unanswered
                defaults['is_correct'] = None
        else:
            # MCQ question - store selected answer
            selected_answer = validated_data.get('selected_answer')
            defaults['selected_answer'] = selected_answer
            defaults['text_answer'] = None  # Clear text answer for MCQ
            
            # Evaluate MCQ correctness if answer provided
            if selected_answer:
                try:
                    defaults['is_correct'] = (str(selected_answer) == str(question.correct_answer))
                except Exception:
                    defaults['is_correct'] = False
            else:
                defaults['is_correct'] = None

        answer, created = TestAnswer.objects.update_or_create(
            session=session,
            question=question,
            defaults=defaults
        )

        # Set answered_at timestamp if answer was provided
        updated_fields = []
        answer_provided = (question_type == 'NVT' and validated_data.get('text_answer')) or \
                         (question_type != 'NVT' and validated_data.get('selected_answer'))
        
        if answer_provided and not answer.answered_at:
            from django.utils import timezone
            answer.answered_at = timezone.now()
            updated_fields.append('answered_at')

        if updated_fields:
            answer.save(update_fields=updated_fields)

        return Response(
            TestAnswerSerializer(answer).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    def _evaluate_nvt_answer(self, student_answer, correct_answer):
        """
        Evaluate NVT answer against correct answer.
        Handles numeric (with tolerance) and string (case-insensitive) comparisons.
        
        Args:
            student_answer: Student's text answer (string)
            correct_answer: Correct answer from Question model (string)
            
        Returns:
            bool: True if answer is correct, False otherwise
        """
        from django.conf import settings
        
        # Strip whitespace from both answers
        student_answer = str(student_answer).strip()
        correct_answer = str(correct_answer).strip()
        
        # Try numeric comparison first
        try:
            student_numeric = float(student_answer)
            correct_numeric = float(correct_answer)
            tolerance = settings.NEET_SETTINGS.get('NVT_NUMERIC_TOLERANCE', 0.01)
            return abs(student_numeric - correct_numeric) <= tolerance
        except (ValueError, TypeError):
            # Not numeric, fall back to string comparison
            case_sensitive = settings.NEET_SETTINGS.get('NVT_CASE_SENSITIVE', False)
            if case_sensitive:
                return student_answer == correct_answer
            else:
                return student_answer.lower() == correct_answer.lower()

    def partial_update(self, request, *args, **kwargs):
        """
        Partially updates an existing test answer.
        Replicates PATCH /api/test-answers/:id logic.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
