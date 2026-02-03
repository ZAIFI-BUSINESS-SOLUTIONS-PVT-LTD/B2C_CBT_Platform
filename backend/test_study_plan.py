"""
Test script for the new study plan endpoint.
Validates data collection, grouping, and LLM integration.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import StudentProfile, TestAnswer, TestSession
from neet_app.services.study_plan_service import (
    collect_wrong_answers_by_topic_and_test,
    generate_study_plan_from_misconceptions
)


def test_collector():
    """Test the wrong answer collector and grouping logic."""
    print("\n" + "="*80)
    print("Testing Wrong Answer Collector")
    print("="*80)
    
    # Find a student with completed tests
    students_with_tests = StudentProfile.objects.filter(
        testsession__is_completed=True
    ).distinct()[:5]
    
    if not students_with_tests:
        print("❌ No students with completed tests found")
        return None
    
    print(f"\n✅ Found {students_with_tests.count()} students with completed tests")
    
    # Test with the first student
    student = students_with_tests.first()
    print(f"\n📊 Testing with student: {student.user.username} (ID: {student.id})")
    
    # Get wrong answer count
    wrong_count = TestAnswer.objects.filter(
        session__student_id=student.id,
        session__is_completed=True,
        is_correct=False
    ).count()
    
    print(f"   Total wrong answers in all tests: {wrong_count}")
    
    # Test collector
    data = collect_wrong_answers_by_topic_and_test(student.id, max_tests=5)
    
    print(f"\n📈 Collection Results:")
    print(f"   Tests analyzed: {data['tests_analyzed']}")
    print(f"   Total wrong questions: {data['total_wrong_questions']}")
    print(f"   Topics with mistakes: {len(data['topics'])}")
    
    if data['topics']:
        print(f"\n📚 Top 3 Topics by Wrong Count:")
        for i, topic in enumerate(data['topics'][:3], 1):
            print(f"   {i}. {topic['topic_name']} ({topic['subject']}): {topic['total_wrong']} wrong")
            print(f"      Tests: {len(topic['tests'])}")
            
            # Show sample questions from first test
            if topic['tests']:
                first_test = topic['tests'][0]
                print(f"      Sample from '{first_test['test_name']}':")
                for q in first_test['questions'][:2]:
                    q_text = q['question_text'][:80] + "..." if len(q['question_text']) > 80 else q['question_text']
                    print(f"         - Q{q['question_id']}: {q_text}")
                    print(f"           Selected: {q['selected_option']} → {q['misconception'][:60]}...")
    
    return student.id


def test_study_plan_generation():
    """Test the full study plan generation with LLM."""
    print("\n" + "="*80)
    print("Testing Study Plan Generation (with LLM)")
    print("="*80)
    
    # Find a student with wrong answers
    student_id = test_collector()
    
    if not student_id:
        print("❌ Cannot test study plan generation without student data")
        return
    
    print(f"\n🤖 Generating study plan for student ID: {student_id}")
    print("   (This will call the Gemini LLM...)")
    
    try:
        result = generate_study_plan_from_misconceptions(student_id, max_tests=5)
        
        print(f"\n✅ Study Plan Generated!")
        print(f"   Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"\n📝 Analysis Summary:")
            print(f"   {result.get('analysis_summary', 'N/A')}")
            
            recommendations = result.get('recommendations', [])
            print(f"\n🎯 Top {len(recommendations)} Recommendations:")
            
            for rec in recommendations:
                print(f"\n   {rec['rank']}. {rec['title']}")
                print(f"      Priority: {rec.get('priority', 'N/A')}")
                print(f"      Affected Questions: {rec.get('affected_questions_count', 'N/A')}")
                print(f"      Estimated Time: {rec.get('estimated_time', 'N/A')}")
                print(f"      Reasoning: {rec.get('reasoning', 'N/A')[:100]}...")
                
                if rec.get('action_steps'):
                    print(f"      Action Steps:")
                    for step in rec['action_steps'][:3]:
                        print(f"         • {step}")
        
        elif result['status'] == 'insufficient_data':
            print(f"\n⚠️ {result.get('message', 'Insufficient data')}")
        
        else:
            print(f"\n❌ Error: {result.get('message', 'Unknown error')}")
        
        # Show supporting data summary
        supporting = result.get('supporting_data', {})
        print(f"\n📊 Supporting Data:")
        print(f"   Tests analyzed: {supporting.get('tests_analyzed', 0)}")
        print(f"   Wrong questions: {supporting.get('total_wrong_questions', 0)}")
        print(f"   Topics: {len(supporting.get('topics', []))}")
        
    except Exception as e:
        print(f"\n❌ Error generating study plan: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("Study Plan Service Test Suite")
    print("="*80)
    
    try:
        test_study_plan_generation()
        
        print("\n" + "="*80)
        print("✅ All Tests Completed")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
