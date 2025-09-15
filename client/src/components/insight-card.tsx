// Type definitions for analytics and insights data
// These types are used by home.tsx and practice-arena.tsx

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
        speedCategory?: string;
        accuracyCategory?: string;
        recommendation?: string;
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
        questions?: number;
        avgTime?: number;
    }>;
    timeBasedTrends: Array<{
        date: string;
        averageScore?: number;
    }>;
    subjectTrends?: { [subject: string]: Array<{
        date: string;
        accuracy: number;
        questionsAttempted: number;
        testNumber?: number;
    }> };
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
    studyRecommendations: string[];
    message?: string;
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
        lastTestTopics: Array<{
            topic: string;
            accuracy: number;
            avgTimeSec: number;
            subject: string;
            chapter: string;
            attempted: number;
        }>;
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
            lastTestFeedback?: {
                status: string;
                message: string;
                insights: string[];
            };
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
