"""
Debug script to check zone insights data flow
"""
from neet_app.models import TestSession, TestAnswer, TestSubjectZoneInsight

print("=" * 60)
print("DATABASE STATE CHECK")
print("=" * 60)

# Count records
print(f"\nTestSessions: {TestSession.objects.count()}")
print(f"TestAnswers: {TestAnswer.objects.count()}")
print(f"ZoneInsights: {TestSubjectZoneInsight.objects.count()}")

# Get first test session
ts = TestSession.objects.first()
if ts:
    print(f"\n{'=' * 60}")
    print(f"FIRST TEST SESSION (ID={ts.id})")
    print(f"{'=' * 60}")
    print(f"Student ID: {ts.student_id}")
    print(f"Completed: {ts.is_completed}")
    print(f"Total Questions: {ts.total_questions}")
    print(f"Test Type: {ts.test_type}")
    
    # Try different query methods for TestAnswer
    print(f"\n--- TestAnswer Query Methods ---")
    
    # Method 1: Using session_id (FK lookup)
    count1 = TestAnswer.objects.filter(session_id=ts.id).count()
    print(f"Method 1 - filter(session_id={ts.id}): {count1} answers")
    
    # Method 2: Using session object
    count2 = TestAnswer.objects.filter(session=ts).count()
    print(f"Method 2 - filter(session=ts): {count2} answers")
    
    # Method 3: Check actual session_id values in database
    print(f"\n--- Sample TestAnswer Records ---")
    answers = TestAnswer.objects.all()[:5]
    for ans in answers:
        print(f"  Answer ID={ans.id}, session_id={ans.session_id}, question_id={ans.question_id}")
    
    # Check if zone insights exist
    print(f"\n--- Zone Insights for Test {ts.id} ---")
    zones = TestSubjectZoneInsight.objects.filter(test_session=ts)
    print(f"Zone insights count: {zones.count()}")
    for z in zones:
        print(f"  Subject: {z.subject}")
        print(f"    Steady: {len(z.steady_zone)} points")
        print(f"    Edge: {len(z.edge_zone)} points")
        print(f"    Focus: {len(z.focus_zone)} points")
    
    # Check subjects in test
    print(f"\n--- Subject Topics in Test ---")
    print(f"Physics topics: {len(ts.physics_topics)} - {ts.physics_topics[:2] if ts.physics_topics else []}")
    print(f"Chemistry topics: {len(ts.chemistry_topics)} - {ts.chemistry_topics[:2] if ts.chemistry_topics else []}")
    print(f"Botany topics: {len(ts.botany_topics)} - {ts.botany_topics[:2] if ts.botany_topics else []}")
    print(f"Zoology topics: {len(ts.zoology_topics)} - {ts.zoology_topics[:2] if ts.zoology_topics else []}")
    print(f"Math topics: {len(ts.math_topics)} - {ts.math_topics[:2] if ts.math_topics else []}")
else:
    print("\nNo test sessions found in database!")

print(f"\n{'=' * 60}")
print("END OF DEBUG CHECK")
print("=" * 60)
