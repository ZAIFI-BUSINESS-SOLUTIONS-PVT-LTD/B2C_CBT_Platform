from django.contrib import admin
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from .models import Topic, Question, TestSession, TestAnswer, StudentProfile, ReviewComment, ChatSession, ChatMessage, StudentInsight, PasswordReset, PlatformTest

@admin.register(PlatformTest)
class PlatformTestAdmin(admin.ModelAdmin):
    list_display = ['test_name', 'test_code', 'test_type', 'time_limit', 'total_questions', 'is_active', 'get_availability_status', 'scheduled_date_time', 'created_at']
    list_filter = ['test_type', 'is_active', 'scheduled_date_time', 'test_year']
    search_fields = ['test_name', 'test_code', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'get_availability_status']
    
    # Use a custom form so we can present selected_topics as a friendly multi-select
    class PlatformTestForm(forms.ModelForm):
        selected_topics_m2m = forms.ModelMultipleChoiceField(
            queryset=Topic.objects.all(),
            required=False,
            widget=FilteredSelectMultiple('Topics', is_stacked=False)
        )
        # New user-friendly fields for difficulty distribution (absolute counts)
        difficulty_easy = forms.IntegerField(required=False, min_value=0, label='Easy questions',
            help_text='Number of easy questions (leave blank to auto).')
        difficulty_medium = forms.IntegerField(required=False, min_value=0, label='Medium questions',
            help_text='Number of medium questions (leave blank to auto).')
        difficulty_hard = forms.IntegerField(required=False, min_value=0, label='Hard questions',
            help_text='Number of hard questions (leave blank to auto).')

        class Meta:
            model = PlatformTest
            fields = '__all__'

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Initialize the M2M field from the JSONField stored ids
            if self.instance and getattr(self.instance, 'selected_topics', None):
                try:
                    ids = list(self.instance.selected_topics)
                    self.fields['selected_topics_m2m'].initial = Topic.objects.filter(id__in=ids)
                except Exception:
                    self.fields['selected_topics_m2m'].initial = []
            # Initialize difficulty fields from JSONField if present
            dist = getattr(self.instance, 'difficulty_distribution', None) or {}
            try:
                self.fields['difficulty_easy'].initial = dist.get('easy')
                self.fields['difficulty_medium'].initial = dist.get('medium')
                self.fields['difficulty_hard'].initial = dist.get('hard')
            except Exception:
                pass

        def save(self, commit=True):
            # Save instance and write back selected topic ids into JSONField
            instance = super().save(commit=False)
            topics_qs = self.cleaned_data.get('selected_topics_m2m')
            if topics_qs is None:
                instance.selected_topics = []
            else:
                instance.selected_topics = [int(t.id) for t in topics_qs]
            # Persist difficulty distribution from friendly fields
            e = self.cleaned_data.get('difficulty_easy')
            m = self.cleaned_data.get('difficulty_medium')
            h = self.cleaned_data.get('difficulty_hard')
            dist = {}
            if e is not None:
                dist['easy'] = int(e)
            if m is not None:
                dist['medium'] = int(m)
            if h is not None:
                dist['hard'] = int(h)
            instance.difficulty_distribution = dist if dist else None
            if commit:
                instance.save()
            return instance

        def clean(self):
            cleaned = super().clean()
            e = cleaned.get('difficulty_easy') or 0
            m = cleaned.get('difficulty_medium') or 0
            h = cleaned.get('difficulty_hard') or 0
            total = e + m + h
            # Validate against total_questions if counts provided
            tq = cleaned.get('total_questions') or getattr(self.instance, 'total_questions', None)
            if total > 0 and tq and int(tq) != total:
                raise forms.ValidationError(f'Sum of easy+medium+hard ({total}) must equal Total questions ({tq}).')
            return cleaned

    form = PlatformTestForm

    fieldsets = (
        ('Test Information', {
            'fields': ('test_name', 'test_code', 'test_year', 'test_type', 'description', 'instructions')
        }),
        ('Test Configuration', {
            # 'selected_topics_m2m' is a friendly dropdown bound to the JSONField 'selected_topics'
            'fields': (
                'time_limit', 'total_questions', 'selected_topics_m2m', 'question_distribution',
                # friendly difficulty inputs
                'difficulty_easy', 'difficulty_medium', 'difficulty_hard'
            )
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