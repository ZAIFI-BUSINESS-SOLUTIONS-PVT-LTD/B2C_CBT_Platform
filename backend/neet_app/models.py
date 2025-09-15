# your_app_name/models.py
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

class Topic(models.Model):
    """
    Replicates the 'topics' table from the Drizzle ORM schema.
    The foundation of the learning system, storing available study topics.
    """
    id = models.AutoField(primary_key=True) # serial("id").primaryKey()
    name = models.TextField(null=False) # text("name").notNull()
    subject = models.TextField(null=False) # text("subject").notNull()
    icon = models.TextField(null=False) # text("icon").notNull()
    chapter = models.TextField(null=True, blank=True) # text("chapter") - nullable

    class Meta:
        db_table = 'topics' # Ensures the table name in DB is 'topics'
        verbose_name = 'Topic'
        verbose_name_plural = 'Topics'
        # Add unique constraint to prevent duplicate topics
        unique_together = [['name', 'subject', 'chapter']]

    def __str__(self):
        return self.name

class Question(models.Model):
    """
    Replicates the 'questions' table from the Drizzle ORM schema.
    Contains multiple-choice questions linked to topics.
    """
    id = models.AutoField(primary_key=True) # serial("id").primaryKey()
    # Foreign key to Topic, db_column matches Drizzle's 'topic_id'
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, null=False, db_column='topic_id') # integer("topic_id").notNull()
    question = models.TextField(null=False) # text("question").notNull()
    option_a = models.TextField(null=False) # text("option_a").notNull()
    option_b = models.TextField(null=False) # text("option_b").notNull()
    option_c = models.TextField(null=False) # text("option_c").notNull()
    option_d = models.TextField(null=False) # text("option_d").notNull()
    # Stores "A", "B", "C", or "D"
    correct_answer = models.CharField(max_length=1, null=False) # text("correct_answer").notNull()
    explanation = models.TextField(null=False) # text("explanation").notNull()
    # Additional fields for question metadata
    difficulty = models.TextField(null=True, blank=True) # text("difficulty") - stores difficulty level
    question_type = models.TextField(null=True, blank=True) # text("question_type") - stores type of question

    class Meta:
        db_table = 'questions' # Ensures the table name in DB is 'questions'
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'
        # Add unique constraint to prevent duplicate questions based on content and topic
        unique_together = [['question', 'topic', 'option_a', 'option_b', 'option_c', 'option_d']]

    def __str__(self):
        return f"Q{self.id}: {self.question[:50]}..."

class PlatformTest(models.Model):
    """
    Represents standardized tests provided by the platform (e.g., NEET 2024 Official Paper).
    These are pre-configured tests with specific question sets and configurations.
    """
    id = models.AutoField(primary_key=True)
    # Test identification
    test_name = models.TextField(null=False)  # e.g., "NEET 2024 Official Paper"
    test_code = models.CharField(max_length=50, unique=True, null=False)  # e.g., "NEET_2024_OFFICIAL"
    test_year = models.IntegerField(null=True, blank=True)  # e.g., 2024
    test_type = models.TextField(null=True, blank=True)  # e.g., "Official", "Practice", "Mock"
    
    # Test configuration
    description = models.TextField(null=True, blank=True)  # Test description
    instructions = models.TextField(null=True, blank=True)  # Special instructions for this test
    time_limit = models.IntegerField(null=False)  # Time limit in minutes
    total_questions = models.IntegerField(null=False)  # Total number of questions
    
    # Question selection criteria
    selected_topics = models.JSONField(null=False)  # Array of topic IDs included in this test
    question_distribution = models.JSONField(null=True, blank=True)  # Optional: questions per subject/topic
    # Difficulty distribution: optional dict describing how many/percent of easy/medium/hard
    # Examples:
    # - {'easy': 40, 'medium': 40, 'hard': 20}  (percentages summing to 100)
    # - {'easy': 5, 'medium': 10, 'hard': 5}  (absolute counts summing to total_questions)
    difficulty_distribution = models.JSONField(null=True, blank=True)
    
    # Test metadata
    is_active = models.BooleanField(default=True)  # Whether test is available for students
    scheduled_date_time = models.DateTimeField(null=True, blank=True)  # If set, test is time-based; if null, available anytime
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(auto_now=True, null=False)
    
    class Meta:
        db_table = 'platform_tests'
        verbose_name = 'Platform Test'
        verbose_name_plural = 'Platform Tests'
        indexes = [
            models.Index(fields=['test_code']),
            models.Index(fields=['test_year', 'test_type']),
            models.Index(fields=['is_active', 'created_at']),
            models.Index(fields=['scheduled_date_time']),
            models.Index(fields=['is_active', 'scheduled_date_time']),
        ]
    
    def __str__(self):
        return f"{self.test_name} ({self.test_code})"
    
    def get_questions(self):
        """Get all questions for this platform test based on selected topics"""
        return Question.objects.filter(topic_id__in=self.selected_topics)
    
    def get_total_questions_count(self):
        """Get actual count of questions available for this test"""
        return self.get_questions().count()
    
    def is_scheduled_test(self):
        """Check if this is a scheduled test (has scheduled_date_time)"""
        return self.scheduled_date_time is not None
    
    def is_open_test(self):
        """Check if this is an open/anytime test (no scheduled_date_time)"""
        return self.scheduled_date_time is None
    
    def is_available_now(self):
        """Check if test is currently available for attempts"""
        from django.utils import timezone
        
        # If not active, not available
        if not self.is_active:
            return False
            
        # If open test, always available
        if self.is_open_test():
            return True
            
        # If scheduled test, check if current time is within the window
        if self.is_scheduled_test():
            current_time = timezone.now()
            # Test is available from scheduled time for the duration + 30 minutes buffer
            test_duration_minutes = self.time_limit + 30  # Add 30 minutes buffer
            from datetime import timedelta
            end_time = self.scheduled_date_time + timedelta(minutes=test_duration_minutes)
            return self.scheduled_date_time <= current_time <= end_time
            
        return False
    
    def get_availability_status(self):
        """Get human-readable availability status"""
        if not self.is_active:
            return "Inactive"
        elif self.is_open_test():
            return "Available Anytime"
        elif self.is_scheduled_test():
            from django.utils import timezone
            current_time = timezone.now()
            
            if current_time < self.scheduled_date_time:
                return f"Scheduled for {self.scheduled_date_time.strftime('%Y-%m-%d %H:%M')}"
            elif self.is_available_now():
                return "Available Now (Live)"
            else:
                return "Test Window Closed"
        return "Unknown Status"

class TestSession(models.Model):
    """
    Enhanced TestSession model with student tracking and subject-wise classification.
    Manages individual test attempts with proper student authentication.
    Now supports both custom tests (user-selected topics) and platform tests (pre-configured).
    """
    id = models.AutoField(primary_key=True)
    # Link to StudentProfile using student_id
    student_id = models.CharField(max_length=20, null=False, db_index=True)  # STU + YY + DDMM + ABC123
    
    # Test type and linking
    test_type = models.CharField(
        max_length=20, 
        choices=[('custom', 'Custom Test'), ('platform', 'Platform Test')], 
        default='custom',
        null=False
    )  # Determines if this is a custom or platform test
    platform_test = models.ForeignKey(
        PlatformTest, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        db_column='platform_test_id'
    )  # Link to PlatformTest (only set if test_type='platform')
    
    # Stores an array of topic IDs as strings
    selected_topics = models.JSONField(null=False)
    # Subject-wise topic classification for analytics
    physics_topics = models.JSONField(default=list, blank=True)  # Topics classified as Physics
    chemistry_topics = models.JSONField(default=list, blank=True)  # Topics classified as Chemistry
    botany_topics = models.JSONField(default=list, blank=True)  # Topics classified as Botany
    zoology_topics = models.JSONField(default=list, blank=True)  # Topics classified as Zoology
    # Test configuration
    time_limit = models.IntegerField(null=True, blank=True)  # Time limit in minutes
    question_count = models.IntegerField(null=True, blank=True)  # Number of questions
    # Test tracking
    start_time = models.DateTimeField(null=False)  # When test started
    end_time = models.DateTimeField(null=True, blank=True)  # When test completed
    is_completed = models.BooleanField(default=False, null=False)
    total_questions = models.IntegerField(null=False)  # Total questions in session
    # Performance metrics
    correct_answers = models.IntegerField(default=0)  # Number of correct answers
    incorrect_answers = models.IntegerField(default=0)  # Number of incorrect answers
    unanswered = models.IntegerField(default=0)  # Number of unanswered questions
    total_time_taken = models.IntegerField(null=True, blank=True)  # Total time in seconds
    # Subject-wise performance
    physics_score = models.FloatField(null=True, blank=True)  # Physics percentage
    chemistry_score = models.FloatField(null=True, blank=True)  # Chemistry percentage
    botany_score = models.FloatField(null=True, blank=True)  # Botany percentage
    zoology_score = models.FloatField(null=True, blank=True)  # Zoology percentage
    # Activity tracking for admin metrics
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = 'test_sessions'
        verbose_name = 'Test Session'
        verbose_name_plural = 'Test Sessions'
        indexes = [
            models.Index(fields=['student_id', 'start_time']),
            models.Index(fields=['is_completed', 'start_time']),
            models.Index(fields=['test_type', 'start_time']),
            models.Index(fields=['platform_test', 'start_time']),
        ]

    def __str__(self):
        test_info = f"Platform: {self.platform_test.test_name}" if self.test_type == 'platform' and self.platform_test else "Custom Test"
        return f"Session {self.id} - {self.student_id} - {test_info} - {'Completed' if self.is_completed else 'In Progress'}"

    def get_student_profile(self):
        """Get the associated StudentProfile"""
        try:
            return StudentProfile.objects.get(student_id=self.student_id)
        except StudentProfile.DoesNotExist:
            return None

    def is_platform_test(self):
        """Check if this is a platform test session"""
        return self.test_type == 'platform' and self.platform_test is not None

    def is_custom_test(self):
        """Check if this is a custom test session"""
        return self.test_type == 'custom'

    def get_test_name(self):
        """Get the test name (platform test name or 'Custom Test')"""
        if self.is_platform_test():
            return self.platform_test.test_name
        return "Custom Test"

    def get_test_configuration(self):
        """Get test configuration (time limit, question count) based on test type"""
        if self.is_platform_test():
            return {
                'time_limit': self.platform_test.time_limit,
                'total_questions': self.platform_test.total_questions,
                'selected_topics': self.platform_test.selected_topics,
                'instructions': self.platform_test.instructions
            }
        else:
            return {
                'time_limit': self.time_limit,
                'total_questions': self.question_count or self.total_questions,
                'selected_topics': self.selected_topics,
                'instructions': None
            }

    def calculate_score_percentage(self):
        """Calculate overall score percentage"""
        if self.total_questions == 0:
            return 0
        return (self.correct_answers / self.total_questions) * 100

    def update_subject_classification(self):
        """Classify selected topics by subjects and update respective fields"""
        # Get the appropriate selected topics based on test type
        topics_to_classify = self.selected_topics
        if self.is_platform_test() and self.platform_test.selected_topics:
            topics_to_classify = self.platform_test.selected_topics
        
        if not topics_to_classify:
            return
        
        # Reset subject topic lists
        self.physics_topics = []
        self.chemistry_topics = []
        self.botany_topics = []
        self.zoology_topics = []
        
        # Get topic objects for selected topic IDs with their subjects
        selected_topic_objects = Topic.objects.filter(id__in=topics_to_classify)
        
        # Classify selected topics by their actual subject field
        for topic in selected_topic_objects:
            topic_name = topic.name
            subject = topic.subject
            
            # Normalize subject names and classify
            if subject.lower() in ['physics']:
                self.physics_topics.append(topic_name)
            elif subject.lower() in ['chemistry']:
                self.chemistry_topics.append(topic_name)
            elif subject.lower() in ['botany', 'biology', 'plant biology']:
                self.botany_topics.append(topic_name)
            elif subject.lower() in ['zoology', 'animal biology']:
                self.zoology_topics.append(topic_name)
            else:
                # Handle edge cases - try to map based on common patterns
                if 'physics' in subject.lower():
                    self.physics_topics.append(topic_name)
                elif 'chemistry' in subject.lower() or 'chemical' in subject.lower():
                    self.chemistry_topics.append(topic_name)
                elif 'plant' in subject.lower() or 'botany' in subject.lower():
                    self.botany_topics.append(topic_name)
                elif 'animal' in subject.lower() or 'zoology' in subject.lower():
                    self.zoology_topics.append(topic_name)
                # If no match, the topic won't be classified (which is fine)

    def calculate_and_update_subject_scores(self):
        """
        Calculate and update subject-wise scores based on test answers.
        Scoring: Correct = +4, Wrong = -1, Unanswered = 0
        Uses TestAnswer -> Question -> Topic -> Subject path
        """
        from django.db.models import Q
        
        # Initialize subject scores
        subject_scores = {
            'Physics': {'correct': 0, 'wrong': 0, 'unanswered': 0, 'total_questions': 0},
            'Chemistry': {'correct': 0, 'wrong': 0, 'unanswered': 0, 'total_questions': 0},
            'Botany': {'correct': 0, 'wrong': 0, 'unanswered': 0, 'total_questions': 0},
            'Zoology': {'correct': 0, 'wrong': 0, 'unanswered': 0, 'total_questions': 0}
        }
        
        # Get all test answers for this session with related data
        test_answers = TestAnswer.objects.filter(session=self).select_related(
            'question__topic'
        )
        
        # Group answers by subject
        for answer in test_answers:
            subject = answer.question.topic.subject
            
            # Normalize subject names to match our scoring dict
            if subject.lower() in ['physics']:
                subject_key = 'Physics'
            elif subject.lower() in ['chemistry']:
                subject_key = 'Chemistry'
            elif subject.lower() in ['botany', 'biology', 'plant biology']:
                subject_key = 'Botany'
            elif subject.lower() in ['zoology', 'animal biology']:
                subject_key = 'Zoology'
            else:
                # Handle edge cases - try to map based on common patterns
                if 'physics' in subject.lower():
                    subject_key = 'Physics'
                elif 'chemistry' in subject.lower() or 'chemical' in subject.lower():
                    subject_key = 'Chemistry'
                elif 'plant' in subject.lower() or 'botany' in subject.lower():
                    subject_key = 'Botany'
                elif 'animal' in subject.lower() or 'zoology' in subject.lower():
                    subject_key = 'Zoology'
                else:
                    continue  # Skip if subject cannot be classified
            
            # Count the answer type
            subject_scores[subject_key]['total_questions'] += 1
            
            if answer.is_correct is True:
                subject_scores[subject_key]['correct'] += 1
            elif answer.is_correct is False:
                subject_scores[subject_key]['wrong'] += 1
            else:  # is_correct is None (unanswered)
                subject_scores[subject_key]['unanswered'] += 1
        
        # Calculate scores for each subject
        # Score = (Correct * 4) + (Wrong * -1) + (Unanswered * 0)
        # Percentage = (Score / Max_Possible_Score) * 100
        
        for subject, stats in subject_scores.items():
            if stats['total_questions'] > 0:
                # Calculate raw score
                raw_score = (stats['correct'] * 4) + (stats['wrong'] * -1)
                
                # Calculate maximum possible score (all correct)
                max_possible_score = stats['total_questions'] * 4
                
                # Calculate percentage (ensuring it doesn't go below 0)
                percentage = max(0, (raw_score / max_possible_score) * 100) if max_possible_score > 0 else 0
                
                # Update the respective field
                if subject == 'Physics':
                    self.physics_score = round(percentage, 2)
                elif subject == 'Chemistry':
                    self.chemistry_score = round(percentage, 2)
                elif subject == 'Botany':
                    self.botany_score = round(percentage, 2)
                elif subject == 'Zoology':
                    self.zoology_score = round(percentage, 2)
            else:
                # No questions for this subject
                if subject == 'Physics':
                    self.physics_score = None
                elif subject == 'Chemistry':
                    self.chemistry_score = None
                elif subject == 'Botany':
                    self.botany_score = None
                elif subject == 'Zoology':
                    self.zoology_score = None
        
        # Save the updated scores
        self.save(update_fields=['physics_score', 'chemistry_score', 'botany_score', 'zoology_score'])
        
        return subject_scores  # Return for debugging/logging purposes

    @staticmethod
    def get_recent_question_ids_for_student(student_id, recent_tests_count=3):
        """
        Get question IDs from student's recent completed test sessions.
        
        Args:
            student_id: The student's ID
            recent_tests_count: Number of recent tests to check (default: 3)
            
        Returns:
            Set of question IDs that were used in recent tests
        """
        from django.conf import settings
        
        # Get the configurable count from settings
        if hasattr(settings, 'NEET_SETTINGS'):
            recent_tests_count = settings.NEET_SETTINGS.get('RECENT_TESTS_COUNT_FOR_EXCLUSION', recent_tests_count)
        
        # Get recent completed test sessions for this student
        recent_sessions = TestSession.objects.filter(
            student_id=student_id,
            is_completed=True
        ).order_by('-start_time')[:recent_tests_count]
        
        # If no recent sessions, return empty set
        if not recent_sessions.exists():
            return set()
        
        # Get all question IDs from TestAnswers for these sessions
        question_ids = TestAnswer.objects.filter(
            session__in=recent_sessions
        ).values_list('question_id', flat=True).distinct()
        
        return set(question_ids)

class TestAnswer(models.Model):
    """
    Replicates the 'test_answers' table from the Drizzle ORM schema.
    Records every student response.
    """
    id = models.AutoField(primary_key=True) # serial("id").primaryKey()
    # Foreign key to TestSession, db_column matches Drizzle's 'session_id'
    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, null=False, db_column='session_id') # integer("session_id").notNull()
    # Foreign key to Question, db_column matches Drizzle's 'question_id'
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=False, db_column='question_id') # integer("question_id").notNull()
    # Student's choice: "A", "B", "C", "D", or null if unanswered
    selected_answer = models.CharField(max_length=1, null=True, blank=True) # text("selected_answer")
    # Whether the selected answer matches the correct answer (nullable as it's calculated later)
    is_correct = models.BooleanField(null=True, blank=True) # boolean("is_correct")
    # Whether student marked this question for later review
    marked_for_review = models.BooleanField(default=False, null=False) # boolean("marked_for_review").default(false)
    # Time spent on this question in seconds
    time_taken = models.IntegerField(null=True, blank=True) # integer("time_spent") - renamed to time_taken for clarity in Django
    # Number of times this question was visited/viewed by the student
    visit_count = models.IntegerField(default=1, null=False) # Tracks how many times student visited this question
    # When the answer was submitted
    answered_at = models.DateTimeField(null=True, blank=True) # timestamp("answered_at")

    class Meta:
        db_table = 'test_answers' # Ensures the table name in DB is 'test_answers'
        verbose_name = 'Test Answer'
        verbose_name_plural = 'Test Answers'
        # Add a unique_together constraint to ensure only one answer per question per session
        unique_together = ('session', 'question')

    def __str__(self):
        return f"Session {self.session.id} - Q{self.question.id}: {self.selected_answer or 'Unanswered'}"

class ReviewComment(models.Model):
    """
    Replicates the 'review_comments' table from the Drizzle ORM schema.
    Allows students to add personal notes and comments on questions.
    """
    id = models.AutoField(primary_key=True) # serial("id").primaryKey()
    # Foreign key to TestSession, db_column matches Drizzle's 'session_id'
    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, null=False, db_column='session_id') # integer("session_id").notNull()
    # Foreign key to Question, db_column matches Drizzle's 'question_id'
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=False, db_column='question_id') # integer("question_id").notNull()
    student_comment = models.TextField(null=False) # text("student_comment").notNull()
    # When comment was first added
    created_at = models.DateTimeField(auto_now_add=True, null=False) # timestamp("created_at").defaultNow()
    # When comment was last modified
    updated_at = models.DateTimeField(auto_now=True, null=False) # timestamp("updated_at").defaultNow()

    class Meta:
        db_table = 'review_comments' # Ensures the table name in DB is 'review_comments'
        verbose_name = 'Review Comment'
        verbose_name_plural = 'Review Comments'
        # Optional: Add unique_together if only one comment per question per session is allowed
        # unique_together = ('session', 'question')

    def __str__(self):
        return f"Comment on Session {self.session.id}, Q{self.question.id}"

class StudentProfile(models.Model):
    """
    Enhanced StudentProfile model with custom student_id primary key and user-defined passwords.
    Serves as the authentication foundation for the NEET testing platform.
    Uses full_name as username with case-insensitive uniqueness enforcement.
    """
    # Custom student ID as primary key (STU + YY + DDMM + ABC123)
    student_id = models.CharField(max_length=20, primary_key=True, unique=True)
    # User-defined password storage (changed from auto-generated to user-defined)
    password_hash = models.CharField(max_length=128)  # Hashed password storage
    generated_password = models.CharField(max_length=64, blank=True)  # User-defined password (plain text for transition)
    
    # Basic profile information
    full_name = models.TextField(null=False)
    email = models.EmailField(unique=True, null=False)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    date_of_birth = models.DateField(null=False)  # Required for ID and password generation
    
    # Google OAuth fields
    google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)  # Google's stable user ID
    google_email = models.EmailField(null=True, blank=True)  # Email from Google
    email_verified = models.BooleanField(default=False)  # Email verification status
    google_picture = models.URLField(null=True, blank=True)  # Google profile picture
    auth_provider = models.CharField(max_length=20, default='local', choices=[
        ('local', 'Local'),
        ('google', 'Google'),
        ('both', 'Both'),
    ])  # Authentication provider
    
    # Educational information
    school_name = models.TextField(null=True, blank=True)
    target_exam_year = models.IntegerField(null=True, blank=True)
    # Account status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)  # Email/phone verification
    last_login = models.DateTimeField(null=True, blank=True)
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(auto_now=True, null=False)
    # Timestamp used to invalidate tokens/sessions after password change
    password_changed_at = models.DateTimeField(null=True, blank=True)
    
    # Subscription fields
    subscription_plan = models.CharField(max_length=50, null=True, blank=True)  # 'basic' or 'pro'
    subscription_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'student_profiles'
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profiles'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['google_sub']),
            models.Index(fields=['google_email']),
            models.Index(fields=['date_of_birth']),
            models.Index(fields=['is_active', 'created_at']),
        ]

    def __str__(self):
        return f"{self.student_id} - {self.full_name}"

    def set_password(self, raw_password):
        """Set password using Django's password hashing"""
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        """Check password using Django's password verification"""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password_hash)

    def set_unusable_password(self):
        """Set an unusable password for Google-only accounts"""
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(None)

    def set_user_password(self, raw_password):
        """Set user-defined password and store both plain text and hashed versions"""
        # Store plain text password in generated_password field (for transition period)
        self.generated_password = raw_password
        # Store hashed password for security
        self.set_password(raw_password)

    def link_google_account(self, google_sub, google_email, email_verified=False, google_picture=None):
        """Link a Google account to this student profile"""
        self.google_sub = google_sub
        self.google_email = google_email
        self.email_verified = email_verified
        if google_picture:
            self.google_picture = google_picture
        
        # Update auth provider
        if self.auth_provider == 'local':
            self.auth_provider = 'both'
        elif self.auth_provider != 'both':
            self.auth_provider = 'google'
    
    def unlink_google_account(self):
        """Unlink Google account from this student profile"""
        self.google_sub = None
        self.google_email = None
        self.google_picture = None
        
        # Update auth provider
        if self.auth_provider in ['google', 'both']:
            self.auth_provider = 'local' if self.password_hash else 'local'
    
    def can_login_with_password(self):
        """Check if student can login with password (has password set)"""
        return bool(self.password_hash)
    
    def can_login_with_google(self):
        """Check if student can login with Google (has Google account linked)"""
        return bool(self.google_sub)

    # Authentication properties required by Django's permission system
    @property
    def is_authenticated(self):
        """Always return True for authenticated students"""
        return True
    
    @property
    def is_anonymous(self):
        """Always return False for authenticated students"""
        return False
    
    @property
    def is_staff(self):
        """Students are not staff by default"""
        return False
    
    @property
    def is_superuser(self):
        """Students are not superusers by default"""
        return False
    
    def has_perm(self, perm, obj=None):
        """Students have basic permissions"""
        return True
    
    def has_perms(self, perm_list, obj=None):
        """Students have basic permissions"""
        return True
    
    def has_module_perms(self, app_label):
        """Students have basic permissions"""
        return True
    
    def get_username(self):
        """Return student_id as username"""
        return self.student_id

    def generate_credentials(self):
        """Generate student_id based on profile data (password now user-defined)"""
        from .utils.student_utils import ensure_unique_student_id
        
        if not self.student_id and self.full_name and self.date_of_birth:
            # Generate unique student ID (keep this functionality)
            self.student_id = ensure_unique_student_id(self.full_name, self.date_of_birth)
            
            # COMMENTED OUT: Auto password generation - now user provides password
            # from .utils.student_utils import generate_password
            # generated_password = generate_password(self.full_name, self.date_of_birth)
            # self.generated_password = generated_password  # Store for display
            # self.set_password(generated_password)  # Hash for security

    def get_test_sessions(self):
        """Get all test sessions for this student"""
        return TestSession.objects.filter(student_id=self.student_id).order_by('-start_time')

    def update_statistics(self):
        """Update test statistics based on completed sessions (fields removed, so now does nothing)"""
        pass

    def save(self, *args, **kwargs):
        """Override save to auto-generate credentials if needed"""
        if not self.student_id:
            self.generate_credentials()
        super().save(*args, **kwargs)


class PasswordReset(models.Model):
    """
    Stores password reset requests. Raw tokens are never stored - only the SHA256 hash
    of the token is kept. Tokens are one-time use and expire after a TTL.
    """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, db_column='user_id')
    reset_token_hash = models.CharField(max_length=128, unique=True, db_index=True)
    expires_at = models.DateTimeField(null=False)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False)

    class Meta:
        db_table = 'password_resets'
        verbose_name = 'Password Reset'
        verbose_name_plural = 'Password Resets'
        indexes = [
            models.Index(fields=['user', 'expires_at']),
            models.Index(fields=['reset_token_hash']),
        ]

    def __str__(self):
        return f"PasswordReset(user={self.user.email}, expires_at={self.expires_at}, used={self.used})"


class ChatSession(models.Model):
    """
    Manages chatbot conversation sessions for students.
    Each session represents a conversation thread between a student and the AI tutor.
    """
    id = models.AutoField(primary_key=True)
    # Link to StudentProfile using student_id for consistency with TestSession
    student_id = models.CharField(max_length=20, null=False, db_index=True)  # STU + YY + DDMM + ABC123
    # Unique session identifier for chatbot conversations
    chat_session_id = models.CharField(max_length=100, unique=True, db_index=True)  # Different from TestSession.id
    # Session metadata
    session_title = models.TextField(null=True, blank=True)  # Optional title for the chat session
    is_active = models.BooleanField(default=True, null=False)
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(auto_now=True, null=False)
    
    class Meta:
        db_table = 'chat_sessions'
        verbose_name = 'Chat Session'
        verbose_name_plural = 'Chat Sessions'
        indexes = [
            models.Index(fields=['student_id', 'created_at']),
            models.Index(fields=['is_active', 'updated_at']),
        ]
    
    def __str__(self):
        return f"Chat Session {self.chat_session_id} - {self.student_id}"
    
    def get_student_profile(self):
        """Get the associated StudentProfile"""
        try:
            return StudentProfile.objects.get(student_id=self.student_id)
        except StudentProfile.DoesNotExist:
            return None


class ChatMessage(models.Model):
    """
    Stores individual chat messages and bot responses within a chat session.
    Maintains conversation history for context and analysis.
    """
    id = models.AutoField(primary_key=True)
    # Foreign key to ChatSession
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages', db_column='chat_session_id')
    # Message type: user question or bot response
    message_type = models.CharField(max_length=10, choices=[('user', 'User'), ('bot', 'Bot')], null=False)
    # Message content
    message_content = models.TextField(null=False)
    # Optional: Store the generated SQL query for debugging and transparency
    sql_query = models.TextField(null=True, blank=True)
    # Optional: Store query execution time for performance monitoring
    processing_time = models.FloatField(null=True, blank=True)  # Time in seconds
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    
    class Meta:
        db_table = 'chat_messages'
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['chat_session', 'created_at']),
            models.Index(fields=['message_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.message_type}: {self.message_content[:50]}..."


class StudentInsight(models.Model):
    """
    Stores student performance insights in the database.
    Replaces the JSON file-based caching system with persistent, queryable storage.
    """
    id = models.AutoField(primary_key=True)
    # Foreign key to StudentProfile using student_id
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, to_field='student_id', db_column='student_id')
    # Foreign key to TestSession (nullable, since insights might not always be tied to a specific test)
    test_session = models.ForeignKey(TestSession, on_delete=models.CASCADE, null=True, blank=True, db_column='test_session_id')
    # Timestamp when insights were generated
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    
    # Topic classifications (stored as JSON arrays)
    strength_topics = models.JSONField(default=list, blank=True)  # List of strength topics
    weak_topics = models.JSONField(default=list, blank=True)  # List of weakness topics
    improvement_topics = models.JSONField(default=list, blank=True)  # List of improvement topics
    unattempted_topics = models.JSONField(default=list, blank=True)  # List of unattempted topics
    last_test_topics = models.JSONField(default=list, blank=True)  # List of last test feedback topics
    
    # LLM-generated insights (stored as JSON objects with status, message, insights)
    llm_strengths = models.JSONField(default=dict, blank=True)  # LLM-generated strengths insights
    llm_weaknesses = models.JSONField(default=dict, blank=True)  # LLM-generated weaknesses insights
    llm_study_plan = models.JSONField(default=dict, blank=True)  # LLM-generated study plan
    llm_last_test_feedback = models.JSONField(default=dict, blank=True)  # LLM-generated last test feedback
    
    # Configuration and summary data
    thresholds_used = models.JSONField(default=dict, blank=True)  # Thresholds used for classification
    summary = models.JSONField(default=dict, blank=True)  # Summary statistics (total topics, tests, etc.)
    
    # Optional insight type for categorization
    insight_type = models.CharField(max_length=20, default='overall', blank=True)  # e.g., 'overall', 'last_test'
    
    class Meta:
        db_table = 'student_insights'
        verbose_name = 'Student Insight'
        verbose_name_plural = 'Student Insights'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'created_at']),
            models.Index(fields=['test_session', 'created_at']),
            models.Index(fields=['insight_type', 'created_at']),
        ]
    
    def __str__(self):
        test_info = f" (Test {self.test_session.id})" if self.test_session else ""
        return f"Insights for {self.student.student_id}{test_info} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def get_student_profile(self):
        """Get the associated StudentProfile"""
        return self.student


class Notification(models.Model):
    """
    Tracks outgoing notifications for auditing, retries and admin visibility.
    """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, null=True, blank=True, db_column='user_id')
    notification_type = models.CharField(max_length=50)  # e.g. welcome, password_reset_request, test_submission
    subject = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, default='pending', choices=[('pending','pending'),('sent','sent'),('failed','failed')])
    error = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [models.Index(fields=['user', 'notification_type', 'status', 'created_at'])]

    def __str__(self):
        target = self.user.email if self.user else self.payload.get('to')
        return f"Notification {self.notification_type} -> {target} [{self.status}]"


# Signal: send welcome email on new StudentProfile creation
@receiver(post_save, sender=StudentProfile)
def _send_welcome_on_create(sender, instance, created, **kwargs):
    """Dispatch a welcome email when a new active student profile is created.

    The import of the notifications service is done inside the handler to avoid
    circular imports at module import time.
    """
    if not created:
        return

    # Only send welcome if there is a valid email and the account is active
    if not instance.email or not instance.is_active:
        return

    try:
        # Local import to avoid circular import at module load
        from .notifications import dispatch_welcome_email

        dispatch_welcome_email(instance)
    except Exception:
        # Avoid raising exceptions during model save flows; log via print to keep dependency-free
        import logging
        logging.exception('Failed to enqueue welcome email')


# --- Platform admin helpers: UserActivity + simple audit trail ---
class UserActivity(models.Model):
    """Track last seen and basic client info for authenticated users.

    This is intentionally lightweight (stored in DB) and used by the
    platform admin dashboard to compute "currently online" metrics.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity')
    last_seen = models.DateTimeField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    def is_online(self, threshold_minutes: int = 5):
        if not self.last_seen:
                return False
        return (timezone.now() - self.last_seen).total_seconds() <= threshold_minutes * 60

    def __str__(self):
        return f"{self.user} last_seen={self.last_seen}"


class StudentActivity(models.Model):
    """
    Track last seen and client info specifically for StudentProfile accounts.
    Used by the platform admin dashboard to compute student-focused metrics.
    """
    student = models.OneToOneField('StudentProfile', on_delete=models.CASCADE, related_name='activity')
    last_seen = models.DateTimeField(null=True, blank=True, db_index=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    def is_online(self, threshold_minutes: int = 5):
        if not self.last_seen:
            return False
        return (timezone.now() - self.last_seen).total_seconds() <= threshold_minutes * 60

    def __str__(self):
        return f"{self.student.student_id} last_seen={self.last_seen}"


class PlatformTestAudit(models.Model):
    """Audit trail of PlatformTest changes.

    Stores a simple record per create/update/delete so admins can see who
    performed changes and when. The performed_by field is a string; in a
    follow-up we can capture request user via middleware/threadlocals.
    """
    platform_test = models.ForeignKey(PlatformTest, on_delete=models.CASCADE, related_name='audits')
    action = models.CharField(max_length=32)
    performed_by = models.CharField(max_length=150, null=True, blank=True)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Audit {self.action} on {self.platform_test.test_code} by {self.performed_by} at {self.created_at}"


# Basic signal to record PlatformTest changes into PlatformTestAudit
@receiver(post_save, sender=PlatformTest)
def _platform_test_post_save(sender, instance, created, **kwargs):
    try:
        performed_by = getattr(instance, '_last_modified_by', None) or 'system'
        action = 'created' if created else 'updated'
        PlatformTestAudit.objects.create(
            platform_test=instance,
            action=action,
            performed_by=str(performed_by),
            payload={
                'test_name': instance.test_name,
                'is_active': instance.is_active,
                'time_limit': instance.time_limit,
                'total_questions': instance.total_questions,
            }
        )
    except Exception:
        # Do not raise during normal save flows
        pass


class PlatformAdmin(models.Model):
    """Separate platform admin credentials for the custom dashboard.

    These users are stored separately from Django's auth.User and only
    authenticate to the custom platform-admin UI. They do NOT grant access
    to Django's /admin/ interface.
    """
    username = models.CharField(max_length=150, unique=True)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'platform_admins'

    def __str__(self):
        return self.username

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password_hash)


class RazorpayOrder(models.Model):
    """
    Store Razorpay order & payment metadata for audit and verification
    """
    id = models.BigAutoField(primary_key=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='razorpay_orders', to_field='student_id', db_column='student_id')
    plan = models.CharField(max_length=50)  # 'basic' or 'pro'
    amount = models.IntegerField(help_text='Amount in paise')
    currency = models.CharField(max_length=10, default='INR')
    razorpay_order_id = models.CharField(max_length=128, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=128, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=256, null=True, blank=True)
    status = models.CharField(max_length=32, default='created', help_text='Order status: initiated | created | paid | failed | remote_failed')  # Track order lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'razorpay_orders'

    def mark_paid(self, payment_id, signature):
        self.razorpay_payment_id = payment_id
        self.razorpay_signature = signature
        self.status = 'paid'
        self.save(update_fields=['razorpay_payment_id', 'razorpay_signature', 'status', 'updated_at'])
