from django.contrib import admin
from .models import Topic, Question, TestSession, TestAnswer, StudentProfile, ReviewComment, ChatSession, ChatMessage

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
    list_display = ['session', 'question', 'selected_answer', 'marked_for_review', 'time_taken']
    list_filter = ['selected_answer', 'marked_for_review', 'session__is_completed']
    search_fields = ['question']
    ordering = ['session', 'question']
    
    def question_preview(self, obj):
        return obj.question.question[:50] + "..." if len(obj.question.question) > 50 else obj.question.question
    question_preview.short_description = 'Question'