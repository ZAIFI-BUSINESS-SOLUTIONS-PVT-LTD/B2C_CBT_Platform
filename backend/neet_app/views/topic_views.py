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
