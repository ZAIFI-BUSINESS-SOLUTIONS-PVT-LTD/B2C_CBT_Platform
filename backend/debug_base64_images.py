"""
Debug script to test base64 image handling.
Run this script to verify if your base64 images are being processed correctly.

Usage:
    python debug_base64_images.py <question_id>
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import Question
import base64


def test_base64_decode(base64_str):
    """Test if a base64 string can be decoded"""
    try:
        # Strip data URI if present
        if base64_str.startswith('data:'):
            base64_str = base64_str.split(',', 1)[1]
        
        # Try to decode
        decoded = base64.b64decode(base64_str)
        print(f"✓ Successfully decoded: {len(decoded)} bytes")
        return True
    except Exception as e:
        print(f"✗ Decode failed: {e}")
        return False


def debug_question_images(question_id):
    """Debug images for a specific question"""
    try:
        question = Question.objects.get(id=question_id)
        print(f"\n{'='*60}")
        print(f"Question ID: {question.id}")
        print(f"Question Text: {question.question[:100]}...")
        print(f"{'='*60}\n")
        
        # Check all image fields
        image_fields = [
            'question_image',
            'option_a_image',
            'option_b_image',
            'option_c_image',
            'option_d_image',
            'explanation_image'
        ]
        
        for field_name in image_fields:
            value = getattr(question, field_name)
            print(f"\n{field_name.upper()}:")
            print(f"  Present: {value is not None and len(value) > 0}")
            
            if value:
                print(f"  Length: {len(value)} characters")
                print(f"  First 50 chars: {value[:50]}")
                print(f"  Last 50 chars: ...{value[-50:]}")
                
                # Check if it starts with data URI
                if value.startswith('data:'):
                    print(f"  ⚠ WARNING: Still has data URI prefix! Backend should strip this.")
                
                # Try to decode
                print(f"  Decode test: ", end='')
                test_base64_decode(value)
            else:
                print(f"  No image data")
        
        print(f"\n{'='*60}")
        
    except Question.DoesNotExist:
        print(f"✗ Question with ID {question_id} not found")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def list_recent_questions_with_images():
    """List recent questions that have images"""
    print("\nRecent questions with images:")
    print(f"{'='*60}\n")
    
    questions = Question.objects.exclude(question_image__isnull=True).exclude(question_image='')[:10]
    
    if not questions:
        print("No questions with images found in database.")
        return
    
    for q in questions:
        print(f"ID: {q.id} | {q.question[:60]}...")
        print(f"  Image length: {len(q.question_image)} chars")
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_base64_images.py <question_id>")
        print("\nOr use 'list' to see recent questions with images:")
        print("python debug_base64_images.py list")
        sys.exit(1)
    
    if sys.argv[1] == 'list':
        list_recent_questions_with_images()
    else:
        try:
            question_id = int(sys.argv[1])
            debug_question_images(question_id)
        except ValueError:
            print("✗ Invalid question ID. Please provide a number.")
            sys.exit(1)


if __name__ == '__main__':
    main()
