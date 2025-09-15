import sentry_sdk
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
        try:
            sentry_sdk.add_breadcrumb(
                message="Getting questions queryset",
                category="questions",
                level="info",
                data={"query_params": dict(self.request.query_params)}
            )
            
            queryset = super().get_queryset()
            topic_ids = self.request.query_params.getlist('topic_ids')
            if topic_ids:
                try:
                    topic_ids_int = [int(tid) for tid in topic_ids]
                    queryset = queryset.filter(topic_id__in=topic_ids_int)
                    
                    sentry_sdk.add_breadcrumb(
                        message="Filtered questions by topic IDs",
                        category="questions",
                        level="info",
                        data={"topic_ids": topic_ids_int, "filtered_count": queryset.count()}
                    )
                    
                except ValueError as e:
                    sentry_sdk.capture_message(
                        "Invalid topic ID provided in question filter",
                        level="warning",
                        extra={"topic_ids": topic_ids}
                    )
                    raise serializers.ValidationError("Invalid topic ID provided. Must be integers.")
            return queryset
        except serializers.ValidationError:
            # Re-raise known validation errors
            raise
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "get_questions_queryset",
                "query_params": dict(self.request.query_params)
            })
            raise
