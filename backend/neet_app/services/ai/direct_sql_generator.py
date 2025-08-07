"""
Direct SQL Query Generator (No LangChain)
Replaces the LangChain SQL agent with a direct approach using our Gemini client
"""
import re
import time
import logging
from typing import Optional, Tuple, Dict, Any
from django.db import connection

logger = logging.getLogger(__name__)


class DirectSQLGenerator:
    """Direct SQL generator without LangChain dependencies"""
    
    def __init__(self, gemini_client):
        self.gemini_client = gemini_client
    
    def is_available(self) -> bool:
        """Check if direct SQL generator is available"""
        return self.gemini_client.is_available()
    
    def generate_sql_query(self, student_id: str, user_message: str) -> Tuple[Dict[str, Any], str]:
        """Generate SQL query using direct Gemini API calls with proper rotation"""
        if not self.is_available():
            raise ValueError("Direct SQL Generator not available")
        
        max_retries = len(self.gemini_client.api_keys) if self.gemini_client.api_keys else 1
        
        for attempt in range(max_retries):
            try:
                sql_prompt = f"""Generate a PostgreSQL SELECT query to answer: "{user_message}" for student {student_id}

Tables:
- test_answers (session_id, question_id, is_correct, selected_answer, time_taken)
- test_sessions (id, student_id, start_time, is_completed) 
- questions (id, topic_id)
- topics (id, name, subject)

ANALYZE THE QUERY TYPE:

If asking for "last X tests" or "over X tests" or "test-by-test":
SELECT 
    ts.start_time::date as test_date,
    COUNT(ta.id) as total_questions,
    SUM(CASE WHEN ta.is_correct THEN 1 ELSE 0 END) as correct_answers,
    ROUND((SUM(CASE WHEN ta.is_correct THEN 1 ELSE 0 END)::numeric / COUNT(ta.id) * 100), 2) as accuracy_percentage
FROM test_answers ta 
JOIN test_sessions ts ON ta.session_id = ts.id 
JOIN questions q ON ta.question_id = q.id 
JOIN topics t ON q.topic_id = t.id 
WHERE ts.student_id = '{student_id}' AND ts.is_completed = TRUE AND t.subject ILIKE '%chemistry%'
GROUP BY ts.id, ts.start_time 
ORDER BY ts.start_time DESC 
LIMIT 10;

If asking for overall subject performance:
SELECT t.subject, COUNT(*) total, SUM(CASE WHEN ta.is_correct THEN 1 ELSE 0 END) correct,
ROUND((SUM(CASE WHEN ta.is_correct THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100), 2) as percentage
FROM test_answers ta 
JOIN test_sessions ts ON ta.session_id = ts.id 
JOIN questions q ON ta.question_id = q.id 
JOIN topics t ON q.topic_id = t.id 
WHERE ts.student_id = '{student_id}' AND ts.is_completed = TRUE AND t.subject ILIKE '%chemistry%'
GROUP BY t.subject;

CRITICAL RULES:
- If using GROUP BY with ts.start_time, MUST include ts.id in GROUP BY too
- For "last X tests", group by individual test sessions (ts.id, ts.start_time)
- For overall performance, group by t.subject only
- Always include WHERE ts.student_id = '{student_id}' AND ts.is_completed = TRUE

Return only the SQL query that matches the question type:"""
                
                # Use our Gemini client directly with proper rotation
                response = self.gemini_client.generate_response(sql_prompt)
                
                if response:
                    sql_query = self._extract_sql_from_response(response)
                    if sql_query:
                        print(f"🤖 Direct SQL Generator created query: {sql_query}")
                        return {'success': True}, sql_query
                
                raise Exception("No valid SQL query generated")
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check for rate limit errors
                rate_limit_terms = [
                    'rate limit', 'quota', 'resource exhausted', '429',
                    'exceeded your current quota', 'quota_value: 50'
                ]
                
                is_rate_limit = any(term in error_msg for term in rate_limit_terms)
                
                if is_rate_limit:
                    print(f"🚫 Rate limit hit on Direct SQL Generator (API key {self.gemini_client.current_key_index + 1})")
                    
                    # Use our working rotation method
                    if hasattr(self.gemini_client, 'rotate_to_next_key'):
                        if self.gemini_client.rotate_to_next_key():
                            print(f"🔄 Rotated to API key {self.gemini_client.current_key_index + 1}")
                            if attempt < max_retries - 1:
                                time.sleep(1)
                                continue
                
                print(f"❌ Direct SQL Generator failed: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"All API keys exhausted. Last error: {e}")
    
    def _extract_sql_from_response(self, response_text: str) -> str:
        """Extract SQL query from response"""
        try:
            print(f"🔍 Extracting SQL from response: {response_text[:200]}...")
            
            # Look for SQL patterns
            sql_patterns = [
                r'```sql\s*(.*?)\s*```',  # SQL in code blocks
                r'```\s*(SELECT.*?);?\s*```',  # SELECT in code blocks  
                r'(SELECT\s+[^;]+;)',  # Single SELECT query
                r'(SELECT.*?FROM.*?;)',  # Basic SELECT FROM pattern
            ]
            
            for pattern in sql_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE | re.DOTALL)
                if matches:
                    sql_query = matches[0].strip()
                    if sql_query and 'SELECT' in sql_query.upper():
                        # Clean up
                        sql_query = re.sub(r'\s+', ' ', sql_query)
                        if not sql_query.endswith(';'):
                            sql_query += ';'
                        print(f"✅ Found SQL with pattern: {sql_query}")
                        return sql_query
            
            # Fallback: find any SELECT statement (more aggressive)
            if 'SELECT' in response_text.upper():
                # Try to extract everything from SELECT to semicolon or end
                select_match = re.search(r'(SELECT.*?)(?:;|\n\n|$)', response_text, re.IGNORECASE | re.DOTALL)
                if select_match:
                    sql_query = select_match.group(1).strip()
                    sql_query = re.sub(r'\s+', ' ', sql_query)  # Normalize whitespace
                    if not sql_query.endswith(';'):
                        sql_query += ';'
                    print(f"✅ Extracted SQL fallback: {sql_query}")
                    return sql_query
            
            print(f"❌ No SQL found in response")
            return ""
            
        except Exception as e:
            print(f"❌ Failed to extract SQL: {e}")
            return ""
    
    def generate_sql_and_execute(self, query: str, student_id: str, context: str = ""):
        """Generate SQL and execute it, returning formatted results"""
        try:
            # Generate the SQL query
            sql_query = self.generate_sql(query, student_id)
            
            if not sql_query:
                return {'success': False, 'error': 'Could not generate SQL query'}
            
            # Execute the query
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
            
            # Convert results to list of dictionaries
            data = []
            for row in results:
                row_dict = {}
                for i, value in enumerate(row):
                    # Handle datetime and decimal serialization
                    if hasattr(value, 'isoformat'):
                        row_dict[columns[i]] = value.isoformat()
                    elif str(type(value).__name__) == 'Decimal':
                        row_dict[columns[i]] = float(value)
                    else:
                        row_dict[columns[i]] = value
                data.append(row_dict)
            
            return {
                'success': True,
                'data': data,
                'sql_query': sql_query,
                'row_count': len(data)
            }
            
        except Exception as e:
            logger.error(f"Error in generate_sql_and_execute: {str(e)}")
            return {'success': False, 'error': str(e)}

    def generate_sql(self, query: str, student_code: str) -> str:
        """Generate SQL query (just the SQL string)"""
        try:
            # Use internal method to generate SQL
            result, sql_query = self.generate_sql_query(query, student_code)
            
            if result.get('success', False) and sql_query:
                return sql_query
            else:
                logger.warning(f"Failed to generate SQL for query: {query}")
                return None
                
        except Exception as e:
            logger.error(f"Error in generate_sql: {str(e)}")
            return None
