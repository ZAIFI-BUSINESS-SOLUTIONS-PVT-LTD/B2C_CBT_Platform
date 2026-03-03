from django.contrib import admin
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from .models import Topic, Question, TestSession, TestAnswer, StudentProfile, ReviewComment, ChatSession, ChatMessage, PasswordReset, PlatformTest, PreviousYearQuestionPaper
from .models import UserActivity, PlatformTestAudit
from .models import PlatformAdmin, PaymentOrder, RazorpayOrder
from .models import Institution, InstitutionAdmin, QuestionOfTheDay, QuestionFeedback

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


@admin.register(Institution)
class InstitutionAdminModel(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['-created_at']


@admin.register(InstitutionAdmin)
class InstitutionAdminUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'institution', 'is_active', 'created_at']
    list_filter = ['is_active', 'institution']
    search_fields = ['username', 'institution__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

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

# StudentInsight admin removed as StudentInsight model is deprecated

@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ['user', 'reset_token_hash', 'expires_at', 'used', 'created_at']
    list_filter = ['used']
    search_fields = ['user']
    ordering = ['-expires_at']


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'last_seen', 'ip_address']
    search_fields = ['user__username', 'user__email']
    ordering = ['-last_seen']


@admin.register(PlatformTestAudit)
class PlatformTestAuditAdmin(admin.ModelAdmin):
    list_display = ['platform_test', 'action', 'performed_by', 'created_at']
    list_filter = ['action']
    ordering = ['-created_at']


@admin.register(PlatformAdmin)
class PlatformAdminAdmin(admin.ModelAdmin):
    list_display = ['username', 'is_active', 'created_at']
    readonly_fields = ['created_at']

    # Provide a nicer admin form for setting a plaintext password which will be
    # hashed before saving. Expose a `password` writable field while keeping
    # `password_hash` hidden from direct editing.
    fields = ('username', 'password', 'is_active', 'created_at')

    def get_form(self, request, obj=None, **kwargs):
        # Dynamically create a form that includes a `password` field.
        from django import forms

        class PlatformAdminForm(forms.ModelForm):
            password = forms.CharField(required=not bool(obj), widget=forms.PasswordInput, help_text='Enter plaintext password to set or change.')

            class Meta:
                model = PlatformAdmin
                fields = ('username', 'password', 'is_active')

        return PlatformAdminForm

    def save_model(self, request, obj, form, change):
        # When saving from admin, if a plaintext password was provided, hash it.
        pwd = form.cleaned_data.get('password')
        if pwd:
            obj.set_password(pwd)
        # Ensure we don't accidentally overwrite created_at etc.
        super().save_model(request, obj, form, change)


@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'student', 'provider', 'plan', 'get_amount_rupees', 'status', 'get_payment_id', 'created_at']
    list_filter = ['provider', 'status', 'plan', 'currency', 'created_at']
    search_fields = ['student__student_id', 'student__email', 'razorpay_order_id', 'razorpay_payment_id', 'play_purchase_token', 'play_order_id']
    readonly_fields = ['id', 'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'play_purchase_token', 'play_product_id', 'play_order_id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'student', 'provider', 'plan', 'amount', 'currency', 'status')
        }),
        ('Razorpay Details', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature'),
            'classes': ('collapse',),
        }),
        ('Google Play Details', {
            'fields': ('play_purchase_token', 'play_product_id', 'play_order_id'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_amount_rupees(self, obj):
        """Display amount in rupees"""
        return f"₹{obj.amount}"
    get_amount_rupees.short_description = 'Amount (₹)'
    get_amount_rupees.admin_order_field = 'amount'
    
    def get_payment_id(self, obj):
        """Display payment ID based on provider"""
        if obj.provider == 'razorpay':
            return obj.razorpay_payment_id or '-'
        elif obj.provider == 'play':
            return obj.play_order_id or '-'
        return '-'
    get_payment_id.short_description = 'Payment ID'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student')


# Note: RazorpayOrder is now an alias for PaymentOrder (defined in models.py)
# No separate admin registration needed since they're the same model


@admin.register(QuestionOfTheDay)
class QuestionOfTheDayAdmin(admin.ModelAdmin):
    """Admin interface for Question of the Day entries"""
    list_display = ['id', 'student', 'date', 'question_preview', 'selected_option', 'is_correct', 'created_at']
    list_filter = ['date', 'is_correct', 'created_at']
    search_fields = ['student__student_id', 'student__full_name', 'question__question']
    readonly_fields = ['created_at']
    ordering = ['-date', '-created_at']
    date_hierarchy = 'date'
    
    def question_preview(self, obj):
        """Show first 50 characters of the question"""
        return obj.question.question[:50] + '...' if len(obj.question.question) > 50 else obj.question.question
    question_preview.short_description = 'Question'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'question')


@admin.register(QuestionFeedback)
class QuestionFeedbackAdmin(admin.ModelAdmin):
    """Admin interface for Question Feedback - allows reviewing student-reported issues"""
    list_display = ['id', 'student', 'test_session', 'question_preview', 'feedback_type', 'created_at']
    list_filter = ['feedback_type', 'created_at', 'test_session__test_type']
    search_fields = ['student__student_id', 'student__full_name', 'question__question', 'remarks']
    readonly_fields = ['student', 'test_session', 'question', 'feedback_type', 'remarks', 'created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def question_preview(self, obj):
        """Show first 60 characters of the question"""
        question_text = obj.question.question
        return question_text[:60] + '...' if len(question_text) > 60 else question_text
    question_preview.short_description = 'Question'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'test_session', 'question')
    
    # Make all fields read-only in the detail view (feedback should not be edited)
    def has_add_permission(self, request):
        """Disable adding feedback through admin - should only come from students"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow viewing but not editing feedback"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting spam/invalid feedback"""
        return True


@admin.register(PreviousYearQuestionPaper)
class PreviousYearQuestionPaperAdmin(admin.ModelAdmin):
    """Admin interface for Previous Year Question Papers"""
    list_display = ['name', 'institution', 'exam_type', 'question_count', 'uploaded_by', 'uploaded_at', 'is_active']
    list_filter = ['exam_type', 'is_active', 'institution', 'uploaded_at']
    search_fields = ['name', 'notes', 'source_filename']
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at', 'question_count', 'source_filename']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'institution', 'exam_type', 'is_active')
        }),
        ('Upload Details', {
            'fields': ('uploaded_by', 'uploaded_at', 'source_filename', 'question_count')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('institution', 'uploaded_by')
