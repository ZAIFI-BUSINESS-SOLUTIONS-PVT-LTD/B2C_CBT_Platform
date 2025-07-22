from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import ReviewComment
from ..serializers import ReviewCommentSerializer


class ReviewCommentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing review comments.
    Corresponds to /api/review-comments in Node.js.
    """
    queryset = ReviewComment.objects.all()
    serializer_class = ReviewCommentSerializer

    @action(detail=False, methods=['get'], url_path='session/(?P<session_id>[^/.]+)')
    def by_session(self, request, session_id=None):
        """
        Retrieves review comments for a specific session.
        Replicates GET /api/review-comments/:sessionId logic.
        """
        comments = ReviewComment.objects.filter(session_id=session_id)
        serializer = self.get_serializer(comments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='session/(?P<session_id>[^/.]+)/question/(?P<question_id>[^/.]+)')
    def by_session_question(self, request, session_id=None, question_id=None):
        """
        Retrieves review comments for a specific question within a session.
        Replicates GET /api/review-comments/:sessionId/:questionId logic.
        """
        comments = ReviewComment.objects.filter(session_id=session_id, question_id=question_id)
        serializer = self.get_serializer(comments, many=True)
        return Response(serializer.data)
