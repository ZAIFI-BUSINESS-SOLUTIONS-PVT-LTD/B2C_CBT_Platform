# your_app_name/serializers.py
from rest_framework import serializers
from .models import Topic, Question, TestSession, TestAnswer, StudentProfile, ReviewComment
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
    password_confirmation = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = StudentProfile
        fields = [
            'full_name', 'email', 'phone_number', 'date_of_birth',
            'school_name', 'target_exam_year', 'password_confirmation'
        ]
        
    def validate_email(self, value):
        """Ensure email uniqueness"""
        if StudentProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError("Student with this email already exists.")
        return value
    
    def create(self, validated_data):
        """Create student with auto-generated credentials"""
        validated_data.pop('password_confirmation', None)
        student = StudentProfile.objects.create(**validated_data)
        # The save() method and signals will handle ID and password generation
        return student


class StudentLoginSerializer(serializers.Serializer):
    student_id = serializers.CharField(max_length=20)
    password = serializers.CharField(max_length=20)
    
    def validate(self, data):
        student_id = data.get('student_id')
        password = data.get('password')
        
        try:
            student = StudentProfile.objects.get(student_id=student_id)
            if not student.check_password(password):
                raise serializers.ValidationError("Invalid credentials.")
            if not student.is_active:
                raise serializers.ValidationError("Account is deactivated.")
            data['student'] = student
        except StudentProfile.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials.")
        
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