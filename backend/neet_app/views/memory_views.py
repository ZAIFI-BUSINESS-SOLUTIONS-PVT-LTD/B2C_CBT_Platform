"""
Memory Views for NEET AI Tutor
Handles chat memory management and retrieval
"""
import sentry_sdk
from rest_framework import status, viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from ..models import ChatMemory
from ..serializers import ChatMemorySerializer, ChatMemoryCreateSerializer
from ..jwt_authentication import StudentJWTAuthentication
from ..errors import AppError
from ..error_codes import ErrorCodes


class ChatMemoryViewSet(mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    """
    ViewSet for managing chat memories
    Provides CRUD operations for chat memories with proper authentication
    """
    serializer_class = ChatMemorySerializer
    authentication_classes = [StudentJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return chat memories for the authenticated student only"""
        try:
            sentry_sdk.add_breadcrumb(
                message="Getting chat memories for student",
                category="memory",
                level="info",
                data={"student_id": getattr(self.request.user, 'student_id', None)}
            )
            
            if hasattr(self.request.user, 'student_id'):
                return ChatMemory.objects.filter(
                    student_id=self.request.user.student_id
                ).order_by('-updated_at')
            return ChatMemory.objects.none()
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "get_chat_memories",
                "user": str(self.request.user)
            })
            return ChatMemory.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Create a new chat memory for the authenticated student"""
        try:
            sentry_sdk.add_breadcrumb(
                message="Creating new chat memory",
                category="memory",
                level="info",
                data={"student_id": getattr(request.user, 'student_id', None)}
            )
            
            # Validate input
            serializer = ChatMemoryCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Get student_id from authenticated user
            student_id = request.user.student_id
            
            # Create chat memory
            memory_data = serializer.validated_data
            chat_memory = ChatMemory.objects.create(
                student_id=student_id,
                memory_type=memory_data.get('memory_type', 'long_term'),
                content=memory_data.get('content', {}),
                source_session_id=memory_data.get('source_session_id'),
                key_tags=memory_data.get('key_tags', []),
                confidence_score=memory_data.get('confidence_score', 1.0)
            )
            
            sentry_sdk.add_breadcrumb(
                message="Chat memory created successfully",
                category="memory",
                level="info",
                data={"memory_id": chat_memory.id, "student_id": student_id}
            )
            
            # Return serialized response
            response_serializer = ChatMemorySerializer(chat_memory)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "create_chat_memory",
                "student_id": getattr(request.user, 'student_id', None),
                "request_data": request.data
            })
            raise AppError(
                code=ErrorCodes.SERVER_ERROR,
                message='Failed to create chat memory'
            )
    
    def update(self, request, *args, **kwargs):
        """Update a chat memory (owner only)"""
        try:
            sentry_sdk.add_breadcrumb(
                message="Updating chat memory",
                category="memory",
                level="info",
                data={"student_id": getattr(request.user, 'student_id', None)}
            )
            
            # Get the memory and ensure it belongs to the user
            memory = self.get_object()
            
            # Validate input
            serializer = ChatMemoryCreateSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            
            # Update fields
            for field, value in serializer.validated_data.items():
                setattr(memory, field, value)
            
            memory.save()
            
            sentry_sdk.add_breadcrumb(
                message="Chat memory updated successfully",
                category="memory",
                level="info",
                data={"memory_id": memory.id}
            )
            
            # Return updated memory
            response_serializer = ChatMemorySerializer(memory)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except ChatMemory.DoesNotExist:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message='Chat memory not found'
            )
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "update_chat_memory",
                "student_id": getattr(request.user, 'student_id', None)
            })
            raise AppError(
                code=ErrorCodes.SERVER_ERROR,
                message='Failed to update chat memory'
            )
    
    def destroy(self, request, *args, **kwargs):
        """Delete a chat memory (owner only)"""
        try:
            sentry_sdk.add_breadcrumb(
                message="Deleting chat memory",
                category="memory",
                level="info",
                data={"student_id": getattr(request.user, 'student_id', None)}
            )
            
            # Get the memory and ensure it belongs to the user
            memory = self.get_object()
            memory_id = memory.id
            
            # Delete the memory
            memory.delete()
            
            sentry_sdk.add_breadcrumb(
                message="Chat memory deleted successfully",
                category="memory",
                level="info",
                data={"memory_id": memory_id}
            )
            
            return Response({
                'success': True,
                'message': 'Chat memory deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except ChatMemory.DoesNotExist:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message='Chat memory not found'
            )
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "delete_chat_memory",
                "student_id": getattr(request.user, 'student_id', None)
            })
            raise AppError(
                code=ErrorCodes.SERVER_ERROR,
                message='Failed to delete chat memory'
            )
    
    @action(detail=False, methods=['get'], url_path='long-term')
    def get_long_term_memories(self, request):
        """Get only long-term memories for the authenticated student"""
        try:
            sentry_sdk.add_breadcrumb(
                message="Getting long-term memories",
                category="memory",
                level="info",
                data={"student_id": getattr(request.user, 'student_id', None)}
            )
            
            memories = ChatMemory.objects.filter(
                student_id=request.user.student_id,
                memory_type='long_term'
            ).order_by('-confidence_score', '-updated_at')
            
            # Limit to top 10 most confident and recent memories
            memories = memories[:10]
            
            serializer = ChatMemorySerializer(memories, many=True)
            
            return Response({
                'memories': serializer.data,
                'count': len(serializer.data)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "get_long_term_memories",
                "student_id": getattr(request.user, 'student_id', None)
            })
            raise AppError(
                code=ErrorCodes.SERVER_ERROR,
                message='Failed to retrieve long-term memories'
            )