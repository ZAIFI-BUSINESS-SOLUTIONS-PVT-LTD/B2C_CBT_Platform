// frontend/src/types/api.ts

// IMPORTANT: These types assume that 'djangorestframework-camel-case' is correctly
// configured in your Django backend's settings.py, which will automatically
// convert snake_case model fields to camelCase in JSON responses.

/**
 * Type representing a Topic record as it will be returned by your Django API.
 * Directly corresponds to the 'Topic' model in your models.py.
 */
export interface Topic {
  id: number; // models.AutoField(primary_key=True) -> number
  name: string; // models.TextField(null=False) -> string
  subject: string; // models.TextField(null=False) -> string
  icon: string; // models.TextField(null=False) -> string
  chapter: string | null; // models.TextField(null=True, blank=True) -> string or null
}

/**
 * Type representing a Question record as it will be returned by your Django API.
 * Directly corresponds to the 'Question' model in your models.py.
 * Note: 'topic' is a ForeignKey, which DRF usually serializes to the related object's ID by default in ModelSerializer.
 */
export interface Question {
  id: number; // models.AutoField(primary_key=True) -> number
  topic: number; // models.ForeignKey(Topic) -> number (ID of the related Topic)
  question: string; // models.TextField(null=False) -> string
  optionA: string; // models.TextField(null=False) -> string (camelCase from option_a)
  optionB: string; // models.TextField(null=False) -> string (camelCase from option_b)
  optionC: string; // models.TextField(null=False) -> string (camelCase from option_c)
  optionD: string; // models.TextField(null=False) -> string (camelCase from option_d)
  correctAnswer: string; // models.CharField(max_length=1, null=False) -> string (camelCase from correct_answer)
  explanation: string; // models.TextField(null=False) -> string
}

/**
 * Type representing a TestSession record as it will be returned by your Django API.
 * Directly corresponds to the 'TestSession' model in your models.py.
 */
export interface TestSession {
  id: number; // models.AutoField(primary_key=True) -> number
  selectedTopics: string[]; // models.JSONField(null=False) storing string IDs -> string[] (camelCase from selected_topics)
  timeLimit: number | null; // models.IntegerField(null=True, blank=True) -> number or null (camelCase from time_limit)
  questionCount: number | null; // models.IntegerField(null=True, blank=True) -> number or null (camelCase from question_count)
  startTime: string; // models.DateTimeField(null=False) -> string (ISO 8601 format, camelCase from start_time)
  endTime: string | null; // models.DateTimeField(null=True, blank=True) -> string or null (camelCase from end_time)
  isCompleted: boolean; // models.BooleanField(default=False, null=False) -> boolean (camelCase from is_completed)
  totalQuestions: number; // models.IntegerField(null=False) -> number (camelCase from total_questions)
}

/**
 * Type representing a TestAnswer record as it will be returned by your Django API.
 * Directly corresponds to the 'TestAnswer' model in your models.py.
 * Note: 'session' and 'question' are ForeignKeys, typically serialized to IDs.
 */
export interface TestAnswer {
  id: number; // models.AutoField(primary_key=True) -> number
  session: number; // models.ForeignKey(TestSession) -> number (ID of the related TestSession)
  question: number; // models.ForeignKey(Question) -> number (ID of the related Question)
  selectedAnswer: string | null; // models.CharField(max_length=1, null=True, blank=True) -> string or null (camelCase from selected_answer)
  isCorrect: boolean | null; // models.BooleanField(null=True, blank=True) -> boolean or null (camelCase from is_correct)
  markedForReview: boolean; // models.BooleanField(default=False, null=False) -> boolean (camelCase from marked_for_review)
  timeTaken: number | null; // models.IntegerField(null=True, blank=True) -> number or null (camelCase from time_taken)
  answeredAt: string | null; // models.DateTimeField(null=True, blank=True) -> string or null (camelCase from answered_at)
}

/**
 * Type representing a ReviewComment record as it will be returned by your Django API.
 * Directly corresponds to the 'ReviewComment' model in your models.py.
 */
export interface ReviewComment {
  id: number; // models.AutoField(primary_key=True) -> number
  session: number; // models.ForeignKey(TestSession) -> number
  question: number; // models.ForeignKey(Question) -> number
  studentComment: string; // models.TextField(null=False) -> string (camelCase from student_comment)
  createdAt: string; // models.DateTimeField(auto_now_add=True, null=False) -> string (camelCase from created_at)
  updatedAt: string; // models.DateTimeField(auto_now=True, null=False) -> string (camelCase from updated_at)
}

/**
 * Type representing a StudentProfile record as it will be returned by your Django API.
 * Directly corresponds to the 'StudentProfile' model in your models.py.
 */
export interface StudentProfile {
  id: number; // models.AutoField(primary_key=True) -> number
  fullName: string; // models.TextField(null=False) -> string (camelCase from full_name)
  email: string; // models.EmailField(unique=True, null=False) -> string
  phoneNumber: string | null; // models.CharField(max_length=20, null=True, blank=True) -> string or null (camelCase from phone_number)
  dateOfBirth: string | null; // models.DateField(null=True, blank=True) -> string (YYYY-MM-DD) or null (camelCase from date_of_birth)
  schoolName: string | null; // models.TextField(null=True, blank=True) -> string or null (camelCase from school_name)
  targetExamYear: number | null; // models.IntegerField(null=True, blank=True) -> number or null (camelCase from target_exam_year)
  profilePicture: string | null; // models.URLField(null=True, blank=True) -> string or null (camelCase from profile_picture)
  createdAt: string; // models.DateTimeField(auto_now_add=True, null=False) -> string (camelCase from created_at)
  updatedAt: string; // models.DateTimeField(auto_now=True, null=False) -> string (camelCase from updated_at)
}

// You will also need an interface for the request payload when creating a test session
// This must also use camelCase keys, as the parser will convert them to snake_case for Django.
export interface CreateTestSessionRequest {
  selectedTopics: string[]; // Frontend will send string IDs
  timeLimit: number | null;
  questionCount: number | null;
  // If you are sending totalQuestions from the frontend, include it here:
  // totalQuestions: number;
}


// Assuming the response for a test session creation endpoint might look like this
// based on your previous discussion of `CreateTestResponse`
export interface CreateTestSessionResponse {
    session: {
    id: number;
    selectedTopics: string[];
    timeLimit: number;
    questionCount: number;
    totalQuestions: number;
  };
  questions: any[];
}


// If your list endpoints paginate, they might return something like this
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// src/types/dashboard.ts
// This interface describes the shape of the data returned by GET /api/dashboard/analytics
export interface AnalyticsData {
  totalTests: number;
  totalQuestions: number;
  overallAccuracy: number;
  averageScore: number;
  completionRate: number;
  subjectPerformance: {
    subject: string;
    accuracy: number;
    questionsAttempted: number;
    averageTime: number;
    color: string;
  }[];
  chapterPerformance: {
    chapter: string;
    subject: string;
    accuracy: number;
    questionsAttempted: number;
    totalQuestions: number;
    improvement: number;
  }[];
  timeAnalysis: {
    averageTimePerQuestion: number;
    fastestTime: number;
    slowestTime: number;
    timeEfficiency: number;
    rushingTendency: number;
  };
  progressTrend: {
    testNumber: number;
    date: string;
    accuracy: number;
    score: number;
  }[];
  weakAreas: {
    chapter: string;
    subject: string;
    accuracy: number;
    questionsAttempted: number;
    totalQuestions: number;
    improvement: number;
    priority: 'High' | 'Medium' | 'Low';
  }[];
  strengthAreas: {
    chapter: string;
    subject: string;
    accuracy: number;
    questionsAttempted: number;
    totalQuestions: number;
    improvement: number; // Placeholder
    consistency: number; // Placeholder
  }[];
  sessions: any[]; // You might want to define a TestSession interface if this array will contain detailed session objects
  answers: any[];   // You might want to define a TestAnswer interface if this array will contain detailed answer objects
  questions: any[]; // You might want to define a Question interface if this array will contain detailed question objects
  totalTimeSpent: number;
}

