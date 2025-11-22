# your_app_name/serializers.py
from rest_framework import serializers
from .models import Topic, Question, TestSession, TestAnswer, StudentProfile, ReviewComment, ChatSession, ChatMessage, ChatMemory, PlatformTest, RazorpayOrder
from django.db.models import F
from django.utils import timezone


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = '__all__'


class PlatformTestSerializer(serializers.ModelSerializer):
    is_scheduled = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()
    is_available_now = serializers.SerializerMethodField()
    availability_status = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()  # Alias for time_limit
    
    class Meta:
        model = PlatformTest
        fields = [
            'id', 'test_name', 'test_code', 'test_year', 'test_type',
            'description', 'instructions', 'time_limit', 'duration', 'total_questions',
            'difficulty_distribution',
            'scheduled_date_time', 'is_scheduled', 'is_open', 'is_available_now',
            'availability_status', 'is_active', 'expires_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_is_scheduled(self, obj):
        return obj.is_scheduled_test()
    
    def get_is_open(self, obj):
        return obj.is_open_test()
    
    def get_is_available_now(self, obj):
        return obj.is_available_now()
    
    def get_availability_status(self, obj):
        return obj.get_availability_status()
    
    def get_duration(self, obj):
        return obj.time_limit


class PlatformTestCreateSerializer(serializers.Serializer):
    """Serializer for admin/institution creation of PlatformTest entries.

    Note: For institution-created tests via Excel upload, the upload flow will
    generate questions and a unique test_code. This serializer supports creating
    standalone platform tests (optionally scheduled) via API.
    """
    test_name = serializers.CharField(max_length=255)
    exam_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    time_limit = serializers.IntegerField(required=False, default=180)
    instructions = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    scheduled_date_time = serializers.DateTimeField(required=False, allow_null=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_test_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Test name cannot be empty")
        return value.strip()

    def create(self, validated_data):
        import uuid
        from datetime import datetime

        test_name = validated_data.get('test_name')
        time_limit = validated_data.get('time_limit', 180)
        instructions = validated_data.get('instructions')
        scheduled_date_time = validated_data.get('scheduled_date_time')
        expires_at = validated_data.get('expires_at') if 'expires_at' in validated_data else None
        exam_type = validated_data.get('exam_type', None)

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_suffix = str(uuid.uuid4())[:8]
        test_code = f"PLAT_{timestamp}_{unique_suffix}"

        platform_test = PlatformTest.objects.create(
            test_name=test_name,
            test_code=test_code,
            test_type='Platform',
            instructions=instructions,
            time_limit=time_limit,
            total_questions=0,
            selected_topics=[],
            is_active=True,
            exam_type=exam_type
        )

        if scheduled_date_time:
            platform_test.scheduled_date_time = scheduled_date_time
            platform_test.save(update_fields=['scheduled_date_time'])

        # set expires_at if provided
        if expires_at:
            platform_test.expires_at = expires_at
            platform_test.save(update_fields=['expires_at'])

        return platform_test


# --- SECURITY CRITICAL ---
# This serializer is used when creating a test session to hide correct answers and explanations.
class QuestionForTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        # Only include safe fields for test-taking (exclude sensitive fields)
        fields = [
            'id', 'topic', 'question', 'question_type', 'option_a', 'option_b', 'option_c', 'option_d',
            # Optional base64 image fields (nullable) - additive and safe to include
            'question_image', 'option_a_image', 'option_b_image', 'option_c_image', 'option_d_image'
        ]


# This serializer is for returning full question details (e.g., in results/analytics)
class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class TestSessionSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    overall_score = serializers.SerializerMethodField()
    platform_test_details = serializers.SerializerMethodField()
    test_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TestSession
        fields = [
            'id', 'student_id', 'student_name', 'test_type', 'platform_test', 'platform_test_details',
            'test_name', 'selected_topics', 'physics_topics', 'chemistry_topics', 'botany_topics', 'zoology_topics', 'biology_topics',
            'time_limit', 'question_count', 'start_time', 'end_time', 'is_completed',
            'total_questions', 'correct_answers', 'incorrect_answers', 'unanswered',
            'total_time_taken', 'physics_score', 'chemistry_score', 'botany_score',
            'zoology_score', 'biology_score', 'math_score', 'math_topics', 'overall_score'
        ]
        read_only_fields = [
            'physics_topics', 'chemistry_topics', 'botany_topics', 'zoology_topics', 'biology_topics', 'math_topics',
            'correct_answers', 'incorrect_answers', 'unanswered', 'total_time_taken',
            'physics_score', 'chemistry_score', 'botany_score', 'zoology_score', 'biology_score', 'math_score'
        ]
    
    def get_student_name(self, obj):
        student_profile = obj.get_student_profile()
        return student_profile.full_name if student_profile else "Unknown Student"
    
    def get_overall_score(self, obj):
        return obj.calculate_score_percentage()
    
    def get_platform_test_details(self, obj):
        if obj.test_type == 'platform' and obj.platform_test:
            return {
                'id': obj.platform_test.id,
                'test_name': obj.platform_test.test_name,
                'test_code': obj.platform_test.test_code,
                'test_type': obj.platform_test.test_type,
                'scheduled_date_time': obj.platform_test.scheduled_date_time.isoformat() if obj.platform_test.scheduled_date_time else None,
                'is_scheduled': obj.platform_test.is_scheduled_test(),
                'availability_status': obj.platform_test.get_availability_status()
            }
        return None
    
    def get_test_name(self, obj):
        return obj.get_test_name()


class TestSessionCreateSerializer(serializers.Serializer):
    # Test configuration (student_id will be automatically set from authenticated user)
    selected_topics = serializers.ListField(
        child=serializers.CharField(max_length=255)
    )
    time_limit = serializers.IntegerField(required=False, default=None, allow_null=True)
    question_count = serializers.IntegerField(required=False, default=None, allow_null=True)
    
    # New fields for time-based question selection
    selection_mode = serializers.ChoiceField(
        choices=[('question_count', 'Question Count'), ('time_limit', 'Time Limit')],
        required=False,  # Optional for backward compatibility
        default='question_count',  # Default to existing behavior
        help_text="How to determine test length"
    )
    
    # New field for test type
    test_type = serializers.ChoiceField(
        choices=[('random', 'Random Test'), ('custom', 'Custom Selection'), ('search', 'Search Topics')],
        required=False,
        default='search',  # Default to search mode for backward compatibility
        help_text="Type of test selection method"
    )
    
    # New field for adaptive question selection
    adaptive_selection = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Use adaptive question selection logic (60% new, 30% wrong/unanswered, 10% correct)"
    )

    def validate_selected_topics(self, value):
        # For random tests, empty topics are allowed (we'll generate them automatically)
        if not value:  # Empty list for random tests
            return value
            
        # For non-random tests, ensure all topic IDs exist
        try:
            topic_ids = [int(t_id) for t_id in value]
            existing_topics = Topic.objects.filter(id__in=topic_ids)
            if len(existing_topics) != len(topic_ids):
                missing_ids = set(topic_ids) - set(existing_topics.values_list('id', flat=True))
                raise serializers.ValidationError(f"Topics with IDs {missing_ids} do not exist.")
        except (ValueError, TypeError) as e:
            raise serializers.ValidationError(f"Invalid topic ID format: {str(e)}")
        return value

    def validate(self, data):
        """Enhanced validation to handle both question count and time-based selection"""
        selection_mode = data.get('selection_mode', 'question_count')
        test_type = data.get('test_type', 'search')
        
        # For random tests, we don't need to validate topics as they will be generated
        if test_type == 'random':
            question_count = data.get('question_count')
            time_limit = data.get('time_limit')
            if not question_count or not time_limit:
                raise serializers.ValidationError("Both question count and time limit are required for random tests")
            # For random tests, we'll generate topics on the backend
            return data
        
        # For custom and search modes, validate normally
        if selection_mode == 'time_limit':
            time_limit = data.get('time_limit')
            if not time_limit:
                raise serializers.ValidationError("Time limit is required when using time-based selection")
            # Calculate question count: 1 question per minute
            data['question_count'] = time_limit
        elif selection_mode == 'question_count':
            # Existing behavior - ensure question_count is provided
            question_count = data.get('question_count')
            if not question_count:
                raise serializers.ValidationError("Question count is required when using count-based selection")
            # Don't override time_limit if it's provided by the frontend
            # Only calculate time limit if it's not provided
            if not data.get('time_limit'):
                data['time_limit'] = question_count
        
        return data

    def create(self, validated_data):
        """Create test session with automatic topic classification"""
        # Get student_id from the authenticated user (passed via context)
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'student_id'):
            raise serializers.ValidationError("Authentication required to create test session")
        
        student_id = request.user.student_id
        
        # Handle different test types
        test_type = validated_data.get('test_type', 'search')
        selected_topics = validated_data.get('selected_topics', [])
        # Ensure selected_topics are stored as a list of ints (normalize incoming strings)
        try:
            selected_topics = [int(t) for t in selected_topics] if selected_topics is not None else []
        except (ValueError, TypeError):
            # If conversion fails, fall back to original list to avoid raising unexpected errors here
            pass
        time_limit = validated_data.get('time_limit')
        question_count = validated_data.get('question_count')
        
        # For random tests, we'll let the view handle question selection directly
        # No need to generate topics here since we're selecting questions from entire database
        
        # Create test session (without generating questions here - the view will handle it)
        test_session = TestSession.objects.create(
            student_id=student_id,  # Use authenticated user's student_id
            selected_topics=selected_topics,  # Empty for random tests
            time_limit=time_limit,
            question_count=question_count,
            start_time=timezone.now(),
            total_questions=question_count or 0  # Will be updated by view after question generation
        )
        
        # The signals will automatically handle topic classification
        return test_session


class TestAnswerSerializer(serializers.ModelSerializer):
    question_details = QuestionSerializer(source='question', read_only=True)
    
    class Meta:
        model = TestAnswer
        fields = [
            'id', 'session', 'question', 'question_details', 'selected_answer', 'text_answer',
            'is_correct', 'marked_for_review', 'time_taken', 'visit_count', 'answered_at'
        ]
        read_only_fields = ['is_correct']


class TestAnswerCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    question_id = serializers.IntegerField()
    selected_answer = serializers.CharField(max_length=1, allow_null=True, required=False) # 'A', 'B', 'C', 'D' or null (for MCQ)
    text_answer = serializers.CharField(max_length=2000, allow_null=True, allow_blank=True, required=False) # Text answer for NVT questions
    marked_for_review = serializers.BooleanField(default=False, required=False)
    time_taken = serializers.IntegerField(default=0, required=False) # Time spent on question in seconds
    visit_count = serializers.IntegerField(default=1, required=False) # Number of times question was visited

    def validate(self, data):
        # Check if session and question exist
        session_id = data.get('session_id')
        question_id = data.get('question_id')

        try:
            session = TestSession.objects.get(pk=session_id)
            question = Question.objects.get(pk=question_id)
            
            # Apply cleaning if LaTeX patterns or simple chemical notations are found
            needs_cleaning = any(pattern in question.question for pattern in ['\\', '$', '^{', '_{', '\\frac', '^ -', '^ +', '^-', '^+', 'x 10^'])
            if not needs_cleaning:
                # Also check options for patterns
                all_options = question.option_a + question.option_b + question.option_c + question.option_d
                needs_cleaning = any(pattern in all_options for pattern in ['\\', '$', '^{', '_{', '\\frac', '^ -', '^ +', '^-', '^+', 'x 10^'])
            if not needs_cleaning and question.explanation:
                # Also check explanation for patterns
                needs_cleaning = any(pattern in question.explanation for pattern in ['\\', '$', '^{', '_{', '\\frac', '^ -', '^ +', '^-', '^+', 'x 10^'])
            
            if needs_cleaning:
                from .views.utils import clean_mathematical_text
                question.question = clean_mathematical_text(question.question)
                question.option_a = clean_mathematical_text(question.option_a)
                question.option_b = clean_mathematical_text(question.option_b)
                question.option_c = clean_mathematical_text(question.option_c)
                question.option_d = clean_mathematical_text(question.option_d)
                if question.explanation:
                    question.explanation = clean_mathematical_text(question.explanation)
                question.save(update_fields=['question', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation'])
        except TestSession.DoesNotExist:
            raise serializers.ValidationError({"session_id": "Test session not found."})
        except Question.DoesNotExist:
            raise serializers.ValidationError({"question_id": "Question not found."})

        # Validate that the session belongs to the authenticated user
        request = self.context.get('request')
        if request and hasattr(request.user, 'student_id'):
            if session.student_id != request.user.student_id:
                raise serializers.ValidationError({"session_id": "You can only submit answers to your own test sessions."})

        # Validate answer based on question type
        question_type = getattr(question, 'question_type', None) or 'Blank'  # Default to MCQ if not set
        selected_answer = data.get('selected_answer')
        text_answer = data.get('text_answer')
        
        if question_type == 'NVT':
            # NVT questions require text_answer
            if text_answer:
                # Sanitize and validate length
                text_answer = text_answer.strip()
                from django.conf import settings
                max_length = settings.NEET_SETTINGS.get('NVT_MAX_ANSWER_LENGTH', 2000)
                if len(text_answer) > max_length:
                    raise serializers.ValidationError({"text_answer": f"Answer must not exceed {max_length} characters."})
                data['text_answer'] = text_answer  # Store sanitized version
            # NVT can be unanswered (empty text_answer is allowed)
        else:
            # MCQ questions (question_type is 'Blank' or empty)
            if selected_answer and selected_answer not in ['A', 'B', 'C', 'D']:
                raise serializers.ValidationError({"selected_answer": "Must be 'A', 'B', 'C', or 'D'."})

        data['session'] = session # Attach objects for view logic
        data['question'] = question
        return data


# Enhanced StudentProfile serializer with authentication and statistics
class StudentProfileSerializer(serializers.ModelSerializer):
    total_tests = serializers.SerializerMethodField()
    recent_tests = serializers.SerializerMethodField()
    institution = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProfile
        fields = [
            'student_id', 'full_name', 'email', 'phone_number', 'date_of_birth',
            'school_name', 'target_exam_year', 'is_active', 'is_verified', 'last_login',
            'created_at', 'updated_at', 'total_tests', 'recent_tests',
            'google_sub', 'google_email', 'email_verified', 'google_picture', 'auth_provider',
            'institution', 'institution_code', 'is_institution_student'
        ]
        read_only_fields = [
            'student_id', 'created_at', 'updated_at', 'last_login', 'google_sub', 'google_email', 'auth_provider'
        ]
        extra_kwargs = {
            'password_hash': {'write_only': True},
            'generated_password': {'write_only': True}
        }
    
    def get_total_tests(self, obj):
        return obj.get_test_sessions().count()
    
    def get_recent_tests(self, obj):
        recent_sessions = obj.get_test_sessions()[:5]  # Last 5 tests
        return TestSessionSerializer(recent_sessions, many=True).data
    
    def get_institution(self, obj):
        """Return institution details if student is linked to an institution"""
        if obj.institution:
            return {
                'id': obj.institution.id,
                'name': obj.institution.name,
                'code': obj.institution.code,
                'exam_types': obj.institution.exam_types or ['neet', 'jee']
            }
        return None


class StudentProfileCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, max_length=64, required=True)
    password_confirmation = serializers.CharField(write_only=True, required=True)
    institution_code = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=50)
    
    class Meta:
        model = StudentProfile
        fields = [
            'full_name', 'email', 'phone_number', 'date_of_birth',
            'school_name', 'target_exam_year', 'password', 'password_confirmation',
            'institution_code'
        ]
        
    def validate_email(self, value):
        """Ensure email uniqueness"""
        if StudentProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError("Student with this email already exists.")
        return value

    def validate_phone_number(self, value):
        """Normalize and validate Indian mobile numbers and enforce uniqueness."""
        if not value:
            return value

        from .utils.otp import normalize_mobile, validate_mobile
        from .models import StudentProfile

        normalized = normalize_mobile(value)
        if not normalized or not validate_mobile(normalized):
            raise serializers.ValidationError("Invalid mobile number. Please provide a valid Indian mobile number.")

        # Ensure uniqueness (do not allow two accounts with same phone)
        if StudentProfile.objects.filter(phone_number=normalized).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")

        return normalized
    
    def validate_full_name(self, value):
        """Ensure full_name uniqueness (case-insensitive) - acts as username"""
        # Allow duplicate full names across different emails. The combined
        # (full_name, email) uniqueness is validated in `validate()` where
        # both fields are available.
        return value
    
    def validate_password(self, value):
        """Validate password strength and policies"""
        from .utils.password_utils import validate_password_strength
        
        is_valid, errors, strength_score = validate_password_strength(value)
        if not is_valid:
            raise serializers.ValidationError(errors)
        return value
    
    def validate(self, data):
        """Validate password confirmation matches"""
        from .utils.password_utils import validate_password_confirmation
        from .utils.password_utils import validate_full_name_uniqueness
        
        password = data.get('password')
        password_confirmation = data.get('password_confirmation')
        
        if password and password_confirmation:
            is_valid, error_message = validate_password_confirmation(password, password_confirmation)
            if not is_valid:
                raise serializers.ValidationError({'password_confirmation': error_message})
        # Enforce combined uniqueness of (full_name, email)
        full_name = data.get('full_name')
        email = data.get('email')
        if full_name and email:
            is_unique, message = validate_full_name_uniqueness(full_name, email)
            if not is_unique:
                # Attach error to the full_name field for front-end display
                raise serializers.ValidationError({'full_name': message})

        return data
    
    def create(self, validated_data):
        """Create student with user-defined password"""
        password = validated_data.pop('password')
        validated_data.pop('password_confirmation', None)
        institution_code = validated_data.pop('institution_code', None)
        
        # Create student instance
        student = StudentProfile(**validated_data)
        
        # Handle institution code if provided
        if institution_code:
            from .models import Institution
            try:
                institution = Institution.objects.get(code__iexact=institution_code.strip(), is_active=True)
                student.institution = institution
                student.institution_code = institution.code
                student.is_institution_student = True
            except Institution.DoesNotExist:
                raise serializers.ValidationError({
                    'institution_code': f'Invalid institution code: {institution_code}. Please check with your institution.'
                })
        
        # Ensure a student_id is generated so frontend immediately has an ID.
        # The model's save() will only auto-generate a STU... id when both
        # full_name and date_of_birth are present. Many frontends (register)
        # don't collect DOB, so generate a suitable ID here:
        try:
            from .utils.student_utils import ensure_unique_student_id
        except Exception:
            # Local import fallback to avoid circular imports during tests
            from .utils.student_utils import ensure_unique_student_id

        if not student.student_id:
            # If user provided a real DOB, use it to generate the STU id
            if getattr(student, 'full_name', None) and getattr(student, 'date_of_birth', None):
                try:
                    student.student_id = ensure_unique_student_id(student.full_name, student.date_of_birth)
                except Exception:
                    student.student_id = None
            else:
                # Requirement: if DOB not provided, use profile creation date (now) to generate STU id
                try:
                    from django.utils import timezone
                    creation_date = timezone.now().date()
                    base_name = student.full_name or (student.email.split('@')[0] if student.email else 'user')
                    student.student_id = ensure_unique_student_id(base_name, creation_date)
                except Exception:
                    student.student_id = None

        # Set user-defined password
        student.set_user_password(password)

        # Save the student (this will persist student_id generated above)
        student.save()

        return student


class StudentLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100, help_text="Student ID, Full Name or Email")
    password = serializers.CharField(max_length=64)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        student = None

        # 1) Try to find student by student_id first
        try:
            student = StudentProfile.objects.get(student_id=username)
        except StudentProfile.DoesNotExist:
            student = None

        # 2) If not found, try by email (case-insensitive)
        if not student:
            try:
                student = StudentProfile.objects.get(email__iexact=username)
            except StudentProfile.DoesNotExist:
                student = None

        # 3) If still not found, try by full_name (case-insensitive).
        #    If multiple accounts share the same full_name, return a clear error
        #    asking the user to login with Student ID or email.
        if not student:
            try:
                student = StudentProfile.objects.get(full_name__iexact=username)
            except StudentProfile.DoesNotExist:
                student = None
            except StudentProfile.MultipleObjectsReturned:
                raise serializers.ValidationError(
                    "Multiple accounts found with this full name. Please login using Student ID or email."
                )

        if not student:
            raise serializers.ValidationError("Invalid credentials.")

        if not student.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")

        if not student.is_active:
            raise serializers.ValidationError("Account is deactivated.")

        data['student'] = student
        return data


class ReviewCommentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    question_text = serializers.SerializerMethodField()
    
    class Meta:
        model = ReviewComment
        fields = [
            'id', 'session', 'question', 'student_comment', 'created_at', 
            'updated_at', 'student_name', 'question_text'
        ]
    
    def get_student_name(self, obj):
        student_profile = obj.session.get_student_profile()
        return student_profile.full_name if student_profile else "Unknown Student"
    
    def get_question_text(self, obj):
        return obj.question.question[:100] + "..." if len(obj.question.question) > 100 else obj.question.question


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for ChatSession model"""
    student_name = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'student_id', 'student_name', 'chat_session_id', 'session_title',
            'is_active', 'created_at', 'updated_at', 'message_count', 'last_message'
        ]
        read_only_fields = ['id', 'chat_session_id', 'created_at', 'updated_at']
    
    def get_student_name(self, obj):
        """Get student name from StudentProfile"""
        student_profile = obj.get_student_profile()
        return student_profile.full_name if student_profile else "Unknown Student"
    
    def get_message_count(self, obj):
        """Get total number of messages in this session"""
        return obj.messages.count()
    
    def get_last_message(self, obj):
        """Get the last message content (truncated)"""
        last_message = obj.messages.last()
        if last_message:
            content = last_message.message_content
            return content[:100] + "..." if len(content) > 100 else content
        return None


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage model"""
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'chat_session', 'message_type', 'message_content',
            'sql_query', 'processing_time', 'created_at', 'time_since'
        ]
        read_only_fields = ['id', 'created_at', 'processing_time', 'sql_query']
    
    def get_time_since(self, obj):
        """Get human-readable time since message was created"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at)


class ChatMessageCreateSerializer(serializers.Serializer):
    """Serializer for creating chat messages"""
    session_id = serializers.CharField(max_length=100)
    message = serializers.CharField(max_length=2000, min_length=1)
    
    def validate_session_id(self, value):
        """Validate that chat session exists and belongs to user"""
        request = self.context.get('request')
        
        try:
            chat_session = ChatSession.objects.get(chat_session_id=value, is_active=True)
            
            # Validate that session belongs to authenticated user
            if request and hasattr(request.user, 'student_id'):
                if chat_session.student_id != request.user.student_id:
                    raise serializers.ValidationError("You can only send messages to your own chat sessions.")
            
            return value
        except ChatSession.DoesNotExist:
            raise serializers.ValidationError("Chat session not found or inactive.")
    
    def validate_message(self, value):
        """Basic message validation"""
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        return value.strip()


class ChatSessionCreateSerializer(serializers.Serializer):
    """Serializer for creating new chat sessions"""
    session_title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    
    def validate_session_title(self, value):
        """Clean and validate session title"""
        if value:
            return value.strip()
        return None


# --- Password reset serializers (moved from serializers/password_reset_serializers.py)
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=6)


# --- Payment serializers ---
class CreateOrderSerializer(serializers.Serializer):
    plan = serializers.CharField()
    
    def validate_plan(self, value):
        """Validate plan name"""
        valid_plans = ['basic', 'pro']
        if value not in valid_plans:
            raise serializers.ValidationError(f"Plan must be one of: {', '.join(valid_plans)}")
        return value


class VerifyPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()
    local_order_id = serializers.IntegerField()


# --- Chat Memory Serializers ---
class ChatMemorySerializer(serializers.ModelSerializer):
    """Serializer for ChatMemory model"""
    
    class Meta:
        model = ChatMemory
        fields = [
            'id', 'student', 'memory_type', 'content', 'source_session_id',
            'key_tags', 'confidence_score', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_confidence_score(self, value):
        """Validate confidence score is between 0.0 and 1.0"""
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError("Confidence score must be between 0.0 and 1.0")
        return value


class ChatMemoryCreateSerializer(serializers.Serializer):
    """Serializer for creating chat memories"""
    memory_type = serializers.ChoiceField(
        choices=[('long_term', 'Long Term'), ('short_term', 'Short Term')],
        default='long_term'
    )
    content = serializers.JSONField()
    source_session_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    key_tags = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    confidence_score = serializers.FloatField(default=1.0, min_value=0.0, max_value=1.0)
    
    def validate_content(self, value):
        """Validate content structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Content must be a JSON object")
        return value


class RazorpayOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = RazorpayOrder
        fields = ['id', 'student', 'plan', 'amount', 'currency', 'razorpay_order_id', 'status', 'created_at']
        read_only_fields = ['id', 'razorpay_order_id', 'status', 'created_at']