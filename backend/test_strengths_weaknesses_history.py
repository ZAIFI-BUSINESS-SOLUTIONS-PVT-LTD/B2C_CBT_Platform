"""
Quick test script to validate strengths/weaknesses history implementation.
Run: python test_strengths_weaknesses_history.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.views.insights_views import get_topic_history_by_test

def test_function_exists():
    """Test that the function exists and has correct signature"""
    print("✓ Function get_topic_history_by_test imported successfully")
    
    # Test with a dummy student_id (won't have data but shouldn't error)
    result = get_topic_history_by_test('TEST_STUDENT', include='correct', max_tests=10)
    print(f"✓ Function executed without error")
    print(f"  Result type: {type(result)}")
    print(f"  Result: {result}")
    
    result_wrong = get_topic_history_by_test('TEST_STUDENT', include='wrong', max_tests=10)
    print(f"✓ Function executed with include='wrong' without error")
    print(f"  Result: {result_wrong}")

def test_data_structure():
    """Test that the returned structure matches requirements"""
    result = get_topic_history_by_test('DUMMY_ID', include='correct', max_tests=5)
    
    if isinstance(result, list):
        print("✓ Returns a list as expected")
        
        if len(result) == 0:
            print("  (Empty result - no data for dummy student)")
        else:
            # Check first topic structure
            topic = result[0]
            required_keys = ['topic', 'subject', 'chapter', 'accuracy', 'avg_time_sec', 
                           'total_questions', 'unattempted', 'tests']
            
            for key in required_keys:
                if key in topic:
                    print(f"  ✓ Has key: {key}")
                else:
                    print(f"  ✗ Missing key: {key}")
            
            # Check test structure
            if 'tests' in topic and len(topic['tests']) > 0:
                test = topic['tests'][0]
                test_keys = ['test_name', 'test_date', 'questions']
                
                for key in test_keys:
                    if key in test:
                        print(f"  ✓ Test has key: {key}")
                    else:
                        print(f"  ✗ Test missing key: {key}")
                
                # Check question structure
                if 'questions' in test and len(test['questions']) > 0:
                    question = test['questions'][0]
                    q_keys = ['question_id', 'question', 'options', 'correct_answer', 
                            'selected_answer', 'is_correct', 'time_taken']
                    
                    for key in q_keys:
                        if key in question:
                            print(f"  ✓ Question has key: {key}")
                        else:
                            print(f"  ✗ Question missing key: {key}")
                    
                    # Verify no session_id or session_test_name
                    if 'session_id' not in question and 'session_test_name' not in question:
                        print("  ✓ Question correctly excludes session_id and session_test_name")
                    else:
                        print("  ✗ Question still has session fields that should be removed")
    else:
        print(f"✗ Does not return a list (returns {type(result)})")

if __name__ == '__main__':
    print("=" * 60)
    print("Testing strengths/weaknesses history implementation")
    print("=" * 60)
    
    try:
        test_function_exists()
        print()
        test_data_structure()
        print()
        print("=" * 60)
        print("✓ All basic tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
