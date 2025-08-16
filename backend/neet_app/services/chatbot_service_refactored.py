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
    Simplified NEET AI tutoring chatbot focusing on core functionality.
    Features: API key rotation, SQL agent, single NEET prompt, intent classification
    """
    
    def __init__(self):
        """Initialize the chatbot service with essential components only"""
        # Initialize SQL Agent (uses Grok API internally)
        self.sql_agent = SQLAgent()
        
        # Initialize Gemini client for general responses
        self.gemini_client = GeminiClient()
        
        # Initialize Grok API for SQL-related responses (backup)
        self.grok_client = self._initialize_grok_client()
        
        # Check if AI components are available
        self.ai_available = self.gemini_client.is_available() and self.sql_agent.is_available()
        
        print(f"NEET Chatbot Service initialized - AI Available: {self.ai_available}")
        
        # Single NEET tutor prompt
        self.neet_prompt = """You are NEET Ninja, a specialized and empathetic AI tutor for NEET aspirants. Your purpose is to assist students by analyzing their performance data and answering their specific questions with personalized, actionable insights.

You are strictly limited to the NEET syllabus, covering Physics, Chemistry, Botany, and Zoology. Below is your topic reference:

NEET_STRUCTURE = {
    Physics: [
        "Physical world", "Units and Measurements", "Motion in a Straight Line", "Motion in a Plane",
        "Laws of Motion", "Work, Energy and Power", "System of Particles and Rotational Motion",
        "Gravitation", "Mechanical Properties of Solids", "Mechanical Properties of Fluids",
        "Thermal Properties of Matter", "Thermodynamics", "Kinetic Theory", "Oscillations", "Waves",
        "Electric Charges and Fields", "Electrostatic Potential and Capacitance", "Current Electricity",
        "Moving Charges and Magnetism", "Magnetism and Matter", "Electromagnetic Induction",
        "Alternating Current", "Electromagnetic Waves", "Ray Optics and Optical Instruments",
        "Wave Optics", "Dual Nature of Radiation and Matter", "Atoms", "Nuclei", "Semiconductor Electronics"
    ],
 
    chemistry: [
        "Some Basic Concepts of Chemistry", "Structure of Atom", "Classification of Elements and Periodicity in Properties",
        "Chemical Bonding and Molecular Structure", "States of Matter", "Thermodynamics", "Equilibrium",
        "Redox Reactions", "Hydrogen", "The s-Block Element (Alkali and Alkaline earth metals)", "Some p-Block Elements",
        "Organic Chemistry – Some Basic Principles and Techniques", "Hydrocarbons", "Environmental Chemistry",
        "Solid State", "Solutions", "Electrochemistry", "Chemical Kinetics", "Surface Chemistry",
        "General Principles and Processes of Isolation of Elements", "The p-Block Elements",
        "The d- and f-Block Elements", "Coordination Compounds", "Haloalkanes and Haloarenes",
        "Alcohols, Phenols and Ethers", "Aldehydes, Ketones and Carboxylic Acids",
        "Organic Compounds containing Nitrogen", "Biomolecules", "Polymers", "Chemistry in Everyday Life"
    ],
 
    Botany: [
        "Diversity in the Living World", "Biological Classification", "Plant Kingdom",
        "Morphology of Flowering Plants", "Anatomy of Flowering Plants", "Structural Organisation in Animals",
        "Cell - The Unit of Life", "Biomolecules", "Cell Cycle and Cell Division", "Transport in Plants",
        "Mineral Nutrition", "Photosynthesis in Higher Plants", "Respiration in Plants",
        "Plant Growth and Development", "Reproduction in Organisms", "Sexual Reproduction in Flowering Plants",
        "Principles of Inheritance and Variation", "Molecular Basis of Inheritance",
        "Strategies for Enhancement in Food Production", "Microbes in Human Welfare",
        "Biotechnology – Principles and Processes", "Biotechnology and Its Applications",
        "Organisms and Populations", "Ecosystem", "Biodiversity and Conservation", "Environmental Issues"
    ],
 
    Zoology: [
        "Animal Kingdom", "Structural Organisation in Animals", "Biomolecules", "Digestion and Absorption",
        "Breathing and Exchange of Gases", "Body Fluids and Circulation", "Excretory Products and Their Elimination",
        "Locomotion and Movement", "Neural Control and Coordination", "Chemical Coordination and Integration",
        "Human Reproduction", "Reproductive Health", "Evolution", "Human Health and Disease",
        "Biotechnology – Principles and Processes", "Biotechnology and Its Applications", "Animal Husbandry"
    ]
}

Do NOT generate generic feedback. Only respond based on the student's actual query. Your analysis and explanation must align with what the student is asking — whether it’s a request for strengths, weaknesses, subject-wise performance, suggestions for improvement, etc.

The input data format is flexible and will vary based on the question. You must interpret the structure and extract relevant meaning based on the field names and values provided.

Your response must:
- Focus only on the intent of the question.
- Use the performance data to support your insights.
- Avoid unnecessary elaboration or listing unless asked.
- Maintain a friendly, motivating, and clear tone.
- Do not include raw data formatting (e.g., asterisks, markdown tables, or code blocks) in your response.
- Do not mention session IDs or any internal identifiers in your answer.
- Present information in clear, readable sentences suitable for students.

Do not provide insights outside the NEET syllabus."""
        
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
    
    def generate_response(self, query: str, student_id: str, chat_session_id: str) -> Dict[str, Any]:
        """
        Generate response using simplified logic with two types:
        1. General queries: Only send prompt + query to LLM
        2. Student-specific queries: Fetch data from DB, send prompt + query + data to LLM
        """
        try:
            start_time = time.time()
            print(f"\n🚀 Starting response generation:")
            print(f"   Query: '{query}'")
            print(f"   Student ID: {student_id}")
            print(f"   Chat Session ID: {chat_session_id}")
            print(f"   AI Available: {self.ai_available}")
            
            # Step 1: Classify intent (general or student_specific)
            intent = self._classify_intent(query)
            print(f"📝 Intent classified as: {intent}")
            
            # Step 2: Handle student-specific queries - fetch SQL data
            sql_data = None
            sql_query = None
            
            if intent == 'student_specific' and self.ai_available:
                print(f"🔍 Student-specific query detected - fetching SQL data...")
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
            
            # Step 3: Generate AI response based on intent type
            if self.ai_available and self.gemini_client:
                print(f"🤖 Generating AI response for intent: {intent}")
                
                if intent == 'general':
                    # For general queries: Only send prompt + query
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
5. Connect topics to real-world applications when possible"""
                    
                    full_prompt = f"{general_prompt}\n\nStudent Query: {query}\n\nProvide a helpful response:"
                    print(f"   Using general prompt (length: {len(full_prompt)} chars)")
                    
                elif intent == 'student_specific':
                    # For student-specific queries: Send detailed prompt + query + data
                    context_info = ""
                    if sql_data:
                        context_info = f"\n\nStudent's Performance Data: {json.dumps(sql_data, indent=2, default=datetime_serializer)}"
                        print(f"   ✅ Including performance data ({len(sql_data)} records)")
                    else:
                        context_info = "\n\nNote: No performance data available for this student."
                        print(f"   ⚠️ No performance data available")
                    
                    full_prompt = f"{self.neet_prompt}\n\nStudent Query: {query}{context_info}\n\nProvide a personalized analysis and response:"
                    print(f"   Using personalized prompt (length: {len(full_prompt)} chars)")
                
                print(f"   Sending to Gemini API...")
                try:
                    # First try Gemini for general responses
                    ai_response = self.gemini_client.generate_response(full_prompt)
                    print(f"   ✅ Gemini response received (length: {len(ai_response)} chars)")
                    print(f"   Response preview: {ai_response[:200]}...")
                    
                except Exception as e:
                    print(f"⚠️ Gemini API error: {e}")
                    
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
                
            else:
                ai_response = "I'm currently unavailable. Please try again in a moment."
                print(f"⚠️ AI unavailable - using fallback response")
            
            # Step 4: Save to database
            processing_time = time.time() - start_time
            print(f"💾 Saving to database (processing time: {processing_time:.2f}s)")
            
            try:
                message_id = self._save_chat_message(
                    chat_session_id, query, ai_response, 
                    metadata={'intent': intent, 'has_sql_data': sql_data is not None, 'processing_time': processing_time}
                )
                print(f"   ✅ Chat message saved with ID: {message_id}")
                
                # Save SQL query if available
                if sql_query and message_id:
                    self._save_sql_query(message_id, sql_query)
                    print(f"   ✅ SQL query saved to message {message_id}")
                    
            except Exception as e:
                print(f"   ❌ Failed to save chat message: {e}")
                message_id = None
            
            result = {
                'response': ai_response,
                'intent': intent,
                'has_personalized_data': sql_data is not None,
                'processing_time': round(processing_time, 2),
                'message_id': message_id,
                'success': True
            }
            
            print(f"🎉 Response generation completed successfully!")
            print(f"   Intent: {intent}")
            print(f"   Has personalized data: {sql_data is not None}")
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
