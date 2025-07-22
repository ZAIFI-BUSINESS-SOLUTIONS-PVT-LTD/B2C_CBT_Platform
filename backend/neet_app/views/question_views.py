from rest_framework import serializers, viewsets

from ..models import Question
from ..serializers import QuestionSerializer


class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for retrieving questions. Read-only.
    Corresponds to /api/questions in Node.js.
    """
    queryset = Question.objects.all().order_by('id')
    serializer_class = QuestionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        topic_ids = self.request.query_params.getlist('topic_ids')
        if topic_ids:
            try:
                topic_ids_int = [int(tid) for tid in topic_ids]
                queryset = queryset.filter(topic_id__in=topic_ids_int)
            except ValueError:
                raise serializers.ValidationError("Invalid topic ID provided. Must be integers.")
        return queryset
