"""
Chatbot Views for NEET AI Tutor
Handles chat session creation, message processing, and history retrieval
"""
import uuid
import sentry_sdk
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import ChatSession, ChatMessage, ChatMemory, StudentProfile
from ..serializers import (
    ChatSessionSerializer, ChatMessageSerializer, 
    ChatMessageCreateSerializer, ChatSessionCreateSerializer,
    ChatMemorySerializer, ChatMemoryCreateSerializer
)
from ..services.chatbot_service_refactored import NeetChatbotService
from ..jwt_authentication import StudentJWTAuthentication
from ..errors import AppError, NotFoundError, ValidationError as AppValidationError
from ..error_codes import ErrorCodes


class ChatSessionViewSet(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.UpdateModelMixin,
                        mixins.DestroyModelMixin,
                        viewsets.GenericViewSet):
    """
    ViewSet for managing chat sessions
    Provides CRUD operations for chat sessions with proper authentication
    """
    serializer_class = ChatSessionSerializer
    authentication_classes = [StudentJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'chat_session_id'  # Use chat_session_id instead of pk
    
    def _generate_session_title_from_message(self, message):
        """Generate a session title from the first message, like ChatGPT"""
        if not message:
            return 'New Chat'
        
        # Clean and truncate message
        trimmed = message.strip()
        if len(trimmed) > 40:
            trimmed = trimmed[:40].strip() + '...'
        
        # Capitalize first letter
        if trimmed:
            return trimmed[0].upper() + trimmed[1:]
        return 'New Chat'
    
    def get_queryset(self):
        """Return chat sessions for the authenticated student only"""
        try:
            sentry_sdk.add_breadcrumb(
                message="Getting chat sessions for student",
                category="chat",
                level="info",
                data={"student_id": getattr(self.request.user, 'student_id', None)}
            )
            
            if hasattr(self.request.user, 'student_id'):
                return ChatSession.objects.filter(
                    student_id=self.request.user.student_id,
                    is_active=True
                ).order_by('-updated_at')
            return ChatSession.objects.none()
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "get_chat_sessions",
                "user": str(self.request.user)
            })
            return ChatSession.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Create a new chat session for the authenticated student"""
        try:
            sentry_sdk.add_breadcrumb(
                message="Creating new chat session",
                category="chat",
                level="info",
                data={"student_id": getattr(request.user, 'student_id', None)}
            )
            
            # Validate input
            serializer = ChatSessionCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Get student_id from authenticated user
            student_id = request.user.student_id
            
            # Generate unique chat session ID
            chat_session_id = str(uuid.uuid4())
            
            # Create chat session directly
            chat_session = ChatSession.objects.create(
                chat_session_id=chat_session_id,
                student_id=student_id,
                session_title=serializer.validated_data.get('session_title', 'New Chat'),
                is_active=True
            )
            
            sentry_sdk.add_breadcrumb(
                message="Chat session created successfully",
                category="chat",
                level="info",
                data={"chat_session_id": chat_session_id, "student_id": student_id}
            )
            
            # Return serialized response
            response_serializer = ChatSessionSerializer(chat_session)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "create_chat_session",
                "student_id": getattr(request.user, 'student_id', None),
                "request_data": request.data
            })
            raise AppError(
                code=ErrorCodes.SERVER_ERROR,
                message='Failed to create chat session'
            )
    
    @action(detail=True, methods=['post'], url_path='send-message')
    def send_message(self, request, chat_session_id=None):
        """Send a message in the chat session"""
        print(f"🔗 Chatbot API called - Session: {chat_session_id}, Student: {request.user.student_id}")
        
        try:
            sentry_sdk.add_breadcrumb(
                message="Processing chatbot message",
                category="chat",
                level="info",
                data={
                    "chat_session_id": chat_session_id, 
                    "student_id": getattr(request.user, 'student_id', None)
                }
            )
            
            # Get the chat session
            try:
                chat_session = ChatSession.objects.get(
                    chat_session_id=chat_session_id,
                    student_id=request.user.student_id,
                    is_active=True
                )
            except ChatSession.DoesNotExist:
                sentry_sdk.capture_message(
                    "Chat session not found for message",
                    level="warning",
                    extra={
                        "chat_session_id": chat_session_id,
                        "student_id": getattr(request.user, 'student_id', None)
                    }
                )
                raise AppError(
                    code=ErrorCodes.CHAT_SESSION_NOT_FOUND,
                    message='Chat session not found'
                )
            
            # Validate message data
            message_serializer = ChatMessageCreateSerializer(
                data={'session_id': chat_session_id, 'message': request.data.get('message', '')},
                context={'request': request}
            )
            message_serializer.is_valid(raise_exception=True)
            
            # Process message with chatbot service  
            user_message = message_serializer.validated_data['message']
            print(f"📝 Processing message: '{user_message}'")
            
            sentry_sdk.add_breadcrumb(
                message="User message validated",
                category="chat",
                level="info",
                data={"message_length": len(user_message)}
            )
            
            # Update session title if this is the first message (no existing messages)
            if chat_session.messages.count() == 0:
                # Generate title from first message like ChatGPT
                title = self._generate_session_title_from_message(user_message)
                chat_session.session_title = title
                chat_session.save()
                print(f"📋 Updated session title to: '{title}'")
                
                sentry_sdk.add_breadcrumb(
                    message="Updated session title",
                    category="chat",
                    level="info",
                    data={"new_title": title}
                )
            
            try:
                chatbot_service = NeetChatbotService()
            except Exception as e:
                sentry_sdk.capture_exception(e, extra={
                    "action": "instantiate_chatbot_service",
                    "chat_session_id": chat_session_id,
                    "student_id": request.user.student_id
                })
                raise AppError(
                    code=ErrorCodes.SERVER_ERROR,
                    message='AI service is currently unavailable'
                )

            # If service instantiated but AI components aren't available, fail gracefully
            if not getattr(chatbot_service, 'ai_available', False):
                sentry_sdk.add_breadcrumb(
                    message="AI service not available for request",
                    category="chat",
                    level="warning",
                    data={"chat_session_id": chat_session_id, "student_id": request.user.student_id}
                )
                raise AppError(
                    code=ErrorCodes.SERVER_ERROR,
                    message='AI service is currently unavailable'
                )
            
            # Support optional async processing: if client passes async=true, enqueue Celery task and return task_id
            async_flag = request.data.get('async', False) or request.query_params.get('async') == 'true'
            if async_flag:
                try:
                    from ..tasks import chat_generate_task
                    task = chat_generate_task.delay(chat_session_id, user_message, request.user.student_id)
                    
                    sentry_sdk.add_breadcrumb(
                        message="Enqueued async chat task",
                        category="chat",
                        level="info",
                        data={"task_id": task.id}
                    )
                    
                    return Response({'status': 'queued', 'task_id': task.id}, status=status.HTTP_202_ACCEPTED)
                except Exception as e:
                    print(f"Failed to enqueue chat task: {e}")
                    sentry_sdk.capture_exception(e, extra={
                        "action": "enqueue_chat_task",
                        "chat_session_id": chat_session_id,
                        "student_id": request.user.student_id
                    })
                    # fall through to synchronous processing

            try:
                with transaction.atomic():
                    # Use the refactored generate_response method
                    bot_response_data = chatbot_service.generate_response(
                        query=user_message,
                        student_id=request.user.student_id,
                        chat_session_id=chat_session_id
                    )

                    print(f"🤖 Chatbot response received:")
                    print(f"   Success: {bot_response_data.get('success', False)}")
                    print(f"   Intent: {bot_response_data.get('intent', 'unknown')}")
                    print(f"   Has personalized data: {bot_response_data.get('has_personalized_data', False)}")
                    print(f"   Processing time: {bot_response_data.get('processing_time', 0)}s")

                    sentry_sdk.add_breadcrumb(
                        message="Chatbot response generated",
                        category="chat",
                        level="info",
                        data={
                            "success": bot_response_data.get('success', False),
                            "intent": bot_response_data.get('intent', 'unknown'),
                            "processing_time": bot_response_data.get('processing_time', 0)
                        }
                    )

                    # Extract the response text
                    bot_response = bot_response_data.get('response', 'Sorry, I encountered an error.')
                    print(f"   Response length: {len(bot_response)} chars")
                    
            except Exception as e:
                sentry_sdk.capture_exception(e, extra={
                    "action": "generate_chatbot_response",
                    "chat_session_id": chat_session_id,
                    "student_id": request.user.student_id,
                    "user_message": user_message
                })
                raise AppError(
                    code=ErrorCodes.SERVER_ERROR,
                    message='Failed to generate AI response',
                    details={'exception': str(e)}
                )
            
            # Get recent messages for context
            recent_messages = chat_session.messages.order_by('-created_at')[:2]
            messages_data = ChatMessageSerializer(recent_messages, many=True).data
            
            # Check if we should trigger memory summarization
            # Trigger every 10 messages to extract long-term memories
            total_messages = chat_session.messages.count()
            if total_messages > 0 and total_messages % 10 == 0:
                try:
                    from ..tasks import chat_memory_summarizer_task
                    # Enqueue summarization task in background
                    chat_memory_summarizer_task.delay(
                        chat_session_id=chat_session_id,
                        student_id=request.user.student_id,
                        message_threshold=10
                    )
                    print(f"🧠 Triggered memory summarization for session {chat_session_id} after {total_messages} messages")
                except Exception as e:
                    print(f"⚠️ Failed to trigger memory summarization: {e}")
                    # Don't fail the main request if summarization fails
            
            return Response({
                'success': bot_response_data.get('success', True),
                'user_message': user_message,
                'bot_response': bot_response,
                'session_id': chat_session_id,
                'recent_messages': messages_data,
                'intent': bot_response_data.get('intent', 'unknown'),
                'has_personalized_data': bot_response_data.get('has_personalized_data', False),
                'has_session_memory': bot_response_data.get('has_session_memory', False),
                'has_long_term_memory': bot_response_data.get('has_long_term_memory', False),
                'processing_time': bot_response_data.get('processing_time', 0),
                'message_id': bot_response_data.get('message_id')
            }, status=status.HTTP_200_OK)
            
        except AppError:
            # Re-raise AppError exceptions without additional processing
            raise
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "send_chat_message",
                "chat_session_id": chat_session_id,
                "student_id": getattr(request.user, 'student_id', None)
            })
            raise AppError(
                code=ErrorCodes.SERVER_ERROR,
                message='Failed to send message'
            )
            
        except AppError:
            # Re-raise known AppError exceptions without additional processing
            raise
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "send_chat_message",
                "chat_session_id": chat_session_id,
                "student_id": getattr(request.user, 'student_id', None)
            })
            raise AppError(
                code=ErrorCodes.SERVER_ERROR,
                message='Failed to send message'
            )
    
    @action(detail=True, methods=['get'], url_path='messages')
    def get_messages(self, request, chat_session_id=None):
        """Get all messages for a chat session"""
        try:
            sentry_sdk.add_breadcrumb(
                message="Getting messages for chat session",
                category="chat",
                level="info",
                data={
                    "chat_session_id": chat_session_id,
                    "student_id": getattr(request.user, 'student_id', None)
                }
            )
            
            # Get the chat session
            try:
                chat_session = ChatSession.objects.get(
                    chat_session_id=chat_session_id,
                    student_id=request.user.student_id,
                    is_active=True
                )
            except ChatSession.DoesNotExist:
                sentry_sdk.capture_message(
                    "Chat session not found when getting messages",
                    level="warning",
                    extra={
                        "chat_session_id": chat_session_id,
                        "student_id": getattr(request.user, 'student_id', None)
                    }
                )
                raise AppError(
                    code=ErrorCodes.CHAT_SESSION_NOT_FOUND,
                    message='Chat session not found'
                )
            
            # Get messages with pagination
            messages = chat_session.messages.order_by('created_at')
            
            # Apply pagination if needed
            page_size = request.query_params.get('page_size', 50)
            try:
                page_size = min(int(page_size), 100)  # Max 100 messages per request
            except (ValueError, TypeError):
                page_size = 50
            
            messages = messages[:page_size]
            
            sentry_sdk.add_breadcrumb(
                message="Retrieved chat messages",
                category="chat",
                level="info",
                data={
                    "message_count": len(messages),
                    "page_size": page_size,
                    "total_messages": chat_session.messages.count()
                }
            )
            
            # Serialize messages
            serializer = ChatMessageSerializer(messages, many=True)
            
            return Response({
                'session_id': chat_session_id,
                'messages': serializer.data,
                'total_messages': chat_session.messages.count()
            }, status=status.HTTP_200_OK)
            
        except AppError:
            # Re-raise known AppError exceptions without additional processing
            raise
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "get_chat_messages",
                "chat_session_id": chat_session_id,
                "student_id": getattr(request.user, 'student_id', None)
            })
            raise AppError(code=ErrorCodes.SERVER_ERROR, message='Failed to retrieve messages', details={'exception': str(e)})
    
    @action(detail=True, methods=['patch'], url_path='deactivate')
    def deactivate_session(self, request, chat_session_id=None):
        """Deactivate a chat session"""
        try:
            sentry_sdk.add_breadcrumb(
                message="Deactivating chat session",
                category="chat",
                level="info",
                data={
                    "chat_session_id": chat_session_id,
                    "student_id": getattr(request.user, 'student_id', None)
                }
            )
            
            try:
                chat_session = ChatSession.objects.get(
                    chat_session_id=chat_session_id,
                    student_id=request.user.student_id,
                    is_active=True
                )
            except ChatSession.DoesNotExist:
                sentry_sdk.capture_message(
                    "Chat session not found when deactivating",
                    level="warning",
                    extra={
                        "chat_session_id": chat_session_id,
                        "student_id": getattr(request.user, 'student_id', None)
                    }
                )
                raise AppError(
                    code=ErrorCodes.CHAT_SESSION_NOT_FOUND,
                    message='Chat session not found'
                )
            
            chat_session.is_active = False
            chat_session.save()
            
            sentry_sdk.add_breadcrumb(
                message="Chat session deactivated successfully",
                category="chat",
                level="info",
                data={"chat_session_id": chat_session_id}
            )
            
            return Response({
                'success': True,
                'message': 'Chat session deactivated successfully'
            }, status=status.HTTP_200_OK)
            
        except AppError:
            # Re-raise known AppError exceptions without additional processing
            raise
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "deactivate_chat_session",
                "chat_session_id": chat_session_id,
                "student_id": getattr(request.user, 'student_id', None)
            })
            raise AppError(code=ErrorCodes.SERVER_ERROR, message='Failed to deactivate session', details={'exception': str(e)})
    
    def destroy(self, request, chat_session_id=None):
        """Delete (soft-delete) a chat session by setting is_active=False"""
        try:
            sentry_sdk.add_breadcrumb(
                message="Deleting chat session",
                category="chat",
                level="info",
                data={
                    "chat_session_id": chat_session_id,
                    "student_id": getattr(request.user, 'student_id', None)
                }
            )
            
            try:
                chat_session = ChatSession.objects.get(
                    chat_session_id=chat_session_id,
                    student_id=request.user.student_id,
                    is_active=True
                )
            except ChatSession.DoesNotExist:
                sentry_sdk.capture_message(
                    "Chat session not found when deleting",
                    level="warning",
                    extra={
                        "chat_session_id": chat_session_id,
                        "student_id": getattr(request.user, 'student_id', None)
                    }
                )
                raise AppError(
                    code=ErrorCodes.CHAT_SESSION_NOT_FOUND,
                    message='Chat session not found'
                )
            
            # Soft delete by setting is_active=False
            chat_session.is_active = False
            chat_session.save()
            
            sentry_sdk.add_breadcrumb(
                message="Chat session deleted successfully",
                category="chat",
                level="info",
                data={"chat_session_id": chat_session_id}
            )
            
            return Response({
                'success': True,
                'message': 'Chat session deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except AppError:
            # Re-raise known AppError exceptions without additional processing
            raise
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "delete_chat_session",
                "chat_session_id": chat_session_id,
                "student_id": getattr(request.user, 'student_id', None)
            })
            raise AppError(code=ErrorCodes.SERVER_ERROR, message='Failed to delete session', details={'exception': str(e)})


class ChatMemoryViewSet(mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    """
    ViewSet for managing chat memories
    Allows students to view and manage their long-term memories
    """
    authentication_classes = [StudentJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ChatMemoryCreateSerializer
        return ChatMemorySerializer
    
    def get_queryset(self):
        """Return memories for the authenticated student only"""
        try:
            sentry_sdk.add_breadcrumb(
                message="Getting chat memories for student",
                category="memory",
                level="info",
                data={"student_id": getattr(self.request.user, 'student_id', None)}
            )
            
            if hasattr(self.request.user, 'student_id'):
                return ChatMemory.objects.filter(
                    student__student_id=self.request.user.student_id
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
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Get student profile
            from ..models import StudentProfile
            student_profile = StudentProfile.objects.get(student_id=request.user.student_id)
            
            # Create memory
            memory = ChatMemory.objects.create(
                student=student_profile,
                **serializer.validated_data
            )
            
            sentry_sdk.add_breadcrumb(
                message="Chat memory created successfully",
                category="memory",
                level="info",
                data={"memory_id": memory.id, "student_id": request.user.student_id}
            )
            
            # Return serialized response
            response_serializer = ChatMemorySerializer(memory)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except StudentProfile.DoesNotExist:
            raise AppError(
                code=ErrorCodes.SERVER_ERROR,
                message='Student profile not found'
            )
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
    
    @action(detail=False, methods=['post'], url_path='trigger-summarization')
    def trigger_summarization(self, request):
        """Manually trigger memory summarization for a session"""
        try:
            session_id = request.data.get('session_id')
            if not session_id:
                raise AppError(
                    code=ErrorCodes.VALIDATION_ERROR,
                    message='session_id is required'
                )
            
            # Verify session belongs to user
            from ..models import ChatSession
            try:
                ChatSession.objects.get(
                    chat_session_id=session_id,
                    student_id=request.user.student_id,
                    is_active=True
                )
            except ChatSession.DoesNotExist:
                raise AppError(
                    code=ErrorCodes.CHAT_SESSION_NOT_FOUND,
                    message='Chat session not found'
                )
            
            # Enqueue summarization task
            from ..tasks import chat_memory_summarizer_task
            task = chat_memory_summarizer_task.delay(
                chat_session_id=session_id,
                student_id=request.user.student_id,
                message_threshold=1  # Allow summarization even with few messages
            )
            
            return Response({
                'success': True,
                'task_id': task.id,
                'message': 'Memory summarization started'
            }, status=status.HTTP_202_ACCEPTED)
            
        except AppError:
            raise
        except Exception as e:
            sentry_sdk.capture_exception(e, extra={
                "action": "trigger_memory_summarization",
                "student_id": getattr(request.user, 'student_id', None)
            })
            raise AppError(
                code=ErrorCodes.SERVER_ERROR,
                message='Failed to trigger summarization'
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_statistics(request):

    """Get chat statistics for the authenticated student"""
    try:
        sentry_sdk.add_breadcrumb(
            message="Getting chat statistics",
            category="chat",
            level="info",
            data={"student_id": getattr(request.user, 'student_id', None)}
        )
        
        student_id = request.user.student_id
        
        # Get statistics
        total_sessions = ChatSession.objects.filter(student_id=student_id).count()
        active_sessions = ChatSession.objects.filter(student_id=student_id, is_active=True).count()
        total_messages = ChatMessage.objects.filter(
            chat_session__student_id=student_id,
            message_type='user'
        ).count()
        
        # Get recent session
        recent_session = ChatSession.objects.filter(
            student_id=student_id,
            is_active=True
        ).order_by('-updated_at').first()
        
        recent_session_data = None
        if recent_session:
            recent_session_data = ChatSessionSerializer(recent_session).data
        
        sentry_sdk.add_breadcrumb(
            message="Chat statistics retrieved",
            category="chat",
            level="info",
            data={
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_messages": total_messages
            }
        )
        
        return Response({
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_messages_sent': total_messages,
            'recent_session': recent_session_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        sentry_sdk.capture_exception(e, extra={
            "action": "get_chat_statistics",
            "student_id": getattr(request.user, 'student_id', None)
        })
        raise AppError(code=ErrorCodes.SERVER_ERROR, message='Failed to get statistics', details={'exception': str(e)})
