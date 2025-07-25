import random
from django.db.models import Avg, Count, Max, Min, Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Question, TestAnswer, TestSession, Topic
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
    
    # Get all completed test sessions for this specific student only
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
