"""
Rerun Results and Insights for a Test

This script accepts a test name (PlatformTest.test_name) and:
1. Finds all TestSessions for that test
2. Recalculates session aggregates (correct, incorrect, unanswered, subject scores)
3. Regenerates zone insights for each session
4. Regenerates student insights for each affected student

Usage:
    python manage.py shell
    >>> exec(open('scripts/rerun_results_and_insights.py').read())
    
Or with Django settings:
    python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings'); import django; django.setup(); exec(open('backend/scripts/rerun_results_and_insights.py').read())"
"""

import sys
import os
from collections import defaultdict
from django.db import transaction

# Ensure Django is set up
import django
if not django.apps.apps.ready:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
    django.setup()

from neet_app.models import (
    PlatformTest, TestSession, TestAnswer, 
    TestSubjectZoneInsight
)
from neet_app.services.zone_insights_service import compute_and_store_zone_insights

# ============================================================
# CONFIGURATION: Set the test name here
# ============================================================
TEST_NAME = "NEET 2024 Sample Test"  # Replace with actual test name
# ============================================================

print("=" * 80)
print(f"🔄 RERUN RESULTS AND INSIGHTS SCRIPT")
print(f"📝 Target Test Name: {TEST_NAME}")
print("=" * 80)

# 1) Find the PlatformTest by test_name
try:
    platform_test = PlatformTest.objects.get(test_name=TEST_NAME)
    print(f"✅ Found PlatformTest: {platform_test.test_name} (ID: {platform_test.id})")
except PlatformTest.DoesNotExist:
    print(f"❌ ERROR: No PlatformTest found with test_name='{TEST_NAME}'")
    print("Available tests:")
    for test in PlatformTest.objects.all()[:10]:
        print(f"  - {test.test_name}")
    sys.exit(1)

# 2) Find all TestSessions for this platform test
sessions_qs = TestSession.objects.filter(
    platform_test=platform_test,
    is_completed=True
).select_related('platform_test')

session_count = sessions_qs.count()
if session_count == 0:
    print(f"⚠️ No completed sessions found for test '{TEST_NAME}'")
    sys.exit(0)

print(f"📊 Found {session_count} completed session(s) for this test")

# Collect unique students
students_to_regen = set()
sessions_to_update = []

for session in sessions_qs:
    sessions_to_update.append(session)
    students_to_regen.add(session.student_id)

print(f"👥 Unique students: {len(students_to_regen)}")
print()

print("🔢 Step 1: Recalculating session aggregates and subject scores...")
for idx, session in enumerate(sessions_to_update, 1):
    try:
        print(f"  [{idx}/{len(sessions_to_update)}] Processing session {session.id} (Student: {session.student_id})")
        
        # Recompute counts from TestAnswer
        answers_qs = TestAnswer.objects.filter(session=session)
        answers_count = answers_qs.count()
        correct = answers_qs.filter(is_correct=True).count()
        incorrect = answers_qs.filter(is_correct=False).count()

        # Prefer session.total_questions (configured test size) as authoritative
        total_q = getattr(session, 'total_questions', None) or 0
        if not total_q or total_q <= 0:
            total_q = answers_count

        # Compute unanswered as remaining questions not present in answers
        unanswered = total_q - (correct + incorrect)
        if unanswered < 0:
            # Defensive fallback: count is_correct is NULL rows
            unanswered = answers_qs.filter(is_correct__isnull=True).count()

        # Update session fields (don't overwrite total_questions if it was set)
        session.correct_answers = correct
        session.incorrect_answers = incorrect
        session.unanswered = unanswered
        if not getattr(session, 'total_questions', None) or session.total_questions <= 0:
            session.total_questions = total_q
        session.save(update_fields=['correct_answers','incorrect_answers','unanswered','total_questions'])
        
        # Recompute subject-wise scores (this method saves subject score fields)
        try:
            session.calculate_and_update_subject_scores()
            print(f"    ✅ Updated aggregates: {correct}C / {incorrect}I / {unanswered}U")
        except Exception as e:
            print(f"    ⚠️ Error calculating subject scores: {e}")
            
    except Exception as e:
        print(f"    ❌ Error processing session {session.id}: {e}")
        continue

print("✅ Session aggregates and subject scores updated.")
print()
# 4) Regenerate zone insights for each session
print("🎯 Step 2: Regenerating zone insights for each session...")
for idx, session in enumerate(sessions_to_update, 1):
    try:
        print(f"  [{idx}/{len(sessions_to_update)}] Generating zone insights for session {session.id}")
        
        # Delete existing zone insights for this session (to avoid stale data)
        deleted_count = TestSubjectZoneInsight.objects.filter(test_session=session).delete()[0]
        if deleted_count > 0:
            print(f"    🗑️ Deleted {deleted_count} old zone insight(s)")
        
        # Generate fresh zone insights using the service
        result = compute_and_store_zone_insights(session.id)
        
        if result:
            subjects = ', '.join(result.keys())
            print(f"    ✅ Generated zone insights for: {subjects}")
        else:
            print(f"    ⚠️ No zone insights generated (no subjects or questions found)")
            
    except Exception as e:
        print(f"    ❌ Failed to regenerate zone insights for session {session.id}: {e}")
        continue

print("✅ Zone insights regeneration complete.")
print()

# 5) Regenerate student insights for each affected student
print("🧠 Student-level insights regeneration skipped — feature removed.")
        traceback.print_exc()
        continue

print("✅ Student insights regeneration complete.")
print()
print("=" * 80)
print("🎉 RERUN COMPLETE")
print(f"   Sessions processed: {len(sessions_to_update)}")
print(f"   Students updated: {len(students_to_regen)}")
print("=" * 80)
print()
print("💡 Next steps:")
print("   1. Verify session aggregates in Django admin or database")
print("   2. Check zone insights: /api/zone-insights/test/<test_id>/")
print("   3. Check student insights: /api/insights/student/<student_id>/")
print("   4. Review frontend dashboards to confirm updated data")

