"""
NEET Chatbot Service - Simplified Version
Main orchestrator focusing on core functionality only
"""
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any
from django.db import connection

from ..models import StudentProfile, ChatSession, ChatMessage
# Import only essential components
from .ai.gemini_client import GeminiClient
from .ai.sql_agent import SQLAgent


def datetime_serializer(obj):
    """JSON serializable datetime and decimal converter"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Handle Decimal objects from PostgreSQL
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class NeetChatbotService:
    """
    Refactored NEET Chatbot Service with improved structure and error handling
    Uses singleton pattern for performance optimization
    """
    
    _instance = None
    _sql_agent = None
    _gemini_client = None
    _grok_client = None
    _ai_available = False
    _initialization_time = None
    _neet_prompt = None
    
    def __new__(cls):
        """Implement singleton pattern to reuse expensive SQL agent initialization"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_services()
        return cls._instance
    
    def _initialize_services(self):
        """Initialize expensive services once and reuse"""
        if self._initialization_time is None:
            import time
            start_time = time.time()
            print("🔧 Initializing NeetChatbotService (first time)...")
            
            # Initialize Gemini client
            try:
                print("🔄 Initializing Gemini client...")
                self._gemini_client = GeminiClient()
                print("✅ Gemini client initialized successfully")
            except Exception as e:
                print(f"❌ Error initializing Gemini client: {e}")
                self._gemini_client = None
            
            # Initialize Grok client for backup
            try:
                print("🔄 Initializing Grok client...")
                self._grok_client = self._initialize_grok_client()
                if self._grok_client:
                    print("✅ Grok client initialized successfully")
                else:
                    print("⚠️ Grok client not available")
            except Exception as e:
                print(f"❌ Error initializing Grok client: {e}")
                self._grok_client = None
            
            # Initialize SQL agent
            try:
                print("🔄 Initializing SQL agent...")
                self._sql_agent = SQLAgent()
                print("✅ SQL Agent initialized successfully")
            except Exception as e:
                print(f"❌ Error initializing SQL agent: {e}")
                self._sql_agent = None
            
            # Set AI availability based on successful initializations
            self._ai_available = (self._gemini_client is not None or 
                                self._grok_client is not None) and self._sql_agent is not None
            
            # Initialize NEET prompt for personalized responses
            self._neet_prompt = """You are NEET Ninja, an AI tutor specializing in NEET exam preparation.

Your expertise covers:
- Physics: Mechanics, Thermodynamics, Optics, Electricity & Magnetism, Modern Physics
- Chemistry: Physical Chemistry, Organic Chemistry, Inorganic Chemistry  
- Biology: Botany, Zoology, Human Physiology, Genetics, Ecology

When providing personalized responses:
1. Analyze the student's performance data carefully
2. Identify strengths, weaknesses, and patterns
3. Provide specific, actionable recommendations
4. Use encouraging and supportive language
5. Connect performance to NEET exam requirements
6. Suggest targeted study strategies and practice areas
7. Do not include raw data formatting (e.g., asterisks, markdown tables, or code blocks) in your response.
8. Do not mention session IDs or any internal identifiers in your answer.
9. Please respond in plain text only, without any Markdown formatting (no bold, italics, headings, or symbols like *, `, #, etc.)."""
            
            self._initialization_time = time.time() - start_time
            print(f"⏱️ Service initialization completed in {self._initialization_time:.2f}s")
            print(f"🤖 AI Available: {self._ai_available}")
            print("NEET Chatbot Service initialized - AI Available: True" if self._ai_available else "NEET Chatbot Service initialized - AI Available: False")
    
    @property
    def sql_agent(self):
        """Get the cached SQL agent instance"""
        return self._sql_agent
    
    @property
    def gemini_client(self):
        """Get the cached Gemini client instance"""
        return self._gemini_client
    
    @property
    def grok_client(self):
        """Get the cached Grok client instance"""
        return self._grok_client
    
    @property
    def ai_available(self):
        """Check if AI services are available"""
        return self._ai_available
    
    @property
    def neet_prompt(self):
        """Get the NEET prompt for personalized responses"""
        return self._neet_prompt
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing or reinitialization)"""
        cls._instance = None
        cls._sql_agent = None
        cls._gemini_client = None
        cls._grok_client = None
        cls._ai_available = False
        cls._initialization_time = None
        cls._neet_prompt = None
        print("🔄 NeetChatbotService instance reset")
        
    def get_initialization_time(self):
        """Get the time it took to initialize the service"""
        return self._initialization_time
        
    def _initialize_grok_client(self):
        """Initialize Grok API client for SQL-related responses (backup)"""
        try:
            import os
            from langchain_groq import ChatGroq
            
            grok_api_key = os.getenv('GROQ_API_KEY')
            if not grok_api_key:
                print("⚠️ GROQ_API_KEY not found in environment variables")
                return None
            
            client = ChatGroq(
                model="llama-3.3-70b-versatile",
                groq_api_key=grok_api_key,
                temperature=0.7,  # Slightly higher temperature for more creative general responses
                max_tokens=2048,  # Higher token limit for detailed explanations
                timeout=30,
                max_retries=3
            )
            
            
            
            print("🔧 Grok API client initialized for backup responses")
            return client
            
        except Exception as e:
            print(f"⚠️ Failed to initialize Grok client: {e}")
            return None

    def _classify_intent(self, query: str) -> str:
        """Classify query as 'general' or 'student_specific' using Gemini LLM"""
        print(f"🔍 Classifying query using Gemini LLM: '{query}'")
        
        # First try LLM-based classification
        if self.gemini_client and self.gemini_client.is_available():
            try:
                classification_prompt = f"""You are an intent classifier for a NEET exam preparation chatbot. 

Your task is to classify student queries into exactly one of these categories:

**STUDENT_SPECIFIC**: Queries that require access to the student's personal performance data, test history, or individual progress. These include:
- Questions about personal performance: "How did I do?", "My weak areas", "My test scores"
- Personal test history: "How many tests have I taken?", "What topics did I attend in last test?"
- Individual progress tracking: "My improvement", "My accuracy", "My mistakes"
- Personal analytics: "Show my performance", "My chemistry marks", "Tests I completed"
- Requests for personalized analysis or recommendations based on their data

**GENERAL**: Educational queries that don't require personal data. These include:
- Subject explanations: "Explain photosynthesis", "What is Newton's law?"
- General study tips: "How to prepare for NEET?", "Study strategies"
- Concept clarifications: "Difference between mitosis and meiosis"
- General NEET information: "NEET exam pattern", "Important topics"
- Educational content that applies to all students

Student Query: "{query}"

Respond with ONLY one word: either "STUDENT_SPECIFIC" or "GENERAL"."""

                print(f"🤖 Sending classification request to Gemini...")
                llm_response = self.gemini_client.generate_response(classification_prompt)
                
                # Clean and validate LLM response
                llm_result = llm_response.strip().upper()
                print(f"🤖 Gemini classification result: '{llm_result}'")
                
                if "STUDENT_SPECIFIC" in llm_result:
                    print(f"✅ LLM classified as: student_specific")
                    return 'student_specific'
                elif "GENERAL" in llm_result:
                    print(f"✅ LLM classified as: general")
                    return 'general'
                else:
                    print(f"⚠️ Unexpected LLM response: '{llm_result}' - falling back to keyword matching")
                    
            except Exception as e:
                print(f"⚠️ LLM classification failed: {e} - falling back to keyword matching")
        
        # Fallback to keyword-based classification if LLM fails
        print(f"🔄 Using fallback keyword-based classification")
        query_lower = query.lower()
        
        # Keywords that indicate student-specific queries (performance analysis)
        student_specific_keywords = [
            # Direct personal references
            'my performance', 'my marks', 'my score', 'my progress', 'my result',
            'my weakness', 'my strength', 'my weak', 'my strong', 'how did i do', 
            'analyze my', 'my accuracy', 'my improvement', 'my test', 'my session', 
            'my analytics', 'my data', 'where am i weak', 'where am i strong',
            'my mistakes', 'my errors', 'what should i improve', 'my report',
            'how am i performing', 'my stats', 'my statistics', 'my last test',
            'last test mark', 'test marks', 'test scores', 'recent test', 
            'previous test', 'my exam', 'exam result', 'how i performed',
            'show my', 'my chemistry', 'my physics', 'my biology', 'my botany',
            'my zoology', 'overall performance', 'chemistry performance',
            'physics performance', 'biology performance',
            
            # Test-related queries
            'how many test', 'how many tests', 'number of tests', 'total tests',
            'tests taken', 'tests completed', 'test count', 'test history',
            'all my tests', 'previous tests', 'past tests', 'test sessions',
            
            # Topic/Subject attendance queries  
            'topics attended', 'topics covered', 'what topics', 'which topics',
            'topics in test', 'subjects covered', 'chapters covered', 'areas covered',
            'topics i have', 'subjects i have', 'what subjects', 'which subjects',
            'last test topics', 'recent test topics', 'test content', 'covered topics',
            'attended topics', 'attempted topics', 'practiced topics',
            
            # Question-specific queries
            'questions attempted', 'how many questions', 'total questions',
            'questions answered', 'questions done', 'question count',
            
            # Time-based personal queries
            'last test', 'recent test', 'latest test', 'yesterday test',
            'today test', 'this week', 'this month', 'recent performance',
            'latest performance', 'current performance', 'till now',
            'so far', 'until now', 'up to now',
            
            # Performance analysis
            'accuracy', 'percentage', 'correct answers', 'wrong answers',
            'right answers', 'incorrect answers', 'score percentage',
            'pass percentage', 'fail percentage', 'success rate',
            
            # Improvement queries
            'improve in', 'work on', 'focus on', 'practice more',
            'weak areas', 'strong areas', 'need improvement',
            'recommendations', 'suggestions', 'advice for me'
        ]
        
        # Check if any student-specific keywords are present
        matched_keywords = [keyword for keyword in student_specific_keywords if keyword in query_lower]
        
        if matched_keywords:
            print(f"✅ Fallback: Matched student-specific keywords: {matched_keywords}")
            return 'student_specific'
        else:
            print(f"❌ Fallback: No student-specific keywords found - treating as general")
            return 'general'
    
    def _get_session_history(self, chat_session_id: str, limit: int = 10) -> list:
        """Fetch recent messages from current session for short-term memory"""
        try:
            from ..models import ChatMessage, ChatSession
            
            # Get the chat session
            chat_session = ChatSession.objects.get(chat_session_id=chat_session_id, is_active=True)
            
            # Fetch last N messages in chronological order
            messages = ChatMessage.objects.filter(
                chat_session=chat_session
            ).order_by('-created_at')[:limit]
            
            # Convert to chronological order and format for prompt
            session_history = []
            for msg in reversed(messages):  # Reverse to get chronological order
                role = "User" if msg.message_type == 'user' else "Bot"
                # Truncate long messages to save tokens
                content = msg.message_content[:200] + "..." if len(msg.message_content) > 200 else msg.message_content
                session_history.append(f"{role}: {content}")
            
            print(f"   📋 Session history: {len(session_history)} messages")
            return session_history
            
        except Exception as e:
            print(f"   ⚠️ Failed to fetch session history: {e}")
            return []
    
    def _get_long_term_memories(self, student_id: str, limit: int = 5) -> list:
        """Fetch long-term memories for the student"""
        try:
            from ..models import ChatMemory
            
            # Fetch most recent and high-confidence long-term memories
            memories = ChatMemory.objects.filter(
                student__student_id=student_id,
                memory_type='long_term'
            ).order_by('-confidence_score', '-updated_at')[:limit]
            
            memory_facts = []
            for memory in memories:
                if isinstance(memory.content, dict):
                    # Extract fact or summary from structured content
                    fact = memory.content.get('fact') or memory.content.get('summary') or str(memory.content)
                else:
                    fact = str(memory.content)
                
                # Truncate if too long
                if len(fact) > 150:
                    fact = fact[:150] + "..."
                
                memory_facts.append(f"- {fact}")
            
            print(f"   🧠 Long-term memories: {len(memory_facts)} facts")
            return memory_facts
            
        except Exception as e:
            print(f"   ⚠️ Failed to fetch long-term memories: {e}")
            return []
    
    def _build_memory_context(self, session_history: list, long_term_memories: list) -> str:
        """Build memory context string for prompt injection"""
        context_parts = []
        
        # Add long-term memories if available
        if long_term_memories:
            context_parts.append("STUDENT MEMORY SUMMARY:")
            context_parts.extend(long_term_memories)
            context_parts.append("")  # Empty line for spacing
        
        # Add session history if available
        if session_history:
            context_parts.append("SESSION HISTORY (recent messages):")
            for i, msg in enumerate(session_history, 1):
                context_parts.append(f"{i}. {msg}")
            context_parts.append("")  # Empty line for spacing
        
        return "\n".join(context_parts)
    
    def generate_response(self, query: str, student_id: str, chat_session_id: str) -> Dict[str, Any]:
        """
        Generate response using simplified logic with memory integration:
        1. General queries: prompt + query + session memory + long-term memory
        2. Student-specific queries: prompt + query + session memory + long-term memory + SQL data
        """
        try:
            start_time = time.time()
            print(f"\n🚀 Starting response generation:")
            print(f"   Query: '{query}'")
            print(f"   Student ID: {student_id}")
            print(f"   Chat Session ID: {chat_session_id}")
            print(f"   AI Available: {self.ai_available}")
            
            # Step 1: Fetch memory context (both short-term and long-term)
            memory_start = time.time()
            session_history = self._get_session_history(chat_session_id)
            long_term_memories = self._get_long_term_memories(student_id)
            memory_time = time.time() - memory_start
            print(f"💾 Memory fetched: {len(session_history)} session messages, {len(long_term_memories)} long-term memories (time: {memory_time:.2f}s)")
            
            # Step 2: Classify intent (general or student_specific)
            intent_start = time.time()
            intent = self._classify_intent(query)
            intent_time = time.time() - intent_start
            print(f"📝 Intent classified as: {intent} (time: {intent_time:.2f}s)")
            
            # Step 2: Handle student-specific queries - fetch SQL data
            sql_data = None
            sql_query = None
            
            if intent == 'student_specific' and self.ai_available:
                print(f"🔍 Student-specific query detected - fetching SQL data...")
                sql_start = time.time()
                try:
                    print(f"   Calling SQL agent with query: '{query}' for student: {student_id}")
                    sql_result = self.sql_agent.generate_sql_and_execute(
                        query, student_id, context=f"Student is asking about their performance data"
                    )
                    print(f"   SQL Agent Result: {sql_result}")
                    
                    if sql_result and sql_result.get('success'):
                        sql_data = sql_result.get('data', [])
                        sql_query = sql_result.get('sql_query', '')
                        print(f"   ✅ SQL executed successfully!")
                        print(f"   SQL Query: {sql_query}")
                        print(f"   Data rows: {len(sql_data) if sql_data else 0}")
                        if sql_data:
                            print(f"   Sample data: {sql_data[:2]}")  # Show first 2 rows
                    else:
                        print(f"   ❌ SQL execution failed or returned no success flag")
                        sql_data = None
                        
                except Exception as e:
                    print(f"   ❌ SQL execution failed with exception: {e}")
                    import traceback
                    traceback.print_exc()
                    sql_data = None
            elif intent == 'student_specific' and not self.ai_available:
                print(f"⚠️ Student-specific query but AI not available")
            else:
                print(f"📖 General query - skipping SQL data fetch")
            
            # Step 3: Build memory context for prompt injection
            memory_context = self._build_memory_context(session_history, long_term_memories)
            
            # Step 4: Generate AI response based on intent type
            if self.ai_available and self.gemini_client:
                ai_start = time.time()
                print(f"🤖 Generating AI response for intent: {intent}")
                
                if intent == 'general':
                    # For general queries: prompt + query + memory context
                    general_prompt = """You are NEET Ninja, an AI tutor specializing in NEET exam preparation.

Your expertise covers:
- Physics: Mechanics, Thermodynamics, Optics, Electricity & Magnetism, Modern Physics
- Chemistry: Physical Chemistry, Organic Chemistry, Inorganic Chemistry  
- Biology: Botany, Zoology, Human Physiology, Genetics, Ecology

When answering:
1. Provide clear, concise explanations
2. Use simple language and examples
3. Focus on NEET-specific concepts and patterns
4. Include formulas, equations, or diagrams when helpful
5. Connect topics to real-world applications when possible
6. Use the student's memory and session history to provide personalized responses
7. Do not include raw data formatting (e.g., asterisks, markdown tables, or code blocks) in your response.
8. Do not mention session IDs or any internal identifiers in your answer.
9. Please respond in plain text only, without any Markdown formatting (no bold, italics, headings, or symbols like *, , #, etc.)."""
                    
                    # Build full prompt with memory context
                    prompt_parts = [general_prompt]
                    if memory_context.strip():
                        prompt_parts.append(f"\n{memory_context}")
                    prompt_parts.append(f"Student Query: {query}\n\nProvide a helpful response:")
                    
                    full_prompt = "\n".join(prompt_parts)
                    print(f"   Using general prompt with memory (length: {len(full_prompt)} chars)")
                    
                elif intent == 'student_specific':
                    # For student-specific queries: detailed prompt + query + memory + SQL data
                    context_info = ""
                    if sql_data:
                        context_info = f"\n\nStudent's Performance Data: {json.dumps(sql_data, indent=2, default=datetime_serializer)}"
                        print(f"   ✅ Including performance data ({len(sql_data)} records)")
                    else:
                        context_info = "\n\nNote: No performance data available for this student."
                        print(f"   ⚠️ No performance data available")
                    
                    # Build full prompt with memory context and performance data
                    prompt_parts = [self.neet_prompt]
                    if memory_context.strip():
                        prompt_parts.append(f"\n{memory_context}")
                    prompt_parts.append(f"Student Query: {query}{context_info}\n\nProvide a personalized analysis and response:")
                    
                    full_prompt = "\n".join(prompt_parts)
                    print(f"   Using personalized prompt with memory (length: {len(full_prompt)} chars)")
                
                print(f"   Sending to Gemini API...")
                gemini_start = time.time()
                try:
                    # First try Gemini for general responses
                    ai_response = self.gemini_client.generate_response(full_prompt)
                    gemini_time = time.time() - gemini_start
                    print(f"   ✅ Gemini response received (length: {len(ai_response)} chars, time: {gemini_time:.2f}s)")
                    print(f"   Response preview: {ai_response[:200]}...")
                    
                except Exception as e:
                    gemini_time = time.time() - gemini_start
                    print(f"⚠️ Gemini API error after {gemini_time:.2f}s: {e}")
                    
                    # Fallback to Grok API if Gemini fails
                    if self.grok_client:
                        print(f"   🔄 Falling back to Grok API...")
                        try:
                            response = self.grok_client.invoke(full_prompt)
                            
                            # Extract content from response
                            if hasattr(response, 'content'):
                                ai_response = response.content
                            else:
                                ai_response = str(response)
                                
                            print(f"   ✅ Grok fallback response received (length: {len(ai_response)} chars)")
                            print(f"   Response preview: {ai_response[:200]}...")
                            
                        except Exception as grok_error:
                            print(f"⚠️ Grok fallback also failed: {grok_error}")
                            ai_response = "I'm experiencing technical difficulties with both AI services. Please try again in a moment."
                    else:
                        ai_response = "I'm experiencing technical difficulties. Please try again in a moment."
                
                ai_time = time.time() - ai_start
                print(f"   🎯 Total AI response time: {ai_time:.2f}s")
                
            else:
                ai_response = "I'm currently unavailable. Please try again in a moment."
                print(f"⚠️ AI unavailable - using fallback response")
            
            # Step 4: Save to database
            processing_time = time.time() - start_time
            print(f"💾 Saving to database (total processing time: {processing_time:.2f}s)")
            
            db_start_time = time.time()
            try:
                message_id = self._save_chat_message(
                    chat_session_id, query, ai_response, 
                    metadata={'intent': intent, 'has_sql_data': sql_data is not None, 'processing_time': processing_time}
                )
                db_save_time = time.time() - db_start_time
                print(f"   ✅ Chat message saved with ID: {message_id} (DB save time: {db_save_time:.2f}s)")
                
                # Save SQL query if available
                if sql_query and message_id:
                    sql_start_time = time.time()
                    self._save_sql_query(message_id, sql_query)
                    sql_save_time = time.time() - sql_start_time
                    print(f"   ✅ SQL query saved to message {message_id} (SQL save time: {sql_save_time:.2f}s)")
                    
            except Exception as e:
                print(f"   ❌ Failed to save chat message: {e}")
                message_id = None
            
            result = {
                'response': ai_response,
                'intent': intent,
                'has_personalized_data': sql_data is not None,
                'has_session_memory': len(session_history) > 0,
                'has_long_term_memory': len(long_term_memories) > 0,
                'processing_time': round(processing_time, 2),
                'message_id': message_id,
                'success': True
            }
            
            print(f"🎉 Response generation completed successfully!")
            print(f"   Intent: {intent}")
            print(f"   Has personalized data: {sql_data is not None}")
            print(f"   Has session memory: {len(session_history) > 0}")
            print(f"   Has long-term memory: {len(long_term_memories) > 0}")
            print(f"   Processing time: {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            print(f"💥 Error in generate_response: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'response': f"I encountered an error while processing your question. Please try again.",
                'intent': 'error',
                'has_personalized_data': False,
                'processing_time': 0,
                'message_id': None,
                'success': False,
                'error': str(e)
            }
    def _save_chat_message(
        self, 
        chat_session_id: str, 
        query: str, 
        response: str, 
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """Save chat message to database - creates two records: user message and bot response"""
        try:
            chat_session = ChatSession.objects.get(chat_session_id=chat_session_id)
            
            # Save user message
            user_message = ChatMessage.objects.create(
                chat_session=chat_session,
                message_content=query,
                message_type='user'
            )
            
            # Save bot response with processing time and metadata
            processing_time = metadata.get('processing_time') if metadata else None
            bot_message = ChatMessage.objects.create(
                chat_session=chat_session,
                message_content=response,
                message_type='bot',
                processing_time=processing_time
            )
            
            return str(bot_message.id)  # Return bot message ID for SQL query saving
            
        except ChatSession.DoesNotExist:
            print(f"Chat session {chat_session_id} not found")
            return None
        except Exception as e:
            print(f"Error saving chat message: {e}")
            return None

    def _save_sql_query(self, chat_message_id: Optional[str], sql_query: str):
        """Save SQL query in the bot message for debugging purposes"""
        if not chat_message_id or not sql_query:
            return
            
        try:
            chat_message = ChatMessage.objects.get(id=chat_message_id)
            chat_message.sql_query = sql_query
            chat_message.save(update_fields=['sql_query'])
        except Exception as e:
            print(f"Error saving SQL query: {e}")

    def test_sql_execution(self, student_id: str) -> Dict[str, Any]:
        """Test SQL execution capability"""
        try:
            test_query = f"Show me my recent test performance"
            result = self.sql_agent.generate_sql_and_execute(test_query, student_id)
            return {
                'success': True,
                'result': result,
                'message': 'SQL execution test completed'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'SQL execution test failed'
            }
