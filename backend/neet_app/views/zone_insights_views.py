"""
Zone Insights API Views
Provides endpoints for test-specific, subject-wise zone insights.
"""

import logging
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import TestSession, TestSubjectZoneInsight, TestAnswer

logger = logging.getLogger(__name__)


def _resolve_student_id_from_request(request):
    """Resolve student_id from request.user in a few common shapes:
    - If request.user is the StudentProfile-like object it may have 'student_id'
    - If request.user is Django's auth.User and has a related StudentProfile (user.studentprofile)
    - Fallback: try to find StudentProfile by email if available
    Returns student_id string or None
    """
    user = getattr(request, 'user', None)
    if not user:
        return None

    # Direct student_id attribute (used by JWT auth wrapper)
    if hasattr(user, 'student_id'):
        try:
            sid = getattr(user, 'student_id')
            if sid:
                return sid
        except Exception:
            pass

    # Django auth.User with OneToOne StudentProfile relation
    try:
        sp = getattr(user, 'studentprofile', None)
        if sp and getattr(sp, 'student_id', None):
            return sp.student_id
    except Exception:
        pass

    # Fallback: lookup by email if available
    try:
        email = getattr(user, 'email', None)
        if email:
            from ..models import StudentProfile
            sp = StudentProfile.objects.filter(email__iexact=email).first()
            if sp:
                return sp.student_id
    except Exception:
        pass

    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_student_tests(request):
    """
    Get list of completed tests for the authenticated student.
    Used to populate the test selector dropdown in the Analysis tab.
    
    Returns:
    {
        "status": "success",
        "tests": [
            {
                "id": 123,
                "test_type": "custom",
                "test_name": "Custom Test",
                "start_time": "2025-11-11T10:00:00Z",
                "end_time": "2025-11-11T13:00:00Z",
                "total_questions": 180,
                "correct_answers": 120,
                "incorrect_answers": 40,
                "unanswered": 20,
                "total_marks": 440,
                "max_marks": 720,
                "physics_score": 75.5,
                "chemistry_score": 68.2,
                "botany_score": 72.0,
                "zoology_score": 70.5
            },
            ...
        ],
        "total_tests": 25
    }
    """
    try:
        # Resolve authenticated student ID from request (supports multiple user shapes)
        student_id = _resolve_student_id_from_request(request)
        if not student_id:
            return Response({
                'status': 'error',
                'message': 'User not properly authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Fetch completed tests that have TestAnswer records
        # This ensures we only show tests that actually have data
        from django.db.models import Exists, OuterRef
        tests = TestSession.objects.filter(
            student_id=student_id,
            is_completed=True
        ).annotate(
            has_answers=Exists(
                TestAnswer.objects.filter(session_id=OuterRef('id'))
            )
        ).filter(has_answers=True).order_by('-end_time')
        
        # Format test data
        tests_data = []
        for test in tests:
            # Calculate marks. Use robust answer-driven logic so total matches
            # per-subject calculations: treat any TestAnswer with selected_answer==None
            # as unanswered regardless of is_correct field.
            try:
                ta = TestAnswer.objects.filter(session_id=test.id)
                attempted = ta.filter(selected_answer__isnull=False).count()
                correct = ta.filter(is_correct=True).count()
                incorrect = attempted - correct
                total_q = test.total_questions or ta.count()
                unanswered = total_q - attempted
                if unanswered < 0:
                    unanswered = ta.filter(selected_answer__isnull=True).count()
            except Exception:
                # fallback to stored counters
                correct = getattr(test, 'correct_answers', 0) or 0
                incorrect = getattr(test, 'incorrect_answers', 0) or 0
                total_q = test.total_questions or 0
                unanswered = getattr(test, 'unanswered', 0) or 0

            total_marks = (correct * 4) - (incorrect * 1)
            max_marks = total_q * 4

            # Determine test name: platform test name or unique Practice Test label
            if test.test_type == 'platform' and test.platform_test:
                test_name = test.platform_test.test_name
            else:
                test_name = f"Practice Test #{test.id}"

            tests_data.append({
                'id': test.id,
                'test_type': test.test_type,
                'test_name': test_name,
                # backward-compat alias used by some cached exports
                'get_test_name': test_name,
                'start_time': test.start_time.isoformat() if test.start_time else None,
                'end_time': test.end_time.isoformat() if test.end_time else None,
                'total_questions': test.total_questions,
                'correct_answers': test.correct_answers,
                'incorrect_answers': test.incorrect_answers,
                'unanswered': test.unanswered,
                # keep the canonical names the frontend expects
                'total_marks': total_marks,
                'max_marks': max_marks,
                # legacy field name seen in some cache dumps
                'total_marks_calc': total_marks,
                'physics_score': test.physics_score,
                'chemistry_score': test.chemistry_score,
                'botany_score': test.botany_score,
                'zoology_score': test.zoology_score,
                'math_score': test.math_score
            })
        
        return Response({
            'status': 'success',
            'tests': tests_data,
            'total_tests': len(tests_data)
        })
        
    except Exception as e:
        logger.error(f"Error in get_student_tests: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_test_zone_insights(request, test_id):
    """
    Get zone insights for a specific test.
    Computes and stores structured metrics in TestSubjectZoneInsight table.
    
    URL: /api/zone-insights/test/<test_id>/
    
    Returns:
    {
        "status": "success",
        "test_info": {...},
        "subjects": [...]
    }
    """
    logger.info(f"get_test_zone_insights called for test_id={test_id}")
    try:
        # Resolve authenticated student ID from request
        student_id = _resolve_student_id_from_request(request)
        if not student_id:
            return Response({
                'status': 'error',
                'message': 'User not properly authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Verify test ownership and completion
        test = get_object_or_404(
            TestSession,
            id=test_id,
            student_id=student_id,
            is_completed=True
        )

        # Helper to normalize subject name
        def _normalize_subject(s: str) -> str:
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

        # Fetch all answers for this test
        answers = TestAnswer.objects.filter(session_id=test.id).select_related('question__topic')
        
        # Group answers by subject
        from collections import defaultdict
        subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology', 'Biology', 'Math']
        subject_answers = {s: [] for s in subjects}
        
        for answer in answers:
            try:
                topic = answer.question.topic
                subject_name = getattr(topic, 'subject', None)
                normalized = _normalize_subject(subject_name) if subject_name else None
                if normalized in subjects:
                    subject_answers[normalized].append(answer)
            except Exception:
                continue
        
        # Calculate overall test metrics
        total_questions = test.total_questions or answers.count()
        total_correct = answers.filter(is_correct=True).count()
        total_incorrect = answers.filter(selected_answer__isnull=False, is_correct=False).count()
        total_skipped = answers.filter(selected_answer__isnull=True).count()
        
        # 1️⃣ Total Possible Marks
        total_possible_marks = total_questions * 4
        
        # 2️⃣ Accuracy
        overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
        
        # 3️⃣ Time Spent (Overall)
        correct_time = sum(a.time_taken or 0 for a in answers if a.is_correct)
        incorrect_time = sum(a.time_taken or 0 for a in answers if a.selected_answer and not a.is_correct)
        skipped_time = sum(a.time_taken or 0 for a in answers if not a.selected_answer)
        total_time = correct_time + incorrect_time + skipped_time
        
        time_spent_json = {
            "total_time_spent": total_time,
            "correct_time_spent": correct_time,
            "incorrect_time_spent": incorrect_time,
            "skipped_time_spent": skipped_time
        }
        
        # 4️⃣ Total Marks (Based on Marking Scheme)
        total_marks = (total_correct * 4) - (total_incorrect * 1)
        
        # 5️⃣ Subject-wise Data
        subject_wise_data = []
        subjects_data_list = []

        for subject in subjects:
            subject_ans = subject_answers[subject]
            if not subject_ans:  # Skip subjects with no questions
                continue

            # Subject calculations
            subj_total = len(subject_ans)
            subj_correct = sum(1 for a in subject_ans if a.is_correct)
            subj_incorrect = sum(1 for a in subject_ans if a.selected_answer and not a.is_correct)
            subj_skipped = sum(1 for a in subject_ans if not a.selected_answer)
            subj_total_mark = subj_total * 4
            subj_marks = (subj_correct * 4) - (subj_incorrect * 1)
            subj_accuracy_pct = (subj_correct / subj_total * 100) if subj_total > 0 else 0

            # Subject-wise data entry (matches requested JSON structure)
            subject_data_entry = {
                "subject_name": subject,
                "total_questions": subj_total,
                "correct_answers": subj_correct,
                "incorrect_answers": subj_incorrect,
                "skipped_answers": subj_skipped,
                "total_mark": subj_total_mark,
                "marks": subj_marks,
                "accuracy": round(subj_accuracy_pct, 2)
            }
            subject_wise_data.append(subject_data_entry)

            subjects_data_list.append({
                'subject': subject,
                'mark': subj_marks,
                'accuracy': round(subj_accuracy_pct, 2),
                'time_spent': {
                    "total_time_spent": sum(a.time_taken or 0 for a in subject_ans),
                    "correct_time_spent": sum(a.time_taken or 0 for a in subject_ans if a.is_correct),
                    "incorrect_time_spent": sum(a.time_taken or 0 for a in subject_ans if a.selected_answer and not a.is_correct),
                    "skipped_time_spent": sum(a.time_taken or 0 for a in subject_ans if not a.selected_answer)
                },
                'total_mark': subj_total_mark,
                'subject_data': subject_data_entry
            })

        # Persist a single TestSubjectZoneInsight row per test session (one row = one test)
        # Build overall values to store
        overall_accuracy_fraction = round(((total_correct / total_questions) if total_questions > 0 else 0), 3)

        # Try to fetch existing insight row (populated by submit pipeline)
        # Only create if missing to avoid overwriting LLM-generated fields
        insight, created = TestSubjectZoneInsight.objects.get_or_create(
            test_session_id=test_id,
            student_id=student_id,
            defaults={
                'student_id': student_id,
                'mark': total_marks,
                'accuracy': overall_accuracy_fraction,  # stored as fraction 0-1
                'time_spend': time_spent_json,
                'total_mark': total_possible_marks,
                'subject_data': subject_wise_data,
                'focus_zone': [],
                'repeated_mistake': [],
                'g_phrase': None,
                'checkpoints': [],
                'topics_analyzed': []
            }
        )
        
        # If row already existed and is missing basic metrics, update only those fields
        # (preserve LLM fields like focus_zone, repeated_mistake, g_phrase)
        if not created and (not insight.subject_data or not insight.mark):
            insight.mark = total_marks
            insight.accuracy = overall_accuracy_fraction
            insight.time_spend = time_spent_json
            insight.total_mark = total_possible_marks
            insight.subject_data = subject_wise_data
            insight.save(update_fields=['mark', 'accuracy', 'time_spend', 'total_mark', 'subject_data'])
            logger.info(f"Updated basic metrics for existing insight row {test_id} (preserved LLM fields)")
        
        # Test name
        if test.test_type == 'platform' and test.platform_test:
            test_name = test.platform_test.test_name
        else:
            test_name = f"Practice Test #{test.id}"
        
        # Prepare response
        response_data = {
            'status': 'success',
            'test_info': {
                'id': test.id,
                'test_name': test_name,
                'start_time': test.start_time.isoformat() if test.start_time else None,
                'end_time': test.end_time.isoformat() if test.end_time else None,
                'total_questions': total_questions,
                'total_possible_marks': total_possible_marks,
                'total_marks': total_marks,
                'accuracy': round(overall_accuracy, 2),
                'time_spent': time_spent_json,
                'subject_wise_data': subject_wise_data
            },
            'subjects': subjects_data_list
        }
        
        logger.info(f"Processed and stored zone insights for test {test_id}")
        return Response(response_data)
        
    except TestSession.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Test not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in get_test_zone_insights: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_zone_insights_status(request, test_id):
    """
    Check if zone insights have been generated for a test.
    Useful for polling after test submission.
    
    For demo tests from Neet Bro Institute, also generates TTS audio URL.
    
    URL: /api/zone-insights/status/<test_id>/
    
    Returns:
    {
        "status": "success",
        "test_id": 123,
        "insights_generated": true,
        "all_subjects_complete": true,
        "subjects_with_insights": ["Physics", "Chemistry", "Botany", "Zoology", "Biology"],
        "expected_subjects": ["Physics", "Chemistry", "Botany", "Zoology", "Biology"],
        "total_subjects": 5,
        "audio_url": "/audio/insight-123-1234567890.mp3"  // Only for demo tests
    }
    """
    try:
        # Resolve authenticated student ID from request (supports multiple user shapes)
        student_id = _resolve_student_id_from_request(request)
        if not student_id:
            return Response({
                'status': 'error',
                'message': 'User not properly authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Verify test ownership
        test = get_object_or_404(
            TestSession,
            id=test_id,
            student_id=student_id
        )
        
        # Determine expected subjects from test session
        expected_subjects = []
        if test.physics_topics:
            expected_subjects.append('Physics')
        if test.chemistry_topics:
            expected_subjects.append('Chemistry')
        if test.botany_topics:
            expected_subjects.append('Botany')
        if test.zoology_topics:
            expected_subjects.append('Zoology')
        if test.biology_topics:
            expected_subjects.append('Biology')
        if test.math_topics:
            expected_subjects.append('Math')
        
        # Prefer a single TestSubjectZoneInsight record per test session.
        # Consider insights "generated" only when a row exists and its
        # `subject_data` is populated and metrics like 'mark', 'accuracy',
        # 'time_spend' and 'total_mark' are present.
        insight = TestSubjectZoneInsight.objects.filter(test_session_id=test_id).first()

        subjects_with_insights = []
        insights_generated = False
        all_subjects_complete = False

        if insight and insight.subject_data:
            try:
                sd = insight.subject_data or []
                if isinstance(sd, list) and len(sd) > 0:
                    # Collect subject names present in the subject_data list
                    for entry in sd:
                        name = entry.get('subject_name') or entry.get('subject')
                        if name:
                            subjects_with_insights.append(name)

                    # Basic validation: ensure top-level metrics exist on the row
                    required_metrics_present = (
                        insight.mark is not None and
                        insight.accuracy is not None and
                        insight.time_spend is not None and
                        insight.total_mark is not None
                    )

                    if subjects_with_insights and required_metrics_present:
                        insights_generated = True

                        # If expected_subjects are provided, ensure they are all present
                        if expected_subjects:
                            all_present = all(subj in subjects_with_insights for subj in expected_subjects)
                            all_subjects_complete = all_present
                        else:
                            # No expected subjects listed on session: treat presence as complete
                            all_subjects_complete = True
            except Exception:
                insights_generated = False
                all_subjects_complete = False
        
        response_data = {
            'status': 'success',
            'test_id': test_id,
            'insights_generated': insights_generated,
            'all_subjects_complete': all_subjects_complete,
            'subjects_with_insights': subjects_with_insights,
            'expected_subjects': expected_subjects,
            'total_subjects': len(subjects_with_insights)
        }
        
        # Return TTS audio URL if it was generated (for demo tests)
        # Only include audio URL when ALL subjects are complete
        if all_subjects_complete and test.insights_audio_url:
            response_data['audio_url'] = test.insights_audio_url
            response_data['is_demo_test'] = True
            logger.info(f"✅ Returning stored TTS audio URL for test {test_id}: {test.insights_audio_url}")
        
        return Response(response_data)
        
    except TestSession.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Test not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in get_zone_insights_status: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_test_zone_insights_raw(request, test_id):
    """
    Raw DB-backed zone insights for a test session.
    Returns structured data from `test_subject_zone_insights` for the given test_id.

    URL: /api/zone-insights/raw/<test_id>/
    """
    try:
        student_id = _resolve_student_id_from_request(request)
        if not student_id:
            return Response({'status': 'error', 'message': 'User not properly authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

        # Verify test ownership
        test = get_object_or_404(TestSession, id=test_id, student_id=student_id)

        insights_qs = TestSubjectZoneInsight.objects.filter(test_session_id=test_id)

        insights = []
        for row in insights_qs:
            insights.append({
                'mark': row.mark,
                'accuracy': row.accuracy,
                'time_spend': row.time_spend or {},
                'total_mark': row.total_mark,
                'subject_data': row.subject_data or [],
                'focus_zone': row.focus_zone or [],
                'repeated_mistake': row.repeated_mistake or [],
                'g_phrase': row.g_phrase,
                'created_at': row.created_at.isoformat() if row.created_at else None
            })

        return Response({'status': 'success', 'test_id': test_id, 'insights': insights})

    except TestSession.DoesNotExist:
        return Response({'status': 'error', 'message': 'Test not found or access denied'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(f"Error in get_test_zone_insights_raw: {e}")
        return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_test_focus_zone(request, test_id):
    """
    Generate focus zone and repeated mistakes data for a specific test using LLM.
    
    **Important**: These insights are ONLY generated for platform tests.
    For custom tests, the fields are set to empty/null.
    
    This endpoint analyzes:
    1. Focus Zone: Wrong and skipped questions from THIS test
    2. Repeated Mistakes: Wrong answers from ALL platform tests for patterns
    
    Both generate subject-wise insights (2 points per subject).
    
    URL: /api/zone-insights/focus-zone/<test_id>/
    Method: POST
    
    Returns (Platform Test):
    {
        "status": "success",
        "test_id": 123,
        "test_type": "platform",
        "focus_zone": {
            "Physics": [
                "Student confused velocity with acceleration in motion equations.\\nPractice 10 motion problems focusing on unit identification.",
                "..."
            ],
            "Chemistry": [...],
            ...
        },
        "repeated_mistake": {
            "Physics": [
                {
                    "topic": "Mechanics",
                    "line1": "Student repeatedly confused velocity with acceleration in 3 tests.",
                    "line2": "Practice 10 motion problems daily focusing on units and formulas."
                },
                {
                    "topic": "Thermodynamics",
                    "line1": "Consistently mixed up isothermal and adiabatic processes across 2 tests.",
                    "line2": "Create comparison chart and solve 15 PV diagram problems."
                }
            ],
            "Chemistry": [
                {
                    "topic": "Redox Reactions",
                    "line1": "Repeatedly confused oxidation-reduction in 3 tests, mixing electron gain-loss.",
                    "line2": "Create flashcards for OIL RIG rule and practice redox daily."
                },
                ...
            ],
            ...
        }
    }
    
    Returns (Custom Test):
    {
        "status": "success",
        "test_id": 456,
        "test_type": "custom",
        "message": "Focus zone and repeated mistakes are only generated for platform tests.",
        "focus_zone": {},
        "repeated_mistake": {}
    }
    """
    try:
        student_id = _resolve_student_id_from_request(request)
        if not student_id:
            return Response({
                'status': 'error',
                'message': 'User not properly authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Verify test ownership
        test = get_object_or_404(TestSession, id=test_id, student_id=student_id)
        
        # Check if test is completed
        if not test.is_completed:
            return Response({
                'status': 'error',
                'message': 'Test must be completed before generating focus zone'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if zone insights exist
        insight = TestSubjectZoneInsight.objects.filter(
            test_session_id=test_id,
            student_id=student_id
        ).first()
        
        if not insight:
            return Response({
                'status': 'error',
                'message': 'Zone insights must be generated before focus zone. Please call /api/zone-insights/test/<test_id>/ first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if this is a platform test
        # Focus zone and repeated mistakes are only generated for platform tests
        if test.test_type != 'platform':
            logger.info(f"ℹ️ Test {test_id} is a custom test. Skipping focus zone and repeated mistakes generation.")
            
            # Set fields to empty/null for custom tests
            insight.focus_zone = {}
            insight.repeated_mistake = {}
            insight.save(update_fields=['focus_zone', 'repeated_mistake'])
            
            return Response({
                'status': 'success',
                'test_id': test_id,
                'test_type': test.test_type,
                'message': 'Focus zone and repeated mistakes are only generated for platform tests.',
                'focus_zone': {},
                'repeated_mistake': {}
            })
        
        # Import the generation functions
        from ..services.zone_insights_service import generate_focus_zone, generate_repeated_mistakes
        
        logger.info(f"🎯 Generating focus zone and repeated mistakes for platform test {test_id}")
        
        # Generate focus zone (current test only)
        logger.info(f"📊 Step 1/2: Generating focus zone for test {test_id}")
        focus_zone_data = generate_focus_zone(test_id)
        
        if not focus_zone_data:
            logger.warning(f"⚠️ Failed to generate focus zone for test {test_id}")
        
        # Generate repeated mistakes (all platform tests)
        logger.info(f"📊 Step 2/2: Generating repeated mistakes for student {student_id}")
        repeated_mistakes_data = generate_repeated_mistakes(student_id, test_id)
        
        if not repeated_mistakes_data:
            logger.warning(f"⚠️ Failed to generate repeated mistakes for student {student_id}")
        
        # Check if at least one succeeded
        if not focus_zone_data and not repeated_mistakes_data:
            return Response({
                'status': 'error',
                'message': 'Failed to generate insights. No data available or LLM error.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Refresh the insight object to get updated data
        insight.refresh_from_db()
        
        return Response({
            'status': 'success',
            'test_id': test_id,
            'test_type': test.test_type,
            'focus_zone': insight.focus_zone or {},
            'repeated_mistake': insight.repeated_mistake or {}
        })
        
    except TestSession.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Test not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in generate_test_focus_zone: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_advanced_metrics(request, test_id):
    """
    Get advanced metrics (g_phrase, focus_zone, repeated_mistake) for a test.
    Returns immediately with current state - does not trigger generation.
    
    URL: /api/zone-insights/advanced/<test_id>/
    
    Returns:
    {
        "status": "success",
        "test_id": 123,
        "test_type": "platform",
        "is_ready": true,
        "g_phrase": "Dr. Khadeejah, 200 marks are recoverable...",
        "focus_zone": {...},
        "repeated_mistakes": {...},
        "message": "Data available" or "Processing..." or "Not applicable for custom tests"
    }
    """
    try:
        student_id = _resolve_student_id_from_request(request)
        if not student_id:
            return Response({
                'status': 'error',
                'message': 'User not properly authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Verify test ownership and completion
        test = get_object_or_404(
            TestSession,
            id=test_id,
            student_id=student_id,
            is_completed=True
        )
        
        # For custom tests, return empty data immediately
        if test.test_type != 'platform':
            return Response({
                'status': 'success',
                'test_id': test_id,
                'test_type': test.test_type,
                'is_ready': True,
                'g_phrase': None,
                'focus_zone': {},
                'repeated_mistakes': {},
                'message': 'Advanced metrics are only available for platform tests'
            })
        
        # Try to fetch existing insight row
        insight = TestSubjectZoneInsight.objects.filter(
            test_session_id=test_id,
            student_id=student_id
        ).first()
        
        if not insight:
            return Response({
                'status': 'success',
                'test_id': test_id,
                'test_type': test.test_type,
                'is_ready': False,
                'g_phrase': None,
                'focus_zone': {},
                'repeated_mistakes': {},
                'message': 'Zone insights not yet generated. Please call /api/zone-insights/test/<test_id>/ first.'
            })
        
        # Check if advanced metrics are ready
        has_g_phrase = bool(insight.g_phrase)
        has_focus_zone = bool(insight.focus_zone and len(insight.focus_zone) > 0)
        has_repeated_mistakes = bool(insight.repeated_mistake and len(insight.repeated_mistake) > 0)
        
        is_ready = has_g_phrase or has_focus_zone or has_repeated_mistakes
        
        return Response({
            'status': 'success',
            'test_id': test_id,
            'test_type': test.test_type,
            'is_ready': is_ready,
            'g_phrase': insight.g_phrase,
            'focus_zone': insight.focus_zone or {},
            'repeated_mistakes': insight.repeated_mistake or {},
            'message': 'Data available' if is_ready else 'Processing...'
        })
        
    except TestSession.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Test not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in get_advanced_metrics: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
