"""
Celery tasks for asynchronous processing.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    # Fallback decorator if Celery not installed
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator
    CELERY_AVAILABLE = False
    logger.warning("Celery not available - tasks will run synchronously")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    soft_time_limit=300,  # 5 minutes
    time_limit=600,  # 10 minutes
    name='neet_app.tasks.generate_misconceptions_task'
)
def generate_misconceptions_task(self, test_id: int):
    """
    Generate misconceptions for all MCQ questions in a test.
    Runs asynchronously after test upload.
    
    Args:
        test_id: PlatformTest ID
        
    Returns:
        Dict with processing statistics
    """
    from django.utils import timezone
    from .models import PlatformTest
    
    try:
        # Update test status to 'processing'
        try:
            test = PlatformTest.objects.get(id=test_id)
            test.misconception_generation_status = 'processing'
            test.save(update_fields=['misconception_generation_status', 'updated_at'])
        except PlatformTest.DoesNotExist:
            logger.error(f'Test {test_id} not found')
            return {'status': 'error', 'error': 'Test not found'}
        
        from .services.misconception_service import generate_misconceptions_for_test
        
        logger.info(f'🧠 Generating misconceptions for test {test_id}')
        print(f"🧠 Starting misconception generation for test {test_id}")
        
        # Generate misconceptions
        result = generate_misconceptions_for_test(test_id, batch_size=20)
        
        if result['success']:
            # Update status to 'completed'
            test.misconception_generation_status = 'completed'
            test.misconception_generated_at = timezone.now()
            test.save(update_fields=['misconception_generation_status', 'misconception_generated_at', 'updated_at'])
            
            logger.info(
                f'✅ Misconceptions generated for test {test_id}: '
                f'{result["processed"]}/{result["total_questions"]} questions processed, '
                f'{result["failed"]} failed, '
                f'subjects: {", ".join(result["subjects_processed"])}'
            )
            print(
                f"✅ Misconceptions complete: {result['processed']}/{result['total_questions']} questions, "
                f"{result['failed']} failed"
            )
        else:
            # Update status to 'failed'
            test.misconception_generation_status = 'failed'
            test.save(update_fields=['misconception_generation_status', 'updated_at'])
            
            logger.error(f'❌ Misconception generation failed for test {test_id}: {result.get("error")}')
            print(f"❌ Misconception generation failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        # Update status to 'failed' on exception
        try:
            test = PlatformTest.objects.get(id=test_id)
            test.misconception_generation_status = 'failed'
            test.save(update_fields=['misconception_generation_status', 'updated_at'])
        except:
            pass
        
        logger.exception(f'generate_misconceptions_task failed for test {test_id}')
        print(f"❌ Misconception task error: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'test_id': test_id,
            'total_questions': 0,
            'processed': 0,
            'failed': 0
        }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    soft_time_limit=300,  # 5 minutes
    time_limit=600,  # 10 minutes
    name='neet_app.tasks.compute_results_task'
)
def compute_results_task(self, session_id: int):
    """
    Compute authoritative test results for a completed session.
    
    This task performs the heavy computation of evaluating each answer, calculating
    correctness, computing totals, and persisting the results to the database.
    It's designed to run asynchronously on Celery workers to avoid blocking the
    HTTP submit request.
    
    **Idempotency**: This task checks if results have already been computed by
    examining the session's answer records. If all answers have been evaluated
    (is_correct field set), the task skips computation to prevent duplicate work.
    
    **What it does**:
    1. Fetches TestSession and all TestAnswer records
    2. Evaluates each answer (MCQ, NVT, or Blank)
    3. Sets is_correct flag on each TestAnswer
    4. Computes totals: correct_answers, incorrect_answers, unanswered
    5. Calculates subject-wise performance
    6. Persists summary to TestSession (correct_answers, incorrect_answers, etc.)
    
    Args:
        session_id: TestSession ID to process
        
    Returns:
        Dict with result statistics:
        {
            'status': 'success' | 'error' | 'skipped',
            'session_id': int,
            'correct_answers': int,
            'incorrect_answers': int,
            'unanswered': int,
            'subjects_processed': int,
            'message': str (optional)
        }
    
    Raises:
        TestSession.DoesNotExist: If session not found
        Exception: Any database or computation error
    """
    from .models import TestSession, TestAnswer, Question
    from django.conf import settings
    
    try:
        # Fetch session
        try:
            session = TestSession.objects.get(id=session_id)
        except TestSession.DoesNotExist:
            logger.error(f'TestSession {session_id} not found')
            return {'status': 'error', 'error': 'Session not found', 'session_id': session_id}
        
        # Idempotency check: if results already computed, skip
        answers = TestAnswer.objects.filter(session=session).select_related('question', 'question__topic')
        
        # Check if any answer has been evaluated (has non-default is_correct value or was explicitly set)
        # We consider results "computed" if we have answers and the session has totals persisted
        if session.correct_answers is not None and session.correct_answers >= 0:
            logger.info(f'⏭️ Results already computed for session {session_id}, skipping')
            print(f"⏭️ Results already computed for session {session_id}")
            return {
                'status': 'skipped',
                'session_id': session_id,
                'message': 'Results already computed',
                'correct_answers': session.correct_answers,
                'incorrect_answers': session.incorrect_answers,
                'unanswered': session.unanswered
            }
        
        logger.info(f'🧮 Computing results for test session {session_id}')
        print(f"🧮 Starting result computation for session {session_id}")
        
        total_questions_in_session = session.total_questions
        correct_answers_count = 0
        incorrect_answers_count = 0
        unanswered_questions_count = 0
        subject_performance = {}
        
        # Process all TestAnswer objects
        for answer in answers:
            question = answer.question
            is_correct = False
            
            # Determine question type (NVT vs MCQ/Blank)
            q_type = (getattr(question, 'question_type', '') or '').upper()
            
            if q_type == 'NVT':
                # NVT: use text_answer field
                student_text = answer.text_answer if answer.text_answer is not None and str(answer.text_answer).strip() != '' else None
                
                if student_text is None:
                    unanswered_questions_count += 1
                    is_correct = False
                else:
                    # Evaluate NVT: numeric comparison first, then string
                    try:
                        student_numeric = float(str(student_text).strip())
                        correct_numeric = float(str(question.correct_answer).strip())
                        tolerance = settings.NEET_SETTINGS.get('NVT_NUMERIC_TOLERANCE', 0.01)
                        if abs(student_numeric - correct_numeric) <= float(tolerance):
                            correct_answers_count += 1
                            is_correct = True
                        else:
                            incorrect_answers_count += 1
                            is_correct = False
                    except (ValueError, TypeError):
                        # String comparison fallback
                        case_sensitive = settings.NEET_SETTINGS.get('NVT_CASE_SENSITIVE', False)
                        if case_sensitive:
                            match = str(student_text).strip() == str(question.correct_answer).strip()
                        else:
                            match = str(student_text).strip().lower() == str(question.correct_answer).strip().lower()
                        
                        if match:
                            correct_answers_count += 1
                            is_correct = True
                        else:
                            incorrect_answers_count += 1
                            is_correct = False
            else:
                # MCQ/Blank: use selected_answer field
                if answer.selected_answer is not None and str(answer.selected_answer).strip() != '':
                    if str(answer.selected_answer).strip() == str(question.correct_answer):
                        correct_answers_count += 1
                        is_correct = True
                    else:
                        incorrect_answers_count += 1
                        is_correct = False
                else:
                    unanswered_questions_count += 1
                    is_correct = False
            
            # Persist correctness
            answer.is_correct = is_correct
            answer.save(update_fields=['is_correct'])
            
            # Track subject performance
            subject_name = question.topic.subject
            if subject_name not in subject_performance:
                subject_performance[subject_name] = {'correct': 0, 'total': 0}
            subject_performance[subject_name]['total'] += 1
            if is_correct:
                subject_performance[subject_name]['correct'] += 1
        
        # Persist session summary
        session.correct_answers = correct_answers_count
        session.incorrect_answers = incorrect_answers_count
        session.unanswered = unanswered_questions_count
        session.save(update_fields=['correct_answers', 'incorrect_answers', 'unanswered'])
        
        logger.info(
            f'✅ Results computed for session {session_id}: '
            f'{correct_answers_count} correct, {incorrect_answers_count} incorrect, '
            f'{unanswered_questions_count} unanswered, {len(subject_performance)} subjects'
        )
        print(
            f"✅ Results complete for session {session_id}: "
            f"{correct_answers_count}/{total_questions_in_session} correct"
        )
        
        return {
            'status': 'success',
            'session_id': session_id,
            'correct_answers': correct_answers_count,
            'incorrect_answers': incorrect_answers_count,
            'unanswered': unanswered_questions_count,
            'subjects_processed': len(subject_performance)
        }
        
    except Exception as e:
        logger.exception(f'compute_results_task failed for session {session_id}')
        print(f"❌ Result computation failed for session {session_id}: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'session_id': session_id
        }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    soft_time_limit=300,  # 5 minutes
    time_limit=600,  # 10 minutes
    name='neet_app.tasks.generate_zone_insights_task'
)
def generate_zone_insights_task(self, session_id: int):
    """
    Generate checkpoint insights for all subjects in a completed test session.
    
    This task orchestrates the generation of subject-wise zone insights (checkpoints)
    using LLM analysis of wrong/skipped questions. Each subject gets exactly 2
    diagnostic checkpoints identifying problems and action plans.
    
    **Idempotency**: This task checks if zone insights already exist in the database
    for this session. If TestSubjectZoneInsight records are found, the task skips
    generation to avoid duplicate API calls and redundant processing.
    
    **What it does**:
    1. Checks if zone insights already exist (idempotency)
    2. Detects subjects present in the test (Physics, Chemistry, Botany, etc.)
    3. For each subject:
       - Extracts wrong/skipped questions grouped by topic
       - Calls LLM (Gemini) to generate 2 diagnostic checkpoints
       - Falls back to generic checkpoints if LLM unavailable
    4. Saves TestSubjectZoneInsight records to database
    5. Frontend polls these records to know when to show results
    
    Args:
        session_id: TestSession ID to process
        
    Returns:
        Dict with generation statistics:
        {
            'status': 'success' | 'error' | 'skipped',
            'session_id': int,
            'subjects_processed': int,
            'subjects': List[str],
            'message': str (optional)
        }
    
    Raises:
        TestSession.DoesNotExist: If session not found
        Exception: Any LLM or database error
    """
    from .models import TestSession, TestSubjectZoneInsight
    
    try:
        # Verify session exists
        try:
            session = TestSession.objects.get(id=session_id)
        except TestSession.DoesNotExist:
            logger.error(f'TestSession {session_id} not found')
            return {'status': 'error', 'error': 'Session not found', 'session_id': session_id}
        
        # Idempotency check: skip if zone insights already exist
        existing_insights = TestSubjectZoneInsight.objects.filter(test_session_id=session_id)
        if existing_insights.exists():
            subjects = list(existing_insights.values_list('subject', flat=True))
            logger.info(f'⏭️ Zone insights already exist for session {session_id}, skipping')
            print(f"⏭️ Zone insights already exist for session {session_id}: {subjects}")
            return {
                'status': 'skipped',
                'session_id': session_id,
                'subjects_processed': len(subjects),
                'subjects': subjects,
                'message': 'Zone insights already generated'
            }
        
        from .services.zone_insights_service import generate_all_subject_checkpoints
        
        logger.info(f'🎯 Generating zone insights for test session {session_id}')
        print(f"🎯 Starting zone insights generation for session {session_id}")
        
        # Generate zone insights for all subjects
        zone_results = generate_all_subject_checkpoints(session_id)
        
        if zone_results:
            logger.info(
                f'✅ Zone insights generated for session {session_id}: '
                f'{len(zone_results)} subjects processed'
            )
            print(f"✅ Zone insights complete: {len(zone_results)} subjects processed")
            return {
                'status': 'success',
                'session_id': session_id,
                'subjects_processed': len(zone_results),
                'subjects': list(zone_results.keys())
            }
        else:
            logger.warning(f'⚠️ No zone insights generated for session {session_id}')
            print(f"⚠️ No zone insights generated for session {session_id}")
            return {
                'status': 'warning',
                'session_id': session_id,
                'message': 'No zone insights generated'
            }
        
    except Exception as e:
        logger.exception(f'generate_zone_insights_task failed for session {session_id}')
        print(f"❌ Zone insights generation failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'session_id': session_id
        }

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2},
    retry_backoff=True,
    soft_time_limit=600,  # 10 minutes (LLM calls can be slow)
    time_limit=900,  # 15 minutes
    name='neet_app.tasks.generate_insights_task'
)
def generate_insights_task(self, student_id: str, request_data: dict = None, force_regenerate: bool = False):
    """
    Generate comprehensive student-level insights based on all completed tests.
    
    This task analyzes a student's overall performance across all tests to generate:
    - Strength topics (high accuracy, fast time)
    - Weak topics (low accuracy, needs improvement)
    - Improvement topics (moderate performance, actionable)
    - Unattempted topics
    - LLM-powered insights (strengths, weaknesses, study plan)
    
    **Idempotency**: This task respects the force_regenerate flag. If False and
    recent insights exist in the database, it skips generation. If True, it always
    regenerates (useful after completing a new test).
    
    **What it does**:
    1. Fetches all completed test sessions for the student
    2. Computes topic-level metrics (accuracy, time, attempts)
    3. Classifies topics into strength/weak/improvement categories
    4. Calls LLM (Gemini) to generate personalized insights
    5. Saves StudentInsight record to database
    6. Frontend fetches these insights for the dashboard
    
    Args:
        student_id: Student ID to analyze
        request_data: Optional dict with thresholds or configuration
        force_regenerate: If True, always regenerate even if cache exists
        
    Returns:
        Dict with generation statistics:
        {
            'status': 'success' | 'error' | 'skipped',
            'student_id': str,
            'insights_generated': bool,
            'topics_analyzed': int,
            'message': str (optional)
        }
    
    Raises:
        StudentProfile.DoesNotExist: If student not found
        Exception: Any LLM or database error
    """
    from .views import insights_views
    from .models import StudentProfile, StudentInsight
    
    try:
        # Verify student exists
        try:
            student = StudentProfile.objects.get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            logger.error(f'Student {student_id} not found')
            return {'status': 'error', 'error': 'Student not found', 'student_id': student_id}
        
        # Idempotency check: if not force_regenerate and recent insights exist, skip
        if not force_regenerate:
            recent_insight = StudentInsight.objects.filter(student_id=student_id).order_by('-created_at').first()
            if recent_insight:
                # Check if insight is recent (within last hour)
                from django.utils import timezone
                from datetime import timedelta
                age = timezone.now() - recent_insight.created_at
                if age < timedelta(hours=1):
                    logger.info(f'⏭️ Recent insights exist for student {student_id}, skipping')
                    print(f"⏭️ Recent insights exist for student {student_id}")
                    return {
                        'status': 'skipped',
                        'student_id': student_id,
                        'message': 'Recent insights already exist',
                        'insights_generated': False
                    }
        
        logger.info(f'🧠 Generating insights for student {student_id}')
        print(f"🧠 Starting insight generation for student {student_id}")
        
        # Get thresholds (default or custom from request_data)
        thresholds = insights_views.get_thresholds(request_data)
        
        # Calculate topic metrics across all tests
        all_metrics = insights_views.calculate_topic_metrics(student_id)
        
        # If no test data, save empty insights
        if not all_metrics or not all_metrics.get('topics'):
            logger.info(f'⚠️ No test data for student {student_id}, saving empty insights')
            empty_response = {
                'status': 'success',
                'data': {
                    'strength_topics': [],
                    'weak_topics': [],
                    'improvement_topics': [],
                    'unattempted_topics': [],
                    'llm_insights': {},
                    'thresholds_used': thresholds,
                    'summary': {
                        'total_topics_analyzed': 0,
                        'total_tests_taken': 0,
                        'message': 'No test data available'
                    }
                }
            }
            insights_views.save_insights_to_database(student_id, empty_response)
            return {
                'status': 'success',
                'student_id': student_id,
                'insights_generated': True,
                'topics_analyzed': 0,
                'message': 'No test data available'
            }
        
        # Classify topics
        classification = insights_views.classify_topics(
            all_metrics['topics'],
            all_metrics['overall_avg_time'],
            thresholds
        )
        
        # Get last test data
        last_test_data = insights_views.get_last_test_metrics(student_id, thresholds)
        
        # Get unattempted topics
        unattempted_topics = insights_views.get_unattempted_topics(all_metrics['topics'])
        
        # Generate LLM insights
        llm_insights = {}
        try:
            # Strengths
            if classification['strength_topics']:
                llm_insights['strengths'] = insights_views.generate_llm_insights(
                    'strengths',
                    classification['strength_topics']
                )
            
            # Weaknesses
            if classification['weak_topics']:
                llm_insights['weaknesses'] = insights_views.generate_llm_insights(
                    'weaknesses',
                    classification['weak_topics']
                )
            
            # Study plan (uses misconception-based service)
            from .services.study_plan_service import generate_study_plan_for_student
            study_plan_result = generate_study_plan_for_student(student_id)
            if study_plan_result and study_plan_result.get('status') == 'success':
                llm_insights['study_plan'] = study_plan_result
        except Exception as llm_error:
            logger.error(f'LLM insight generation failed for student {student_id}: {llm_error}')
            print(f"⚠️ LLM insights partial failure: {llm_error}")
        
        # Build summary
        summary = {
            'total_topics_analyzed': len(all_metrics['topics']),
            'total_tests_taken': all_metrics.get('total_tests_taken', 0),
            'strength_topics_count': len(classification['strength_topics']),
            'weak_topics_count': len(classification['weak_topics']),
            'improvement_topics_count': len(classification['improvement_topics']),
            'unattempted_topics_count': len(unattempted_topics)
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
                'summary': summary
            }
        }
        
        # Get latest session ID
        from .models import TestSession
        latest_session = TestSession.objects.filter(
            student_id=student_id,
            is_completed=True
        ).order_by('-end_time').first()
        latest_session_id = latest_session.id if latest_session else None
        
        # Save to database
        insights_views.save_insights_to_database(student_id, response_data, latest_session_id)
        
        logger.info(f'✅ Insights generated for student {student_id}: {summary["total_topics_analyzed"]} topics')
        print(f"✅ Insights complete for student {student_id}")
        
        return {
            'status': 'success',
            'student_id': student_id,
            'insights_generated': True,
            'topics_analyzed': summary['total_topics_analyzed']
        }
        
    except Exception as e:
        logger.exception(f'generate_insights_task failed for student {student_id}')
        print(f"❌ Insight generation failed for student {student_id}: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'student_id': student_id
        }


@shared_task(
    bind=True,
    name='neet_app.tasks.process_test_submission_task'
)
def process_test_submission_task(self, session_id: int):
    """
    Orchestrator task for complete test submission processing pipeline.
    
    This is the main entry point for test submission processing. It chains together
    all the necessary tasks to fully process a completed test submission:
    
    **Pipeline Sequence**:
    1. **compute_results_task**: Evaluate answers and calculate results
    2. **generate_zone_insights_task**: Generate subject-wise checkpoints
    3. **generate_insights_task**: Generate student-level overall insights
    
    **Why this orchestrator exists**:
    - Ensures tasks run in correct order (results → zone insights → student insights)
    - Prevents duplicate processing through idempotency checks in each task
    - Allows workers to handle entire pipeline asynchronously
    - Frontend can poll for completion status without blocking submit request
    
    **How it works**:
    - Uses Celery chain() to sequence tasks
    - Each task is idempotent and can be retried safely
    - If any task fails, subsequent tasks won't run (chain stops on error)
    - Workers pick up the chain and execute it completely
    
    **Frontend Integration**:
    1. User clicks Submit → API marks session complete and enqueues this task
    2. Frontend shows loading video
    3. Frontend polls GET /api/zone-insights/status/<test_id>/
    4. When zone insights ready, frontend redirects to dashboard
    5. Student insights load in background on dashboard
    
    Args:
        session_id: TestSession ID to process through the full pipeline
        
    Returns:
        Dict with pipeline execution status:
        {
            'status': 'started' | 'error',
            'session_id': int,
            'pipeline': str (description),
            'message': str (optional)
        }
    
    Raises:
        TestSession.DoesNotExist: If session not found
        Exception: Any task chain setup error
    """
    from .models import TestSession
    
    try:
        # Verify session exists
        try:
            session = TestSession.objects.get(id=session_id)
        except TestSession.DoesNotExist:
            logger.error(f'TestSession {session_id} not found for pipeline')
            return {'status': 'error', 'error': 'Session not found', 'session_id': session_id}
        
        student_id = session.student_id
        
        logger.info(f'🚀 Starting test submission pipeline for session {session_id}')
        print(f"🚀 Pipeline started for session {session_id} (student: {student_id})")
        
        # Build task chain: results → zone insights → student insights
        try:
            from celery import chain
            
            workflow = chain(
                compute_results_task.si(session_id),
                generate_zone_insights_task.si(session_id),
                generate_insights_task.si(student_id, {}, True)  # force_regenerate=True
            )
            
            # Execute the chain asynchronously
            result = workflow.apply_async()
            
            logger.info(f'✅ Pipeline chain enqueued for session {session_id} (chain ID: {result.id})')
            print(f"✅ Pipeline chain enqueued for session {session_id}")
            
            return {
                'status': 'started',
                'session_id': session_id,
                'student_id': student_id,
                'pipeline': 'compute_results → zone_insights → student_insights',
                'chain_id': str(result.id)
            }
            
        except Exception as chain_error:
            logger.error(f'Failed to create task chain for session {session_id}: {chain_error}')
            print(f"❌ Pipeline chain creation failed for session {session_id}: {chain_error}")
            
            # Fallback: enqueue tasks individually (not chained)
            logger.info(f'🔄 Falling back to individual task enqueues for session {session_id}')
            compute_results_task.apply_async(args=[session_id])
            generate_zone_insights_task.apply_async(args=[session_id])
            generate_insights_task.apply_async(args=[student_id, {}, True])
            
            return {
                'status': 'started',
                'session_id': session_id,
                'student_id': student_id,
                'pipeline': 'fallback: individual tasks',
                'message': 'Chain creation failed, tasks enqueued individually'
            }
        
    except Exception as e:
        logger.exception(f'process_test_submission_task failed for session {session_id}')
        print(f"❌ Pipeline orchestrator failed for session {session_id}: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'session_id': session_id
        }