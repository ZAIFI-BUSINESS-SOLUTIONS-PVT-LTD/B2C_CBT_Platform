"""
SQL Agent using Grok API with LangChain
Handles natural language to SQL conversion and execution
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
from langchain_groq import ChatGroq


class SQLAgentGrok:
    """SQL Agent using Grok API with simplified architecture"""
    
    def __init__(self):
        self.llm = None
        self.db = None
        self.cache_prefix = "sql_query_cache_grok"
        self.cache_timeout = 3600  # 1 hour cache
        self._initialize()
    
    def _initialize(self):
        """Initialize SQL Agent with Grok API"""
        self._create_database_connection()
        self._create_llm()
    
    def _create_database_connection(self):
        """Create database connection"""
        if not self.db:
            db_config = settings.DATABASES['default']
            db_url = f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"
            
            self.db = SQLDatabase.from_uri(
                db_url,
                include_tables=[
                    'student_profiles',
                    'test_sessions', 
                    'test_answers',
                    'topics',
                    'questions'
                ],
                sample_rows_in_table_info=1
            )
            print("🔗 Database connection established")
    
    def _create_llm(self):
        """Create LLM with Grok API"""
        try:
            import os
            grok_api_key = os.getenv('GROQ_API_KEY')
            if not grok_api_key:
                print("⚠️ GROQ_API_KEY not found in environment variables")
                return False
            
            self.llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                groq_api_key=grok_api_key,
                temperature=0.1,
                max_tokens=1024,
                timeout=15,
                max_retries=2
            )
            
            print(f"🔧 LLM configured with Grok API using Llama-3.3-70b-versatile model")
            return True
            
        except Exception as e:
            print(f"⚠️ LLM creation failed: {e}")
            self.llm = None
            return False
    
    def is_available(self) -> bool:
        """Check if SQL agent is available"""
        return self.llm is not None and self.db is not None
    
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
    
    def generate_sql_query(self, student_id: str, user_message: str) -> Tuple[Dict[str, Any], str]:
        """Generate SQL query using Grok API"""
        if not self.is_available():
            return self._generate_fallback_response(student_id, user_message)
        
        # Check cache first
        cached_sql = self._get_cached_query(student_id, user_message)
        if cached_sql:
            return {'success': True, 'cached': True}, cached_sql
        
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 SQL Generation attempt {attempt + 1}/{max_retries} using Grok API")
                
                # Get database schema context
                schema_info = self._get_schema_context()
                
                # Create optimized prompt
                prompt = f"""You are a PostgreSQL query generator for NEET student performance analysis.

DATABASE SCHEMA:
{schema_info}

TASK: Generate a PostgreSQL query for student '{student_id}': "{user_message}"

RULES:
1. Use test_answers table for performance data (NOT test_sessions score fields)
2. Always filter: student_id = '{student_id}' AND is_completed = TRUE
3. JOIN with test_sessions, questions, topics as needed
4. Use PostgreSQL syntax only
5. Limit results to 20 rows maximum

COMMON PATTERNS:
- Subject performance: GROUP BY t.subject, calculate percentages
- Individual tests: GROUP BY ts.id, ts.start_time
- Recent performance: ORDER BY ts.start_time DESC

IMPORTANT: Wrap your final SQL query in <sql_query>...</sql_query> tags.

Example:
<sql_query>
SELECT t.subject, COUNT(*) as total, SUM(CASE WHEN ta.is_correct THEN 1 ELSE 0 END) as correct
FROM test_answers ta
JOIN test_sessions ts ON ta.session_id = ts.id  
JOIN questions q ON ta.question_id = q.id
JOIN topics t ON q.topic_id = t.id
WHERE ts.student_id = '{student_id}' AND ts.is_completed = TRUE
GROUP BY t.subject
ORDER BY correct DESC LIMIT 10;
</sql_query>
"""
                
                # Generate SQL using LLM
                response = self.llm.invoke(prompt)
                
                # Extract SQL from response
                if hasattr(response, 'content'):
                    response_text = response.content
                else:
                    response_text = str(response)
                
                sql_query = self._extract_sql_from_response(response_text)
                
                if sql_query:
                    print(f"🤖 Generated SQL: {sql_query[:100]}...")
                    self._cache_query(student_id, user_message, sql_query)
                    return {'success': True, 'cached': False}, sql_query
                else:
                    raise Exception("No valid SQL extracted from response")
                    
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed: {str(e)[:100]}...")
                
                if attempt == max_retries - 1:
                    print("❌ All retries exhausted, using fallback")
                    return self._generate_fallback_response(student_id, user_message)
                
                # Wait before retry
                time.sleep(1)
        
        return self._generate_fallback_response(student_id, user_message)
    
    def _get_schema_context(self) -> str:
        """Get database schema context"""
        try:
            if self.db:
                return self.db.get_table_info()
        except Exception as e:
            print(f"⚠️ Could not get schema info: {e}")
        
        # Fallback schema description
        return """
        Tables: student_profiles, test_sessions, test_answers, topics, questions
        
        Key relationships:
        - test_answers.session_id -> test_sessions.id
        - test_answers.question_id -> questions.id  
        - questions.topic_id -> topics.id
        - test_sessions.student_id -> student_profiles.student_id
        
        Performance data is in test_answers.is_correct (boolean)
        """
    
    def _extract_sql_from_response(self, response_text: str) -> str:
        """Extract SQL query from LLM response"""
        try:
            print(f"🔍 Extracting SQL from response...")
            
            # Primary: Look for <sql_query> tags
            marker_pattern = r'<sql_query>\s*(.*?)\s*</sql_query>'
            marker_matches = re.findall(marker_pattern, response_text, re.IGNORECASE | re.DOTALL)
            
            if marker_matches:
                sql_query = marker_matches[0].strip()
                if sql_query and 'SELECT' in sql_query.upper():
                    return self._clean_sql_query(sql_query)
            
            # Fallback: Look for SQL patterns
            sql_patterns = [
                r'```sql\s*(.*?)\s*```',
                r'```\s*(SELECT.*?)\s*```',
                r'(SELECT\s+.*?FROM\s+.*?(?:WHERE.*?)?(?:GROUP BY.*?)?(?:ORDER BY.*?)?(?:LIMIT.*?)?);?'
            ]
            
            for pattern in sql_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE | re.DOTALL)
                if matches:
                    for match in matches:
                        sql_query = match.strip()
                        if sql_query and 'SELECT' in sql_query.upper() and 'FROM' in sql_query.upper():
                            return self._clean_sql_query(sql_query)
            
            print(f"⚠️ No valid SQL pattern found in response")
            return ""
            
        except Exception as e:
            print(f"❌ SQL extraction failed: {e}")
            return ""
    
    def _clean_sql_query(self, sql_query: str) -> str:
        """Clean and validate SQL query"""
        # Normalize whitespace
        sql_query = re.sub(r'\s+', ' ', sql_query).strip()
        
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
        
        return sql_query
    
    def _generate_fallback_response(self, student_id: str, user_message: str) -> Tuple[Dict[str, Any], str]:
        """Generate fallback SQL query when AI fails"""
        print("🔄 Generating fallback SQL query...")
        
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
        LIMIT 10;
        """.strip()
        
        print(f"📝 Fallback SQL: {fallback_sql[:100]}...")
        return {'success': True, 'fallback': True}, fallback_sql
    
    def execute_sql_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query with error handling"""
        print(f"📊 Executing SQL query: {sql_query[:100]}...")
        
        try:
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                
                # Get column names
                columns = [col[0] for col in cursor.description] if cursor.description else []
                
                # Fetch results
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
                            row_dict[col_name] = str(value)
                    
                    results.append(row_dict)
                
                print(f"✅ Query returned {len(results)} rows")
                return results
                
        except Exception as e:
            print(f"❌ SQL execution error: {e}")
            return [{
                'error': True,
                'message': str(e),
                'query': sql_query[:200] + "..." if len(sql_query) > 200 else sql_query
            }]
    
    def generate_sql_and_execute(self, query: str, student_id: str, context: str = "") -> Dict[str, Any]:
        """Generate and execute SQL query in one step"""
        try:
            # Generate SQL query
            result, sql_query = self.generate_sql_query(student_id, query)
            
            if not result.get('success', False):
                return {
                    'success': False,
                    'error': 'Failed to generate SQL query',
                    'data': None,
                    'sql_query': None,
                    'cached': result.get('cached', False)
                }
            
            # Execute SQL query
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
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.llm = None
            self.db = None
            print("🧹 SQL Agent cleanup completed")
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")
