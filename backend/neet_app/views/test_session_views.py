import logging
import random
import sentry_sdk
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from ..errors import AppError, ValidationError as AppValidationError, NotFoundError
from ..error_codes import ErrorCodes
from rest_framework.permissions import IsAuthenticated

from ..models import Question, TestSession, TestAnswer
from ..serializers import (
    QuestionForTestSerializer, TestSessionCreateSerializer, 
    TestSessionSerializer
)
from ..notifications import dispatch_test_result_email

logger = logging.getLogger(__name__)


class TestSessionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing test sessions.
    Corresponds to /api/test-sessions in Node.js.
    Only returns sessions for the authenticated user.
    """
    serializer_class = TestSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter test sessions by authenticated user"""
        logger.info(f"get_queryset - User: {self.request.user}")
        logger.info(f"User type: {type(self.request.user)}")
        logger.info(f"User authenticated: {self.request.user.is_authenticated}")
        
        if not hasattr(self.request.user, 'student_id'):
            logger.warning(f"User has no student_id attribute: {self.request.user}")
            return TestSession.objects.none()
            
        logger.info(f"Filtering by student_id: {self.request.user.student_id}")
        queryset = TestSession.objects.filter(
            student_id=self.request.user.student_id
        ).order_by('-start_time')
        
        logger.info(f"Queryset count: {queryset.count()}")
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return TestSessionCreateSerializer
        return TestSessionSerializer

    def create(self, request, *args, **kwargs):
        """
        Creates a new test session with student authentication.
        Enhanced version with time-based or count-based question selection.
        Backward compatible with existing question_count requests.
        """
        try:
            # Log test session creation with Sentry
            logger.info(f"Creating test session for user: {request.user.student_id}")
            sentry_sdk.add_breadcrumb(
                message="Test session creation started",
                category="test_session",
                level="info",
                data={
                    "student_id": request.user.student_id,
                    "request_data": request.data
                }
            )
            
            # Pass request context to serializer for authenticated user access
            serializer = self.get_serializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            
            # Get student_id before creating session to check question availability
            student_id = request.user.student_id
            selected_topics = serializer.validated_data.get('selected_topics', [])
            requested_question_count = serializer.validated_data.get('question_count')
            adaptive_selection = serializer.validated_data.get('adaptive_selection', False)
            
            # Get recent question IDs to exclude
            recent_question_ids = TestSession.get_recent_question_ids_for_student(student_id)
            
            # Check if this is a random test
            test_type = request.data.get('test_type', 'search')
            
            if test_type == 'random':
                # For random tests, skip topic-based selection and directly select from entire database
                from .utils import generate_random_questions_from_database
                
                available_questions = generate_random_questions_from_database(
                    requested_question_count,
                    exclude_question_ids=recent_question_ids
                )
                available_count = available_questions.count()
                
                # For random tests, we should always have enough questions since we're using the entire database
                if available_count < requested_question_count:
                    logger.warning(f"Random test: Only {available_count} questions available in entire database, but {requested_question_count} requested")
                    # For random tests, adjust the count to what's available rather than failing
                    serializer.validated_data['question_count'] = available_count
                    requested_question_count = available_count
            else:
                # For topic-based tests (custom/search), use the existing logic
                if adaptive_selection:
                    # For adaptive selection, we're more lenient - just check if any questions exist
                    from .utils import adaptive_generate_questions_for_topics
                    available_questions = generate_questions_for_topics(
                        selected_topics, 
                        None,  # Don't limit to get total available count
                        exclude_question_ids=recent_question_ids
                    )
                    available_count = available_questions.count()
                    
                    # For adaptive selection, we only fail if no questions are available at all
                    if available_count == 0:
                        raise AppValidationError(
                            message='No questions available for selected topics.',
                            details={'available_questions': 0, 'requested_questions': requested_question_count}
                        )
                    
                    # If we have fewer questions than requested, log it but continue (adaptive selection will handle it)
                    if available_count < requested_question_count:
                        logger.info(f"Adaptive selection: Only {available_count} questions available for {requested_question_count} requested, but continuing with adaptive logic")
                else:
                    # For traditional selection, enforce strict availability
                    from .utils import generate_questions_for_topics
                    available_questions = generate_questions_for_topics(
                        selected_topics, 
                        None,  # Don't limit to get total available count
                        exclude_question_ids=recent_question_ids
                    )
                    available_count = available_questions.count()
                    
                    # Validate if we have enough questions for topic-based tests
                    if available_count < requested_question_count:
                        raise AppValidationError(
                            message=f'Only {available_count} questions available for selected topics, but {requested_question_count} requested.',
                            details={'available_questions': available_count, 'requested_questions': requested_question_count}
                        )
            
            # Create the session (serializer generates questions internally with exclusion)
            session = serializer.save()
            
            # Get the final questions with proper exclusion and count limit
            if test_type == 'random':
                # For random tests, choose between adaptive and traditional selection
                if adaptive_selection:
                    from .utils import adaptive_generate_random_questions_from_database
                    selected_questions = adaptive_generate_random_questions_from_database(
                        session.question_count,
                        student_id,
                        exclude_question_ids=recent_question_ids
                    )
                else:
                    from .utils import generate_random_questions_from_database
                    selected_questions = generate_random_questions_from_database(
                        session.question_count,
                        exclude_question_ids=recent_question_ids
                    )
            else:
                # For topic-based tests, choose between adaptive and traditional selection
                if adaptive_selection:
                    from .utils import adaptive_generate_questions_for_topics
                    selected_questions = adaptive_generate_questions_for_topics(
                        session.selected_topics, 
                        session.question_count,
                        student_id,
                        exclude_question_ids=recent_question_ids
                    )
                else:
                    selected_questions = generate_questions_for_topics(
                        session.selected_topics, 
                        session.question_count,
                        exclude_question_ids=recent_question_ids
                    )
            
            # Update session with actual question count
            # If this was a random test, store the topics of the randomly-selected questions
            if test_type == 'random':
                try:
                    # selected_questions may be a QuerySet or list of Question objects
                    topic_ids = list({getattr(q, 'topic_id', getattr(q, 'topic').id) for q in selected_questions})
                    session.selected_topics = topic_ids
                    session.save(update_fields=['selected_topics'])
                except Exception:
                    logger.exception('Failed to populate session.selected_topics for random test')

            session.total_questions = len(selected_questions)
            session.save(update_fields=['total_questions'])

            # Create TestAnswer records for all assigned questions (initially unanswered)
            test_answers = []
            for question in selected_questions:
                test_answers.append(TestAnswer(
                    session=session,
                    question=question,
                    selected_answer=None,
                    is_correct=False,
                    marked_for_review=False,
                    time_taken=0
                ))
            TestAnswer.objects.bulk_create(test_answers)

            session_data = TestSessionSerializer(session).data
            questions_data = QuestionForTestSerializer(selected_questions, many=True).data

            return Response({
                'id': session.id,  # Add id field that tests expect
                'session': session_data,
                'questions': questions_data,
                'message': f'Test session created for student {session.student_id}'
            }, status=status.HTTP_201_CREATED)
            
        except (AppValidationError, DRFValidationError) as e:
            # Let validation errors pass through to be handled by the exception handler
            raise e
        except Exception as e:
            logger.error(f"Error creating test session: {str(e)}", exc_info=True)
            
            # Capture exception in Sentry with additional context
            sentry_sdk.capture_exception(e, extra={
                "student_id": getattr(request.user, 'student_id', 'unknown'),
                "request_data": request.data,
                "action": "test_session_create"
            })
            
            raise AppError(code=ErrorCodes.SERVER_ERROR, message='Failed to create test session', details={'exception': str(e)})

    def retrieve(self, request, pk=None):
        """
        Retrieves a test session and its questions.
        Replicates GET /api/test-sessions/:id logic.
        Only allows access to user's own sessions.
        """
        # Debug logging
        logger.info(f"Retrieve request - User: {request.user}, Session ID: {pk}")
        logger.info(f"User authenticated: {request.user.is_authenticated}")
        logger.info(f"User student_id: {getattr(request.user, 'student_id', 'No student_id')}")
        
        # Ensure only authenticated user's sessions are accessible
        try:
            session = get_object_or_404(
                self.get_queryset(), 
                pk=pk
            )
            logger.info(f"Session found: {session.id}, belongs to: {session.student_id}")
        except Http404:
            logger.error(f"Session not found: {pk}")
            raise NotFoundError(message='Test session not found')
        except Exception as e:
            logger.error(f"Session retrieval failed: {e}")
            raise AppError(code=ErrorCodes.SERVER_ERROR, message='Failed to retrieve test session', details={'exception': str(e)})

        try:
            topic_ids = [int(topic_id) for topic_id in session.selected_topics]
        except ValueError:
            raise AppError(code=ErrorCodes.SERVER_ERROR, message='Invalid topic IDs stored in session.')

        # Get questions from TestAnswer table (the exact questions assigned to this session)
        test_answers = TestAnswer.objects.filter(session=session).select_related('question')
        selected_questions = [answer.question for answer in test_answers]

        # If no TestAnswer rows exist (legacy or previously-miscreated session), create them now
        if not selected_questions:
            try:
                # Try to import question generation utility
                from .utils import generate_questions_for_topics

                # Exclude recent questions for this student to preserve exclusion logic
                recent_question_ids = TestSession.get_recent_question_ids_for_student(session.student_id)

                # Generate questions for the session topics
                generated_questions = generate_questions_for_topics(
                    session.selected_topics,
                    session.question_count,
                    exclude_question_ids=recent_question_ids
                )

                # If none generated, try without exclusion as a fallback
                if generated_questions.count() == 0:
                    generated_questions = generate_questions_for_topics(
                        session.selected_topics,
                        session.question_count,
                        exclude_question_ids=None
                    )

                # Create TestAnswer records for generated questions
                test_answer_objs = []
                for q in generated_questions:
                    test_answer_objs.append(TestAnswer(
                        session=session,
                        question=q,
                        selected_answer=None,
                        is_correct=False,
                        marked_for_review=False,
                        time_taken=0
                    ))
                TestAnswer.objects.bulk_create(test_answer_objs)

                # Refresh selected_questions from generated set
                selected_questions = list(generated_questions)
                # Update session.total_questions if mismatch
                if session.total_questions != len(selected_questions):
                    session.total_questions = len(selected_questions)
                    session.save(update_fields=['total_questions'])

            except Exception as e:
                logger.exception('Failed to generate questions for session %s: %s', session.id, str(e))
                raise AppError(code=ErrorCodes.SERVER_ERROR, message='Failed to generate questions for session', details={'exception': str(e)})

        session_data = TestSessionSerializer(session).data
        questions_data = QuestionForTestSerializer(selected_questions, many=True).data

        return Response({
            'session': session_data,
            'questions': questions_data
        })

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Submits a test session, marks it as complete, calculates results,
        and updates individual answer correctness.
        Only allows access to user's own sessions.
        """
        # Ensure only authenticated user's sessions are accessible
        session = get_object_or_404(
            self.get_queryset().select_related(), 
            pk=pk
        )

        session.is_completed = True
        session.end_time = timezone.now()
        session.save(update_fields=['is_completed', 'end_time'])

        answers = TestAnswer.objects.filter(session=session).select_related('question').prefetch_related('question__topic')

        total_questions_in_session = session.total_questions
        correct_answers_count = 0
        incorrect_answers_count = 0
        unanswered_questions_count = 0

        detailed_answers = []
        subject_performance = {}

        try:
            session_topic_ids = [int(tid) for tid in session.selected_topics]
        except ValueError:
            raise AppError(code=ErrorCodes.SERVER_ERROR, message='Invalid topic IDs stored in session.')

        # Get questions and ensure they are cleaned
        questions = Question.objects.filter(topic_id__in=session_topic_ids).select_related('topic')
        question_map = {}
        for q in questions:
            # Apply cleaning if LaTeX patterns or simple chemical notations are found
            needs_cleaning = any(pattern in q.question for pattern in ['\\', '$', '^{', '_{', '\\frac', '^ -', '^ +', '^-', '^+', 'x 10^'])
            if not needs_cleaning:
                # Also check options for patterns
                all_options = q.option_a + q.option_b + q.option_c + q.option_d
                needs_cleaning = any(pattern in all_options for pattern in ['\\', '$', '^{', '_{', '\\frac', '^ -', '^ +', '^-', '^+', 'x 10^'])
            if not needs_cleaning and q.explanation:
                # Also check explanation for patterns
                needs_cleaning = any(pattern in q.explanation for pattern in ['\\', '$', '^{', '_{', '\\frac', '^ -', '^ +', '^-', '^+', 'x 10^'])
            
            if needs_cleaning:
                from .utils import clean_mathematical_text
                # Clean fields but be defensive: saving cleaned text may conflict with
                # an existing question due to a unique constraint on
                # (question, topic_id, option_a, option_b, option_c, option_d).
                new_question = clean_mathematical_text(q.question)
                new_option_a = clean_mathematical_text(q.option_a)
                new_option_b = clean_mathematical_text(q.option_b)
                new_option_c = clean_mathematical_text(q.option_c)
                new_option_d = clean_mathematical_text(q.option_d)
                new_explanation = clean_mathematical_text(q.explanation) if q.explanation else None

                # Check for an existing question with identical cleaned fields (exclude self)
                try:
                    duplicate_exists = Question.objects.filter(
                        question=new_question,
                        topic_id=q.topic_id,
                        option_a=new_option_a,
                        option_b=new_option_b,
                        option_c=new_option_c,
                        option_d=new_option_d,
                    ).exclude(pk=q.pk).exists()
                except Exception:
                    # On unexpected DB error, don't block submit; fallback to attempting save
                    duplicate_exists = False

                if duplicate_exists:
                    logger.warning(
                        'Skipping save for question %s because cleaned text would duplicate an existing question',
                        q.id
                    )
                else:
                    # Apply cleaned values and attempt save; catch IntegrityError as defensive measure
                    q.question = new_question
                    q.option_a = new_option_a
                    q.option_b = new_option_b
                    q.option_c = new_option_c
                    q.option_d = new_option_d
                    if new_explanation is not None:
                        q.explanation = new_explanation
                    try:
                        q.save(update_fields=['question', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation'])
                    except Exception as e:
                        # Catch IntegrityError or other DB errors and log; do not abort submission
                        logger.exception('Failed to save cleaned question %s: %s', getattr(q, 'id', 'unknown'), str(e))
            question_map[q.id] = q

        # Process all TestAnswer objects (now includes all assigned questions)
        for answer in answers:
            question = answer.question
            is_correct = False

            # Determine question type (NVT vs MCQ/Blank)
            q_type = (getattr(question, 'question_type', '') or '').upper()

            if q_type == 'NVT':
                # Prefer text_answer for NVT questions
                student_text = answer.text_answer if answer.text_answer is not None and str(answer.text_answer).strip() != '' else None

                if student_text is None:
                    # For NVT, missing text_answer is considered unanswered (do not fallback to selected_answer)
                    unanswered_questions_count += 1
                    is_correct = False
                else:
                    # Evaluate NVT answer: try numeric comparison first, then string
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
                        # Fall back to string comparison
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
                # Default/MCQ handling: compare selected_answer to correct_answer
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

            # Persist correctness (maintain existing field semantics)
            answer.is_correct = is_correct
            answer.save(update_fields=['is_correct'])

            detailed_answers.append({
                'questionId': question.id,
                'question': question.question,
                'selectedAnswer': answer.selected_answer,
                'correctAnswer': question.correct_answer,
                'isCorrect': is_correct,
                'explanation': question.explanation,
                # Include explanation image (nullable) for results display
                'explanation_image': getattr(question, 'explanation_image', None),
                'optionA': question.option_a,
                'optionB': question.option_b,
                'optionC': question.option_c,
                'optionD': question.option_d,
                # Include option images (nullable) so results page can show them
                'option_a_image': getattr(question, 'option_a_image', None),
                'option_b_image': getattr(question, 'option_b_image', None),
                'option_c_image': getattr(question, 'option_c_image', None),
                'option_d_image': getattr(question, 'option_d_image', None),
                'markedForReview': answer.marked_for_review,
                'timeTaken': answer.time_taken
            })

            subject_name = question.topic.subject
            if subject_name not in subject_performance:
                subject_performance[subject_name] = {'correct': 0, 'total': 0}
            subject_performance[subject_name]['total'] += 1
            if is_correct:
                subject_performance[subject_name]['correct'] += 1

        answered_questions_count = len(answers)

        score_percentage = (correct_answers_count / total_questions_in_session) * 100 if total_questions_in_session > 0 else 0

        # Compute authoritative time taken.
        # Prefer client-provided timestamps (so UI can mark exact active test window) to avoid
        # including server-side processing time that happens after submit button click.
        time_taken_seconds = None
        client_start = request.data.get('clientStartTime') or request.data.get('client_start_time')
        client_end = request.data.get('clientEndTime') or request.data.get('client_end_time')
        if client_start and client_end:
            try:
                from django.utils.dateparse import parse_datetime
                cs = parse_datetime(client_start)
                ce = parse_datetime(client_end)
                if cs and ce:
                    # If parsed datetimes are naive/aware, subtracting works if both are same type.
                    # Only accept if end > start
                    if ce > cs:
                        time_taken_seconds = int((ce - cs).total_seconds())
            except Exception:
                # If parsing fails, fall back to server-side computation below
                time_taken_seconds = None

        # Fallback: use server-side start/end if client timestamps not provided or invalid
        if time_taken_seconds is None:
            if session.start_time and session.end_time:
                try:
                    time_taken_seconds = int((session.end_time - session.start_time).total_seconds())
                except Exception:
                    time_taken_seconds = 0
            else:
                time_taken_seconds = 0

        # Persist summarized session metrics so the TestSession row reflects the final results
        try:
            session.correct_answers = correct_answers_count
            session.incorrect_answers = incorrect_answers_count
            session.unanswered = unanswered_questions_count
            session.total_time_taken = time_taken_seconds
            # Optionally persist score percentage or leave calculation to calculate_score_percentage()
            session.save(update_fields=['correct_answers', 'incorrect_answers', 'unanswered', 'total_time_taken'])
        except Exception:
            # Do not fail result response if DB write has issues; log exception for visibility
            logger.exception('Failed to persist session summary for session %s', session.id)

        formatted_subject_performance = []
        for subject_name, data in subject_performance.items():
            formatted_subject_performance.append({
                'subject': subject_name,
                'correct': data['correct'],
                'total': data['total'],
                'accuracy': (data['correct'] / data['total']) * 100 if data['total'] > 0 else 0
            })

        results = {
            'session_id': session.id,
            'total_questions': total_questions_in_session,
            'correct_answers': correct_answers_count,
            'incorrect_answers': incorrect_answers_count,
            'unanswered_questions': unanswered_questions_count,
            'score_percentage': round(score_percentage, 2),
            'time_taken': time_taken_seconds,
            'subject_performance': formatted_subject_performance,
            'detailed_answers': detailed_answers
        }

        # Generate zone insights synchronously before returning
        # Student insights will be generated asynchronously via signals
        try:
            from ..services.zone_insights_service import generate_all_subject_zones
            print(f"🎯 Starting synchronous zone insights generation for test {session.id}")
            zone_results = generate_all_subject_zones(session.id)
            if zone_results:
                print(f"✅ Zone insights generated for {len(zone_results)} subjects")
            else:
                print(f"⚠️ No zone insights generated for test {session.id}")
        except Exception as e:
            # Don't fail submission if zone insights fail
            logger.exception(f"Failed to generate zone insights for session {session.id}: {e}")
            print(f"❌ Zone insights generation failed: {e}")

        # Send test result email asynchronously (best-effort)
        try:
            student_profile = None
            # Try to get student profile from session.user relation if exists
            from ..models import StudentProfile
            try:
                student_profile = StudentProfile.objects.get(student_id=session.student_id)
            except Exception:
                student_profile = None

            if student_profile:
                dispatch_test_result_email(student_profile, results)
        except Exception:
            # Do not fail the request if email send fails; log for visibility
            logger.exception('Failed to dispatch test result email for session %s', session.id)

        return Response(results)

    @action(detail=True, methods=['post'])
    def quit(self, request, pk=None):
        """
        Quits a test session and marks it as incomplete.
        Only allows access to user's own sessions.
        """
        # Ensure only authenticated user's sessions are accessible
        session = get_object_or_404(
            self.get_queryset().select_related(), 
            pk=pk
        )

        # Check if the test is already completed
        if session.is_completed:
            raise AppValidationError(message='Cannot quit a completed test session.')

        # Mark the session as incomplete and set end time
        session.is_completed = False  # Explicitly mark as incomplete
        session.end_time = timezone.now()
        session.save(update_fields=['is_completed', 'end_time'])

        logger.info(f"Test session {session.id} marked as incomplete (quit by user)")

        return Response({
            "message": "Test session has been marked as incomplete.",
            "session_id": session.id,
            "status": "incomplete"
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """
        Retrieves the results for a completed test session.
        Only allows access to user's own sessions.
        """
        # Ensure only authenticated user's sessions are accessible
        session = get_object_or_404(
            self.get_queryset().select_related(), 
            pk=pk
        )

        answers = TestAnswer.objects.filter(session=session).select_related('question').prefetch_related('question__topic')

        total_questions_in_session = session.total_questions
        correct_answers_count = 0
        incorrect_answers_count = 0
        unanswered_questions_count = 0

        detailed_answers = []
        subject_performance = {}

        try:
            session_topic_ids = [int(tid) for tid in session.selected_topics]
        except ValueError:
            return Response(
                {"error": "Invalid topic IDs stored in session."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Process all TestAnswer objects (now includes all assigned questions)
        for answer in answers:
            question = answer.question
            is_correct = answer.is_correct
            if answer.selected_answer is None or str(answer.selected_answer).strip() == '':
                unanswered_questions_count += 1
            elif is_correct:
                correct_answers_count += 1
            else:
                incorrect_answers_count += 1

            detailed_answers.append({
                'question_id': question.id,
                'question': question.question,
                'selected_answer': answer.selected_answer,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'explanation': question.explanation,
                # Include explanation image (nullable)
                'explanation_image': getattr(question, 'explanation_image', None),
                'option_a': question.option_a,
                'option_b': question.option_b,
                'option_c': question.option_c,
                'option_d': question.option_d,
                # Include option images (nullable)
                'option_a_image': getattr(question, 'option_a_image', None),
                'option_b_image': getattr(question, 'option_b_image', None),
                'option_c_image': getattr(question, 'option_c_image', None),
                'option_d_image': getattr(question, 'option_d_image', None),
                'marked_for_review': answer.marked_for_review,
                'time_taken': answer.time_taken
            })

            subject_name = question.topic.subject
            if subject_name not in subject_performance:
                subject_performance[subject_name] = {'correct': 0, 'total': 0}
            subject_performance[subject_name]['total'] += 1
            if is_correct:
                subject_performance[subject_name]['correct'] += 1

        answered_questions_count = len(answers)

        score_percentage = (correct_answers_count / total_questions_in_session) * 100 if total_questions_in_session > 0 else 0

        time_taken_seconds = 0
        if session.start_time and session.end_time:
            time_taken_seconds = int((session.end_time - session.start_time).total_seconds())

        formatted_subject_performance = []
        for subject_name, data in subject_performance.items():
            formatted_subject_performance.append({
                'subject': subject_name,
                'correct': data['correct'],
                'total': data['total'],
                'accuracy': (data['correct'] / data['total']) * 100 if data['total'] > 0 else 0
            })

        results = {
            'session_id': session.id,
            'total_questions': total_questions_in_session,
            'correct_answers': correct_answers_count,
            'incorrect_answers': incorrect_answers_count,
            'unanswered_questions': unanswered_questions_count,
            'score_percentage': round(score_percentage, 2),
            'time_taken': time_taken_seconds,
            'subject_performance': formatted_subject_performance,
            'detailed_answers': detailed_answers
        }

        return Response(results)
