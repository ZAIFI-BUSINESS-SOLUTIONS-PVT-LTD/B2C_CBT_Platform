"""
Chatbot Views for NEET AI Tutor
Handles chat session creation, message processing, and history retrieval
"""
import uuid
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import ChatSession, ChatMessage, StudentProfile
from ..serializers import (
    ChatSessionSerializer, ChatMessageSerializer, 
    ChatMessageCreateSerializer, ChatSessionCreateSerializer
)
from ..services.chatbot_service_refactored import NeetChatbotService
from ..jwt_authentication import StudentJWTAuthentication


class ChatSessionViewSet(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.UpdateModelMixin,
                        viewsets.GenericViewSet):
    """
    ViewSet for managing chat sessions
    Provides CRUD operations for chat sessions with proper authentication
    """
    serializer_class = ChatSessionSerializer
    authentication_classes = [StudentJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'chat_session_id'  # Use chat_session_id instead of pk
    
    def get_queryset(self):
        """Return chat sessions for the authenticated student only"""
        if hasattr(self.request.user, 'student_id'):
            return ChatSession.objects.filter(
                student_id=self.request.user.student_id,
                is_active=True
            ).order_by('-updated_at')
        return ChatSession.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Create a new chat session for the authenticated student"""
        try:
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
            
            # Return serialized response
            response_serializer = ChatSessionSerializer(chat_session)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'Failed to create chat session'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='send-message')
    def send_message(self, request, chat_session_id=None):
        """Send a message in the chat session"""
        try:
            print(f"🔗 Chatbot API called - Session: {chat_session_id}, Student: {request.user.student_id}")
            
            # Get the chat session
            chat_session = get_object_or_404(
                ChatSession, 
                chat_session_id=chat_session_id,
                student_id=request.user.student_id,
                is_active=True
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
            
            chatbot_service = NeetChatbotService()
            
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
                
                # Extract the response text
                bot_response = bot_response_data.get('response', 'Sorry, I encountered an error.')
                print(f"   Response length: {len(bot_response)} chars")
            
            # Get recent messages for context
            recent_messages = chat_session.messages.order_by('-created_at')[:2]
            messages_data = ChatMessageSerializer(recent_messages, many=True).data
            
            return Response({
                'success': bot_response_data.get('success', True),
                'user_message': user_message,
                'bot_response': bot_response,
                'session_id': chat_session_id,
                'recent_messages': messages_data,
                'intent': bot_response_data.get('intent', 'unknown'),
                'has_personalized_data': bot_response_data.get('has_personalized_data', False),
                'processing_time': bot_response_data.get('processing_time', 0),
                'message_id': bot_response_data.get('message_id')
            }, status=status.HTTP_200_OK)
            
        except ChatSession.DoesNotExist:
            return Response({'error': 'Chat session not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Failed to send message: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], url_path='messages')
    def get_messages(self, request, chat_session_id=None):
        """Get all messages for a chat session"""
        try:
            # Get the chat session
            chat_session = get_object_or_404(
                ChatSession,
                chat_session_id=chat_session_id,
                student_id=request.user.student_id,
                is_active=True
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
            
            # Serialize messages
            serializer = ChatMessageSerializer(messages, many=True)
            
            return Response({
                'session_id': chat_session_id,
                'messages': serializer.data,
                'total_messages': chat_session.messages.count()
            }, status=status.HTTP_200_OK)
            
        except ChatSession.DoesNotExist:
            return Response({'error': 'Chat session not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Failed to retrieve messages: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['patch'], url_path='deactivate')
    def deactivate_session(self, request, chat_session_id=None):
        """Deactivate a chat session"""
        try:
            chat_session = get_object_or_404(
                ChatSession,
                chat_session_id=chat_session_id,
                student_id=request.user.student_id,
                is_active=True
            )
            
            chat_session.is_active = False
            chat_session.save()
            
            return Response({
                'success': True,
                'message': 'Chat session deactivated successfully'
            }, status=status.HTTP_200_OK)
            
        except ChatSession.DoesNotExist:
            return Response({'error': 'Chat session not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Failed to deactivate session: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_statistics(request):
    """Get chat statistics for the authenticated student"""
    try:
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
        
        return Response({
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_messages_sent': total_messages,
            'recent_session': recent_session_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Failed to get statistics: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
