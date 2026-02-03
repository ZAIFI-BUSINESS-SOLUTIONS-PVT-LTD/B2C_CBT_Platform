export interface AnalyticsData {
  totalTests: number;
  totalQuestions: number;
  overallAccuracy: number;
  totalTimeSpent: number;
  averageTimePerQuestion: number;
  uniqueQuestionsAttempted?: number;
  totalQuestionsInBank?: number;
  speedVsAccuracy: {
    fastButInaccurate: number;
    slowButAccurate: number;
    idealPace: number;
    speedCategory?: string; // Add if backend eventually provides these
    accuracyCategory?: string; // Add if backend eventually provides these
    recommendation?: string; // Add if backend eventually provides these
  };
  strengthAreas: Array<{
    subject: string;
    accuracy: number;
  }>;
  challengingAreas: Array<{
    subject: string;
    accuracy: number;
  }>;
  subjectPerformance: Array<{
    subject: string;
    accuracy: number;
    questions?: number; // These were in chartData, but not explicitly in backend response
    avgTime?: number; // These were in chartData, but not explicitly in backend response
  }>;
  timeBasedTrends: Array<{
    date: string; // ISO format date string
    // averageScore removed: field no longer exists
  }>;
  subjectAccuracyPast7?: Array<{
    subject: string;
    totalQuestions: number;
    correctAnswers: number;
    accuracy: number;
  }>;
  topicPerformance?: Array<{
    topicId?: number | string;
    topic: string;
    subject: string;
    totalQuestions: number;
    correctAnswers: number;
    accuracy: number;
  }>;
  timeDistributionPast7?: {
    overall: Array<{ status: string; timeSec: number; avgTimeSec?: number }>;
    bySubject: { [subject: string]: Array<{ status: string; timeSec: number; avgTimeSec?: number }> };
    subjects: string[];
  };
  studyRecommendations: string[]; // Or Array<{ priority: string; subject: string; reason: string; actionTip: string; }> if detailed
  message?: string; // For the "Take more tests" message
}

export interface InsightsData {
  status: string;
  data: {
    strengthTopics: Array<{
      topic: string;
      accuracy: number;
      avgTimeSec: number;
      subject: string;
      chapter: string;
    }>;
    weakTopics: Array<{
      topic: string;
      accuracy: number;
      avgTimeSec: number;
      subject: string;
      chapter: string;
    }>;
    improvementTopics: Array<{
      topic: string;
      accuracy: number;
      avgTimeSec: number;
      subject: string;
      chapter: string;
    }>;
    // lastTestTopics removed: backend no longer provides last-test topic list
    llmInsights: {
      strengths?: {
        status: string;
        message: string;
        insights: string[];
      };
      weaknesses?: {
        status: string;
        message: string;
        insights: string[];
      };
      studyPlan?: {
        status: string;
        message: string;
        insights: string[];
      };
      // lastTestFeedback removed: backend no longer provides last-test LLM feedback
    };
    summary: {
      totalTopicsAnalyzed: number;
      totalTestsTaken: number;
      strengthsCount: number;
      weaknessesCount: number;
      improvementsCount: number;
      overallAvgTime?: number;
      lastSessionId?: number;
    };
    cached?: boolean;
    thresholdsUsed?: any;
  };
  cacheInfo?: {
    fileExists: boolean;
    fileSize: number;
    lastModified: string | null;
  };
  cached?: boolean;
}

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
    leaderboard?: Array<{
      studentId: string;
      studentName: string;
      accuracy: number;
      physics?: number | null;
      chemistry?: number | null;
      botany?: number | null;
      zoology?: number | null;
      timeTakenSec: number;
      rank: number;
    }>;
    subjectAccuracyForTest?: Array<{
      subject: string;
      accuracy: number | null;
      totalQuestions: number;
    }>;
    timeDistributionForTest?: {
      overall: Array<{ status: string; timeSec: number }>;
      bySubject: { [subject: string]: Array<{ status: string; timeSec: number }> };
      subjects: string[];
    };
  } | null;
}
