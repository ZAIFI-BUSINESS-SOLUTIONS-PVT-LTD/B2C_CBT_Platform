from rest_framework import status, viewsets
from rest_framework.response import Response
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
