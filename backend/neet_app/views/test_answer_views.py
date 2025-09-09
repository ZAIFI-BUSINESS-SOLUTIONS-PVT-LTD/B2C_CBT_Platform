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
        Replicates POST /api/test-answers logic.
        """
        # Pass request context to serializer for authentication validation
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        session = validated_data.pop('session')
        question = validated_data.pop('question')

        answer, created = TestAnswer.objects.update_or_create(
            session=session,
            question=question,
            defaults={
                'selected_answer': validated_data.get('selected_answer'),
                'marked_for_review': validated_data.get('marked_for_review', False),
                # NOTE: time_taken is now handled by the separate time-tracking endpoint
                # We don't update time_taken here to avoid conflicts
            }
        )

        # If selected_answer provided, set answered_at (if not already) and compute is_correct immediately
        sel = validated_data.get('selected_answer', None)
        updated_fields = []
        if sel is not None:
            if not answer.answered_at:
                from django.utils import timezone
                answer.answered_at = timezone.now()
                updated_fields.append('answered_at')
            # Determine correctness
            try:
                correct_flag = (str(sel) == str(question.correct_answer))
            except Exception:
                correct_flag = False
            if answer.is_correct != correct_flag:
                answer.is_correct = correct_flag
                updated_fields.append('is_correct')

        if updated_fields:
            answer.save(update_fields=updated_fields)

        return Response(
            TestAnswerSerializer(answer).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

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
