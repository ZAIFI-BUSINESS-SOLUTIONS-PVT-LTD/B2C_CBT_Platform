# your_app_name/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.db.models.signals import pre_save
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

    class Meta:
        db_table = 'questions' # Ensures the table name in DB is 'questions'
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'

    def __str__(self):
        return f"Q{self.id}: {self.question[:50]}..."

class TestSession(models.Model):
    """
    Enhanced TestSession model with student tracking and subject-wise classification.
    Manages individual test attempts with proper student authentication.
    """
    id = models.AutoField(primary_key=True)
    # Link to StudentProfile using student_id
    student_id = models.CharField(max_length=20, null=False, db_index=True)  # STU + YY + DDMM + ABC123
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

    class Meta:
        db_table = 'test_sessions'
        verbose_name = 'Test Session'
        verbose_name_plural = 'Test Sessions'
        indexes = [
            models.Index(fields=['student_id', 'start_time']),
            models.Index(fields=['is_completed', 'start_time']),
        ]

    def __str__(self):
        return f"Session {self.id} - {self.student_id} - {'Completed' if self.is_completed else 'In Progress'}"

    def get_student_profile(self):
        """Get the associated StudentProfile"""
        try:
            return StudentProfile.objects.get(student_id=self.student_id)
        except StudentProfile.DoesNotExist:
            return None

    def calculate_score_percentage(self):
        """Calculate overall score percentage"""
        if self.total_questions == 0:
            return 0
        return (self.correct_answers / self.total_questions) * 100

    def update_subject_classification(self):
        """Classify selected topics by subjects and update respective fields"""
        from .utils.topic_utils import classify_topics_by_subject
        
        if not self.selected_topics:
            return
        
        # Get all topics and their classification
        classification = classify_topics_by_subject()
        
        # Reset subject topic lists
        self.physics_topics = []
        self.chemistry_topics = []
        self.botany_topics = []
        self.zoology_topics = []
        
        # Get topic names for selected topic IDs
        selected_topic_objects = Topic.objects.filter(id__in=self.selected_topics)
        selected_topic_names = [topic.name for topic in selected_topic_objects]
        
        # Classify selected topics
        for topic_name in selected_topic_names:
            if topic_name in classification.get('Physics', []):
                self.physics_topics.append(topic_name)
            elif topic_name in classification.get('Chemistry', []):
                self.chemistry_topics.append(topic_name)
            elif topic_name in classification.get('Botany', []):
                self.botany_topics.append(topic_name)
            elif topic_name in classification.get('Zoology', []):
                self.zoology_topics.append(topic_name)

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
    Enhanced StudentProfile model with custom student_id primary key and auto-generated passwords.
    Serves as the authentication foundation for the NEET testing platform.
    """
    # Custom student ID as primary key (STU + YY + DDMM + ABC123)
    student_id = models.CharField(max_length=20, primary_key=True, unique=True)
    # Auto-generated password (FIRSTFOUR + DDMM)
    password_hash = models.CharField(max_length=128)  # Hashed password storage
    generated_password = models.CharField(max_length=20, blank=True)  # Plain text for display (temporary)
    
    # Basic profile information
    full_name = models.TextField(null=False)
    email = models.EmailField(unique=True, null=False)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    date_of_birth = models.DateField(null=False)  # Required for ID and password generation
    
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

    class Meta:
        db_table = 'student_profiles'
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profiles'
        indexes = [
            models.Index(fields=['email']),
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
        """Generate student_id and password based on profile data"""
        from .utils.student_utils import ensure_unique_student_id, generate_password
        
        if not self.student_id and self.full_name and self.date_of_birth:
            # Generate unique student ID
            self.student_id = ensure_unique_student_id(self.full_name, self.date_of_birth)
            
            # Generate and set password
            generated_password = generate_password(self.full_name, self.date_of_birth)
            self.generated_password = generated_password  # Store for display
            self.set_password(generated_password)  # Hash for security

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