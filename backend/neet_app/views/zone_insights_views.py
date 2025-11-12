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
            # Calculate marks
            total_marks = (test.correct_answers * 4) - (test.incorrect_answers * 1)
            max_marks = test.total_questions * 4
            
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
    Returns test summary and subject-wise zone insights (Steady, Edge, Focus).
    
    URL: /api/zone-insights/test/<test_id>/
    
    Returns:
    {
        "status": "success",
        "test_info": {
            "id": 123,
            "test_name": "Custom Test",
            "start_time": "2025-11-11T10:00:00Z",
            "end_time": "2025-11-11T13:00:00Z",
            "total_marks": 440,
            "max_marks": 720,
            "percentage": 61.11,
            "subject_marks": {
                "Physics": {
                    "score": 75.5,
                    "correct": 30,
                    "incorrect": 10,
                    "unanswered": 5,
                    "marks": 110,
                    "max_marks": 180
                },
                ...
            }
        },
        "zone_insights": [
            {
                "subject": "Physics",
                "steady_zone": ["point 1", "point 2"],
                "edge_zone": ["point 1", "point 2"],
                "focus_zone": ["point 1", "point 2"]
            },
            ...
        ]
    }
    """
    logger.info(f"get_test_zone_insights called for test_id={test_id}")
    try:
        # Resolve authenticated student ID from request (supports multiple user shapes)
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

        # Get student profile object for DB writes
        student_profile = test.get_student_profile()

        # Calculate overall marks (existing logic). If TestSession counters
        # are not populated, fall back to computing from TestAnswer rows.
        total_correct = getattr(test, 'correct_answers', 0) or 0
        total_incorrect = getattr(test, 'incorrect_answers', 0) or 0
        total_unanswered = getattr(test, 'unanswered', 0) or 0

        # If the session counters look empty, compute from TestAnswer table
        if (total_correct + total_incorrect + total_unanswered) == 0:
            try:
                ta_qs = TestAnswer.objects.filter(session_id=test.id)
                total_correct = ta_qs.filter(is_correct=True).count()
                total_incorrect = ta_qs.filter(is_correct=False).count()
                total_unanswered = ta_qs.filter(is_correct__isnull=True).count()
            except Exception:
                # keep the original zeros if anything fails
                total_correct = total_incorrect = total_unanswered = 0

        total_marks = (total_correct * 4) - (total_incorrect * 1)
        max_marks = (test.total_questions or 0) * 4
        percentage = (total_marks / max_marks * 100) if max_marks > 0 else 0

        # Test name: platform test name or Practice Test #<id>
        if test.test_type == 'platform' and test.platform_test:
            test_name = test.platform_test.test_name
        else:
            test_name = f"Practice Test #{test.id}"

        # Subject-wise marks: compute directly from TestAnswer rows to ensure
        # counts (correct/incorrect/unanswered) match the actual answers for
        # this session. This avoids relying on possibly stale TestSession
        # counters and guarantees consistency with DB answers.
        from collections import defaultdict

        # Initialize counters for expected subjects
        subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology', 'Math']
        counters = {s: {'correct': 0, 'incorrect': 0, 'unanswered': 0, 'total_questions': 0} for s in subjects}

        # Helper to normalize subject name (reuse same logic used for insights)
        def _normalize_subject_name_for_counts(s: str) -> str:
            if not s:
                return 'Other'
            s_low = s.lower()
            if 'physics' in s_low:
                return 'Physics'
            if 'chemistry' in s_low:
                return 'Chemistry'
            if 'botany' in s_low or 'plant' in s_low or 'biology' in s_low:
                return 'Botany'
            if 'zoology' in s_low or 'animal' in s_low:
                return 'Zoology'
            if 'math' in s_low or 'algebra' in s_low or 'geometry' in s_low:
                return 'Math'
            return s.strip()

        try:
            # Build subject counters by iterating answers once and attributing each
            # answer to exactly one subject using the question.topic.subject value.
            # This avoids double-counting when topic.subject contains multiple
            # keywords or when session topic lists overlap between subjects.
            answers = TestAnswer.objects.filter(session_id=test.id).select_related('question__topic')

            for a in answers:
                q_topic = None
                try:
                    q_topic = a.question.topic
                except Exception:
                    q_topic = None

                subj_name = None
                if q_topic is not None:
                    subj_name = getattr(q_topic, 'subject', None)

                norm = _normalize_subject_name_for_counts(subj_name) if subj_name else None
                # Only count if normalized subject is one of our tracked subjects
                if norm not in subjects:
                    continue

                counters[norm]['total_questions'] += 1
                # Classify answer state robustly:
                # - If selected_answer is None or empty => unanswered
                # - Else, if is_correct True => correct
                # - Otherwise treat as incorrect
                sel = getattr(a, 'selected_answer', None)
                if sel is None or (isinstance(sel, str) and sel.strip() == ''):
                    counters[norm]['unanswered'] += 1
                else:
                    if a.is_correct is True:
                        counters[norm]['correct'] += 1
                    else:
                        counters[norm]['incorrect'] += 1

        except Exception:
            # If anything fails, fall back to empty counters
            counters = {s: {'correct': 0, 'incorrect': 0, 'unanswered': 0, 'total_questions': 0} for s in subjects}

        # Build subject_marks in response shape using counters
        subject_marks = {}
        for subj in subjects:
            stats = counters.get(subj, {})
            correct = stats.get('correct', 0)
            incorrect = stats.get('incorrect', 0)
            total_q = stats.get('total_questions', 0)
            unanswered = stats.get('unanswered', 0)
            marks = (correct * 4) - (incorrect * 1)
            max_m = total_q * 4
            # Score percentage: if subject percentage stored on TestSession prefer that, else compute
            score_pct = getattr(test, f"{subj.lower()}_score", None)
            if score_pct is None and max_m > 0:
                score_pct = round((marks / max_m) * 100, 2) if max_m > 0 else 0

            subject_marks[subj] = {
                'score': score_pct if score_pct is not None else 0,
                'correct': correct,
                'incorrect': incorrect,
                'unanswered': unanswered,
                'marks': marks,
                'max_marks': max_m
            }

        # BUILD INSIGHTS: simplify per your request
        # 1) detect which subjects are present in this test by reading TestAnswer -> Question -> Topic.subject
        # 2) for each subject, gather all answers for that subject, build question payload and call LLM once

        answers_qs = TestAnswer.objects.filter(session_id=test_id).select_related('question__topic')

        # Group answers by normalized subject name
        def normalize_subject_name(s: str) -> str:
            if not s:
                return 'Other'
            s_low = s.lower()
            if 'physics' in s_low:
                return 'Physics'
            if 'chemistry' in s_low:
                return 'Chemistry'
            if 'botany' in s_low or 'plant' in s_low or 'biology' in s_low:
                # make Botany default for plant biology
                return 'Botany'
            if 'zoology' in s_low or 'animal' in s_low:
                return 'Zoology'
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

        # Use existing service to generate insights per subject
        from ..services.zone_insights_service import generate_zone_insights_for_subject

        # Only generate insights for subjects that are not already stored.
        # This avoids re-calling the LLM every time the user clicks the test.
        insights_data = []
    # Normalize existing subjects from DB so we compare case-insensitively
        raw_existing = TestSubjectZoneInsight.objects.filter(test_session=test).values_list('subject', flat=True)
        existing_subjects = set([normalize_subject_name(s) for s in raw_existing if s])
        logger.debug(f"Existing stored subjects for test {test_id}: {existing_subjects}")
        for subj, ans_list in grouped.items():
            # Build question payloads from answers
            questions_payload = []
            for a in ans_list[:100]:  # limit to reasonable size
                q = a.question
                topic = getattr(q, 'topic', None)
                options = {
                    'A': getattr(q, 'option_a', None),
                    'B': getattr(q, 'option_b', None),
                    'C': getattr(q, 'option_c', None),
                    'D': getattr(q, 'option_d', None),
                }
                questions_payload.append({
                    'question_id': q.id,
                    # Include full question text (do not truncate) for richer LLM context
                    'question': (q.question if getattr(q, 'question', None) else ''),
                    'options': options,
                    'correct_answer': getattr(q, 'correct_answer', None),
                    'selected_answer': a.selected_answer if a.selected_answer else None,
                    'is_correct': a.is_correct,
                    'time_taken': a.time_taken or 0,
                    'topic': getattr(topic, 'name', None) if topic else None
                })
            # Normalize subject for storage/lookup
            subj_norm = normalize_subject_name(subj)

            # If insights for this subject already exist, skip generation
            if subj_norm in existing_subjects:
                logger.debug(f"Skipping generation for subject {subj_norm} (already stored)")
                continue

            # Call LLM once per subject (only for missing subjects)
            try:
                zones = generate_zone_insights_for_subject(subj, questions_payload)
            except Exception as e:
                logger.error(f"LLM error for test {test_id} subject {subj}: {str(e)}")
                zones = {
                    'steady_zone': [],
                    'edge_zone': [],
                    'focus_zone': []
                }

            # Persist zones to DB (create or update)
            try:
                TestSubjectZoneInsight.objects.update_or_create(
                    test_session=test,
                    subject=subj_norm,
                    defaults={
                        'student': student_profile,
                        'steady_zone': zones.get('steady_zone', []),
                        'edge_zone': zones.get('edge_zone', []),
                        'focus_zone': zones.get('focus_zone', []),
                        'questions_analyzed': questions_payload
                    }
                )
                # mark as stored so subsequent loop iterations in same request won't regenerate
                existing_subjects.add(subj_norm)
            except Exception as e:
                logger.error(f"Failed to save zone insights for test {test_id} subject {subj}: {e}")

            insights_data.append({
                'subject': subj_norm,
                'steady_zone': zones.get('steady_zone', []),
                'edge_zone': zones.get('edge_zone', []),
                'focus_zone': zones.get('focus_zone', [])
            })

        # Return DB-backed insights so frontend always sees stored results (including previous runs)
        try:
            stored = TestSubjectZoneInsight.objects.filter(test_session=test).values(
                'subject', 'steady_zone', 'edge_zone', 'focus_zone'
            )
            final_insights = [
                {
                    'subject': normalize_subject_name(s['subject']),
                    'steady_zone': s['steady_zone'] or [],
                    'edge_zone': s['edge_zone'] or [],
                    'focus_zone': s['focus_zone'] or []
                }
                for s in stored
            ]
            # If DB had entries, prefer them; otherwise return generated insights
            if final_insights:
                insights_data = final_insights
        except Exception as e:
            logger.error(f"Failed to load stored insights for test {test_id}: {e}")
        
        logger.info(f"Returning {len(insights_data)} zone insights for test {test_id}")
        response_data = {
            'status': 'success',
            'test_info': {
                'id': test.id,
                'test_name': test_name,
                'start_time': test.start_time.isoformat() if test.start_time else None,
                'end_time': test.end_time.isoformat() if test.end_time else None,
                'total_marks': total_marks,
                'max_marks': max_marks,
                'percentage': round(percentage, 2),
                'subject_marks': subject_marks
            },
            'zone_insights': insights_data
        }
        logger.debug(f"Response data: test_name={test_name}, total_marks={total_marks}, insights_count={len(insights_data)}")
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
    
    URL: /api/zone-insights/status/<test_id>/
    
    Returns:
    {
        "status": "success",
        "test_id": 123,
        "insights_generated": true,
        "subjects_with_insights": ["Physics", "Chemistry", "Botany", "Zoology"],
        "total_subjects": 4
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
        
        # Check if insights exist
        insights = TestSubjectZoneInsight.objects.filter(
            test_session_id=test_id
        ).values_list('subject', flat=True)
        
        subjects_with_insights = list(insights)
        
        return Response({
            'status': 'success',
            'test_id': test_id,
            'insights_generated': len(subjects_with_insights) > 0,
            'subjects_with_insights': subjects_with_insights,
            'total_subjects': len(subjects_with_insights)
        })
        
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
    Returns rows from `test_subject_zone_insights` for the given test_id.

    URL: /api/zone-insights/raw/<test_id>/
    """
    try:
        student_id = _resolve_student_id_from_request(request)
        if not student_id:
            return Response({'status': 'error', 'message': 'User not properly authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

        # Verify test ownership
        test = get_object_or_404(TestSession, id=test_id, student_id=student_id)
        student_profile = test.get_student_profile()

        insights_qs = TestSubjectZoneInsight.objects.filter(test_session_id=test_id)

        insights = []
        for row in insights_qs:
            insights.append({
                'subject': row.subject,
                'steady_zone': row.steady_zone or [],
                'edge_zone': row.edge_zone or [],
                'focus_zone': row.focus_zone or [],
                'questions_analyzed': row.questions_analyzed or [],
                'created_at': row.created_at.isoformat() if row.created_at else None
            })

        return Response({'status': 'success', 'test_id': test_id, 'raw_insights': insights})

    except TestSession.DoesNotExist:
        return Response({'status': 'error', 'message': 'Test not found or access denied'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(f"Error in get_test_zone_insights_raw: {e}")
        return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
