#!/usr/bin/env python
"""
CLI Wrapper for Rerunning Test Results and Insights

This script provides a command-line interface to regenerate test results,
zone insights, and student insights for a specific test.

Usage:
    python scripts/rerun_test_insights.py --test-name "NEET 2024 Sample Test"
    python scripts/rerun_test_insights.py --test-name "JEE Mains Mock 1" --skip-llm
    python scripts/rerun_test_insights.py --list-tests

Options:
    --test-name TEXT    Name of the test to process (required unless --list-tests)
    --skip-llm          Skip LLM-based insight generation (faster, uses fallbacks)
    --list-tests        List all available tests and exit
    --help              Show this help message
"""

import os
import sys
import argparse
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
import django
django.setup()

from django.db import transaction
from neet_app.models import (
    PlatformTest, TestSession, TestAnswer, 
    TestSubjectZoneInsight, StudentInsight
)
# Try to import Celery tasks (optional). If Celery not configured or unavailable, we'll fall back.
from neet_app.views import insights_views
from neet_app.services.zone_insights_service import generate_all_subject_zones, generate_zone_insights_for_subject
try:
    from neet_app.tasks import generate_insights_task, generate_zone_insights_task
    CELERY_TASKS_AVAILABLE = True
except Exception:
    generate_insights_task = None
    generate_zone_insights_task = None
    CELERY_TASKS_AVAILABLE = False


def list_available_tests():
    """List all available platform tests."""
    tests = PlatformTest.objects.all().order_by('-created_at')
    
    if not tests.exists():
        print("❌ No platform tests found in database")
        return
    
    print("\n" + "=" * 80)
    print("📋 AVAILABLE PLATFORM TESTS")
    print("=" * 80)
    
    for test in tests:
        session_count = TestSession.objects.filter(
            platform_test=test, is_completed=True
        ).count()
        
        status = "✅ Active" if test.is_active else "❌ Inactive"
        test_type = f"[{test.test_type}]" if test.test_type else ""
        
        print(f"\n  Test Name: {test.test_name}")
        print(f"  Test Code: {test.test_code} {test_type}")
        print(f"  Status: {status}")
        print(f"  Sessions: {session_count} completed")
        print(f"  Created: {test.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    print("\n" + "=" * 80)


def recalculate_session_aggregates(session):
    """Recalculate and update session aggregates and subject scores."""
    # Recompute counts from TestAnswer
    # Important: some TestAnswer rows may exist for every question but have selected_answer=None
    # while is_correct=False. Treat any row with selected_answer==None as UNANSWERED regardless
    # of the is_correct flag. We therefore compute attempted count from selected_answer,
    # derive incorrect = attempted - correct, and unanswered = total_questions - attempted.
    answers_qs = TestAnswer.objects.filter(session=session)
    answers_count = answers_qs.count()
    attempted = answers_qs.filter(selected_answer__isnull=False).count()
    correct = answers_qs.filter(is_correct=True).count()
    # Count incorrect as those with an actual selected_answer and is_correct explicitly False
    incorrect = answers_qs.filter(is_correct=False, selected_answer__isnull=False).count()

    # Determine total questions for the session. Prefer existing session.total_questions
    # (set when test was created or uploaded). If missing, fall back to number of answers rows.
    total_q = getattr(session, 'total_questions', None) or 0
    if not total_q or total_q <= 0:
        total_q = answers_count

    # Compute unanswered as remaining questions not attempted
    unanswered = total_q - attempted
    if unanswered < 0:
        # Defensive fallback: count rows where selected_answer is null
        unanswered = answers_qs.filter(selected_answer__isnull=True).count()

    # Update session fields
    session.correct_answers = correct
    session.incorrect_answers = incorrect
    session.unanswered = unanswered
    # Keep existing total_questions (do not overwrite with answer rows unless it was empty)
    if not getattr(session, 'total_questions', None) or session.total_questions <= 0:
        session.total_questions = total_q
    session.save(update_fields=['correct_answers', 'incorrect_answers', 'unanswered', 'total_questions'])
    
    # Recompute subject-wise scores
    session.calculate_and_update_subject_scores()
    
    return correct, incorrect, unanswered


def regenerate_zone_insights(session):
    """Regenerate zone insights for a session."""
    # Delete existing zone insights to avoid duplicates/stale entries
    deleted_count = TestSubjectZoneInsight.objects.filter(test_session=session).delete()[0]

    # Build insights using the same answer-driven grouping logic used by the view
    # This avoids relying on TestSession topic lists which may be missing/incorrect.
    try:
        # Fetch all answers for the session and group by normalized subject name
        answers_qs = TestAnswer.objects.filter(session_id=session.id).select_related('question__topic')

        def normalize_subject_name(s: str) -> str:
            if not s:
                return 'Other'
            s_low = s.lower()
            if 'physics' in s_low:
                return 'Physics'
            if 'chemistry' in s_low:
                return 'Chemistry'
            if 'botany' in s_low or 'plant' in s_low:
                return 'Botany'
            if 'zoology' in s_low or 'animal' in s_low:
                return 'Zoology'
            if 'biology' in s_low or 'bio' in s_low:
                return 'Biology'
            if 'math' in s_low or 'algebra' in s_low or 'geometry' in s_low:
                return 'Math'
            return s.strip()

        grouped = {}
        for a in answers_qs:
            q = a.question
            topic = getattr(q, 'topic', None)
            subj_raw = getattr(topic, 'subject', None) if topic else None
            subj = normalize_subject_name(subj_raw)
            grouped.setdefault(subj, []).append(a)

        results = {}

        for subj, ans_list in grouped.items():
            # Build question payloads from answers (same shape as view/service expects)
            questions_payload = []
            for a in ans_list:
                q = a.question
                options = {
                    'A': getattr(q, 'option_a', None),
                    'B': getattr(q, 'option_b', None),
                    'C': getattr(q, 'option_c', None),
                    'D': getattr(q, 'option_d', None),
                }
                questions_payload.append({
                    'question_id': q.id,
                    'question': (q.question if getattr(q, 'question', None) else ''),
                    'options': options,
                    'correct_answer': getattr(q, 'correct_answer', None),
                    'selected_answer': a.selected_answer if a.selected_answer else None,
                    'is_correct': a.is_correct,
                    'time_taken': a.time_taken or 0,
                })

            subj_norm = normalize_subject_name(subj)

            if not questions_payload:
                print(f"    ⚠️ No answers/questions for subject {subj_norm}, skipping")
                continue

            # Generate zone insights for this subject using the service function
            try:
                zones = generate_zone_insights_for_subject(subj, questions_payload)
            except Exception as e:
                print(f"    ❌ Error generating zones for {subj_norm}: {e}")
                zones = {'steady_zone': [], 'edge_zone': [], 'focus_zone': []}

            # Persist into TestSubjectZoneInsight (use student_id field since we have session.student_id)
            try:
                TestSubjectZoneInsight.objects.update_or_create(
                    test_session=session,
                    subject=subj_norm,
                    defaults={
                        'student_id': session.student_id,
                        'steady_zone': zones.get('steady_zone', []),
                        'edge_zone': zones.get('edge_zone', []),
                        'focus_zone': zones.get('focus_zone', []),
                        'questions_analyzed': questions_payload
                    }
                )
                results[subj_norm] = zones
                print(f"    💾 Saved zone insights for {subj_norm}")
            except Exception as e:
                print(f"    ❌ Failed to save zone insight for {subj_norm}: {e}")
                continue

        return results, deleted_count

    except Exception as e:
        print(f"    ❌ Error regenerating zone insights for session {session.id}: {e}")
        return {}, deleted_count

'''
def regenerate_student_insights(student_id, skip_llm=False):
    """Regenerate student insights."""
    # If Celery is available prefer enqueuing the async task which handles full insight generation
    try:
        if CELERY_TASKS_AVAILABLE and insights_views.is_celery_worker_available():
            # enqueue task with force_regenerate flag
            generate_insights_task.delay(student_id, {}, True)
            return True
    except Exception:
        # if enqueue fails, fall back to synchronous generation below
        pass

    thresholds = insights_views.get_thresholds()
    all_metrics = insights_views.calculate_topic_metrics(student_id)
    
    if not all_metrics or 'topics' not in all_metrics:
        # Save empty insight
        empty_response = {
            'status': 'success',
            'data': {
                'strength_topics': [],
                'weak_topics': [],
                'improvement_topics': [],
                'last_test_topics': [],
                'unattempted_topics': [],
                'thresholds_used': thresholds,
                'summary': {
                    'total_topics_analyzed': 0,
                    'total_tests_taken': 0,
                    'unattempted_topics_count': 0,
                    'message': 'No test data available for analysis'
                },
                'cached': False
            }
        }
        insights_views.save_insights_to_database(student_id, empty_response)
        return False
    
    # Classify topics
    classification = insights_views.classify_topics(
        all_metrics['topics'], 
        all_metrics.get('overall_avg_time', 0), 
        thresholds
    )
    
    # Get last test data
    last_test_data = insights_views.get_last_test_metrics(student_id, thresholds)
    unattempted_topics = insights_views.get_unattempted_topics(all_metrics['topics'])
    
    # Generate LLM insights (optional)
    llm_insights = {}
    if not skip_llm:
        try:
            if classification.get('strength_topics'):
                llm_insights['strengths'] = insights_views.generate_llm_insights(
                    'strengths', classification['strength_topics']
                )
            if classification.get('weak_topics'):
                llm_insights['weaknesses'] = insights_views.generate_llm_insights(
                    'weaknesses', classification['weak_topics']
                )
            llm_insights['study_plan'] = insights_views.generate_llm_insights('study_plan', {
                'weak_topics': classification.get('weak_topics', []),
                'improvement_topics': classification.get('improvement_topics', []),
                'strength_topics': classification.get('strength_topics', []),
                'unattempted_topics': unattempted_topics
            })
            if last_test_data.get('last_test_topics'):
                llm_insights['last_test_feedback'] = insights_views.generate_llm_insights(
                    'last_test_feedback', last_test_data['last_test_topics']
                )
        except Exception as llm_error:
            print(f"    ⚠️ LLM insight generation failed: {llm_error}")
    
    # Build summary
    total_tests = TestSession.objects.filter(student_id=student_id, is_completed=True).count()
    latest_session = TestSession.objects.filter(
        student_id=student_id, is_completed=True
    ).order_by('-end_time').first()
    latest_session_id = latest_session.id if latest_session else None
    
    summary = {
        'total_topics_analyzed': len(all_metrics['topics']),
        'total_tests_taken': total_tests,
        'strengths_count': len(classification.get('strength_topics', [])),
        'weaknesses_count': len(classification.get('weak_topics', [])),
        'improvements_count': len(classification.get('improvement_topics', [])),
        'unattempted_topics_count': len(unattempted_topics),
        'overall_avg_time': round(all_metrics.get('overall_avg_time', 0), 2),
        'last_session_id': latest_session_id
    }
    
    # Build response
    response_data = {
        'status': 'success',
        'data': {
            **classification,
            **last_test_data,
            'unattempted_topics': unattempted_topics,
            'llm_insights': llm_insights,
            'thresholds_used': thresholds,
            'summary': summary,
            'cached': False
        }
    }
    
    # Save insights
    insights_views.save_insights_to_database(
        student_id, response_data, test_session_id=latest_session_id
    )
    
    return True
'''

def main():
    parser = argparse.ArgumentParser(
        description='Rerun test results and insights for a specific test',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--test-name',
        type=str,
        help='Name of the test to process (exact match)'
    )
    
    parser.add_argument(
        '--skip-llm',
        action='store_true',
        help='Skip LLM-based insight generation (faster)'
    )
    
    parser.add_argument(
        '--list-tests',
        action='store_true',
        help='List all available tests and exit'
    )
    
    args = parser.parse_args()
    
    # Handle list tests
    if args.list_tests:
        list_available_tests()
        return 0
    
    # Validate test name provided
    if not args.test_name:
        parser.print_help()
        print("\n❌ ERROR: --test-name is required (or use --list-tests to see available tests)")
        return 1
    
    # Main processing
    print("=" * 80)
    print(f"🔄 RERUN RESULTS AND INSIGHTS")
    print(f"📝 Test Name: {args.test_name}")
    print(f"⚡ Skip LLM: {args.skip_llm}")
    print("=" * 80)
    print()
    
    # Find the platform test
    try:
        platform_test = PlatformTest.objects.get(test_name=args.test_name)
        print(f"✅ Found PlatformTest: {platform_test.test_name} (ID: {platform_test.id})")
    except PlatformTest.DoesNotExist:
        print(f"❌ ERROR: No PlatformTest found with test_name='{args.test_name}'")
        print("\nUse --list-tests to see available tests")
        return 1
    except PlatformTest.MultipleObjectsReturned:
        print(f"❌ ERROR: Multiple tests found with test_name='{args.test_name}'")
        print("Please use a more specific test name")
        return 1
    
    # Find all completed sessions
    sessions = list(TestSession.objects.filter(
        platform_test=platform_test,
        is_completed=True
    ).select_related('platform_test'))
    
    if not sessions:
        print(f"⚠️ No completed sessions found for test '{args.test_name}'")
        return 0
    
    students = set(session.student_id for session in sessions)
    
    print(f"📊 Found {len(sessions)} completed session(s)")
    print(f"👥 Unique students: {len(students)}")
    print()
    
    # Step 1: Recalculate session aggregates
    print("🔢 Step 1: Recalculating session aggregates and subject scores...")
    for idx, session in enumerate(sessions, 1):
        try:
            print(f"  [{idx}/{len(sessions)}] Processing session {session.id} (Student: {session.student_id})")
            correct, incorrect, unanswered = recalculate_session_aggregates(session)
            print(f"    ✅ Updated: {correct}C / {incorrect}I / {unanswered}U")
        except Exception as e:
            print(f"    ❌ Error: {e}")
            continue
    
    print("✅ Session aggregates updated")
    print()
    
    # Step 2: Regenerate zone insights
    print("🎯 Step 2: Regenerating zone insights...")
    for idx, session in enumerate(sessions, 1):
        try:
            print(f"  [{idx}/{len(sessions)}] Session {session.id}")
            result, deleted = regenerate_zone_insights(session)
            
            if deleted > 0:
                print(f"    🗑️ Deleted {deleted} old insight(s)")
            
            if result:
                subjects = ', '.join(result.keys())
                print(f"    ✅ Generated: {subjects}")
            else:
                print(f"    ⚠️ No insights generated")
        except Exception as e:
            print(f"    ❌ Error: {e}")
            continue
    
    print("✅ Zone insights regenerated")
    print()
    '''
    # Step 3: Regenerate student insights
    print("🧠 Step 3: Regenerating student insights...")
    if args.skip_llm:
        print("   ⚡ LLM generation disabled (faster mode)")
    
    for idx, student_id in enumerate(students, 1):
        try:
            print(f"  [{idx}/{len(students)}] Student {student_id}")
            success = regenerate_student_insights(student_id, skip_llm=args.skip_llm)
            
            if success:
                print(f"    ✅ Insights regenerated")
            else:
                print(f"    ⚠️ No test data available")
        except Exception as e:
            print(f"    ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("✅ Student insights regenerated")
    print()
    '''
    # Summary
    print("=" * 80)
    print("🎉 RERUN COMPLETE")
    print(f"   Sessions: {len(sessions)}")
    print(f"   Students: {len(students)}")
    print("=" * 80)
    print()
    print("💡 Next steps:")
    print("   1. Verify session data in Django admin")
    print("   2. Check zone insights: /api/zone-insights/test/<test_id>/")
    print("   3. Check student insights: /api/insights/student/<student_id>/")
    print("   4. Review frontend dashboards")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
