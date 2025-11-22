"""
Find test sessions that actually have answers
"""
from neet_app.models import TestSession, TestAnswer, TestSubjectZoneInsight

print("=" * 60)
print("FINDING VALID TEST SESSIONS WITH ANSWERS")
print("=" * 60)

# Find test sessions with answers
sessions_with_answers = TestAnswer.objects.values('session_id').distinct()
session_ids = [s['session_id'] for s in sessions_with_answers]

print(f"\nTest sessions with answers: {session_ids}")

for sid in session_ids[:3]:  # Check first 3
    ts = TestSession.objects.filter(id=sid).first()
    if ts:
        answer_count = TestAnswer.objects.filter(session_id=sid).count()
        zone_count = TestSubjectZoneInsight.objects.filter(test_session_id=sid).count()
        
        print(f"\n{'=' * 60}")
        print(f"TEST SESSION {sid}")
        print(f"{'=' * 60}")
        print(f"Student: {ts.student_id}")
        print(f"Completed: {ts.is_completed}")
        print(f"Total Questions: {ts.total_questions}")
        print(f"Correct: {ts.correct_answers}, Incorrect: {ts.incorrect_answers}, Unanswered: {ts.unanswered}")
        print(f"TestAnswers: {answer_count}")
        print(f"Zone Insights: {zone_count}")
        print(f"\nSubject Topics:")
        print(f"  Physics: {len(ts.physics_topics)} topics")
        print(f"  Chemistry: {len(ts.chemistry_topics)} topics")
        print(f"  Botany: {len(ts.botany_topics)} topics")
        print(f"  Zoology: {len(ts.zoology_topics)} topics")
        print(f"  Biology: {len(ts.biology_topics)} topics")
        print(f"  Math: {len(ts.math_topics)} topics")
        
        # Check if subject classification method works
        if not any([ts.physics_topics, ts.chemistry_topics, ts.botany_topics, ts.zoology_topics, ts.biology_topics, ts.math_topics]):
            print(f"\n⚠️ WARNING: No subject topics classified!")
            print(f"Selected topics field: {ts.selected_topics}")
