from django.contrib import admin
from .models import Topic, Question, TestSession, TestAnswer, StudentProfile, ReviewComment, ChatSession, ChatMessage, StudentInsight, PasswordReset, PlatformTest

@admin.register(PlatformTest)
class PlatformTestAdmin(admin.ModelAdmin):
    list_display = ['test_name', 'test_code', 'test_type', 'time_limit', 'total_questions', 'is_active', 'get_availability_status', 'scheduled_date_time', 'created_at']
    list_filter = ['test_type', 'is_active', 'scheduled_date_time', 'test_year']
    search_fields = ['test_name', 'test_code', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'get_availability_status']
    
    fieldsets = (
        ('Test Information', {
            'fields': ('test_name', 'test_code', 'test_year', 'test_type', 'description', 'instructions')
        }),
        ('Test Configuration', {
            'fields': ('time_limit', 'total_questions', 'selected_topics', 'question_distribution')
        }),
        ('Scheduling', {
            'fields': ('scheduled_date_time', 'is_active'),
            'description': 'Leave scheduled_date_time empty for "Available Anytime" tests, or set a specific date/time for scheduled tests.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'get_availability_status'),
            'classes': ('collapse',)
        }),
    )
    
    def get_availability_status(self, obj):
        return obj.get_availability_status()
    get_availability_status.short_description = 'Current Status'

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'icon']
    list_filter = ['subject']
    search_fields = ['name', 'subject']
    ordering = ['subject', 'name']
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'full_name', 'email', 'is_active']
    list_filter = ['is_active']
    search_fields = ['student_id', 'full_name', 'email']
    ordering = ['student_id']

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['student_id','chat_session_id','session_title','is_active']
    list_filter = ['student_id']
    search_fields = ['session_id', 'student__full_name']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['chat_session', 'message_type', 'created_at', 'processing_time']
    list_filter = ['message_type']
    search_fields = ['chat_session__session_id', 'message_content']
    ordering = ['-created_at']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['topic','question', 'correct_answer', 'explanation']
    list_filter = ['correct_answer']
    search_fields = ['question']
    ordering = ['topic', 'id']
    
    def question_preview(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
    question_preview.short_description = 'Question'

@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'total_questions', 'time_limit', 'is_completed', 'start_time', 'end_time']
    list_filter = ['is_completed', 'start_time']
    ordering = ['-start_time']
    readonly_fields = ['start_time']

@admin.register(TestAnswer)
class TestAnswerAdmin(admin.ModelAdmin):
    list_display = ['session', 'question', 'selected_answer', 'marked_for_review', 'time_taken', 'visit_count']
    list_filter = ['selected_answer', 'marked_for_review', 'session__is_completed']
    search_fields = ['question']
    ordering = ['session', 'question']
    
    def question_preview(self, obj):
        return obj.question.question[:50] + "..." if len(obj.question.question) > 50 else obj.question.question
    question_preview.short_description = 'Question'

@admin.register(StudentInsight)
class StudentInsightAdmin(admin.ModelAdmin):
    list_display = ['student', 'test_session', 'llm_strengths','llm_study_plan','llm_weaknesses','llm_last_test_feedback','created_at']
    list_filter = ['student']
    search_fields = ['student__full_name', 'test_session__id', 'llm_strengths', 'llm_study_plan', 'llm_weaknesses', 'llm_last_test_feedback']
    ordering = ['-created_at']

@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ['user', 'reset_token_hash', 'expires_at', 'used', 'created_at']
    list_filter = ['used']
    search_fields = ['user']
    ordering = ['-expires_at']