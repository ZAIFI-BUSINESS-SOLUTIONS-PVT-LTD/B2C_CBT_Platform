# your_app_name/serializers.py
from rest_framework import serializers
from .models import Topic, Question, TestSession, TestAnswer, StudentProfile, ReviewComment, ChatSession, ChatMessage
from django.db.models import F
from django.utils import timezone


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = '__all__'


# --- SECURITY CRITICAL ---
# This serializer is used when creating a test session to hide correct answers and explanations.
class QuestionForTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        # Only include safe fields for test-taking (exclude sensitive fields)
        fields = ['id', 'topic', 'question', 'option_a', 'option_b', 'option_c', 'option_d']


# This serializer is for returning full question details (e.g., in results/analytics)
class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class TestSessionSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    overall_score = serializers.SerializerMethodField()
    
    class Meta:
        model = TestSession
        fields = [
            'id', 'student_id', 'student_name', 'selected_topics', 
            'physics_topics', 'chemistry_topics', 'botany_topics', 'zoology_topics',
            'time_limit', 'question_count', 'start_time', 'end_time', 'is_completed',
            'total_questions', 'correct_answers', 'incorrect_answers', 'unanswered',
            'total_time_taken', 'physics_score', 'chemistry_score', 'botany_score',
            'zoology_score', 'overall_score'
        ]
        read_only_fields = [
            'physics_topics', 'chemistry_topics', 'botany_topics', 'zoology_topics',
            'correct_answers', 'incorrect_answers', 'unanswered', 'total_time_taken',
            'physics_score', 'chemistry_score', 'botany_score', 'zoology_score'
        ]
    
    def get_student_name(self, obj):
        student_profile = obj.get_student_profile()
        return student_profile.full_name if student_profile else "Unknown Student"
    
    def get_overall_score(self, obj):
        return obj.calculate_score_percentage()


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

    def validate_selected_topics(self, value):
        # Ensure all topic IDs exist
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
            # Calculate time limit: 1 minute per question
            data['time_limit'] = question_count
        
        return data

    def create(self, validated_data):
        """Create test session with automatic topic classification"""
        # Get student_id from the authenticated user (passed via context)
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'student_id'):
            raise serializers.ValidationError("Authentication required to create test session")
        
        student_id = request.user.student_id
        
        # Generate questions for selected topics
        from .views.utils import generate_questions_for_topics
        
        selected_topics = validated_data['selected_topics']
        time_limit = validated_data.get('time_limit')
        question_count = validated_data.get('question_count')
        
        # Generate questions
        questions = generate_questions_for_topics(selected_topics, question_count)
        
        # Create test session
        test_session = TestSession.objects.create(
            student_id=student_id,  # Use authenticated user's student_id
            selected_topics=selected_topics,
            time_limit=time_limit,
            question_count=question_count or len(questions),
            start_time=timezone.now(),
            total_questions=len(questions)
        )
        
        # The signals will automatically handle topic classification
        return test_session

class TestAnswerSerializer(serializers.ModelSerializer):
    question_details = QuestionSerializer(source='question', read_only=True)
    
    class Meta:
        model = TestAnswer
        fields = [
            'id', 'session', 'question', 'question_details', 'selected_answer', 
            'is_correct', 'marked_for_review', 'time_taken', 'answered_at'
        ]
        read_only_fields = ['is_correct']


class TestAnswerCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    question_id = serializers.IntegerField()
    selected_answer = serializers.CharField(max_length=1, allow_null=True, required=False) # 'A', 'B', 'C', 'D' or null
    marked_for_review = serializers.BooleanField(default=False, required=False)
    time_taken = serializers.IntegerField(default=0, required=False) # Time spent on question in seconds

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
            
            if needs_cleaning:
                from .views.utils import clean_mathematical_text
                question.question = clean_mathematical_text(question.question)
                question.option_a = clean_mathematical_text(question.option_a)
                question.option_b = clean_mathematical_text(question.option_b)
                question.option_c = clean_mathematical_text(question.option_c)
                question.option_d = clean_mathematical_text(question.option_d)
                question.save(update_fields=['question', 'option_a', 'option_b', 'option_c', 'option_d'])
        except TestSession.DoesNotExist:
            raise serializers.ValidationError({"session_id": "Test session not found."})
        except Question.DoesNotExist:
            raise serializers.ValidationError({"question_id": "Question not found."})

        # Validate that the session belongs to the authenticated user
        request = self.context.get('request')
        if request and hasattr(request.user, 'student_id'):
            if session.student_id != request.user.student_id:
                raise serializers.ValidationError({"session_id": "You can only submit answers to your own test sessions."})

        # Validate selected_answer if provided
        selected_answer = data.get('selected_answer')
        if selected_answer and selected_answer not in ['A', 'B', 'C', 'D']:
            raise serializers.ValidationError({"selected_answer": "Must be 'A', 'B', 'C', or 'D'."})

        data['session'] = session # Attach objects for view logic
        data['question'] = question
        return data


# Enhanced StudentProfile serializer with authentication and statistics
class StudentProfileSerializer(serializers.ModelSerializer):
    total_tests = serializers.SerializerMethodField()
    recent_tests = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProfile
        fields = [
            'student_id', 'full_name', 'email', 'phone_number', 'date_of_birth',
            'school_name', 'target_exam_year', 'is_active', 'is_verified', 'last_login',
            'created_at', 'updated_at', 'total_tests', 'recent_tests'
        ]
        read_only_fields = [
            'student_id', 'created_at', 'updated_at', 'last_login'
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


class StudentProfileCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, max_length=64, required=True)
    password_confirmation = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = StudentProfile
        fields = [
            'full_name', 'email', 'phone_number', 'date_of_birth',
            'school_name', 'target_exam_year', 'password', 'password_confirmation'
        ]
        
    def validate_email(self, value):
        """Ensure email uniqueness"""
        if StudentProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError("Student with this email already exists.")
        return value
    
    def validate_full_name(self, value):
        """Ensure full_name uniqueness (case-insensitive) - acts as username"""
        from .utils.password_utils import validate_full_name_uniqueness
        
        is_unique, error_message = validate_full_name_uniqueness(value)
        if not is_unique:
            raise serializers.ValidationError(error_message)
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
        
        password = data.get('password')
        password_confirmation = data.get('password_confirmation')
        
        if password and password_confirmation:
            is_valid, error_message = validate_password_confirmation(password, password_confirmation)
            if not is_valid:
                raise serializers.ValidationError({'password_confirmation': error_message})
        
        return data
    
    def create(self, validated_data):
        """Create student with user-defined password"""
        password = validated_data.pop('password')
        validated_data.pop('password_confirmation', None)
        
        # Create student instance
        student = StudentProfile(**validated_data)
        
        # Set user-defined password
        student.set_user_password(password)
        
        # Save the student (this will trigger student_id generation via signals)
        student.save()
        
        return student


class StudentLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100, help_text="Student ID or Full Name")
    password = serializers.CharField(max_length=64)
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        student = None
        
        # Try to find student by student_id first
        try:
            student = StudentProfile.objects.get(student_id=username)
        except StudentProfile.DoesNotExist:
            # If not found by student_id, try by full_name (case-insensitive)
            try:
                student = StudentProfile.objects.get(full_name__iexact=username)
            except StudentProfile.DoesNotExist:
                pass
        
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