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
    Compute and store zone insights metrics for all subjects in a completed test session.
    
    This task calculates and persists subject-wise performance metrics including:
    - Total possible marks and actual marks
    - Accuracy percentages
    - Time spent breakdown (correct/incorrect/skipped)
    - Subject-wise aggregated data
    
    **Idempotency**: This task checks if zone insights already exist in the database
    for this session. If TestSubjectZoneInsight records with populated subject_data
    are found, the task skips generation to avoid redundant processing.
    
    **What it does**:
    1. Checks if zone insights already exist (idempotency)
    2. Fetches all TestAnswer records for the session
    3. Groups answers by subject (Physics, Chemistry, Botany, etc.)
    4. For each subject:
       - Calculates marks, accuracy, time spent
       - Stores structured data in TestSubjectZoneInsight table
    5. Frontend polls these records to display analytics
    
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
        Exception: Any database error
    """
    from .models import TestSession, TestSubjectZoneInsight
    
    try:
        # Verify session exists
        try:
            session = TestSession.objects.get(id=session_id)
        except TestSession.DoesNotExist:
            logger.error(f'TestSession {session_id} not found')
            return {'status': 'error', 'error': 'Session not found', 'session_id': session_id}
        
        # Idempotency check: skip if zone insights with subject_data already exist
        existing_insights = TestSubjectZoneInsight.objects.filter(
            test_session_id=session_id
        ).exclude(subject_data__isnull=True)
        
        if existing_insights.exists():
            subjects_set = set()
            for row in existing_insights:
                sd = row.subject_data or []
                if isinstance(sd, list):
                    for entry in sd:
                        name = entry.get('subject_name') or entry.get('subject')
                        if name:
                            subjects_set.add(name)

            subjects = sorted(list(subjects_set))
            logger.info(f'⏭️ Zone insights already exist for session {session_id}, skipping')
            print(f"⏭️ Zone insights already exist for session {session_id}: {subjects}")
            return {
                'status': 'skipped',
                'session_id': session_id,
                'subjects_processed': len(subjects),
                'subjects': subjects,
                'message': 'Zone insights already generated'
            }
        
        from .services.zone_insights_service import compute_and_store_zone_insights
        
        logger.info(f'🎯 Computing zone insights for test session {session_id}')
        print(f"🎯 Starting zone insights computation for session {session_id}")
        
        # Compute and store zone insights for all subjects
        zone_results = compute_and_store_zone_insights(session_id)

        if not zone_results:
            logger.warning(f'⚠️ No zone insights generated for session {session_id}')
            print(f"⚠️ No zone insights generated for session {session_id}")
            return {
                'status': 'warning',
                'session_id': session_id,
                'message': 'No zone insights generated'
            }

        logger.info(
            f'✅ Zone insights computed for session {session_id}: '
            f'{len(zone_results)} subjects processed'
        )
        print(f"✅ Zone insights complete: {len(zone_results)} subjects processed")
        # NOTE: Do not run LLM-derived generation (focus_zone, repeated_mistake)
        # inline inside this task. LLM work is heavy and may be retried or
        # executed separately; the dedicated `generate_focus_zone_task` is the
        # canonical place to run `generate_focus_zone` and
        # `generate_repeated_mistakes` to avoid duplicate invocations and to
        # provide clearer retry/isolation semantics.

        return {
            'status': 'success',
            'session_id': session_id,
            'subjects_processed': len(zone_results),
            'subjects': list(zone_results.keys())
        }
        
    except Exception as e:
        logger.exception(f'generate_zone_insights_task failed for session {session_id}')
        print(f"❌ Zone insights computation failed: {e}")
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
    # NOTE: `generate_insights_task` removed. Student-level insights generation
    # has been deprecated and the task intentionally left unimplemented to
    # prevent accidental usage. If insights generation is required in future,
    # reintroduce the implementation from the previous commit or restore via
    # version control.
    logger.info('generate_insights_task is deprecated and has been removed')
    return {
        'status': 'deprecated',
        'message': 'Student-level insights generation has been removed'
    }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 1},
    retry_backoff=True,
    soft_time_limit=900,   # 15 minutes (LLM with retries can be slow)
    time_limit=1200,       # 20 minutes hard limit
    name='neet_app.tasks.generate_focus_zone_task'
)
def generate_focus_zone_task(self, session_id: int):
    """
    Generate focus_zone and repeated_mistake fields for a completed platform test session.

    Only runs for platform-type tests; custom tests are silently skipped.

    Steps:
    1. Confirm session exists and is a completed platform test.
    2. Confirm a TestSubjectZoneInsight row already exists (written by generate_zone_insights_task).
    3. Call generate_focus_zone() to populate focus_zone using the LLM.
    4. Call generate_repeated_mistakes() to populate repeated_mistake using the LLM.

    Args:
        session_id: TestSession ID

    Returns:
        Dict with status and which fields were updated.
    """
    from .models import TestSession, TestSubjectZoneInsight

    try:
        try:
            session = TestSession.objects.get(id=session_id)
        except TestSession.DoesNotExist:
            logger.error(f'generate_focus_zone_task: TestSession {session_id} not found')
            return {'status': 'error', 'error': 'Session not found', 'session_id': session_id}

        # Only generate for platform tests
        if session.test_type != 'platform':
            logger.info(
                f'generate_focus_zone_task: session {session_id} is "{session.test_type}" — skipping '
                f'(focus_zone / repeated_mistake are only for platform tests)'
            )
            return {
                'status': 'skipped',
                'session_id': session_id,
                'message': 'Not a platform test — focus_zone/repeated_mistake skipped',
            }

        # Ensure zone-insights row exists (written by generate_zone_insights_task before us)
        insight = TestSubjectZoneInsight.objects.filter(
            test_session_id=session_id,
            student_id=session.student_id,
        ).first()

        if not insight:
            logger.warning(
                f'generate_focus_zone_task: no TestSubjectZoneInsight found for session {session_id}. '
                f'Cannot generate focus_zone / repeated_mistake.'
            )
            return {
                'status': 'error',
                'error': 'Zone insights row missing; run generate_zone_insights_task first',
                'session_id': session_id,
            }

        from .services.zone_insights_service import generate_focus_zone, generate_repeated_mistakes

        student_id = session.student_id
        updated_fields = []

        # --- Focus Zone ---
        logger.info(f'🎯 [generate_focus_zone_task] Generating focus_zone for session {session_id}')
        try:
            focus_zone_data = generate_focus_zone(session_id)
            if focus_zone_data:
                updated_fields.append('focus_zone')
                logger.info(f'✅ focus_zone generated for session {session_id}')
            else:
                logger.warning(f'⚠️ generate_focus_zone returned empty for session {session_id}')
        except Exception as fz_err:
            logger.error(f'generate_focus_zone failed for session {session_id}: {fz_err}')

        # --- Repeated Mistakes ---
        logger.info(f'🔁 [generate_focus_zone_task] Generating repeated_mistake for student {student_id} / session {session_id}')
        try:
            repeated_data = generate_repeated_mistakes(student_id, session_id)
            if repeated_data:
                updated_fields.append('repeated_mistake')
                logger.info(f'✅ repeated_mistake generated for session {session_id}')
            else:
                logger.warning(f'⚠️ generate_repeated_mistakes returned empty for session {session_id}')
        except Exception as rm_err:
            logger.error(f'generate_repeated_mistakes failed for session {session_id}: {rm_err}')

        return {
            'status': 'success' if updated_fields else 'warning',
            'session_id': session_id,
            'updated_fields': updated_fields,
            'message': f'Updated: {", ".join(updated_fields)}' if updated_fields else 'No fields updated',
        }

    except Exception as e:
        logger.exception(f'generate_focus_zone_task failed for session {session_id}')
        return {'status': 'error', 'error': str(e), 'session_id': session_id}


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
    2. **generate_zone_insights_task**: Compute marks/accuracy/subject_data and g_phrase
    3. **generate_focus_zone_task**: Generate focus_zone and repeated_mistake via LLM (platform tests only)
    
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
        
        # Build task chain: results → zone insights → focus zone + repeated mistakes (platform only)
        try:
            from celery import chain
            
            workflow = chain(
                compute_results_task.si(session_id),
                generate_zone_insights_task.si(session_id),
                generate_focus_zone_task.si(session_id),
            )
            
            # Execute the chain asynchronously
            result = workflow.apply_async()
            
            logger.info(f'✅ Pipeline chain enqueued for session {session_id} (chain ID: {result.id})')
            print(f"✅ Pipeline chain enqueued for session {session_id}")
            
            return {
                'status': 'started',
                'session_id': session_id,
                'student_id': student_id,
                'pipeline': 'compute_results → zone_insights → focus_zone/repeated_mistakes',
                'chain_id': str(result.id)
            }
            
        except Exception as chain_error:
            logger.error(f'Failed to create task chain for session {session_id}: {chain_error}')
            print(f"❌ Pipeline chain creation failed for session {session_id}: {chain_error}")
            
            # Fallback: enqueue tasks individually (not chained)
            logger.info(f'🔄 Falling back to individual task enqueues for session {session_id}')
            compute_results_task.apply_async(args=[session_id])
            generate_zone_insights_task.apply_async(args=[session_id])
            generate_focus_zone_task.apply_async(args=[session_id])
            
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