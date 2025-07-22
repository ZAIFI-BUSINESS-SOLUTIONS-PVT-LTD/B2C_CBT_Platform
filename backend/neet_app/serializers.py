# your_app_name/serializers.py
from rest_framework import serializers
from .models import Topic, Question, TestSession, TestAnswer, StudentProfile, ReviewComment
from django.db.models import F

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
    class Meta:
        model = TestSession
        fields = '__all__'

class TestSessionCreateSerializer(serializers.Serializer):
    # selected_topics is expected as a list of strings (IDs)
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

class TestAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAnswer
        fields = '__all__'

class TestAnswerCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    question_id = serializers.IntegerField()
    selected_answer = serializers.CharField(max_length=1, allow_null=True, required=False) # 'A', 'B', 'C', 'D' or null
    marked_for_review = serializers.BooleanField(default=False, required=False)
    time_taken = serializers.IntegerField(default=0, required=False) # Renamed from time_spent to time_taken for consistency with Django model field

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

        data['session'] = session # Attach objects for view logic
        data['question'] = question
        return data

# Placeholder serializers (if needed for other viewsets)
class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = '__all__'

class ReviewCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewComment
        fields = '__all__'