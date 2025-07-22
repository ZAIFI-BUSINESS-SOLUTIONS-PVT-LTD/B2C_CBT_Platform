# your_app_name/models.py
from django.db import models
from django.utils import timezone # Used for default values for DateTimeField

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
    Replicates the 'test_sessions' table from the Drizzle ORM schema.
    Manages individual test attempts.
    """
    id = models.AutoField(primary_key=True) # serial("id").primaryKey()
    # Stores an array of topic IDs as strings, using JSONField for Drizzle's text().array()
    selected_topics = models.JSONField(null=False) # text("selected_topics").array().notNull()
    # Time limit in minutes, nullable for question-based tests
    time_limit = models.IntegerField(null=True, blank=True) # integer("time_limit")
    # Number of questions, nullable for time-based tests
    question_count = models.IntegerField(null=True, blank=True) # integer("question_count")
    # When the test session was created and started
    start_time = models.DateTimeField(null=False) # timestamp("start_time").notNull()
    # When the test was completed, nullable if still in progress
    end_time = models.DateTimeField(null=True, blank=True) # timestamp("end_time")
    # Whether the test has been submitted and completed
    is_completed = models.BooleanField(default=False, null=False) # boolean("is_completed").default(false)
    # Total number of questions generated for this session
    total_questions = models.IntegerField(null=False) # integer("total_questions").notNull()

    class Meta:
        db_table = 'test_sessions' # Ensures the table name in DB is 'test_sessions'
        verbose_name = 'Test Session'
        verbose_name_plural = 'Test Sessions'

    def __str__(self):
        return f"Session {self.id} - {'Completed' if self.is_completed else 'In Progress'}"

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
    Replicates the 'student_profiles' table from the Drizzle ORM schema.
    Stores student profile information.
    """
    id = models.AutoField(primary_key=True) # serial("id").primaryKey()
    full_name = models.TextField(null=False) # text("full_name").notNull()
    email = models.EmailField(unique=True, null=False) # text("email").notNull().unique()
    phone_number = models.CharField(max_length=20, null=True, blank=True) # text("phone_number")
    date_of_birth = models.DateField(null=True, blank=True) # date("date_of_birth")
    school_name = models.TextField(null=True, blank=True) # text("school_name")
    target_exam_year = models.IntegerField(null=True, blank=True) # integer("target_exam_year")
    profile_picture = models.URLField(null=True, blank=True) # text("profile_picture")
    created_at = models.DateTimeField(auto_now_add=True, null=False) # timestamp("created_at").defaultNow()
    updated_at = models.DateTimeField(auto_now=True, null=False) # timestamp("updated_at").defaultNow()

    class Meta:
        db_table = 'student_profiles' # Ensures the table name in DB is 'student_profiles'
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profiles'

    def __str__(self):
        return self.full_name