"""
TTS Helper - Generate audio URLs by calling the Node TTS microservice
"""

import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# TTS service configuration (update with your deployment URL)
TTS_SERVICE_URL = getattr(settings, 'TTS_SERVICE_URL', 'http://localhost:3001')


def generate_insight_audio(text, test_id=None, institution_name=None):
    """
    Generate TTS audio by calling the Node microservice.
    
    Args:
        text (str): Text to convert to speech
        test_id (int, optional): Test session ID for filename tagging
        institution_name (str, optional): Institution name for gating
        
    Returns:
        str: Audio URL path (e.g., "/audio/insight-123-1234567890.mp3")
        None: If generation failed
    """
    try:
        endpoint = f"{TTS_SERVICE_URL}/api/generate-insight-audio"
        
        payload = {
            "text": text,
        }
        
        if test_id:
            payload["testId"] = str(test_id)
        
        if institution_name:
            payload["institution"] = institution_name
        
        logger.info(f"📨 Calling TTS service: {endpoint}")
        logger.debug(f"Payload: testId={test_id}, institution={institution_name}, text_length={len(text)}")
        
        # Call TTS microservice with timeout
        response = requests.post(
            endpoint,
            json=payload,
            timeout=10  # 10 second timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            audio_url = data.get('audioUrl')
            logger.info(f"✅ TTS audio generated: {audio_url}")
            return audio_url
        else:
            logger.error(f"❌ TTS service error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("❌ TTS service timeout (>10s)")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ TTS service connection error - is service running at {TTS_SERVICE_URL}?")
        return None
    except Exception as e:
        logger.error(f"❌ TTS generation failed: {str(e)}")
        return None


def is_demo_test_for_neet_bro(test_session):
    """
    Check if this is a demo test from Neet Bro Institute.
    
    Args:
        test_session (TestSession): Test session instance
        
    Returns:
        bool: True if this is a demo test from Neet Bro Institute
    """
    try:
        # Check if test is a platform test with institution
        if test_session.test_type != 'platform' or not test_session.platform_test:
            return False
        
        platform_test = test_session.platform_test
        
        # Check if it's an institution test
        if not platform_test.is_institution_test or not platform_test.institution:
            return False
        
        # Check institution name (case-insensitive)
        institution_name = platform_test.institution.name.lower()
        is_neet_bro = 'neet' in institution_name and 'bro' in institution_name
        
        # Check if test name contains "demo"
        test_name = platform_test.test_name.lower()
        is_demo = 'demo' in test_name
        
        return is_neet_bro and is_demo
        
    except Exception as e:
        logger.error(f"Error checking demo test status: {str(e)}")
        return False


def extract_checkpoint_text_for_audio(checkpoints_by_subject):
    """
    Extract first checkpoint from each subject and format for TTS.
    
    Format:
    "Hi, you have completed your first test successfully. Here are the feedback 
    of your performance from our end. For Physics: [first checkpoint checklist]. 
    For Chemistry: [first checkpoint checklist]..."
    
    Args:
        checkpoints_by_subject (list): List of dicts with 'subject' and 'checkpoints' keys
        
    Returns:
        str: Formatted text for TTS
    """
    intro = "Hi, you have completed your first test successfully. Here are the feedback of your performance from our end. "
    
    checkpoint_texts = []
    
    for subject_data in checkpoints_by_subject:
        subject = subject_data.get('subject', '')
        checkpoints = subject_data.get('checkpoints', [])
        
        if checkpoints and len(checkpoints) > 0:
            # Get first checkpoint's checklist text
            first_checkpoint = checkpoints[0]
            checklist = first_checkpoint.get('checklist', '')
            
            if checklist:
                checkpoint_texts.append(f"For {subject}: {checklist}")
    
    if not checkpoint_texts:
        # Fallback if no checkpoints
        return intro + "Great job on completing the test!"
    
    full_text = intro + " ".join(checkpoint_texts)
    
    # Ensure text doesn't exceed max length (800 chars)
    if len(full_text) > 800:
        full_text = full_text[:797] + "..."
    
    return full_text
