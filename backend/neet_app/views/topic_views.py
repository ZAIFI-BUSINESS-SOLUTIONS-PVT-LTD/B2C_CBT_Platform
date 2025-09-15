import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Topic, Question
from ..serializers import TopicSerializer
from ..errors import AppError
from ..error_codes import ErrorCodes
from django.db.models import Count

logger = logging.getLogger(__name__)

def initialize_chapter_structure():
    """
    Implement your actual data initialization logic here.
    This function should create your default Topics and Questions.
    """
    print("Executing chapter structure initialization...")
    
    if not Topic.objects.exists():
        physics_topic = Topic.objects.create(
            name="Forces", 
            subject="Physics", 
            icon="icon_physics.png", 
            chapter="Mechanics"
        )
        chemistry_topic = Topic.objects.create(
            name="Chemical Bonding", 
            subject="Chemistry", 
            icon="icon_chemistry.png", 
            chapter="Inorganic"
        )

        Question.objects.create(
            topic=physics_topic,
            question="What is Newton's second law?",
            option_a="F=ma", 
            option_b="E=mc^2", 
            option_c="V=IR", 
            option_d="A=πr²",
            correct_answer="A", 
            explanation="Newton's second law states that the force acting on an object is equal to the mass of that object times its acceleration."
        )
        Question.objects.create(
            topic=chemistry_topic,
            question="Which type of bond involves the sharing of electrons?",
            option_a="Ionic", 
            option_b="Covalent", 
            option_c="Metallic", 
            option_d="Hydrogen",
            correct_answer="B", 
            explanation="Covalent bonds are formed when atoms share electrons."
        )
        logger.info("Sample topics and questions initialized.")
    else:
        logger.info("Topics already exist. Skipping initialization.")


class TopicViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing topics.
    Corresponds to /api/topics in Node.js.
    """
    queryset = Topic.objects.all().order_by('id')
    serializer_class = TopicSerializer

    def list(self, request, *args, **kwargs):
        """
        GET /api/topics - Retrieve all available topics.
        Replicates Node.js auto-initialization logic if no topics exist.
        """
        topics = self.get_queryset()

        if not topics.exists():
            logger.info("No topics found. Initializing chapter structure...")
            try:
                initialize_chapter_structure()
                topics = self.get_queryset()
                logger.info(f"Initialized {topics.count()} topics.")
            except Exception as e:
                logger.error(f"Error during topic initialization: {e}")
                raise AppError(code=ErrorCodes.SERVER_ERROR, message='Failed to initialize topics', details={'exception': str(e)})

        serializer = self.get_serializer(topics, many=True)
        return Response({
            'count': topics.count(),
            'next': None,
            'previous': None,
            'results': serializer.data
        })

    def get_queryset(self):
        queryset = super().get_queryset()
        subject = self.request.query_params.get('subject', None)
        if subject:
            queryset = queryset.filter(subject__iexact=subject)
        return queryset

    @action(detail=False, methods=['get'], url_path='question-counts')
    def question_counts(self, request):
        """
        GET /api/topics/question-counts/
        Returns exact question counts per topic.

        Query params:
        - topic_ids: Can be provided multiple times (?topic_ids=1&topic_ids=2...). If omitted, counts for all topics are returned.
        - subject (optional): Case-insensitive filter by subject name.
        - chapters (optional): Comma-separated list of chapter names to filter topics.

        Response:
        {
          "counts": { "1": 12, "2": 5, ... }
        }
        """
        try:
            topic_ids = request.query_params.getlist('topic_ids')
            subject = request.query_params.get('subject')
            chapters_param = request.query_params.get('chapters')

            topic_qs = Topic.objects.all()
            if subject:
                topic_qs = topic_qs.filter(subject__iexact=subject)
            if chapters_param:
                chapters = [c.strip() for c in chapters_param.split(',') if c.strip()]
                if chapters:
                    topic_qs = topic_qs.filter(chapter__in=chapters)

            if topic_ids:
                try:
                    topic_ids_int = [int(tid) for tid in topic_ids]
                except ValueError:
                    return Response({
                        'error': 'INVALID_INPUT',
                        'message': 'All topic_ids must be integers.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                topic_qs = topic_qs.filter(id__in=topic_ids_int)

            # If no topics found after filtering, return empty counts
            if not topic_qs.exists():
                return Response({'counts': {}}, status=status.HTTP_200_OK)

            # Aggregate counts from Question model
            counts_qs = (
                Question.objects
                .filter(topic_id__in=topic_qs.values_list('id', flat=True))
                .values('topic_id')
                .annotate(total=Count('id'))
            )

            counts_map = {str(row['topic_id']): int(row['total']) for row in counts_qs}

            # Ensure topics with zero questions are included as 0
            for tid in topic_qs.values_list('id', flat=True):
                tid_str = str(tid)
                if tid_str not in counts_map:
                    counts_map[tid_str] = 0

            return Response({'counts': counts_map}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Failed to fetch question counts per topic: %s', str(e))
            raise AppError(code=ErrorCodes.SERVER_ERROR, message='Failed to fetch topic question counts', details={'exception': str(e)})

    @action(detail=False, methods=['delete'])
    def delete_all(self, request):
        """
        DELETE /api/topics - Deletes all existing topics and then re-initializes them.
        Matches Node.js DELETE /api/topics logic exactly.
        """
        try:
            with transaction.atomic():
                initial_count = Topic.objects.all().count()
                Topic.objects.all().delete()
                logger.info(f"{initial_count} topics deleted for reset.")

                initialize_chapter_structure()
                new_topics = self.get_queryset()
                logger.info(f"Re-initialized {new_topics.count()} topics.")

            serializer = self.get_serializer(new_topics, many=True)
            return Response({
                'message': "Topics reset successfully",
                'count': new_topics.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error resetting and re-initializing topics: {e}")
            raise AppError(code=ErrorCodes.SERVER_ERROR, message='Failed to reset topics', details={'exception': str(e)})
