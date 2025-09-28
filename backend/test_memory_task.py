#!/usr/bin/env python
import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from django.db import models
from neet_app.models import ChatMemory, ChatSession, ChatMessage
from neet_app.tasks import chat_memory_summarizer_task

def test_memory_summarization():
    print("=== Testing Memory Summarization ===")
    
    # Find a session with enough messages
    session_with_messages = None
    for session in ChatSession.objects.filter(is_active=True):
        msg_count = session.messages.count()
        if msg_count >= 10:
            session_with_messages = session
            print(f"Found session {session.chat_session_id[:8]}... with {msg_count} messages")
            break
    
    if not session_with_messages:
        print("❌ No session found with 10+ messages")
        # Let's use the session with the most messages
        session_with_messages = ChatSession.objects.filter(is_active=True).annotate(
            msg_count=models.Count('messages')
        ).order_by('-msg_count').first()
        
        if session_with_messages:
            msg_count = session_with_messages.messages.count()
            print(f"Using session {session_with_messages.chat_session_id[:8]}... with {msg_count} messages instead")
        else:
            print("❌ No active sessions found!")
            return
    
    print(f"\n=== Testing Synchronous Task Execution ===")
    print(f"Session ID: {session_with_messages.chat_session_id}")
    print(f"Student ID: {session_with_messages.student_id}")
    
    # Test the task synchronously (not via Celery)
    try:
        result = chat_memory_summarizer_task(
            chat_session_id=session_with_messages.chat_session_id,
            student_id=session_with_messages.student_id,
            message_threshold=1  # Lower threshold for testing
        )
        print(f"✅ Task executed successfully!")
        print(f"Result: {result}")
        
        # Check if memories were created
        memory_count_after = ChatMemory.objects.count()
        print(f"ChatMemory count after task: {memory_count_after}")
        
        if memory_count_after > 0:
            print("\n=== Created Memories ===")
            for memory in ChatMemory.objects.all()[:3]:
                print(f"Memory {memory.id}: {memory.memory_type}")
                print(f"  Content: {str(memory.content)[:200]}...")
                print(f"  Tags: {memory.key_tags}")
                print(f"  Confidence: {memory.confidence_score}")
                print()
        
    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_memory_summarization()