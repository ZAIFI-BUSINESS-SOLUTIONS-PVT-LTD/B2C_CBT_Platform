// frontend/src/types/api.ts

// IMPORTANT: These types assume that 'djangorestframework-camel-case' is correctly
// configured in your Django backend's settings.py, which will automatically
// convert snake_case model fields to camelCase in JSON responses.

/**
 * Type representing a StudentProfile record as it will be returned by your Django API.
 * Directly corresponds to the 'StudentProfile' model in your models.py.
 */
export interface StudentProfile {
  studentId: string; // models.CharField(max_length=20, primary_key=True) -> string (camelCase from student_id)
  fullName: string; // models.TextField(null=False) -> string (camelCase from full_name)
  email: string; // models.EmailField(unique=True, null=False) -> string
  phoneNumber: string | null; // models.CharField(max_length=20, null=True, blank=True) -> string or null (camelCase from phone_number)
  dateOfBirth: string; // models.DateField(null=False) -> string (YYYY-MM-DD format, camelCase from date_of_birth)
  schoolName: string | null; // models.TextField(null=True, blank=True) -> string or null (camelCase from school_name)
  targetExamYear: number | null; // models.IntegerField(null=True, blank=True) -> number or null (camelCase from target_exam_year)
  isActive: boolean; // models.BooleanField(default=True) -> boolean (camelCase from is_active)
  isVerified: boolean; // models.BooleanField(default=False) -> boolean (camelCase from is_verified)
  lastLogin: string | null; // models.DateTimeField(null=True, blank=True) -> string or null (camelCase from last_login)
  createdAt: string; // models.DateTimeField(auto_now_add=True) -> string (camelCase from created_at)
  updatedAt: string; // models.DateTimeField(auto_now=True) -> string (camelCase from updated_at)
}

/**
 * Authentication state for the application
 */
export interface AuthState {
  isAuthenticated: boolean;
  student: StudentProfile | null;
}

/**
 * Login credentials for student authentication
 */
export interface LoginCredentials {
  email: string;
  password: string;
}

/**
 * Login response from the API (JWT)
 */
export interface LoginResponse {
  access: string;
  refresh: string;
  student: StudentProfile;
}

/**
 * Basic login response (session-based)
 */
export interface BasicLoginResponse {
  message: string;
  student: StudentProfile;
}

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
 * Type representing a PlatformTest record as it will be returned by your Django API.
 * Directly corresponds to the 'PlatformTest' model in your models.py.
 */
export interface PlatformTest {
  id: number; // models.AutoField(primary_key=True) -> number
  testName: string; // models.TextField(null=False) -> string (camelCase from test_name)
  testCode: string; // models.CharField(max_length=50, unique=True, null=False) -> string (camelCase from test_code)
  testYear: number | null; // models.IntegerField(null=True, blank=True) -> number or null (camelCase from test_year)
  testType: string | null; // models.TextField(null=True, blank=True) -> string or null (camelCase from test_type)
  description: string | null; // models.TextField(null=True, blank=True) -> string or null
  instructions: string | null; // models.TextField(null=True, blank=True) -> string or null
  timeLimit: number; // models.IntegerField(null=False) -> number (camelCase from time_limit)
  totalQuestions: number; // models.IntegerField(null=False) -> number (camelCase from total_questions)
  selectedTopics: number[]; // models.JSONField(null=False) -> number[] (camelCase from selected_topics)
  questionDistribution: any | null; // models.JSONField(null=True, blank=True) -> any or null (camelCase from question_distribution)
  isActive: boolean; // models.BooleanField(default=True) -> boolean (camelCase from is_active)
  createdAt: string; // models.DateTimeField(auto_now_add=True, null=False) -> string (camelCase from created_at)
  updatedAt: string; // models.DateTimeField(auto_now=True, null=False) -> string (camelCase from updated_at)
  scheduledDateTime: string | null; // models.DateTimeField(null=True, blank=True) -> string or null (camelCase from scheduled_date_time)
  // Computed properties
  isScheduled: boolean; // Whether this test has a scheduled date/time
  isAvailable: boolean; // Whether this test is currently available to attempt
  availabilityStatus: 'scheduled' | 'open' | 'expired'; // Status of the test
  // Per-student computed flags returned by the available-tests endpoint
  hasCompleted?: boolean; // Whether the currently-authenticated student has completed this test
  hasActiveSession?: boolean; // Whether the currently-authenticated student has an active session for this test
}

/**
 * Type for available platform tests list response
 */
export interface AvailablePlatformTestsResponse {
  scheduledTests: PlatformTest[];
  openTests: PlatformTest[];
}

/**
 * Type for starting a platform test
 */
export interface StartPlatformTestRequest {
  testId: number;
}

/**
 * Type for platform test start response
 */
export interface StartPlatformTestResponse {
  session: TestSession;
  questions: Question[];
  testDetails: PlatformTest;
}

/**
 * Type representing a TestSession record as it will be returned by your Django API.
 * Directly corresponds to the 'TestSession' model in your models.py.
 */
export interface TestSession {
  id: number; // models.AutoField(primary_key=True) -> number
  studentId: string; // models.CharField(max_length=20, null=False) -> string (camelCase from student_id)
  testType: 'custom' | 'platform'; // models.CharField(choices=[('custom', 'Custom Test'), ('platform', 'Platform Test')]) (camelCase from test_type)
  platformTest: number | null; // models.ForeignKey(PlatformTest) -> number or null (camelCase from platform_test)
  selectedTopics: string[]; // models.JSONField(null=False) storing string IDs -> string[] (camelCase from selected_topics)
  physicsTopics: string[]; // models.JSONField(default=list, blank=True) -> string[] (camelCase from physics_topics)
  chemistryTopics: string[]; // models.JSONField(default=list, blank=True) -> string[] (camelCase from chemistry_topics)
  botanyTopics: string[]; // models.JSONField(default=list, blank=True) -> string[] (camelCase from botany_topics)
  zoologyTopics: string[]; // models.JSONField(default=list, blank=True) -> string[] (camelCase from zoology_topics)
  timeLimit: number | null; // models.IntegerField(null=True, blank=True) -> number or null (camelCase from time_limit)
  questionCount: number | null; // models.IntegerField(null=True, blank=True) -> number or null (camelCase from question_count)
  startTime: string; // models.DateTimeField(null=False) -> string (ISO 8601 format, camelCase from start_time)
  endTime: string | null; // models.DateTimeField(null=True, blank=True) -> string or null (camelCase from end_time)
  isCompleted: boolean; // models.BooleanField(default=False, null=False) -> boolean (camelCase from is_completed)
  totalQuestions: number; // models.IntegerField(null=False) -> number (camelCase from total_questions)
  correctAnswers: number; // models.IntegerField(default=0) -> number (camelCase from correct_answers)
  incorrectAnswers: number; // models.IntegerField(default=0) -> number (camelCase from incorrect_answers)
  unanswered: number; // models.IntegerField(default=0) -> number
  totalTimeTaken: number | null; // models.IntegerField(null=True, blank=True) -> number or null (camelCase from total_time_taken)
  physicsScore: number | null; // models.FloatField(null=True, blank=True) -> number or null (camelCase from physics_score)
  chemistryScore: number | null; // models.FloatField(null=True, blank=True) -> number or null (camelCase from chemistry_score)
  botanyScore: number | null; // models.FloatField(null=True, blank=True) -> number or null (camelCase from botany_score)
  zoologyScore: number | null; // models.FloatField(null=True, blank=True) -> number or null (camelCase from zoology_score)
}

/**
 * Type for creating a new test session
 */
export interface CreateTestSessionRequest {
  studentId: string; // Required: Student ID for authentication
  selectedTopics: string[]; // Required: Array of topic IDs
  timeLimit?: number; // Optional: Time limit in minutes
  questionCount?: number; // Optional: Number of questions
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

// You will also need an interface for the request payload when creating a test session
// This must also use camelCase keys, as the parser will convert them to snake_case for Django.


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

/**
 * Platform Test Analytics Data
 */
export interface PlatformTestAnalyticsData {
  availableTests: Array<{
    id: number;
    testName: string;
    testCode: string;
    testYear: number | null;
    testType: string | null;
  }>;
  selectedTestMetrics: {
    testId: number;
    testName: string;
    testCode: string;
    overallAccuracy: number;
    rank: number | null;
    totalStudents: number;
    percentile: number | null;
    avgTimePerQuestion: number;
    sessionId?: number;
    testDate?: string;
    message?: string;
    error?: string;
    // Optional leaderboard of top performers for this test
    leaderboard?: Array<{
      studentId?: string;
      studentName: string;
      overallAccuracy: number | null;
      physics?: number | null;
      chemistry?: number | null;
      botany?: number | null;
      zoology?: number | null;
      timeTakenSec?: number | null;
      rank?: number | null;
    }>;
  } | null;
}

