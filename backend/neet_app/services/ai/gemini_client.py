"""
Gemini Client with API Key Rotation
Handles Google Gemini AI interactions with automatic key rotation to avoid rate limits
"""
import os
import time
import threading
from typing import Optional, List
import google.generativeai as genai
from django.conf import settings


class GeminiClient:
    """
    Google Gemini AI client with automatic API key rotation
    """
    
    def __init__(self):
        """Initialize Gemini client with multiple API keys"""
        # Load API keys from settings or environment
        self.api_keys = self._load_api_keys()
        self.current_key_index = 0
        self.rate_limit_delay = 1  # seconds between requests
        self.last_request_time = 0
        self.lock = threading.Lock()
        
        # Model configuration
        # Allow overriding max output tokens via environment or Django settings
        self.model_name = "gemini-2.5-flash"
        self.temperature = 0.3
        try:
            # prefer Django settings if available
            self.max_output_tokens = int(getattr(settings, 'GEMINI_MAX_OUTPUT_TOKENS', os.getenv('GEMINI_MAX_OUTPUT_TOKENS', 4096)))
        except Exception:
            self.max_output_tokens = 4096
        
        # Initialize with first available key
        self.client = None
        self._initialize_client()
        
        print(f"GeminiClient initialized with {len(self.api_keys)} API keys")
    
    def _load_api_keys(self) -> List[str]:
        """Load API keys from settings or environment variables"""
        # Check settings first
        if hasattr(settings, 'GEMINI_API_KEYS') and settings.GEMINI_API_KEYS:
            return settings.GEMINI_API_KEYS
        
        # Check for environment variables (GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.)
        api_keys = []
        for i in range(1, 11):  # Support up to 10 keys
            key = os.getenv(f'GEMINI_API_KEY_{i}')
            if key:
                api_keys.append(key.strip())
        
        # Fallback to single key
        if not api_keys:
            single_key = os.getenv('GEMINI_API_KEY')
            if single_key:
                api_keys.append(single_key.strip())
        
        if not api_keys:
            print("Warning: No Gemini API keys found!")
            print("Add your API keys to settings.py as GEMINI_API_KEYS list or")
            print("set environment variables GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.")
        
        return api_keys
    
    def _initialize_client(self):
        """Initialize Gemini client with current API key"""
        if not self.api_keys:
            self.client = None
            return
        
        try:
            current_key = self.api_keys[self.current_key_index]
            genai.configure(api_key=current_key)
            
            # Configure safety settings for educational content
            safety_settings = {
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }
            
            self.client = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_output_tokens,
                },
                safety_settings=safety_settings
            )
            print(f"Initialized Gemini client with API key {self.current_key_index + 1}")
        except Exception as e:
            print(f"Error initializing Gemini client: {e}")
            self.client = None
    
    def _rotate_api_key(self):
        """Rotate to the next API key"""
        with self.lock:
            old_index = self.current_key_index
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            print(f"🔄 Rotating from API key {old_index + 1} to API key {self.current_key_index + 1}")
            self._initialize_client()
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def generate_response(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generate response with automatic key rotation on rate limit errors
        """
        if not self.client:
            return self._get_fallback_response()
        
        for attempt in range(max_retries):
            try:
                # Rate limiting
                self._wait_for_rate_limit()
                
                # Generate response
                response = self.client.generate_content(prompt)
                
                if response and response.candidates:
                    # Try simple text accessor first
                    try:
                        if response.text:
                            return response.text.strip()
                    except (ValueError, AttributeError):
                        # If simple accessor fails, use parts structure
                        pass
                    
                    # Extract text from response parts
                    text_parts = []
                    print(f"🔍 Processing {len(response.candidates)} candidates")
                    
                    for i, candidate in enumerate(response.candidates):
                        print(f"Candidate {i}: finish_reason={candidate.finish_reason}")
                        
                        # Check for safety blocks
                        if candidate.finish_reason == 2:  # SAFETY
                            print(f"🚫 Response blocked by safety filters")
                            if candidate.safety_ratings:
                                for rating in candidate.safety_ratings:
                                    print(f"   Safety: {rating.category} - {rating.probability}")
                            return "I cannot analyze this conversation due to content safety restrictions. Please try with a shorter or different conversation."
                        elif candidate.finish_reason == 3:  # RECITATION
                            print(f"🚫 Response blocked due to recitation concerns")
                            return "I cannot provide this response due to recitation concerns. Please rephrase your request."
                        
                        if candidate.content and candidate.content.parts:
                            print(f"  Has {len(candidate.content.parts)} content parts")
                            for j, part in enumerate(candidate.content.parts):
                                print(f"    Part {j}: type={type(part)}, has_text={hasattr(part, 'text')}")
                                if hasattr(part, 'text') and part.text:
                                    text_parts.append(part.text)
                                    print(f"    ✅ Added text: {part.text[:50]}...")
                                elif hasattr(part, 'text'):
                                    print(f"    ❌ Text attribute empty")
                                else:
                                    print(f"    ❌ No text attribute, available: {[attr for attr in dir(part) if not attr.startswith('_')]}")
                        else:
                            print(f"  ❌ No content or parts")
                    
                    if text_parts:
                        combined = ''.join(text_parts).strip()
                        print(f"✅ Successfully combined {len(text_parts)} text parts: {combined[:100]}...")
                        return combined
                    else:
                        print("❌ No text content found in any response parts")
                        return self._get_fallback_response()
                else:
                    print("Warning: Empty response or no candidates from Gemini")
                    return self._get_fallback_response()
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check for rate limit or quota errors (more comprehensive)
                rate_limit_terms = [
                    'rate limit', 'quota', 'resource exhausted', '429',
                    'generativelanguage.googleapis.com/generate_content_free_tier_requests',
                    'generaterequeststperdayperprojectpermodel-freetier',
                    'exceeded your current quota',
                    'quota_value: 50'  # Free tier limit
                ]
                
                if any(term in error_msg for term in rate_limit_terms):
                    print(f"🚫 Rate limit/quota hit on API key {self.current_key_index + 1}")
                    print(f"   Error: {str(e)[:200]}...")
                    
                    # Don't retry with same key if all keys tried
                    if attempt >= len(self.api_keys):
                        print("❌ All API keys exhausted, returning fallback response")
                        return self._get_fallback_response()
                    
                    self._rotate_api_key()
                    print(f"🔄 Rotated to API key {self.current_key_index + 1}, retrying...")
                    
                    # Wait a bit before retrying with new key
                    time.sleep(2)
                    continue
                
                # Check for authentication errors
                elif any(term in error_msg for term in ['authentication', 'invalid api key', '401', '403']):
                    print(f"🔑 Authentication error with API key {self.current_key_index + 1}")
                    print(f"   Error: {str(e)[:200]}...")
                    self._rotate_api_key()
                    continue
                
                # Other errors
                else:
                    print(f"⚠️ Gemini API error (attempt {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        return self._get_fallback_response()
                    time.sleep(1)
        
        return self._get_fallback_response()
    
    def _get_fallback_response(self) -> str:
        """Get fallback response when AI is unavailable"""
        return "I'm currently experiencing technical difficulties. Please try your question again in a moment."
    
    def is_available(self) -> bool:
        """Check if Gemini client is available"""
        return self.client is not None and len(self.api_keys) > 0
    
    def get_api_key_status(self) -> dict:
        """Get status of all API keys"""
        return {
            'total_keys': len(self.api_keys),
            'current_key_index': self.current_key_index,
            'current_key_masked': f"***{self.api_keys[self.current_key_index][-4:]}" if self.api_keys else None,
            'client_available': self.is_available()
        }
    
    def test_all_keys(self) -> dict:
        """Test all API keys to check their validity"""
        results = {}
        original_index = self.current_key_index
        
        for i, key in enumerate(self.api_keys):
            try:
                self.current_key_index = i
                self._initialize_client()
                
                # Test with a simple prompt
                test_response = self.generate_response("Say 'OK' if this API key works.")
                results[f'key_{i+1}'] = {
                    'status': 'working' if 'OK' in test_response else 'limited',
                    'response': test_response[:50] + '...' if len(test_response) > 50 else test_response
                }
            except Exception as e:
                results[f'key_{i+1}'] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Restore original key
        self.current_key_index = original_index
        self._initialize_client()
        
        return results
