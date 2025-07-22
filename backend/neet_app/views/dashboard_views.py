import random
from django.db.models import Avg, Count, Max, Min, Sum
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Question, TestAnswer, TestSession, Topic
from ..serializers import QuestionSerializer, TestAnswerSerializer, TestSessionSerializer


@api_view(['GET'])
def dashboard_analytics(request):
    """
    Generates comprehensive student performance analytics for the dashboard.
    Replicates GET /api/dashboard/analytics logic.
    """
    all_sessions = TestSession.objects.all()
    completed_sessions = all_sessions.filter(is_completed=True).order_by('start_time')

    if not completed_sessions.exists():
        return Response({
            "totalTests": 0,
            "totalQuestions": 0,
            "overallAccuracy": 0,
            "averageScore": 0,
            "completionRate": 0,
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
    all_answers_for_completed_sessions = TestAnswer.objects.filter(
        session__in=completed_sessions
    ).select_related('question__topic')

    total_questions_attempted = all_answers_for_completed_sessions.count()
    correct_answers_count = all_answers_for_completed_sessions.filter(is_correct=True).count()

    overall_accuracy = (correct_answers_count / total_questions_attempted) * 100 if total_questions_attempted > 0 else 0
    average_score = overall_accuracy

    completion_rate = (total_tests / all_sessions.count()) * 100 if all_sessions.count() > 0 else 0

    # Subject-wise Performance
    subject_performance = []
    all_subjects = Topic.objects.values_list('subject', flat=True).distinct()
    for subject_name in all_subjects:
        topic_ids_for_subject = Topic.objects.filter(subject=subject_name).values_list('id', flat=True)
        subject_answers = all_answers_for_completed_sessions.filter(question__topic_id__in=topic_ids_for_subject)

        subject_total_attempted = subject_answers.count()
        subject_correct = subject_answers.filter(is_correct=True).count()
        subject_accuracy = (subject_correct / subject_total_attempted) * 100 if subject_total_attempted > 0 else 0

        subject_avg_time_per_q = subject_answers.aggregate(avg_time=Avg('time_taken'))['avg_time'] or 0

        color_map = {
            'Physics': '#3b82f6',
            'Chemistry': '#10b981',
            'Botany': '#f59e0b',
            'Zoology': '#8b5cf6',
        }

        subject_performance.append({
            'subject': subject_name,
            'accuracy': round(subject_accuracy, 2),
            'questionsAttempted': subject_total_attempted,
            'averageTime': round(subject_avg_time_per_q, 2),
            'color': color_map.get(subject_name, '#6b7280')
        })

    # Chapter-wise Performance
    chapter_performance = []
    distinct_chapters = Topic.objects.exclude(chapter__isnull=True).values('chapter', 'subject').distinct()
    for chapter_data in distinct_chapters:
        chapter_name = chapter_data['chapter']
        subject_name = chapter_data['subject']

        topic_ids_for_chapter = Topic.objects.filter(
            chapter=chapter_name, subject=subject_name
        ).values_list('id', flat=True)

        chapter_answers = all_answers_for_completed_sessions.filter(question__topic_id__in=topic_ids_for_chapter)
        chapter_total_attempted = chapter_answers.count()
        chapter_correct = chapter_answers.filter(is_correct=True).count()
        chapter_accuracy = (chapter_correct / chapter_total_attempted) * 100 if chapter_total_attempted > 0 else 0

        total_questions_in_chapter = Question.objects.filter(topic_id__in=topic_ids_for_chapter).count()

        chapter_performance.append({
            'chapter': chapter_name,
            'subject': subject_name,
            'accuracy': round(chapter_accuracy, 2),
            'questionsAttempted': chapter_total_attempted,
            'totalQuestions': total_questions_in_chapter,
            'improvement': 0  # Placeholder: Needs historical data for actual calculation
        })

    # Time Analysis
    total_time_spent_on_answers = all_answers_for_completed_sessions.aggregate(total_time=Sum('time_taken'))['total_time'] or 0
    average_time_per_question = (total_time_spent_on_answers / total_questions_attempted) if total_questions_attempted > 0 else 0

    fastest_time_per_question = all_answers_for_completed_sessions.aggregate(min_time=Min('time_taken'))['min_time'] or 0
    slowest_time_per_question = all_answers_for_completed_sessions.aggregate(max_time=Max('time_taken'))['max_time'] or 0

    time_efficiency = 0  # Placeholder
    rushing_tendency = 0  # Placeholder

    time_analysis = {
        'averageTimePerQuestion': round(average_time_per_question, 2),
        'fastestTime': fastest_time_per_question,
        'slowestTime': slowest_time_per_question,
        'timeEfficiency': time_efficiency,
        'rushingTendency': rushing_tendency
    }

    # Progress Trend (last 10 completed sessions)
    progress_trend = []
    recent_completed_sessions = completed_sessions.order_by('start_time')[:10]
    for i, session in enumerate(recent_completed_sessions):
        session_answers = TestAnswer.objects.filter(session=session)
        session_correct = session_answers.filter(is_correct=True).count()
        session_total = session.total_questions
        session_accuracy = (session_correct / session_total) * 100 if session_total > 0 else 0

        progress_trend.append({
            'testNumber': i + 1,
            'date': session.start_time.isoformat().split('T')[0],
            'accuracy': round(session_accuracy, 2),
            'score': round(session_accuracy, 2)
        })

    # Weak Areas (chapters with low accuracy, more than 0 questions attempted)
    weak_areas = sorted([
        ch for ch in chapter_performance if ch['accuracy'] < 70 and ch['questionsAttempted'] > 0
    ], key=lambda x: x['accuracy'])[:5]

    for area in weak_areas:
        if area['accuracy'] < 50:
            area['priority'] = 'High'
        elif area['accuracy'] < 60:
            area['priority'] = 'Medium'
        else:
            area['priority'] = 'Low'

    # Strengths (chapters with high accuracy, more than 0 questions attempted)
    strengths = sorted([
        ch for ch in chapter_performance if ch['accuracy'] > 80 and ch['questionsAttempted'] > 0
    ], key=lambda x: x['accuracy'], reverse=True)[:5]

    for area in strengths:
        area['consistency'] = 0  # Placeholder

    total_time_spent_in_tests = sum([
        (s.end_time - s.start_time).total_seconds() for s in completed_sessions if s.start_time and s.end_time
    ])

    analytics = {
        'totalTests': total_tests,
        'totalQuestions': total_questions_attempted,
        'overallAccuracy': round(overall_accuracy, 2),
        'averageScore': round(average_score, 2),
        'completionRate': round(completion_rate, 2),
        'subjectPerformance': subject_performance,
        'chapterPerformance': chapter_performance,
        'timeAnalysis': time_analysis,
        'progressTrend': progress_trend,
        'weakAreas': weak_areas,
        'strengths': strengths,
    }

    return Response({
        'sessions': TestSessionSerializer(completed_sessions, many=True).data,
        'answers': TestAnswerSerializer(all_answers_for_completed_sessions, many=True).data,
        'questions': QuestionSerializer(Question.objects.filter(
            id__in=all_answers_for_completed_sessions.values_list('question_id', flat=True)
        ), many=True).data,
        'analytics': analytics,
        'totalTimeSpent': int(total_time_spent_in_tests)
    })


@api_view(['GET'])
def dashboard_comprehensive_analytics(request):
    """
    Comprehensive landing dashboard analytics.
    Replicates GET /api/dashboard/comprehensive-analytics logic.
    """
    all_sessions = TestSession.objects.all()
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
    recent_sessions_desc = completed_sessions.order_by('-start_time')[:7]
    for session in recent_sessions_desc:
        session_answers = TestAnswer.objects.filter(session=session)
        session_correct = session_answers.filter(is_correct=True).count()
        session_total = session.total_questions
        session_accuracy = (session_correct / session_total) * 100 if session_total > 0 else 0
        session_time_spent_on_answers = session_answers.aggregate(total_time=Sum('time_taken'))['total_time'] or 0
        session_speed = (session_time_spent_on_answers / session_answers.count()) if session_answers.count() > 0 else 0

        time_based_trends_raw.append({
            'date': session.start_time.isoformat().split('T')[0],
            'accuracy': round(session_accuracy, 2),
            'speed': round(session_speed, 2),
            'testsCount': 1
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
        'studyRecommendations': study_recommendations
    })
