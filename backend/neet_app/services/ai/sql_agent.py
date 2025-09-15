"""
SQL Agent using LangChain
Handles natural language to SQL conversion and execution with advanced rate limit handling
"""
import re
import time
import json
import hashlib
from typing import Optional, Tuple, Dict, Any, List
from django.conf import settings
from django.core.cache import cache

# Import LangChain components
from langchain_community.utilities import SQLDatabase


class SQLAgent:
    """Enhanced LangChain SQL Agent with caching, exponential backoff, and optimized rotation"""
    
    def __init__(self, gemini_client=None):
        # gemini_client parameter kept for compatibility but not used
        self.sql_agent = None
        self.db = None
        self.llm = None  # Store LLM separately for efficient updates
        self.cache_prefix = "sql_query_cache"
        self.cache_timeout = 3600  # 1 hour cache
        self._initialize()
    
    def _initialize(self):
        """Initialize LangChain SQL agent"""
        self._create_database_connection()
        self._create_llm_with_timeouts()
        self._create_sql_agent()
    
    def _create_database_connection(self):
        """Create database connection once and reuse"""
        if not self.db:
            try:
                db_config = settings.DATABASES.get('default', {})

                user = db_config.get('USER') or ''
                password = db_config.get('PASSWORD') or ''
                host = db_config.get('HOST') or 'localhost'
                port = db_config.get('PORT')
                name = db_config.get('NAME') or ''

                # Build auth part only if user is present
                auth = ''
                if user and password:
                    auth = f"{user}:{password}@"
                elif user:
                    auth = f"{user}@"

                # Include port only when provided and non-empty
                host_port = host
                if port:
                    host_port = f"{host}:{port}"

                db_url = f"postgresql://{auth}{host_port}/{name}"

                # Initialize database connection with minimal schema for faster loading
                try:
                    self.db = SQLDatabase.from_uri(
                        db_url,
                        include_tables=[
                            'student_profiles',
                            'test_sessions', 
                            'test_answers',
                            'topics',
                            'questions'
                        ],
                        sample_rows_in_table_info=1  # Minimal sample data
                    )
                    print("🔗 Database connection established")
                except Exception as e:
                    # Don't allow URI parsing or SQLDatabase errors to bubble up
                    print(f"⚠️ Could not initialize SQLDatabase from URI: {e}")
                    self.db = None
            except Exception as e:
                print(f"⚠️ Error building DB URL: {e}")
                self.db = None
    
    def _create_llm_with_timeouts(self):
        """Create or update LLM with Grok API using Llama 3.3 70B Versatile model"""
        try:
            import os
            from langchain_groq import ChatGroq
            
            # Use Grok API with Llama 3.3 70B Versatile model
            grok_api_key = os.getenv('GROQ_API_KEY')
            if not grok_api_key:
                print("⚠️ GROQ_API_KEY not found in environment variables")
                return False

            # Create LLM with Grok API
            self.llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                groq_api_key=grok_api_key,
                temperature=0.1,
                max_tokens=1024,
                timeout=10,
                max_retries=2
            )
            
            print(f"🔧 LLM configured with Grok API using Llama-3.3-70b-versatile model")
            return True
            
        except Exception as e:
            print(f"⚠️ LLM creation failed: {e}")
            self.llm = None
            return False
    
    
    
    def _create_sql_agent(self):
        """Create SQL agent using existing LLM and database connection"""
        try:
            if not self.llm or not self.db:
                print("⚠️ LLM or Database not available for SQL agent")
                return False
            
            # Set environment variable to suppress pydantic warnings
            import os
            os.environ['PYDANTIC_V1_MODE'] = '1'
            
            # Try to suppress warnings and compatibility issues
            import warnings
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            warnings.filterwarnings("ignore", message=".*pydantic.*")
            warnings.filterwarnings("ignore", message=".*__modify_schema__.*")
            
            # First try: Direct simple agent approach (most compatible)
            print("🔄 Attempting simple SQL agent creation...")
            if self._create_simple_sql_agent():
                print(f"✅ SQL Agent created with Grok API using Llama-3.3-70b-versatile model")
                return True
            
            # Try different approaches for SQL agent creation only if simple fails
            try:
                from langchain_community.agent_toolkits import SQLDatabaseToolkit
                from langchain.agents import create_sql_agent, AgentType
                
                # Method 1: Try with newer LangChain approach
                from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
                from langchain.agents import AgentExecutor, create_openai_functions_agent
                from langchain_core.prompts import ChatPromptTemplate
                
                # Create toolkit
                toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
                
                # Create a simple prompt template
                prompt = ChatPromptTemplate.from_messages([
                    ("system", self._get_optimized_sql_prefix()),
                    ("human", "{input}"),
                    ("assistant", "I'll help you generate a SQL query."),
                ])
                
                # Get tools from toolkit
                tools = toolkit.get_tools()
                
                # Create agent with tools
                from langchain.agents import create_react_agent
                
                self.sql_agent = create_react_agent(
                    llm=self.llm,
                    tools=tools,
                    prompt=prompt
                )
                
                # Wrap in executor
                self.sql_agent = AgentExecutor.from_agent_and_tools(
                    agent=self.sql_agent,
                    tools=tools,
                    verbose=False,
                    max_iterations=3,
                    early_stopping_method="generate",
                    handle_parsing_errors=True
                )
                
            except Exception as e1:
                print(f"⚠️ Modern agent creation failed: {e1}, trying legacy method...")
                
                # Method 2: Legacy approach with compatibility fixes
                try:
                    # Suppress warnings temporarily
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        
                        # Create SQL toolkit with existing components
                        toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
                        
                        # Create optimized SQL agent with compatibility mode
                        self.sql_agent = create_sql_agent(
                            llm=self.llm,
                            toolkit=toolkit,
                            verbose=False,
                            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                            prefix=self._get_sql_agent_prefix(),  # Use detailed prefix
                            max_iterations=3,
                            early_stopping_method="generate",
                            handle_parsing_errors=True
                        )
                        
                except Exception as e2:
                    print(f"⚠️ Legacy agent creation also failed: {e2}")
                    # Method 3: Fall back to simple agent (already tried above)
                    if not self.sql_agent:
                        print("🔄 All complex methods failed, using simple agent...")
                        return self._create_simple_sql_agent()
            
            print(f"✅ SQL Agent created with Grok API using Llama-3.3-70b-versatile model")
            return True
            
        except Exception as e:
            print(f"⚠️ SQL Agent creation failed: {e}")
            print("🔄 Falling back to simple SQL agent...")
            # Always fall back to simple agent if complex creation fails
            return self._create_simple_sql_agent()
    
    def _create_simple_sql_agent(self):
        """Create a simple SQL agent as fallback when complex creation fails"""
        try:
            print("🔄 Creating simple SQL agent as fallback...")
            
            # Create a simple wrapper that acts like an agent
            class SimpleSQLAgent:
                def __init__(self, llm, db):
                    self.llm = llm
                    self.db = db
                
                def invoke(self, prompt):
                    """Simple invoke method that directly uses LLM"""
                    try:
                        # Add schema context to the prompt
                        schema_context = self._get_schema_context()
                        full_prompt = f"{schema_context}\n\n{prompt}"
                        
                        # Use the LLM directly
                        response = self.llm.invoke(full_prompt)
                        
                        # Extract content from response
                        if hasattr(response, 'content'):
                            return {'output': response.content}
                        else:
                            return {'output': str(response)}
                    except Exception as e:
                        return {'output': f"Error: {str(e)}"}
                
                def _get_schema_context(self):
                    """Get database schema context"""
                    try:
                        return self.db.get_table_info()
                    except Exception as e:
                        # Fallback schema if database info retrieval fails
                        print(f"⚠️ Could not get table info: {e}")
                        return """
                        POSTGRESQL DATABASE SCHEMA FOR NEET STUDENT PERFORMANCE:
                        
                        Tables:
                        - student_profiles (student_id VARCHAR PRIMARY KEY, full_name TEXT, email VARCHAR)
                        - test_sessions (id SERIAL PRIMARY KEY, student_id VARCHAR, start_time TIMESTAMP, is_completed BOOLEAN)
                        - test_answers (id SERIAL PRIMARY KEY, session_id INTEGER, question_id INTEGER, is_correct BOOLEAN, selected_answer VARCHAR)
                        - questions (id SERIAL PRIMARY KEY, topic_id INTEGER)
                        - topics (id SERIAL PRIMARY KEY, name TEXT, subject TEXT)
                        
                        Use PostgreSQL syntax. Focus on test_answers table for performance data.
                        Always filter by student_id and is_completed = TRUE.
                        """
            
            self.sql_agent = SimpleSQLAgent(self.llm, self.db)
            print("✅ Simple SQL Agent created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Simple SQL Agent creation failed: {e}")
            self.sql_agent = None
            return False
    
    def _update_api_key(self):
        """Update API key - simplified for Grok API (no rotation needed)"""
        success = self._create_llm_with_timeouts()
        if success and self.llm:
            # Update the toolkit's LLM
            if hasattr(self.sql_agent, 'toolkit'):
                self.sql_agent.toolkit.llm = self.llm
            # Update the agent's LLM
            if hasattr(self.sql_agent, 'llm_chain'):
                self.sql_agent.llm_chain.llm = self.llm
            print(f"🔄 Updated SQL Agent with Grok API")
            return True
        return False
    
    def _get_cache_key(self, student_id: str, user_message: str) -> str:
        """Generate cache key for query"""
        query_hash = hashlib.md5(f"{student_id}:{user_message}".encode()).hexdigest()
        return f"{self.cache_prefix}:{query_hash}"
    
    def _get_cached_query(self, student_id: str, user_message: str) -> Optional[str]:
        """Retrieve cached SQL query"""
        try:
            cache_key = self._get_cache_key(student_id, user_message)
            cached_sql = cache.get(cache_key)
            if cached_sql:
                print(f"💾 Cache hit for query: {user_message[:50]}...")
                return cached_sql
        except Exception as e:
            print(f"⚠️ Cache retrieval failed: {e}")
        return None
    
    def _cache_query(self, student_id: str, user_message: str, sql_query: str):
        """Cache successful SQL query"""
        try:
            cache_key = self._get_cache_key(student_id, user_message)
            cache.set(cache_key, sql_query, timeout=self.cache_timeout)
            print(f"💾 Cached SQL query for: {user_message[:50]}...")
        except Exception as e:
            print(f"⚠️ Cache storage failed: {e}")
    
    def _get_optimized_sql_prefix(self):
        """Optimized, concise prefix for faster processing"""
        return """PostgreSQL query generator for NEET student performance analysis.
        
        TABLES:
        - test_answers: session_id, question_id, is_correct (MAIN PERFORMANCE DATA)  
        - test_sessions: id, student_id, start_time, is_completed
        - questions: id, topic_id
        - topics: id, name, subject (Physics/Chemistry/Botany/Zoology)
        - student_profiles: student_id, full_name
        
        RULES:
        1. Use test_answers for performance (NOT test_sessions score fields - they're empty)
        2. Filter: student_id = target AND is_completed = TRUE  
        3. PostgreSQL syntax only - NO NESTED AGGREGATES (no AVG(SUM(...)))
        4. Limit 20 rows max
        
        PATTERNS:
        - Subject performance: JOIN test_answers→test_sessions→questions→topics, GROUP BY subject
        - Test-by-test: GROUP BY session_id, start_time for individual tests
        - For averages: Use simple SUM(...)/COUNT(...) not AVG(SUM(...))
        - Always wrap final query in <sql_query>query here</sql_query>
        """
    
    def _get_sql_agent_prefix(self):
        """Schema-aware prefix for SQL agent"""
        return """
        You are an agent designed to interact with a PostgreSQL database for NEET student performance analysis.
        
        CRITICAL: This is PostgreSQL, NOT MySQL. Use PostgreSQL syntax:
        - Use STRING_AGG() instead of GROUP_CONCAT()
        - Use ARRAY_AGG() for arrays
        - Use proper PostgreSQL date functions
        - Use LIMIT instead of TOP
        
        AVAILABLE TABLES AND EXACT SCHEMA:
        
        1. student_profiles:
           - student_id (VARCHAR PRIMARY KEY) - Unique student identifier
           - full_name (TEXT) - Student's full name
           - email (VARCHAR) - Student's email
           - date_of_birth (DATE) - Student's birth date
           - target_exam_year (INTEGER) - Target year for NEET exam
           
        2. test_sessions:
           - id (SERIAL PRIMARY KEY)
           - student_id (VARCHAR) - Foreign key to student_profiles.student_id
           - start_time, end_time (TIMESTAMP) - Test duration (use for dates only)
           - is_completed (BOOLEAN) - Whether test is completed
           - **DO NOT USE: physics_score, chemistry_score, botany_score, zoology_score, correct_answers, incorrect_answers - these are not populated**
           
        3. test_answers: **PRIMARY DATA SOURCE FOR PERFORMANCE**
           - id (SERIAL PRIMARY KEY)
           - session_id (INTEGER) - Foreign key to test_sessions.id
           - question_id (INTEGER) - Foreign key to questions.id
           - is_correct (BOOLEAN) - Whether answer is correct (THIS IS THE REAL PERFORMANCE DATA)
           - selected_answer (VARCHAR) - Student's choice A/B/C/D
           - time_taken (INTEGER) - Time spent on question
           - answered_at (TIMESTAMP) - When answered
           
        4. topics:
           - id (SERIAL PRIMARY KEY)
           - name (TEXT) - Topic name
           - subject (TEXT) - Subject (Physics/Chemistry/Botany/Zoology)
           
        5. questions:
           - id (SERIAL PRIMARY KEY)
           - topic_id (INTEGER) - Foreign key to topics.id
           

        QUERY RULES:
        1. ALWAYS filter by student_id when analyzing student performance
        2. ONLY use completed test sessions (is_completed = true)
        3. Use proper JOINs to connect related tables
        4. Order results by start_time DESC for recent data
        5. Use LIMIT clause to avoid large datasets
        6. NO NESTED AGGREGATES - never use AVG(SUM(...)) or similar patterns
        7. For averages: use simple SUM(...)/COUNT(...) calculations
        8. For UNION queries: ALL SELECT statements MUST have the same number of columns and compatible data types
        9. Use NULL or appropriate placeholder values to match column counts in UNION operations

        SAFETY:
        - ONLY SELECT queries allowed
        - NO UPDATE, DELETE, INSERT, or DROP operations
        """
    
    def is_available(self) -> bool:
        """Check if SQL agent is available"""
        return self.sql_agent is not None
    
    def generate_sql_query(self, student_id: str, user_message: str) -> Tuple[Dict[str, Any], str]:
        """Generate SQL query using Grok API with simplified retry logic"""
        if not self.is_available():
            raise ValueError("SQL Agent not available")
        
        # Check cache first
        cached_sql = self._get_cached_query(student_id, user_message)
        if cached_sql:
            return {'success': True, 'cached': True}, cached_sql
        
        max_retries = 3  # Simple retry count for Grok API
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 SQL Agent attempt {attempt + 1}/{max_retries} using Grok API")
                
                # Optimized, concise prompt
                sql_prompt = f"""Generate PostgreSQL query for student {student_id}: "{user_message}"
                
                Use test_answers table for performance data. Join with test_sessions, questions, topics as needed.
                Filter: student_id = '{student_id}' AND is_completed = TRUE
                
                Common patterns:
                - Subject performance: GROUP BY t.subject  
                - Individual tests: GROUP BY ts.id, ts.start_time
                - Recent tests: ORDER BY ts.start_time DESC LIMIT X
                
                Wrap final query in <sql_query>SELECT ... ;</sql_query>"""
                
                # Execute with simplified timeout handling
                try:
                    # For Windows compatibility, use threading approach
                    import threading
                    result_container = {'result': None, 'error': None}
                    
                    def execute_agent():
                        try:
                            result_container['result'] = self.sql_agent.invoke(sql_prompt)
                        except Exception as e:
                            result_container['error'] = e
                    
                    thread = threading.Thread(target=execute_agent)
                    thread.daemon = True
                    thread.start()
                    thread.join(timeout=15)  # Longer timeout for Grok API
                    
                    if thread.is_alive():
                        raise TimeoutError("SQL generation timed out after 15 seconds")
                    
                    if result_container['error']:
                        raise result_container['error']
                    
                    if result_container['result'] is None:
                        raise Exception("No result from SQL agent")
                    
                    agent_response = result_container['result']
                    
                except Exception as e:
                        error_msg = str(e).lower()
                        
                        # Enhanced quota detection
                        quota_indicators = [
                            'exceeded your current quota',
                            'quota_metric',
                            'generaterequestsperdayperprojectpermodel',
                            'rate limit', 'quota', '429', 'resource exhausted',
                            'billing details', 'quota_value'
                        ]
                        
                        is_quota_exceeded = any(indicator in error_msg for indicator in quota_indicators)
                        
                        if is_quota_exceeded:
                            print(f"🚫 Quota exceeded on API key {self.gemini_client.current_key_index + 1}")
                            
                            # Try next API key if available
                            if attempt < max_retries - 1 and self.gemini_client.rotate_api_key():
                                print(f"� Rotating to API key {self.gemini_client.current_key_index + 1}")
                                
                                # Update LLM with new key
                                if not self._update_api_key():
                                    print("⚠️ Key update failed, recreating agent...")
                                    self._create_sql_agent()
                                
                                # Short delay before retry
                                time.sleep(1)
                                continue
                            else:
                                print("❌ All API keys exhausted due to quota limits")
                                return self._generate_fallback_response(student_id, user_message)
                        
                        # Handle timeout or other errors
                        if 'timeout' in error_msg or isinstance(e, TimeoutError):
                            print(f"⏱️ Timeout on API key {self.gemini_client.current_key_index + 1}")
                            
                            # For timeouts, also try rotating API key since it might be due to quota issues
                            if attempt < max_retries - 1 and self.gemini_client.rotate_api_key():
                                print(f"🔄 Timeout - rotating to API key {self.gemini_client.current_key_index + 1}")
                                
                                # Update LLM with new key
                                if not self._update_api_key():
                                    print("⚠️ Key update failed, recreating agent...")
                                    self._create_sql_agent()
                                
                                time.sleep(1)
                                continue
                            elif attempt < max_retries - 1:
                                # If no more keys to rotate, still continue with current key
                                continue
                        
                        # Re-raise for final attempt
                        if attempt == max_retries - 1:
                            print(f"❌ Final attempt failed: {str(e)[:100]}...")
                            return self._generate_fallback_response(student_id, user_message)
                        
                        raise e
                        
                # If we get here, extract and validate SQL
                sql_query = self._extract_sql_with_markers(agent_response)
                
                if sql_query:
                    # Check for nested aggregates and fix them
                    fixed_sql = self._fix_nested_aggregates(sql_query)
                    
                    # If fix returns empty string, trigger fallback
                    if not fixed_sql or not fixed_sql.strip():
                        print("🔄 Nested aggregates detected - using fallback response")
                        return self._generate_fallback_response(student_id, user_message)
                    
                    print(f"🤖 Generated SQL: {fixed_sql[:100]}...")
                    # Cache successful query
                    self._cache_query(student_id, user_message, fixed_sql)
                    return {'success': True, 'cached': False}, fixed_sql
                else:
                    print("⚠️ No valid SQL extracted from response, trying fallback...")
                    raise Exception("No valid SQL extracted")
                    
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed: {str(e)[:100]}...")
                
                if attempt == max_retries - 1:
                    print("❌ All retries exhausted, using fallback")
                    return self._generate_fallback_response(student_id, user_message)
        
        return self._generate_fallback_response(student_id, user_message)
    
    def _generate_fallback_response(self, student_id: str, user_message: str) -> Tuple[Dict[str, Any], str]:
        """Generate a simple fallback SQL query when AI fails"""
        print("🔄 Generating fallback SQL query...")
        
        # Analyze user message to provide specific fallback
        message_lower = user_message.lower()
        
        if 'average accuracy' in message_lower or 'avg accuracy' in message_lower:
            # Special case for average accuracy - avoid nested aggregates
            fallback_sql = f"""
            SELECT 
                ROUND(
                    (SUM(CASE WHEN ta.is_correct = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(ta.id)), 2
                ) as average_accuracy_percentage
            FROM test_answers ta
            JOIN test_sessions ts ON ta.session_id = ts.id
            WHERE ts.student_id = '{student_id}' 
            AND ts.is_completed = TRUE;
            """.strip()
        elif 'average time' in message_lower or 'avg time' in message_lower or 'time taken' in message_lower:
            # Average time per question - simple aggregate without ORDER BY issues
            fallback_sql = f"""
            SELECT 
                ROUND(AVG(ta.time_taken), 2) as avg_time_seconds,
                COUNT(ta.id) as total_questions
            FROM test_answers ta
            JOIN test_sessions ts ON ta.session_id = ts.id
            WHERE ts.student_id = '{student_id}' 
            AND ts.is_completed = TRUE
            AND ta.time_taken IS NOT NULL;
            """.strip()
        elif 'recent' in message_lower or 'latest' in message_lower or 'last test' in message_lower:
            # Recent performance fallback - use subquery to avoid GROUP BY issues
            fallback_sql = f"""
            SELECT 
                ts.start_time,
                COUNT(ta.id) as total_questions,
                SUM(CASE WHEN ta.is_correct = TRUE THEN 1 ELSE 0 END) as correct_answers,
                ROUND(
                    (SUM(CASE WHEN ta.is_correct = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(ta.id)), 2
                ) as percentage
            FROM test_answers ta
            JOIN test_sessions ts ON ta.session_id = ts.id
            WHERE ts.student_id = '{student_id}' 
            AND ts.is_completed = TRUE
            AND ts.id = (
                SELECT id FROM test_sessions 
                WHERE student_id = '{student_id}' 
                AND is_completed = TRUE 
                ORDER BY start_time DESC 
                LIMIT 1
            )
            GROUP BY ts.id, ts.start_time;
            """.strip()
        else:
            # Default subject performance query as fallback
            fallback_sql = f"""
            SELECT 
                t.subject,
                COUNT(ta.id) as total_questions,
                SUM(CASE WHEN ta.is_correct = TRUE THEN 1 ELSE 0 END) as correct_answers,
                ROUND(
                    (SUM(CASE WHEN ta.is_correct = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(ta.id)), 2
                ) as percentage
            FROM test_answers ta
            JOIN test_sessions ts ON ta.session_id = ts.id
            JOIN questions q ON ta.question_id = q.id
            JOIN topics t ON q.topic_id = t.id
            WHERE ts.student_id = '{student_id}' 
            AND ts.is_completed = TRUE
            GROUP BY t.subject
            ORDER BY percentage DESC
            LIMIT 4;
            """.strip()
        
        print(f"📝 Fallback SQL: {fallback_sql[:100]}...")
        return {'success': True, 'fallback': True}, fallback_sql
    
    def _extract_sql_with_markers(self, agent_response) -> str:
        """Extract SQL using specific markers for more reliable parsing"""
        try:
            response_text = ""
            
            if isinstance(agent_response, dict):
                response_text = str(agent_response.get('output', ''))
                if not response_text:
                    response_text = str(agent_response.get('result', '')) or str(agent_response)
            else:
                response_text = str(agent_response)
            
            print(f"🔍 Extracting SQL from response (length: {len(response_text)})...")
            
            # Primary: Look for marker-wrapped queries
            marker_pattern = r'<sql_query>\s*(.*?)\s*</sql_query>'
            marker_matches = re.findall(marker_pattern, response_text, re.IGNORECASE | re.DOTALL)
            
            if marker_matches:
                sql_query = marker_matches[0].strip()
                if sql_query and 'SELECT' in sql_query.upper():
                    sql_query = self._clean_sql_query(sql_query)
                    # Always check for nested aggregates
                    sql_query = self._fix_nested_aggregates(sql_query)
                    if sql_query:  # Only return if not empty after fixing
                        print(f"✅ Found marked SQL query: {sql_query[:150]}...")
                        return sql_query
            
            # Fallback: Use existing regex patterns
            fallback_sql = self._extract_sql_fallback(response_text)
            if fallback_sql:
                # CRITICAL: Also check fallback SQL for nested aggregates
                fallback_sql = self._fix_nested_aggregates(fallback_sql)
                if fallback_sql:  # Only return if not empty after fixing
                    print(f"✅ Found fallback SQL query: {fallback_sql[:150]}...")
                    return fallback_sql
            
            print(f"⚠️ No valid SQL found in response. Content: {response_text[:300]}...")
            return ""
            
        except Exception as e:
            print(f"❌ SQL extraction failed: {e}")
            return ""
    
    def _extract_sql_fallback(self, response_text: str) -> str:
        """Fallback SQL extraction using regex patterns"""
        sql_patterns = [
            r'```sql\s*(.*?)\s*```',
            r'```\s*(SELECT.*?);?\s*```', 
            r'(SELECT\s+.*?FROM\s+.*?(?:WHERE.*?)?(?:ORDER BY.*?)?(?:LIMIT.*?)?);?'
        ]
        
        for pattern in sql_patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if matches:
                for match in matches:
                    sql_query = match.strip()
                    if sql_query and 'SELECT' in sql_query.upper() and 'FROM' in sql_query.upper():
                        return self._clean_sql_query(sql_query)
        
        return ""
    
    def _clean_sql_query(self, sql_query: str) -> str:
        """Clean and validate SQL query"""
        # Normalize whitespace
        sql_query = re.sub(r'\s+', ' ', sql_query).strip()
        
        # Check for placeholder SQL and reject it
        if '...' in sql_query or sql_query == 'SELECT ... ;':
            print("⚠️ Detected placeholder SQL, rejecting...")
            return ""
        
        # Ensure semicolon
        if not sql_query.endswith(';'):
            sql_query += ';'
        
        # Remove trailing comma before semicolon
        if sql_query.rstrip(';').endswith(','):
            sql_query = sql_query.rstrip(';').rstrip(',') + ';'
        
        # Remove comments
        if '--' in sql_query:
            sql_query = sql_query.split('--')[0].strip()
            if not sql_query.endswith(';'):
                sql_query += ';'
        
        # Fix common GROUP BY issues
        sql_query = self._fix_group_by_issues(sql_query)
        
        return sql_query
    
    def _fix_group_by_issues(self, sql_query: str) -> str:
        """Fix common GROUP BY clause issues in PostgreSQL"""
        try:
            sql_upper = sql_query.upper()
            
            # Check if query has aggregate functions but problematic ORDER BY
            has_aggregates = any(func in sql_upper for func in ['AVG(', 'SUM(', 'COUNT(', 'MAX(', 'MIN('])
            has_order_by = 'ORDER BY' in sql_upper
            has_group_by = 'GROUP BY' in sql_upper
            
            if has_aggregates and has_order_by and not has_group_by:
                # Case: AVG/SUM with ORDER BY but no GROUP BY
                # This often happens with "last test" or "recent performance" queries
                
                if 'ts.start_time' in sql_query.lower():
                    # Replace ORDER BY ts.start_time with subquery approach
                    print("🔧 Fixing ORDER BY issue with aggregate function...")
                    
                    # Remove ORDER BY ts.start_time DESC LIMIT
                    pattern = r'ORDER BY\s+ts\.start_time\s+(DESC|ASC)?\s*(LIMIT\s+\d+)?;?'
                    sql_query = re.sub(pattern, '', sql_query, flags=re.IGNORECASE)
                    
                    # Ensure proper ending
                    if not sql_query.rstrip().endswith(';'):
                        sql_query = sql_query.rstrip() + ';'
                    
                    print(f"✅ Fixed ORDER BY issue in aggregate query")
            
            return sql_query
            
        except Exception as e:
            print(f"⚠️ Error fixing GROUP BY issues: {e}")
            return sql_query
    
    def _fix_nested_aggregates(self, sql_query: str) -> str:
        """Detect and fix nested aggregates in SQL queries"""
        try:
            if not sql_query or not sql_query.strip():
                return sql_query
            
            # Check for common nested aggregate patterns
            nested_patterns = [
                r'AVG\s*\(\s*CAST\s*\(\s*SUM\s*\(',  # AVG(CAST(SUM(...)))
                r'AVG\s*\(\s*SUM\s*\(',              # AVG(SUM(...))
                r'AVG\s*\(\s*COUNT\s*\(',            # AVG(COUNT(...))
                r'SUM\s*\(\s*AVG\s*\(',              # SUM(AVG(...))
                r'COUNT\s*\(\s*SUM\s*\(',            # COUNT(SUM(...))
                r'MAX\s*\(\s*SUM\s*\(',              # MAX(SUM(...))
                r'MIN\s*\(\s*AVG\s*\('               # MIN(AVG(...))
            ]
            
            # Check if query has nested aggregates
            has_nested = any(re.search(pattern, sql_query, re.IGNORECASE) for pattern in nested_patterns)
            
            if has_nested:
                print("🔧 Detected nested aggregates, applying automatic fix...")
                
                # Extract student_id from the query
                student_match = re.search(r"student_id\s*=\s*'([^']+)'", sql_query)
                if student_match:
                    student_id = student_match.group(1)
                    
                    # Determine the type of query and provide appropriate fix
                    if any(keyword in sql_query.lower() for keyword in ['average', 'avg', 'accuracy', 'percentage']):
                        # Average accuracy query - use simple calculation
                        fixed_sql = f"""SELECT 
    ROUND(
        (SUM(CASE WHEN ta.is_correct = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(ta.id)), 2
    ) as average_accuracy_percentage
FROM test_answers ta
JOIN test_sessions ts ON ta.session_id = ts.id
WHERE ts.student_id = '{student_id}' 
AND ts.is_completed = TRUE"""
                        
                        print("✅ Applied nested aggregates fix: Simple average accuracy calculation")
                        return fixed_sql.strip() + ';'
                    
                    elif 'subject' in sql_query.lower():
                        # Subject-wise performance query
                        fixed_sql = f"""SELECT 
    t.subject,
    COUNT(ta.id) as total_questions,
    SUM(CASE WHEN ta.is_correct = TRUE THEN 1 ELSE 0 END) as correct_answers,
    ROUND(
        (SUM(CASE WHEN ta.is_correct = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(ta.id)), 2
    ) as percentage
FROM test_answers ta
JOIN test_sessions ts ON ta.session_id = ts.id
JOIN questions q ON ta.question_id = q.id
JOIN topics t ON q.topic_id = t.id
WHERE ts.student_id = '{student_id}' 
AND ts.is_completed = TRUE
GROUP BY t.subject
ORDER BY percentage DESC"""
                        
                        print("✅ Applied nested aggregates fix: Subject performance query")
                        return fixed_sql.strip() + ';'
                
                # If we can't extract student_id or determine query type, return empty to trigger fallback
                print("⚠️ Complex nested aggregates detected, triggering fallback generation...")
                return ""
            
            # No nested aggregates found, return original query
            return sql_query
            
        except Exception as e:
            print(f"⚠️ Error fixing nested aggregates: {e}")
            return sql_query
    
    def _extract_sql_from_response(self, agent_response) -> str:
        """Extract SQL query from LangChain agent response"""
        try:
            # Handle different response types
            response_text = ""
            
            if isinstance(agent_response, dict):
                # LangChain agent returns a dict with 'output' key
                response_text = str(agent_response.get('output', ''))
                if not response_text:
                    # Try other possible keys
                    response_text = str(agent_response.get('result', ''))
                    if not response_text:
                        response_text = str(agent_response)
            else:
                response_text = str(agent_response)
            
            print(f"🔍 Extracting SQL from: {response_text[:200]}...")
            
            # Look for SQL patterns in the response
            sql_patterns = [
                r'```sql\s*(.*?)\s*```',  # SQL in code blocks
                r'```\s*(SELECT.*?);?\s*```',  # SELECT in code blocks
                r'(SELECT\s+[^;]+;)',  # Single SELECT query ending with semicolon
                r'(SELECT\s+.*?FROM\s+.*?(?:WHERE.*?)?(?:ORDER BY.*?)?(?:LIMIT.*?)?);?',  # Full SELECT query
                r'(WITH\s+.*?SELECT\s+.*?FROM\s+.*?(?:WHERE.*?)?(?:ORDER BY.*?)?(?:LIMIT.*?)?);?',  # CTE queries
            ]
            
            for pattern in sql_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
                if matches:
                    for match in matches:
                        sql_query = match.strip()
                        # Skip empty queries or just semicolons
                        if sql_query and sql_query != ';' and 'SELECT' in sql_query.upper():
                            # Clean up the SQL
                            sql_query = re.sub(r'\s+', ' ', sql_query)  # Normalize whitespace
                            sql_query = sql_query.rstrip(';') + ';'  # Ensure semicolon at end
                            
                            # Basic syntax validation
                            if sql_query.count(',') > 0 and sql_query.rstrip(';').endswith(','):
                                # Remove trailing comma before semicolon
                                sql_query = sql_query.rstrip(';').rstrip(',') + ';'
                            
                            # Ensure proper FROM clause exists
                            if 'SELECT' in sql_query.upper() and 'FROM' not in sql_query.upper():
                                print(f"⚠️ Skipping SQL without FROM clause: {sql_query[:100]}...")
                                continue
                            
                            # Take only the first query if multiple are found
                            if '--' in sql_query:
                                sql_query = sql_query.split('--')[0].strip()
                                if not sql_query.endswith(';'):
                                    sql_query += ';'
                            
                            print(f"✅ Found SQL query: {sql_query}")
                            return sql_query
            
            # If no specific SQL found but response contains SELECT, extract it
            if 'SELECT' in response_text.upper():
                # Find SELECT statements
                select_matches = re.findall(r'(SELECT[^;]+;?)', response_text, re.IGNORECASE | re.DOTALL)
                if select_matches:
                    for match in select_matches:
                        sql_query = match.strip()
                        if sql_query and sql_query != ';':
                            # Clean up and format
                            sql_query = re.sub(r'\s+', ' ', sql_query)
                            if not sql_query.endswith(';'):
                                sql_query += ';'
                            
                            # Basic syntax validation
                            if sql_query.count(',') > 0 and sql_query.rstrip(';').endswith(','):
                                # Remove trailing comma before semicolon
                                sql_query = sql_query.rstrip(';').rstrip(',') + ';'
                            
                            # Remove comments
                            if '--' in sql_query:
                                sql_query = sql_query.split('--')[0].strip()
                                if not sql_query.endswith(';'):
                                    sql_query += ';'
                            
                            print(f"✅ Extracted SQL from text: {sql_query}")
                            return sql_query
            
            print(f"⚠️ No valid SQL pattern found in response")
            return ""
            
        except Exception as e:
            print(f"❌ Failed to extract SQL from agent response: {e}")
            return ""

    def execute_sql_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query with enhanced error handling and result formatting"""
        print(f"📊 Executing SQL query: {sql_query[:100]}...")
        
        try:
            # Import Django here to avoid circular import issues
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                
                # Get column names
                columns = [col[0] for col in cursor.description] if cursor.description else []
                
                # Fetch all results
                rows = cursor.fetchall()
                
                if not rows:
                    print("⚠️ Query returned no results")
                    return []
                
                # Convert to list of dictionaries
                results = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        col_name = columns[i] if i < len(columns) else f"col_{i}"
                        
                        # Handle different data types
                        if value is None:
                            row_dict[col_name] = None
                        elif isinstance(value, (int, float, bool)):
                            row_dict[col_name] = value
                        elif isinstance(value, str):
                            row_dict[col_name] = value
                        else:
                            # Convert other types to string
                            row_dict[col_name] = str(value)
                    
                    results.append(row_dict)
                
                print(f"✅ Query returned {len(results)} rows")
                return results
                
        except Exception as e:
            print(f"❌ SQL execution error: {e}")
            # Return error information in a structured format
            return [{
                'error': True,
                'message': str(e),
                'query': sql_query[:200] + "..." if len(sql_query) > 200 else sql_query
            }]
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.sql_agent = None
            print("🧹 SQL Agent cleanup completed")
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get SQL Agent statistics"""
        return {
            'available': self.is_available(),
            'api_provider': 'Grok API',
            'model': 'llama-3.3-70b-versatile',
            'database_available': self._test_database_connection(),
            'cache_info': 'Django cache enabled'
        }
    
    def _test_database_connection(self) -> bool:
        """Test database connectivity"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                return True
        except:
            return False
    
    def generate_sql_and_execute(self, query: str, student_id: str, context: str = "") -> Dict[str, Any]:
        """
        Generate SQL query and execute it, returning the results with enhanced caching and performance
        """
        try:
            # Step 1: Generate SQL query (with caching)
            result, sql_query = self.generate_sql_query(student_id, query)
            
            if not result.get('success', False):
                return {
                    'success': False,
                    'error': 'Failed to generate SQL query',
                    'data': None,
                    'sql_query': None,
                    'cached': result.get('cached', False)
                }
            
            # Step 2: Execute SQL query using our enhanced execute method
            data = self.execute_sql_query(sql_query)
            
            # Check for errors in execution
            if data and len(data) == 1 and data[0].get('error'):
                return {
                    'success': False,
                    'error': data[0]['message'],
                    'data': None,
                    'sql_query': sql_query,
                    'cached': result.get('cached', False)
                }
            
            return {
                'success': True,
                'data': data,
                'sql_query': sql_query,
                'row_count': len(data),
                'cached': result.get('cached', False)
            }
            
        except Exception as e:
            print(f"❌ SQL generation and execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': None,
                'sql_query': sql_query if 'sql_query' in locals() else None,
                'cached': False
            }
