"""
Institution analytics views.

Provides student list, per-student performance trends, and question-level
filtered download for institution admins.

Endpoints:
  GET  /api/institution-admin/analytics/students/
  GET  /api/institution-admin/analytics/students/<student_id>/performance/
  POST /api/institution-admin/analytics/students/<student_id>/download/
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q

from neet_app.models import StudentProfile, TestSession, TestAnswer, TestSubjectZoneInsight
from neet_app.institution_auth import institution_admin_required

import json
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1.  List students enrolled in the institution
# ---------------------------------------------------------------------------

@institution_admin_required
@require_http_methods(["GET"])
def list_institution_students(request):
    """
    List all students enrolled in the institution.
    Supports search by full name or mobile number (phone_number).

    GET /api/institution-admin/analytics/students/?search=<query>

    Returns:
        { "students": [{ "student_id", "full_name", "phone_number" }], "count": N }
    """
    try:
        # NOTE: return students across all institutions per admin request
        # (do not filter by `request.institution`). Search still applies.
        search = request.GET.get("search", "").strip()

        qs = StudentProfile.objects.filter(
            is_active=True,
        ).order_by("full_name")

        if search:
            qs = qs.filter(
                Q(phone_number__icontains=search) | Q(full_name__icontains=search)
            )

        students = [
            {
                "student_id": s.student_id,
                "full_name":  s.full_name  or "",
                "phone_number": s.phone_number or "",
            }
            for s in qs
        ]

        return JsonResponse({"students": students, "count": len(students)}, status=200)

    except Exception:
        logger.exception("Error in list_institution_students")
        return JsonResponse(
            {"error": "SERVER_ERROR", "message": "An unexpected error occurred"},
            status=500,
        )


# ---------------------------------------------------------------------------
# 2.  Per-student performance (trend + test list)
# ---------------------------------------------------------------------------

@institution_admin_required
@require_http_methods(["GET"])
def get_student_performance(request, student_id):
    """
    Return performance trend data and the full test list for one student.

    GET /api/institution-admin/analytics/students/<student_id>/performance/
        ?test_type=all   (default)
        ?test_type=custom
        ?test_type=platform

    Returns:
    {
        "student": { "student_id", "full_name", "phone_number" },
        "performance_trend": [
            { "session_id", "test_name", "accuracy", "date", "test_type" }
        ],
        "test_list": [
            { "session_id", "test_name", "marks", "total_questions",
              "correct", "incorrect", "unanswered",
              "accuracy", "time_spent", "date", "test_type" }
        ]
    }
    """
    try:
        test_type_filter = request.GET.get("test_type", "all").strip().lower()

        # Allow admins to view performance for any student (not restricted by institution)
        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            return JsonResponse(
                {"error": "NOT_FOUND", "message": "Student not found"},
                status=404,
            )

        # Build session queryset
        qs = (
            TestSession.objects
            .filter(student_id=student_id, is_completed=True)
            .select_related("platform_test")
            .order_by("start_time")
        )

        if test_type_filter == "custom":
            qs = qs.filter(test_type="custom")
        elif test_type_filter == "platform":
            qs = qs.filter(test_type="platform")

        performance_trend = []
        test_list = []

        for session in qs:
            # Accuracy
            accuracy = (
                round(session.correct_answers / session.total_questions * 100, 1)
                if session.total_questions
                else 0.0
            )

            # Test name
            if session.test_type == "platform" and session.platform_test:
                test_name = session.platform_test.test_name
            else:
                test_name = f"Custom Test ({session.start_time.strftime('%d %b %Y')})"

            time_spent = session.total_time_taken or 0
            date_str = session.start_time.isoformat()

            # Try to include zone-insight marks if available
            insight = TestSubjectZoneInsight.objects.filter(test_session=session, student=student).first()
            mark = insight.mark if insight and insight.mark is not None else None
            total_mark = insight.total_mark if insight and insight.total_mark is not None else None

            performance_trend.append(
                {
                    "session_id": session.id,
                    "test_name":  test_name,
                    "accuracy":   accuracy,
                    "date":       date_str,
                    "test_type":  session.test_type,
                    "mark":       mark,
                    "total_mark": total_mark,
                }
            )
            test_list.append(
                {
                    "session_id":      session.id,
                    "test_name":       test_name,
                    # Prefer insight mark when present; fall back to correct_answers
                    "marks":           mark if mark is not None else session.correct_answers,
                    "total_questions": total_mark if total_mark is not None else session.total_questions,
                    "correct":         session.correct_answers,
                    "incorrect":       session.incorrect_answers,
                    "unanswered":      session.unanswered,
                    "accuracy":        accuracy,
                    "time_spent":      time_spent,
                    "date":            date_str,
                    "test_type":       session.test_type,
                    "mark_value":      mark,
                    "total_mark_value": total_mark,
                }
            )

        return JsonResponse(
            {
                "student": {
                    "student_id":   student.student_id,
                    "full_name":    student.full_name    or "",
                    "phone_number": student.phone_number or "",
                },
                "performance_trend": performance_trend,
                "test_list":         test_list,
            },
            status=200,
        )

    except Exception:
        logger.exception("Error in get_student_performance")
        return JsonResponse(
            {"error": "SERVER_ERROR", "message": "An unexpected error occurred"},
            status=500,
        )


# ---------------------------------------------------------------------------
# 3.  Download filtered question-level data as structured JSON
# ---------------------------------------------------------------------------

@csrf_exempt
@institution_admin_required
@require_http_methods(["POST"])
def download_student_questions(request, student_id):
    """
    Download filtered question-level data for a student as structured JSON.

    POST /api/institution-admin/analytics/students/<student_id>/download/
    Body:
    {
        "session_ids":    [1, 2, 3],
        "question_types": ["correct", "wrong", "skipped"]   // any combination
    }

    Returns:
    {
        "student": { "student_id", "full_name", "phone_number" },
        "questions": [
            {
                "session_id",   "test_name",     "question_number",
                "question_text","option_a",      "option_b",
                "option_c",     "option_d",      "correct_answer",
                "student_answer","is_correct",   "skipped",
                "misconception","time_taken_seconds",
                "topic",        "subject",       "difficulty"
            }
        ],
        "total": N
    }
    """
    try:
        # Allow admins to download question data for any student (not restricted by institution)
        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            return JsonResponse(
                {"error": "NOT_FOUND", "message": "Student not found"},
                status=404,
            )

        data = json.loads(request.body)
        session_ids    = data.get("session_ids", [])
        question_types = data.get("question_types", ["correct", "wrong", "skipped"])

        if not session_ids:
            return JsonResponse(
                {"error": "INVALID_INPUT", "message": "session_ids is required"},
                status=400,
            )

        if not question_types:
            return JsonResponse(
                {
                    "error": "INVALID_INPUT",
                    "message": "At least one question_type is required",
                },
                status=400,
            )

        # Fetch completed sessions for this student
        sessions = (
            TestSession.objects
            .filter(
                id__in=session_ids,
                student_id=student_id,
                is_completed=True,
            )
            .select_related("platform_test")
        )
        session_map = {s.id: s for s in sessions}

        if not session_map:
            return JsonResponse(
                {"error": "NOT_FOUND", "message": "No matching sessions found"},
                status=404,
            )

        # --- Build answer type filter ---
        # "correct"  → is_correct=True
        # "wrong"    → answered but is_correct=False
        # "skipped"  → no answer recorded
        type_filter = Q()

        if "correct" in question_types:
            type_filter |= Q(is_correct=True)

        if "wrong" in question_types:
            # Answered (selected_answer or text_answer is non-empty) but incorrect
            answered_q = (
                ~Q(selected_answer="") & Q(selected_answer__isnull=False)
            ) | (
                ~Q(text_answer="") & Q(text_answer__isnull=False)
            )
            type_filter |= Q(is_correct=False) & answered_q

        if "skipped" in question_types:
            # Both selected_answer and text_answer are NULL or empty string
            skipped_q = (
                Q(selected_answer__isnull=True) | Q(selected_answer="")
            ) & (
                Q(text_answer__isnull=True) | Q(text_answer="")
            )
            type_filter |= skipped_q

        answers = (
            TestAnswer.objects
            .filter(Q(session_id__in=list(session_map.keys())) & type_filter)
            .select_related("question", "question__topic")
            .order_by("session_id", "id")
        )

        # Build response grouped by session/test. Number questions per session (1-based).
        session_question_counter: dict = {}
        session_questions_map: dict = {sid: [] for sid in session_map.keys()}

        for ans in answers:
            q = ans.question
            session = session_map.get(ans.session_id)
            if not session:
                continue

            # Per-session question counter (1-based)
            counter = session_question_counter.get(ans.session_id, 0) + 1
            session_question_counter[ans.session_id] = counter

            # Test name
            if session.test_type == "platform" and session.platform_test:
                test_name = session.platform_test.test_name
            else:
                test_name = f"Custom Test ({session.start_time.strftime('%d %b %Y')})"

            # Misconception for the student's chosen wrong option
            misconception = None
            if ans.selected_answer and q.misconceptions:
                key = f"option_{ans.selected_answer.lower()}"
                misconception = q.misconceptions.get(key)

            student_answer = ans.selected_answer or ans.text_answer or None

            qobj = {
                "question_number":     counter,
                "question_text":       q.question,
                "option_a":            q.option_a,
                "option_b":            q.option_b,
                "option_c":            q.option_c,
                "option_d":            q.option_d,
                "correct_answer":      q.correct_answer,
                "student_answer":      student_answer,
                "misconception":       misconception,
                "time_taken_seconds":  ans.time_taken,
                "topic":               q.topic.name    if q.topic else None,
                "subject":             q.topic.subject if q.topic else None,
                "difficulty":          q.difficulty,
            }

            session_questions_map[ans.session_id].append(qobj)

        # Build ordered list grouped by test/session
        questions_by_test = []
        total_questions = 0
        # Keep order consistent with session_map (which preserves queryset order)
        for sid, session in session_map.items():
            items = session_questions_map.get(sid, [])
            total_questions += len(items)
            if session.test_type == "platform" and session.platform_test:
                test_name = session.platform_test.test_name
            else:
                test_name = f"Custom Test ({session.start_time.strftime('%d %b %Y')})"

            # Try to fetch zone insight for this session to include marks
            insight = TestSubjectZoneInsight.objects.filter(test_session=session, student=student).first()
            mark = insight.mark if insight and insight.mark is not None else None
            total_mark = insight.total_mark if insight and insight.total_mark is not None else None

            questions_by_test.append(
                {
                    "session_id": sid,
                    "test_name":  test_name,
                    "mark":       mark,
                    "total_mark": total_mark,
                    "questions":  items,
                }
            )

        return JsonResponse(
            {
                "student": {
                    "student_id":   student.student_id,
                    "full_name":    student.full_name    or "",
                    "phone_number": student.phone_number or "",
                },
                "questions_by_test": questions_by_test,
                "total": total_questions,
            },
            status=200,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "INVALID_JSON", "message": "Invalid JSON in request body"},
            status=400,
        )
    except Exception:
        logger.exception("Error in download_student_questions")
        return JsonResponse(
            {"error": "SERVER_ERROR", "message": "An unexpected error occurred"},
            status=500,
        )
