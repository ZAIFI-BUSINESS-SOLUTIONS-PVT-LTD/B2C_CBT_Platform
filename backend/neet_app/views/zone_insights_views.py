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
    Get checkpoint insights for a specific test.
    Returns test summary and subject-wise checkpoints.
    
    URL: /api/zone-insights/test/<test_id>/
    
    Returns:
    {
        "status": "success",
        "test_info": {...},
        "checkpoints": [
            {
                "subject": "Physics",
                "checkpoints": [...]
            }
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

        # Calculate overall marks using the same robust approach as per-subject
        # Treat selected_answer==None as unanswered. Derive attempted and incorrect
        # from selected_answer presence so counts match subject breakdowns.
        try:
            ta_qs = TestAnswer.objects.filter(session_id=test.id)
            attempted = ta_qs.filter(selected_answer__isnull=False).count()
            total_correct = ta_qs.filter(is_correct=True).count()
            total_incorrect = attempted - total_correct
            total_q = test.total_questions or ta_qs.count()
            total_unanswered = total_q - attempted
            if total_unanswered < 0:
                total_unanswered = ta_qs.filter(selected_answer__isnull=True).count()
        except Exception:
            total_correct = getattr(test, 'correct_answers', 0) or 0
            total_incorrect = getattr(test, 'incorrect_answers', 0) or 0
            total_unanswered = getattr(test, 'unanswered', 0) or 0
            total_q = test.total_questions or 0

        total_marks = (total_correct * 4) - (total_incorrect * 1)
        max_marks = (total_q or 0) * 4
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
        subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology', 'Biology', 'Math']
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
            if 'botany' in s_low or 'plant' in s_low:
                return 'Botany'
            if 'zoology' in s_low or 'animal' in s_low:
                return 'Zoology'
            if 'biology' in s_low or 'bio' in s_low:
                return 'Biology'
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

        # BUILD CHECKPOINTS: use new checkpoint generation service
        # Check if checkpoints already exist for this test
        existing_checkpoints = TestSubjectZoneInsight.objects.filter(test_session=test)
        
        checkpoints_data = []
        
        if not existing_checkpoints.exists():
            # Generate checkpoints for all subjects
            logger.info(f"Generating checkpoints for test {test_id}")
            from ..services.zone_insights_service import generate_all_subject_checkpoints
            
            try:
                generate_all_subject_checkpoints(test_id)
                # Reload from DB after generation
                existing_checkpoints = TestSubjectZoneInsight.objects.filter(test_session=test)
            except Exception as e:
                logger.error(f"Failed to generate checkpoints for test {test_id}: {str(e)}")
        
        # Load checkpoints from DB
        for checkpoint_obj in existing_checkpoints:
            checkpoints_data.append({
                'subject': checkpoint_obj.subject,
                'checkpoints': checkpoint_obj.checkpoints or []
            })
        
        logger.info(f"Returning {len(checkpoints_data)} checkpoints for test {test_id}")
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
            'checkpoints': checkpoints_data
        }
        logger.debug(f"Response data: test_name={test_name}, total_marks={total_marks}, checkpoints_count={len(checkpoints_data)}")
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
        "subjects_with_insights": ["Physics", "Chemistry", "Botany", "Zoology", "Biology"],
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
        
        # Check if insights exist
        insights = TestSubjectZoneInsight.objects.filter(
            test_session_id=test_id
        ).values_list('subject', flat=True)
        
        subjects_with_insights = list(insights)
        insights_generated = len(subjects_with_insights) > 0
        
        response_data = {
            'status': 'success',
            'test_id': test_id,
            'insights_generated': insights_generated,
            'subjects_with_insights': subjects_with_insights,
            'total_subjects': len(subjects_with_insights)
        }
        
        # Generate TTS audio URL for demo tests from Neet Bro Institute
        if insights_generated:
            from ..utils.tts_helper import is_demo_test_for_neet_bro, extract_checkpoint_text_for_audio, generate_insight_audio
            
            if is_demo_test_for_neet_bro(test):
                try:
                    # Fetch checkpoints to extract text
                    insights_qs = TestSubjectZoneInsight.objects.filter(test_session_id=test_id)
                    checkpoints_by_subject = []
                    
                    for insight in insights_qs:
                        checkpoints_by_subject.append({
                            'subject': insight.subject,
                            'checkpoints': insight.checkpoints or []
                        })
                    
                    # Extract first checkpoint from each subject
                    audio_text = extract_checkpoint_text_for_audio(checkpoints_by_subject)
                    
                    # Get institution name
                    institution_name = None
                    if test.platform_test and test.platform_test.institution:
                        institution_name = test.platform_test.institution.name
                    
                    # Generate audio
                    audio_url = generate_insight_audio(audio_text, test_id, institution_name)
                    
                    if audio_url:
                        response_data['audio_url'] = audio_url
                        response_data['is_demo_test'] = True
                        logger.info(f"✅ Generated TTS audio for demo test {test_id}: {audio_url}")
                    else:
                        logger.warning(f"⚠️ Failed to generate TTS audio for demo test {test_id}")
                        
                except Exception as e:
                    logger.error(f"Error generating TTS audio for test {test_id}: {str(e)}")
                    # Don't fail the request if audio generation fails
                    pass
        
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
    Raw DB-backed checkpoint insights for a test session.
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
                'checkpoints': row.checkpoints or [],
                'topics_analyzed': row.topics_analyzed or [],
                'created_at': row.created_at.isoformat() if row.created_at else None
            })

        return Response({'status': 'success', 'test_id': test_id, 'raw_insights': insights})

    except TestSession.DoesNotExist:
        return Response({'status': 'error', 'message': 'Test not found or access denied'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(f"Error in get_test_zone_insights_raw: {e}")
        return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
