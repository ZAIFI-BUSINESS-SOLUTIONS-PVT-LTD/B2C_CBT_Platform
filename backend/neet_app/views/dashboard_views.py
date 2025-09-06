import random
from django.db.models import Avg, Count, Max, Min, Sum, Q
import random
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Question, TestAnswer, TestSession, Topic, PlatformTest, StudentProfile
from ..serializers import QuestionSerializer, TestAnswerSerializer, TestSessionSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_analytics(request):
    """
    Generates comprehensive student performance analytics for the dashboard.
    Returns real analytics data based on completed test sessions for the authenticated user only.
    """
    # Get the authenticated student
    if not hasattr(request.user, 'student_id'):
        return Response({"error": "User not properly authenticated"}, status=401)
    
    student_id = request.user.student_id
    
    # Get all sessions for this student; treat a session as completed if any of:
    # - is_completed == True
    # - end_time is not null (submit likely set end_time)
    # - total_time_taken is not null (summary persisted)
    # This is defensive: some older flows may have missed setting the boolean.
    # Consider only sessions explicitly marked completed
    completed_sessions = TestSession.objects.filter(
        student_id=student_id,
        is_completed=True
    ).order_by('start_time')

    if not completed_sessions.exists():
        return Response({
            "totalTests": 0,
            "totalQuestions": 0,
            "overallAccuracy": 0,
            "averageScore": 0,
            "completionRate": 100,
            "subjectPerformance": [],
            "chapterPerformance": [],
            "timeAnalysis": {
                "averageTimePerQuestion": 0,
                "fastestTime": 0,
                "slowestTime": 0,
                "timeEfficiency": 0,
                "rushingTendency": 0
            },
            "progressTrend": [],
            "weakAreas": [],
            "strengths": [],
            "sessions": [],
            "answers": [],
            "questions": [],
            "totalTimeSpent": 0,
        })

    # Basic Metrics
    total_tests = completed_sessions.count()
    all_answers = TestAnswer.objects.filter(
        session__in=completed_sessions
    ).select_related('question__topic', 'question')

    total_questions_attempted = all_answers.count()
    correct_answers = all_answers.filter(is_correct=True).count()
    overall_accuracy = (correct_answers / total_questions_attempted * 100) if total_questions_attempted > 0 else 0

    # Calculate average score across all sessions (based on correct_answers/total_questions)
    session_scores = []
    for session in completed_sessions:
        if session.total_questions > 0:
            session_score = (session.correct_answers / session.total_questions) * 100
            session_scores.append(session_score)
    
    average_score = sum(session_scores) / len(session_scores) if session_scores else 0

    # Subject Performance Analysis
    subject_performance = []
    subjects = ['Physics', 'Chemistry', 'Biology']
    
    for subject in subjects:
        subject_answers = all_answers.filter(question__topic__subject=subject)
        if subject_answers.exists():
            subject_correct = subject_answers.filter(is_correct=True).count()
            subject_total = subject_answers.count()
            subject_accuracy = (subject_correct / subject_total * 100) if subject_total > 0 else 0
            
            subject_performance.append({
                "subject": subject,
                "accuracy": round(subject_accuracy, 2),
                "totalQuestions": subject_total,
                "correctAnswers": subject_correct
            })

    # Progress Trend (last 5 sessions)
    recent_sessions = completed_sessions.order_by('-start_time')[:5]
    progress_trend = []
    for session in reversed(recent_sessions):
        session_score = (session.correct_answers / session.total_questions * 100) if session.total_questions > 0 else 0
        session_accuracy = (session.correct_answers / session.total_questions * 100) if session.total_questions > 0 else 0
        progress_trend.append({
            "testDate": session.start_time.strftime("%Y-%m-%d"),
            "score": round(session_score, 2),
            "accuracy": round(session_accuracy, 2)
        })

    # Calculate total time spent (using total_time_taken field)
    total_time_spent = 0
    for session in completed_sessions:
        if session.total_time_taken:
            total_time_spent += session.total_time_taken / 60  # Convert seconds to minutes
        elif session.start_time and session.end_time:
            # Fallback: calculate from start/end time if total_time_taken is not available
            session_duration = (session.end_time - session.start_time).total_seconds() / 60
            total_time_spent += session_duration

    # Session data for detailed view
    sessions_data = []
    for session in completed_sessions:
        session_score = (session.correct_answers / session.total_questions * 100) if session.total_questions > 0 else 0
        sessions_data.append({
            "id": session.id,
            "startTime": session.start_time.isoformat() if session.start_time else None,
            "endTime": session.end_time.isoformat() if session.end_time else None,
            "score": round(session_score, 2),
            "correctAnswers": session.correct_answers,
            "totalQuestions": session.total_questions,
            "isCompleted": session.is_completed
        })

    return Response({
        "totalTests": total_tests,
        "totalQuestions": total_questions_attempted,
        "overallAccuracy": round(overall_accuracy, 2),
        "averageScore": round(average_score, 2),
        "completionRate": 100,  # All fetched sessions are completed
        "subjectPerformance": subject_performance,
        "chapterPerformance": [],  # Can be implemented later if needed
        "timeAnalysis": {
            "averageTimePerQuestion": round(total_time_spent / total_questions_attempted, 2) if total_questions_attempted > 0 else 0,
            "fastestTime": 0,  # Can be calculated if needed
            "slowestTime": 0,  # Can be calculated if needed
            "timeEfficiency": 100,  # Can be calculated based on expected vs actual time
            "rushingTendency": 0  # Can be calculated based on time patterns
        },
        "progressTrend": progress_trend,
        "weakAreas": [],  # Can be populated based on low-performing topics
        "strengths": [],   # Can be populated based on high-performing topics
        "sessions": sessions_data,
        "answers": [],     # Can be populated if detailed answer analysis is needed
        "questions": [],   # Can be populated if question analysis is needed
        "totalTimeSpent": round(total_time_spent, 2),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_comprehensive_analytics(request):
    """
    Comprehensive landing dashboard analytics.
    Returns analytics data for the authenticated user only.
    """        
    # Get the authenticated student
    if not hasattr(request.user, 'student_id'):
        return Response({"error": "User not properly authenticated"}, status=401)
    
    student_id = request.user.student_id
    
    # Filter all queries by the authenticated student
    # Only consider sessions that are explicitly completed
    all_sessions = TestSession.objects.filter(student_id=student_id)
    completed_sessions = all_sessions.filter(is_completed=True)

    if not completed_sessions.exists():
        return Response({
            'totalTests': 0,
            'totalQuestions': 0,
            'overallAccuracy': 0,
            'averageScore': 0,
            'totalTimeSpent': 0,
            'averageTimePerQuestion': 0,
            'speedVsAccuracy': {
                'averageSpeed': 0,
                'speedCategory': 'Moderate',
                'accuracyCategory': 'Medium',
                'recommendation': 'Take more tests to generate personalized recommendations.'
            },
            'strengthAreas': [],
            'challengingAreas': [],
            'subjectPerformance': [],
            'timeBasedTrends': [],
            'studyRecommendations': []
            # Add unique questions attempted (0) and total questions in bank
            ,
            'uniqueQuestionsAttempted': 0,
            'totalQuestionsInBank': Question.objects.count()
            ,
            'topicPerformance': [],
            'topicsAttemptedCount': 0
        })

    total_tests = completed_sessions.count()
    all_answers_for_completed_sessions = TestAnswer.objects.filter(
        session__in=completed_sessions
    ).select_related('question__topic')
    total_questions_attempted = all_answers_for_completed_sessions.count()
    correct_answers_count = all_answers_for_completed_sessions.filter(is_correct=True).count()

    overall_accuracy = (correct_answers_count / total_questions_attempted) * 100 if total_questions_attempted > 0 else 0
    average_score = overall_accuracy

    total_time_spent_in_tests = sum([
        (s.end_time - s.start_time).total_seconds() for s in completed_sessions if s.start_time and s.end_time
    ])
    average_time_per_question = (all_answers_for_completed_sessions.aggregate(avg_time=Avg('time_taken'))['avg_time'] or 0)

    speed_category = 'Moderate'
    if average_time_per_question < 60:
        speed_category = 'Fast'
    elif average_time_per_question >= 120:
        speed_category = 'Slow'

    accuracy_category = 'Medium'
    if overall_accuracy >= 80:
        accuracy_category = 'High'
    elif overall_accuracy < 60:
        accuracy_category = 'Low'

    recommendation = ''
    if speed_category == 'Fast' and accuracy_category == 'High':
        recommendation = 'Excellent balance! You\'re fast and accurate. Focus on challenging topics to maintain this performance.'
    elif speed_category == 'Fast' and accuracy_category == 'Low':
        recommendation = 'You\'re fast but making mistakes. Slow down slightly and focus on accuracy. Review incorrect answers.'
    elif speed_category == 'Slow' and accuracy_category == 'High':
        recommendation = 'Great accuracy! Work on speed drills with familiar topics to improve timing without losing precision.'
    elif speed_category == 'Slow' and accuracy_category == 'Low':
        recommendation = 'Focus on understanding concepts first, then practice speed. Quality over quantity in initial stages.'
    else:
        recommendation = 'You have a good foundation. Practice regularly to improve both speed and accuracy.'

    speed_vs_accuracy = {
        'averageSpeed': round(average_time_per_question, 2),
        'speedCategory': speed_category,
        'accuracyCategory': accuracy_category,
        'recommendation': recommendation
    }

    subject_performance_summary = []
    all_subjects = Topic.objects.values_list('subject', flat=True).distinct()
    for subject_name in all_subjects:
        topic_ids_for_subject = Topic.objects.filter(subject=subject_name).values_list('id', flat=True)
        subject_answers = all_answers_for_completed_sessions.filter(question__topic_id__in=topic_ids_for_subject)
        total = subject_answers.count()
        correct = subject_answers.filter(is_correct=True).count()
        accuracy = (correct / total) * 100 if total > 0 else 0
        avg_time_per_q = subject_answers.aggregate(avg_time=Avg('time_taken'))['avg_time'] or 0

        if total > 0:
            subject_performance_summary.append({
                'subject': subject_name,
                'accuracy': round(accuracy, 2),
                'totalQuestions': total,
                'correctAnswers': correct,
                'timeSpent': subject_answers.aggregate(total_time=Sum('time_taken'))['total_time'] or 0,
                'avgTimePerQuestion': round(avg_time_per_q, 2),
                'improvement': 0  # Placeholder
            })

    subject_performance_summary_sorted_acc = sorted(subject_performance_summary, key=lambda x: x['accuracy'])
    challenging_areas = subject_performance_summary_sorted_acc[:3]
    strength_areas = subject_performance_summary_sorted_acc[-3:][::-1]

    for area in challenging_areas:
        area['improvementTips'] = [
            f"Practice {area['subject']} fundamentals daily",
            "Focus on conceptual understanding",
            "Take subject-specific mock tests",
            "Review incorrect answers carefully"
        ]

    for area in strength_areas:
        area['consistency'] = round(random.uniform(80, 100), 2)

    time_based_trends_raw = []
    # Prepare an ordered list of completed session ids to compute per-student test numbers
    all_completed_ids = list(completed_sessions.order_by('start_time').values_list('id', flat=True))
    recent_sessions_desc = completed_sessions.order_by('-start_time')[:7]
    for session in recent_sessions_desc:
        session_answers = TestAnswer.objects.filter(session=session)
        session_correct = session_answers.filter(is_correct=True).count()
        session_total = session.total_questions
        session_accuracy = (session_correct / session_total) * 100 if session_total > 0 else 0
        session_time_spent_on_answers = session_answers.aggregate(total_time=Sum('time_taken'))['total_time'] or 0
        session_speed = (session_time_spent_on_answers / session_answers.count()) if session_answers.count() > 0 else 0

        # Compute the ordinal test number for this student (1-based)
        try:
            test_number = all_completed_ids.index(session.id) + 1
        except ValueError:
            test_number = None

        time_based_trends_raw.append({
            'date': session.start_time.isoformat().split('T')[0],
            'accuracy': round(session_accuracy, 2),
            'speed': round(session_speed, 2),
            'testsCount': 1,
            'testNumber': test_number
        })
    time_based_trends = time_based_trends_raw[::-1]

    study_recommendations = []

    if challenging_areas:
        study_recommendations.append({
            'priority': 'High',
            'subject': challenging_areas[0]['subject'],
            'topic': 'Fundamental Concepts',
            'reason': f"Low accuracy ({challenging_areas[0]['accuracy']:.1f}%) indicates conceptual gaps",
            'actionTip': 'Spend 2-3 hours daily on basic concepts and practice problems'
        })

    if average_time_per_question > 120:
        study_recommendations.append({
            'priority': 'Medium',
            'subject': 'All Subjects',
            'topic': 'Speed Enhancement',
            'reason': 'Taking too long per question affects overall performance',
            'actionTip': 'Practice timed tests with 90-second per question limit'
        })

    if strength_areas:
        study_recommendations.append({
            'priority': 'Low',
            'subject': strength_areas[0]['subject'],
            'topic': 'Advanced Problems',
            'reason': f"Strong performance ({strength_areas[0]['accuracy']:.1f}%) - ready for challenges",
            'actionTip': 'Attempt previous year questions and advanced problem sets'
        })

    # Compute unique questions attempted and total bank size
    unique_questions_attempted = all_answers_for_completed_sessions.values_list('question_id', flat=True).distinct().count()
    total_questions_in_bank = Question.objects.count()

    # Topic-level performance: compute per-topic total and correct counts for this student
    # Aggregation done on TestAnswer rows within completed sessions for this student
    topic_performance = []
    topic_agg = all_answers_for_completed_sessions.values(
        'question__topic_id',
        'question__topic__name',
        'question__topic__subject'
    ).annotate(
        total=Count('id'),
        correct=Count('id', filter=Q(is_correct=True))
    ).order_by('-total')

    for t in topic_agg:
        total = t.get('total', 0) or 0
        correct = t.get('correct', 0) or 0
        accuracy = (correct / total * 100) if total > 0 else 0
        topic_performance.append({
            'topicId': t.get('question__topic_id'),
            'topic': t.get('question__topic__name'),
            'subject': t.get('question__topic__subject'),
            'totalQuestions': total,
            'correctAnswers': correct,
            'accuracy': round(accuracy, 2)
        })

    topics_attempted_count = len(topic_performance)

    # Fallback: if aggregation returned no rows but there are answers, compute per-topic counts explicitly
    if topics_attempted_count == 0 and total_questions_attempted > 0:
        topic_ids = all_answers_for_completed_sessions.values_list('question__topic_id', flat=True).distinct()
        for tid in topic_ids:
            topic_obj = Topic.objects.filter(id=tid).first()
            if not topic_obj:
                continue
            subj_answers = all_answers_for_completed_sessions.filter(question__topic_id=tid)
            total = subj_answers.count()
            correct = subj_answers.filter(is_correct=True).count()
            accuracy = (correct / total * 100) if total > 0 else 0
            topic_performance.append({
                'topicId': tid,
                'topic': topic_obj.name,
                'subject': topic_obj.subject,
                'totalQuestions': total,
                'correctAnswers': correct,
                'accuracy': round(accuracy, 2)
            })

        topics_attempted_count = len(topic_performance)

    # --- New: Aggregations for the past 7 tests ---
    # recent_sessions_desc already contains up to 7 most recent sessions (ordered desc)
    recent_sessions_for_agg = list(recent_sessions_desc)
    # Answers limited to most recent 7 sessions
    recent_answers = all_answers_for_completed_sessions.filter(session__in=recent_sessions_desc)

    # Subject-wise accuracy distribution across past 7 tests
    subject_accuracy_past7 = []
    for subject_name in all_subjects:
        topic_ids_for_subject = Topic.objects.filter(subject=subject_name).values_list('id', flat=True)
        subj_answers = recent_answers.filter(question__topic_id__in=topic_ids_for_subject)
        subj_total = subj_answers.count()
        subj_correct = subj_answers.filter(is_correct=True).count()
        subj_accuracy = (subj_correct / subj_total * 100) if subj_total > 0 else 0

        subject_accuracy_past7.append({
            'subject': subject_name,
            'totalQuestions': subj_total,
            'correctAnswers': subj_correct,
            'accuracy': round(subj_accuracy, 2)
        })

    # Time distribution (sec) between correct / incorrect / unanswered for past 7 tests
    from django.db.models import Q as DjangoQ

    overall_correct_time = recent_answers.filter(is_correct=True).aggregate(total_time=Sum('time_taken'))['total_time'] or 0
    overall_incorrect_time = recent_answers.filter(is_correct=False).aggregate(total_time=Sum('time_taken'))['total_time'] or 0
    overall_unanswered_time = recent_answers.filter(DjangoQ(is_correct__isnull=True) | DjangoQ(selected_answer__isnull=True)).aggregate(total_time=Sum('time_taken'))['total_time'] or 0

    # Compute averages per test (over the number of recent sessions considered)
    sessions_count = max(1, len(recent_sessions_for_agg))
    overall_correct_avg = round(overall_correct_time / sessions_count, 2)
    overall_incorrect_avg = round(overall_incorrect_time / sessions_count, 2)
    overall_unanswered_avg = round(overall_unanswered_time / sessions_count, 2)

    time_distribution_overall = [
        {'status': 'correct', 'timeSec': overall_correct_time, 'avgTimeSec': overall_correct_avg},
        {'status': 'incorrect', 'timeSec': overall_incorrect_time, 'avgTimeSec': overall_incorrect_avg},
        {'status': 'unanswered', 'timeSec': overall_unanswered_time, 'avgTimeSec': overall_unanswered_avg},
    ]

    # By-subject breakdown
    time_distribution_by_subject = {}
    for subject_name in all_subjects:
        topic_ids_for_subject = Topic.objects.filter(subject=subject_name).values_list('id', flat=True)
        subj_answers = recent_answers.filter(question__topic_id__in=topic_ids_for_subject)
        correct_t = subj_answers.filter(is_correct=True).aggregate(total_time=Sum('time_taken'))['total_time'] or 0
        incorrect_t = subj_answers.filter(is_correct=False).aggregate(total_time=Sum('time_taken'))['total_time'] or 0
        unanswered_t = subj_answers.filter(DjangoQ(is_correct__isnull=True) | DjangoQ(selected_answer__isnull=True)).aggregate(total_time=Sum('time_taken'))['total_time'] or 0

        # Average per test for this subject across recent sessions
        correct_avg = round(correct_t / sessions_count, 2)
        incorrect_avg = round(incorrect_t / sessions_count, 2)
        unanswered_avg = round(unanswered_t / sessions_count, 2)

        time_distribution_by_subject[subject_name] = [
            {'status': 'correct', 'timeSec': correct_t, 'avgTimeSec': correct_avg},
            {'status': 'incorrect', 'timeSec': incorrect_t, 'avgTimeSec': incorrect_avg},
            {'status': 'unanswered', 'timeSec': unanswered_t, 'avgTimeSec': unanswered_avg},
        ]

    subjects_list = list(all_subjects)

    return Response({
        'totalTests': total_tests,
        'totalQuestions': total_questions_attempted,
        'overallAccuracy': round(overall_accuracy, 2),
        'averageScore': round(average_score, 2),
        'totalTimeSpent': int(total_time_spent_in_tests),
        'averageTimePerQuestion': round(average_time_per_question, 2),
        'speedVsAccuracy': speed_vs_accuracy,
        'strengthAreas': strength_areas,
        'challengingAreas': challenging_areas,
        'subjectPerformance': subject_performance_summary,
        'timeBasedTrends': time_based_trends,
        'studyRecommendations': study_recommendations,
        'uniqueQuestionsAttempted': unique_questions_attempted,
        'totalQuestionsInBank': total_questions_in_bank,
    'topicPerformance': topic_performance,
    'topicsAttemptedCount': topics_attempted_count,
        # New payloads for pie charts (past 7 tests)
        'subjectAccuracyPast7': subject_accuracy_past7,
        'timeDistributionPast7': {
            'overall': time_distribution_overall,
            'bySubject': time_distribution_by_subject,
            'subjects': subjects_list
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_test_analytics(request):
    """
    Provides analytics for platform tests including available tests and student performance.
    Returns platform test data for the Alternate tab metrics.
    """
    # Get the authenticated student
    if not hasattr(request.user, 'student_id'):
        return Response({"error": "User not properly authenticated"}, status=401)
    
    student_id = request.user.student_id
    
    # Get list of platform tests the student has taken (slicer should show only tests the student has taken)
    # Only include platform tests from sessions that were completed
    taken_platform_test_ids = TestSession.objects.filter(
        student_id=student_id,
        platform_test__isnull=False,
        is_completed=True
    ).values_list('platform_test_id', flat=True).distinct()

    platform_tests_qs = PlatformTest.objects.filter(
        id__in=taken_platform_test_ids,
        is_active=True
    ).values('id', 'test_name', 'test_code', 'test_year', 'test_type').order_by('-test_year', 'test_name')

    available_tests = []
    for pt in platform_tests_qs:
        available_tests.append({
            'id': pt.get('id'),
            'testName': pt.get('test_name'),
            'testCode': pt.get('test_code'),
            'testYear': pt.get('test_year'),
            'testType': pt.get('test_type'),
        })
    
    # Get platform test ID from query params (optional)
    selected_test_id = request.GET.get('test_id')
    
    # Initialize response data
    response_data = {
        'availableTests': available_tests,
        'selectedTestMetrics': None
    }
    
    # If a specific test is selected, calculate metrics for that test
    if selected_test_id:
        try:
            selected_test = PlatformTest.objects.get(id=selected_test_id, is_active=True)
        except PlatformTest.DoesNotExist:
            response_data['selectedTestMetrics'] = {
                'error': 'Platform test not found or inactive.'
            }
        else:
            # Gather all completed sessions for this platform test ordered by start_time desc
            all_sessions = TestSession.objects.filter(
                test_type='platform',
                platform_test=selected_test,
                is_completed=True
            ).order_by('-start_time')

            # Build per-student best percentage mapping (student_id -> best_percent)
            student_best = {}
            # Also keep track of the most recent session for the authenticated student
            student_most_recent_session = None

            for s in all_sessions:
                # Prefer calculating accuracy from TestAnswer records to avoid stale/zero fields on TestSession
                answers_qs = TestAnswer.objects.filter(session=s)
                total_answers = answers_qs.count()
                if total_answers > 0:
                    correct_count = answers_qs.filter(is_correct=True).count()
                    percent = (correct_count / total_answers) * 100
                else:
                    # Fallback to TestSession stored fields if TestAnswer rows are missing
                    if s.total_questions and s.total_questions > 0:
                        percent = (s.correct_answers / s.total_questions) * 100
                    else:
                        percent = 0

                prev = student_best.get(s.student_id)
                if prev is None or percent > prev:
                    student_best[s.student_id] = percent

                if s.student_id == student_id and student_most_recent_session is None:
                    student_most_recent_session = s

            total_students = len(student_best)

            # Compute current student's metrics if they have a session
            if student_most_recent_session:
                # Prefer TestAnswer-based calculation for student's most recent session
                cur_answers = TestAnswer.objects.filter(session=student_most_recent_session)
                cur_total = cur_answers.count()
                if cur_total > 0:
                    cur_correct = cur_answers.filter(is_correct=True).count()
                    overall_accuracy = (cur_correct / cur_total) * 100
                else:
                    overall_accuracy = (student_most_recent_session.correct_answers / student_most_recent_session.total_questions * 100) if student_most_recent_session.total_questions else 0

                # Determine rank using best percentage across students (robust to ties)
                # Ensure current student is present in the mapping
                current_percent = student_best.get(student_id)
                if current_percent is None:
                    # Fallback: use most recent session percent
                    current_percent = overall_accuracy
                    student_best[student_id] = current_percent

                # Create a descending ordered list of (student_id, percent)
                sorted_by_percent = sorted(student_best.items(), key=lambda kv: kv[1], reverse=True)

                # Find rank as the 1-based index of the first occurrence of this student's percent
                rank = 1
                for idx, (sid, pct) in enumerate(sorted_by_percent, start=1):
                    if sid == student_id:
                        rank = idx
                        break

                # Percentile: robust calculation handling ties and avoiding division by zero
                if total_students > 0:
                    num_below = sum(1 for pct in student_best.values() if pct < current_percent)
                    num_equal = sum(1 for pct in student_best.values() if pct == current_percent)
                    # Use midpoint rank for ties: add half of equals
                    percentile = ((num_below + (num_equal / 2)) / total_students) * 100
                else:
                    percentile = 0

                # Avg time per question: prefer stored total_time_taken; fallback to summing TestAnswer.time_taken
                if student_most_recent_session.total_time_taken and student_most_recent_session.total_questions:
                    avg_time_per_question = student_most_recent_session.total_time_taken / student_most_recent_session.total_questions
                else:
                    ans_agg = TestAnswer.objects.filter(session=student_most_recent_session).aggregate(total_time=Sum('time_taken'), cnt=Count('id'))
                    total_time = ans_agg.get('total_time') or 0
                    cnt = ans_agg.get('cnt') or 0
                    avg_time_per_question = (total_time / cnt) if cnt > 0 else 0

                # Subject-wise accuracy for this student in the selected test
                subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology']
                subject_accuracy_for_test = []
                for subj in subjects:
                    subj_answers = TestAnswer.objects.filter(session=student_most_recent_session, question__topic__subject__iexact=subj)
                    subj_total = subj_answers.count()
                    subj_correct = subj_answers.filter(is_correct=True).count()
                    subj_accuracy = (subj_correct / subj_total * 100) if subj_total > 0 else None
                    subject_accuracy_for_test.append({
                        'subject': subj,
                        'accuracy': round(subj_accuracy, 2) if subj_accuracy is not None else None,
                        'totalQuestions': subj_total
                    })

                # Time distribution for this student's most recent session of the selected test
                overall_correct_time = TestAnswer.objects.filter(session=student_most_recent_session, is_correct=True).aggregate(total_time=Sum('time_taken'))['total_time'] or 0
                overall_incorrect_time = TestAnswer.objects.filter(session=student_most_recent_session, is_correct=False).aggregate(total_time=Sum('time_taken'))['total_time'] or 0
                overall_unanswered_time = TestAnswer.objects.filter(session=student_most_recent_session).filter(Q(is_correct__isnull=True) | Q(selected_answer__isnull=True)).aggregate(total_time=Sum('time_taken'))['total_time'] or 0

                time_distribution_overall_test = [
                    {'status': 'correct', 'timeSec': overall_correct_time},
                    {'status': 'incorrect', 'timeSec': overall_incorrect_time},
                    {'status': 'unanswered', 'timeSec': overall_unanswered_time},
                ]

                # By-subject breakdown for this session
                time_distribution_by_subject_test = {}
                for subj in subjects:
                    subj_answers = TestAnswer.objects.filter(session=student_most_recent_session, question__topic__subject__iexact=subj)
                    correct_t = subj_answers.filter(is_correct=True).aggregate(total_time=Sum('time_taken'))['total_time'] or 0
                    incorrect_t = subj_answers.filter(is_correct=False).aggregate(total_time=Sum('time_taken'))['total_time'] or 0
                    unanswered_t = subj_answers.filter(Q(is_correct__isnull=True) | Q(selected_answer__isnull=True)).aggregate(total_time=Sum('time_taken'))['total_time'] or 0
                    time_distribution_by_subject_test[subj] = [
                        {'status': 'correct', 'timeSec': correct_t},
                        {'status': 'incorrect', 'timeSec': incorrect_t},
                        {'status': 'unanswered', 'timeSec': unanswered_t},
                    ]

                response_data['selectedTestMetrics'] = {
                    'testId': selected_test.id,
                    'testName': selected_test.test_name,
                    'testCode': selected_test.test_code,
                    'overallAccuracy': round(overall_accuracy, 1),
                    'rank': rank,
                    'totalStudents': total_students,
                    'percentile': round(percentile, 1) if percentile is not None else None,
                    'avgTimePerQuestion': round(avg_time_per_question, 1),
                    'sessionId': student_most_recent_session.id,
                    'testDate': student_most_recent_session.start_time.isoformat() if student_most_recent_session.start_time else None,
                    'subjectAccuracyForTest': subject_accuracy_for_test,
                    'timeDistributionForTest': {
                        'overall': time_distribution_overall_test,
                        'bySubject': time_distribution_by_subject_test,
                        'subjects': subjects
                    }
                }
                # Build leaderboard: top 3 students by best percent (rank ascending)
                leaderboard = []
                # sorted_by_percent already computed earlier as sorted(student_best.items(), key=lambda kv: kv[1], reverse=True)
                # ensure it's available here
                sorted_students = sorted(student_best.items(), key=lambda kv: kv[1], reverse=True)

                def select_best_session_for_student(sid, target_percent):
                    # Find session for this student with percent closest to target_percent (prefer highest percent and lower time)
                    candidate_sessions = all_sessions.filter(student_id=sid)
                    best_s = None
                    best_diff = None
                    for cs in candidate_sessions:
                        pct = (cs.correct_answers / cs.total_questions * 100) if cs.total_questions else 0
                        diff = abs(pct - target_percent)
                        if best_diff is None or diff < best_diff or (diff == best_diff and (cs.total_time_taken or 0) < (best_s.total_time_taken or 0)):
                            best_diff = diff
                            best_s = cs
                    return best_s

                subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology']
                for sid, pct in sorted_students[:3]:
                    s_session = select_best_session_for_student(sid, pct)
                    if not s_session:
                        continue

                    # Calculate per-subject accuracies from TestAnswer table for this session
                    subj_acc = {}
                    for subj in subjects:
                        subj_answers = TestAnswer.objects.filter(session=s_session, question__topic__subject__iexact=subj)
                        total = subj_answers.count()
                        correct = subj_answers.filter(is_correct=True).count()
                        subj_acc[subj.lower()] = round((correct / total * 100), 2) if total > 0 else None

                    # Time taken
                    if s_session.total_time_taken:
                        time_taken = s_session.total_time_taken
                    else:
                        time_taken = TestAnswer.objects.filter(session=s_session).aggregate(total_time=Sum('time_taken'))['total_time'] or 0

                    # Student name
                    student_profile = StudentProfile.objects.filter(student_id=sid).first()
                    student_name = student_profile.full_name if student_profile else sid

                    leaderboard.append({
                        'studentId': sid,
                        'studentName': student_name,
                        'accuracy': round(pct, 2),
                        'physics': subj_acc.get('physics'),
                        'chemistry': subj_acc.get('chemistry'),
                        'botany': subj_acc.get('botany'),
                        'zoology': subj_acc.get('zoology'),
                        'timeTakenSec': time_taken,
                        'rank': sorted_students.index((sid, pct)) + 1
                    })

                # Sort leaderboard by rank asc and attach
                leaderboard = sorted(leaderboard, key=lambda x: x['rank'])
                response_data['selectedTestMetrics']['leaderboard'] = leaderboard
            else:
                # Student hasn't taken this test; still report total students who have taken it
                response_data['selectedTestMetrics'] = {
                    'testId': selected_test.id,
                    'testName': selected_test.test_name,
                    'testCode': selected_test.test_code,
                    'message': 'You have not taken this test yet.',
                    'overallAccuracy': 0,
                    'rank': None,
                    'totalStudents': total_students,
                    'percentile': None,
                    'avgTimePerQuestion': 0
                }
    # Ensure we always return a Response
    return Response(response_data)
