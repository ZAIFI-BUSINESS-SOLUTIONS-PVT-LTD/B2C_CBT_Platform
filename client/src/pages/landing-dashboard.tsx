/**
 * Landing Dashboard Page
 * 
 * This is the main dashboard page showing comprehensive student performance analytics.
 * Features include:
 * - Overall performance metrics and trends
 * - Calendar view showing test history and performance
 * - Subject-wise performance charts and analytics
 * - Speed vs accuracy analysis
 * - Strength and weakness identification
 * - Personalized study recommendations
 * - Performance calendar with daily/weekly insights
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { useLocation, Link } from "wouter";
import { useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Calendar } from "@/components/ui/calendar";
import { Separator } from "@/components/ui/separator";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  LineChart,
  Line,
  Area,
  AreaChart
} from 'recharts';
import { Label } from 'recharts';
import { 
  Target, 
  TrendingUp, 
  Clock, 
  Award, 
  BookOpen,
  Calendar as CalendarIcon,
  BarChart3,
  AlertCircle,
  CheckCircle,
  Zap,
  Brain,
  Home,
  PlusCircle,
  Users,
  Trophy,
  Activity,
  Star,
  ArrowRight,
  ChevronRight,
  Timer,
  Lightbulb,
  MessageCircle
} from "lucide-react";
import { StudentProfile } from "@/components/student-profile";

// Color scheme for charts
const COLORS = {
  primary: '#3B82F6',
  success: '#10B981',
  warning: '#F59E0B',
  danger: '#EF4444',
  purple: '#8B5CF6',
  indigo: '#6366F1',
  teal: '#14B8A6',
  pink: '#EC4899'
};
interface AnalyticsData {
  totalTests: number;
  totalQuestions: number;
  overallAccuracy: number;
  totalTimeSpent: number;
  averageTimePerQuestion: number;
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
  studyRecommendations: string[]; // Or Array<{ priority: string; subject: string; reason: string; actionTip: string; }> if detailed
  message?: string; // For the "Take more tests" message
}

interface InsightsData {
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

const CHART_COLORS = [COLORS.primary, COLORS.success, COLORS.warning, COLORS.purple];

/**
 * Main Landing Dashboard Component
 */
export default function LandingDashboard() {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const { isAuthenticated, loading } = useAuth();
  const [, navigate] = useLocation();

  // === NAVIGATION GUARD ===
  // Redirect to home page when user tries to navigate back from landing dashboard
  useEffect(() => {
    const handlePopState = (e: PopStateEvent) => {
      e.preventDefault();
      console.log('🔄 Back navigation detected from Landing Dashboard page, redirecting to home...');
      navigate('/', { replace: true });
    };

    // Push current state and listen for back navigation
    window.history.pushState(null, '', window.location.href);
    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, [navigate]);

  // Redirect to home if not authenticated
  if (!loading && !isAuthenticated) {
    navigate('/');
    return null;
  }

  // Fetch comprehensive analytics data
  const { data: analytics, isLoading, error } = useQuery<AnalyticsData>({
    queryKey: ['/api/dashboard/comprehensive-analytics/'],
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: isAuthenticated && !loading, // Only run when authenticated
  });

  // Fetch insights data directly from cache file
  const { data: insights, isLoading: insightsLoading, error: insightsError } = useQuery<InsightsData>({
    queryKey: ['/api/insights/cache/'],
    refetchInterval: 30000, // Refresh every 30 seconds for real-time updates
    enabled: isAuthenticated && !loading, // Only run when authenticated
  });



  if (isLoading || insightsLoading) {
    return <DashboardSkeleton />;
  }

  if (error || !analytics) {
    return <ErrorState />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50">
      {/* Header with Navigation */}
      <header className="bg-white/95 backdrop-blur-sm border-b border-blue-100 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button 
                variant="ghost" 
                className="flex items-center gap-2 text-[#64748B] hover:text-[#1F2937] hover:bg-[#F8FAFC]"
                onClick={() => navigate('/')}
              >
                <Home className="h-4 w-4" />
                Home
              </Button>
              <Separator orientation="vertical" className="h-6 bg-[#E2E8F0]" />
              <div className="flex items-center space-x-2">
                <BarChart3 className="h-6 w-6 text-[#4F83FF]" />
                <h1 className="text-xl font-medium text-[#1F2937]">Performance Dashboard</h1>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <Button 
                variant="outline" 
                className="shadow-sm border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC]"
                onClick={() => navigate('/chatbot')}
              >
                <MessageCircle className="h-4 w-4 mr-2" />
                AI Tutor
              </Button>
              <Button 
                className="bg-[#4F83FF] hover:bg-[#3B82F6] text-white shadow-md"
                onClick={() => navigate('/topics')}
              >
                <PlusCircle className="h-4 w-4 mr-2" />
                Take New Test
              </Button>
              <StudentProfile />
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-[#1F2937] mb-2">
            Welcome back, NEET Warrior! 🎯
          </h2>
          <p className="text-lg text-[#6B7280]">
            Track your progress and optimize your NEET preparation with detailed analytics
          </p>
        </div>

  {/* Insights Container */}
  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-6 mb-8" style={{gridAutoRows: '1fr'}}>
          
          <InsightCard
            title="Study Plan"
            description="AI-generated personalized study recommendations."
            icon={<Activity className="h-6 w-6" />}
            isLocked={false}
            lockMessage=""
          >
            <div className="mt-2 space-y-3">
              {insights?.data?.llmInsights?.studyPlan?.insights ? (
                <div className="space-y-2">
                  {insights.data.llmInsights.studyPlan.insights.map((insight: string, idx: number) => (
                    <div key={idx} className="p-3 bg-blue-50 rounded-lg border-l-4 border-blue-400">
                      <p className="text-sm text-blue-800">{insight}</p>
                    </div>
                  ))}
                  <div className="mt-2">
                    {insights.cacheInfo && (
                      <p className="text-xs text-gray-500">
                        Updated: {insights.cacheInfo.lastModified ? new Date(insights.cacheInfo.lastModified).toLocaleString() : 'N/A'}
                      </p>
                    )}
                  </div>
                </div>
              ) : insights?.data?.improvementTopics && insights.data.improvementTopics.length > 0 ? (
                <div>
                  <p className="text-sm text-blue-700 mb-2">Recommended focus areas:</p>
                  <ul className="space-y-1 text-sm">
                    {insights.data.improvementTopics.slice(0, 3).map((topic: any, idx: number) => (
                      <li key={idx} className="flex justify-between">
                        <span className="truncate mr-2">{topic.topic}</span>
                        <span className="font-semibold text-blue-600">{topic.accuracy.toFixed(1)}%</span>
                      </li>
                    ))}
                  </ul>
                  {insights.cacheInfo && (
                    <p className="text-xs text-gray-500 mt-2">
                      Cache: {insights.cacheInfo.lastModified ? new Date(insights.cacheInfo.lastModified).toLocaleString() : 'N/A'}
                    </p>
                  )}
                </div>
              ) : insights?.data?.weakTopics && insights.data.weakTopics.length > 0 ? (
                <div>
                  <p className="text-sm text-blue-700 mb-2">Focus on improving these areas:</p>
                  <ul className="space-y-1 text-sm">
                    {insights.data.weakTopics.slice(0, 2).map((topic: any, idx: number) => (
                      <li key={idx} className="flex justify-between">
                        <span className="truncate mr-2">{topic.topic}</span>
                        <span className="font-semibold text-blue-600">{topic.accuracy.toFixed(1)}%</span>
                      </li>
                    ))}
                  </ul>
                  {insights.cacheInfo && (
                    <p className="text-xs text-gray-500 mt-2">
                      Cache: {insights.cacheInfo.lastModified ? new Date(insights.cacheInfo.lastModified).toLocaleString() : 'N/A'}
                    </p>
                  )}
                </div>
              ) : (
                <div className="p-3 bg-blue-50 rounded-lg border-l-4 border-blue-400">
                  <p className="text-sm text-blue-800">Take some tests to get AI-generated study plans!</p>
                </div>
              )}
            </div>
          </InsightCard>
          <InsightCard
            title="Last Test Feedback"
            description="AI feedback on your most recent test performance."
            icon={<Brain className="h-6 w-6" />}
            isLocked={false}
            lockMessage=""
          >
            <div className="mt-2 space-y-3">
              {insights?.data?.llmInsights?.lastTestFeedback?.insights ? (
                <div className="space-y-2">
                  {insights.data.llmInsights.lastTestFeedback.insights.map((insight: string, idx: number) => (
                    <div key={idx} className="p-3 bg-purple-50 rounded-lg border-l-4 border-purple-400">
                      <p className="text-sm text-purple-800">{insight}</p>
                    </div>
                  ))}
                  <div className="mt-2">
                    {insights.cacheInfo && (
                      <p className="text-xs text-gray-500">
                        Updated: {insights.cacheInfo.lastModified ? new Date(insights.cacheInfo.lastModified).toLocaleString() : 'N/A'}
                      </p>
                    )}
                  </div>
                </div>
              ) : insights?.data?.lastTestTopics && insights.data.lastTestTopics.length > 0 ? (
                <div>
                  <p className="text-sm text-purple-700 mb-2">Recent test performance:</p>
                  <ul className="space-y-1 text-sm">
                    {insights.data.lastTestTopics.slice(0, 3).map((topic: any, idx: number) => (
                      <li key={idx} className="flex justify-between">
                        <span className="truncate mr-2">{topic.topic}</span>
                        <span className="font-semibold text-purple-600">{topic.accuracy.toFixed(1)}%</span>
                      </li>
                    ))}
                  </ul>
                  {insights.cacheInfo && (
                    <p className="text-xs text-gray-500 mt-2">
                      Cache: {insights.cacheInfo.lastModified ? new Date(insights.cacheInfo.lastModified).toLocaleString() : 'N/A'}
                    </p>
                  )}
                </div>
              ) : (
                <div className="p-3 bg-purple-50 rounded-lg border-l-4 border-purple-400">
                  <p className="text-sm text-purple-800">Complete a test to get AI feedback on your performance!</p>
                </div>
              )}
            </div>
          </InsightCard>
          <InsightCard
            title="Strengths"
            description="AI insights on your strongest topics."
            icon={<Star className="h-6 w-6" />}
            isLocked={!analytics || analytics.totalTests === 0}
            lockMessage="Complete practice tests to unlock your strengths!"
          >
            <div className="mt-2 space-y-3">
              {insights?.data?.llmInsights?.strengths?.insights ? (
                <div className="space-y-2">
                  {insights.data.llmInsights.strengths.insights.map((insight: string, idx: number) => (
                    <div key={idx} className="p-3 bg-green-50 rounded-lg border-l-4 border-green-400">
                      <p className="text-sm text-green-800">{insight}</p>
                    </div>
                  ))}
                  <div className="mt-2">
                    {insights.cacheInfo && (
                      <p className="text-xs text-gray-500">
                        Updated: {insights.cacheInfo.lastModified ? new Date(insights.cacheInfo.lastModified).toLocaleString() : 'N/A'}
                      </p>
                    )}
                  </div>
                </div>
              ) : insights?.data?.strengthTopics && insights.data.strengthTopics.length > 0 ? (
                <div>
                  <p className="text-sm text-green-700 mb-2">Your top performing topics:</p>
                  <ul className="space-y-1 text-sm">
                    {insights.data.strengthTopics.slice(0, 3).map((topic: any, idx: number) => (
                      <li key={idx} className="flex justify-between">
                        <span className="truncate mr-2">{topic.topic}</span>
                        <span className="font-semibold text-green-600">{topic.accuracy.toFixed(1)}%</span>
                      </li>
                    ))}
                  </ul>
                  {insights.cacheInfo && (
                    <p className="text-xs text-gray-500 mt-2">
                      Cache: {insights.cacheInfo.lastModified ? new Date(insights.cacheInfo.lastModified).toLocaleString() : 'N/A'}
                    </p>
                  )}
                </div>
              ) : (
                <div className="p-3 bg-green-50 rounded-lg border-l-4 border-green-400">
                  <p className="text-sm text-green-800">Take some tests to get AI analysis of your strengths!</p>
                </div>
              )}
            </div>
          </InsightCard>
          <InsightCard
            title="Weaknesses"
            description="AI insights on areas needing improvement."
            icon={<AlertCircle className="h-6 w-6" />}
            isLocked={false}
            lockMessage=""
          >
            <div className="mt-2 space-y-3">
              {insights?.data?.llmInsights?.weaknesses?.insights ? (
                <div className="space-y-2">
                  {insights.data.llmInsights.weaknesses.insights.map((insight: string, idx: number) => (
                    <div key={idx} className="p-3 bg-red-50 rounded-lg border-l-4 border-red-400">
                      <p className="text-sm text-red-800">{insight}</p>
                    </div>
                  ))}
                  <div className="mt-2">
                    {insights.cacheInfo && (
                      <p className="text-xs text-gray-500">
                        Updated: {insights.cacheInfo.lastModified ? new Date(insights.cacheInfo.lastModified).toLocaleString() : 'N/A'}
                      </p>
                    )}
                  </div>
                </div>
              ) : insights?.data?.weakTopics && insights.data.weakTopics.length > 0 ? (
                <div>
                  <p className="text-sm text-red-700 mb-2">Topics needing focus:</p>
                  <ul className="space-y-1 text-sm">
                    {insights.data.weakTopics.slice(0, 3).map((topic: any, idx: number) => (
                      <li key={idx} className="flex justify-between">
                        <span className="truncate mr-2">{topic.topic}</span>
                        <span className="font-semibold text-red-600">{topic.accuracy.toFixed(1)}%</span>
                      </li>
                    ))}
                  </ul>
                  {insights.cacheInfo && (
                    <p className="text-xs text-gray-500 mt-2">
                      Cache: {insights.cacheInfo.lastModified ? new Date(insights.cacheInfo.lastModified).toLocaleString() : 'N/A'}
                    </p>
                  )}
                </div>
              ) : (
                <div className="p-3 bg-red-50 rounded-lg border-l-4 border-red-400">
                  <p className="text-sm text-red-800">Take some tests to get AI analysis of your weaknesses!</p>
                </div>
              )}
            </div>
          </InsightCard>
        </div>

        {/* Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total Tests"
            value={analytics.totalTests}
            icon={<Trophy className="h-5 w-5" />}
            color="bg-[#4F83FF]"
          />
          <MetricCard
            title="Overall Accuracy"
            value={`${analytics.overallAccuracy.toFixed(1)}%`}
            icon={<Target className="h-5 w-5" />}
            color="bg-[#8B5CF6]"
          />
          <MetricCard
            title="Avg. Speed"
            value={`${Math.round(analytics.averageTimePerQuestion)}s`}
            icon={<Timer className="h-5 w-5" />}
            color="bg-[#F59E0B]"
          />
        </div>

        {/* Main Dashboard Content */}
        <div className="w-full">
          {/* Performance Overview - Full Width */}
          <div className="w-full space-y-6">
            {/* Performance Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Performance Overview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="subjects" className="w-full">
                  <TabsList className="grid w-full grid-cols-2 max-w-md mx-auto">
                    <TabsTrigger value="subjects">Subjects</TabsTrigger>
                    <TabsTrigger value="trends">Trends</TabsTrigger>
                  </TabsList>
                  <TabsContent value="subjects" className="space-y-4">
                    <SubjectPerformanceChart data={analytics.subjectPerformance} />
                  </TabsContent>
                  <TabsContent value="trends" className="space-y-4">
                    <PerformanceTrendsChart data={analytics.timeBasedTrends} />
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Insight Card Component
 */
interface InsightCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  isLocked: boolean;
  lockMessage?: string;
  children?: React.ReactNode;
}

function InsightCard({ title, description, icon, isLocked, lockMessage, children }: InsightCardProps) {
  const [showLockModal, setShowLockModal] = useState(false);
  const [, navigate] = useLocation();

  const handleClick = () => {
    if (isLocked) {
      setShowLockModal(true);
    }
  };

  return (
    <>
      <div className="relative">
        <div
          onClick={handleClick}
          className="p-6 rounded-2xl shadow-lg border-2 border-[#4F83FF]/20 transition-all duration-300 bg-[#E8F0FF] hover:bg-[#DBEAFE] hover:shadow-xl cursor-pointer"
        >
          <div className="flex items-center space-x-4">
            <div className="p-3 rounded-full bg-[#4F83FF] text-white shadow-md">
              {icon}
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-bold text-[#1F2937]">
                {title}
              </h3>
              <p className="text-sm text-[#6B7280]">
                {description}
              </p>
            </div>
          </div>
          
          {/* Content container - only this part gets blurred */}
          <div className="mt-4 relative">
            {!isLocked && children ? (
              <div className="min-h-32 bg-white rounded-lg p-3 border border-[#E2E8F0]">
                {children}
              </div>
            ) : (
              <div className="h-32 bg-white rounded-lg flex items-center justify-center border border-[#E2E8F0]">
                <p className="text-[#94A3B8] text-sm">
                  {isLocked ? "Complete tests to unlock insights" : "Coming soon..."}
                </p>
              </div>
            )}
            
            {isLocked && (
              <div className="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur-sm rounded-lg z-10">
                <div className="text-center px-4">
                  <AlertCircle className="h-8 w-8 text-[#4F83FF] mx-auto mb-2" />
                  <p className="text-[#1F2937] font-medium">
                    Take tests to unlock
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Lock Modal */}
      {showLockModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-md mx-4 border-2 border-blue-200">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Target className="h-8 w-8 text-blue-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">
                Insights Locked
              </h3>
              <p className="text-gray-600 mb-6">
                {lockMessage || "Complete practice tests to unlock detailed insights and analytics!"}
              </p>
              <div className="flex space-x-3">
                <Button
                  variant="outline"
                  onClick={() => setShowLockModal(false)}
                  className="flex-1"
                >
                  Close
                </Button>
                <Button
                  onClick={() => {
                    setShowLockModal(false);
                    navigate('/topics');
                  }}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                >
                  Take Test
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/**
 * Metric Card Component
 */
interface MetricCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
}

function MetricCard({ title, value, icon, color }: MetricCardProps) {
  return (
    <Card className="bg-white shadow-md border border-[#E2E8F0] hover:shadow-lg transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-[#6B7280]">{title}</p>
            <p className="text-2xl font-bold text-[#1F2937]">{value}</p>
          </div>
          <div className={`p-3 rounded-full ${color} text-white shadow-md`}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Subject Performance Chart Component
 */
function SubjectPerformanceChart({ data }: { data: any[] }) {
  const chartData = data.map(item => ({
    subject: item.subject,
    accuracy: item.accuracy,
    questions: item.totalQuestions,
    avgTime: item.avgTimePerQuestion
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="subject">
            <Label value="Subject" offset={-5} position="insideBottom" />
          </XAxis>
          <YAxis>
            <Label value="Accuracy (%)" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />
          </YAxis>
          <Tooltip />
          <Bar dataKey="accuracy" fill={COLORS.primary} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Performance Trends Chart Component
 */
function PerformanceTrendsChart({ data }: { data: any[] }) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date">
            <Label value="Date" offset={-5} position="insideBottom" />
          </XAxis>
          <YAxis>
            <Label value="Accuracy (%)" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />
          </YAxis>
          <Tooltip />
          <Line type="monotone" dataKey="accuracy" stroke={COLORS.primary} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Speed Analysis Card Component
 */
function SpeedAnalysisCard({ speedData }: { speedData: any }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="text-center p-4 bg-blue-50 rounded-lg">
          <div className="text-2xl font-bold text-blue-600">
            {speedData.speedCategory}
          </div>
          <div className="text-sm text-gray-600">Speed Rating</div>
        </div>
        <div className="text-center p-4 bg-green-50 rounded-lg">
          <div className="text-2xl font-bold text-green-600">
            {speedData.accuracyCategory}
          </div>
          <div className="text-sm text-gray-600">Accuracy Rating</div>
        </div>
      </div>
      <div className="bg-gray-50 p-4 rounded-lg">
        <h4 className="font-medium mb-2">Recommendation</h4>
        <p className="text-sm text-gray-600">{speedData.recommendation}</p>
      </div>
    </div>
  );
}

/**
 * Strengths Card Component
 */
function StrengthsCard({ strengths }: { strengths: any[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-green-600">
          <CheckCircle className="h-5 w-5" />
          Your Strengths
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {strengths.slice(0, 3).map((strength, index) => (
            <div key={index} className="flex items-center justify-between">
              <span className="text-sm font-medium">{strength.subject}</span>
              <Badge variant="outline" className="text-green-600">
                {strength.accuracy.toFixed(1)}%
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Weaknesses Card Component
 */
function WeaknessesCard({ weaknesses }: { weaknesses: any[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-orange-600">
          <AlertCircle className="h-5 w-5" />
          Areas to Improve
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {weaknesses.slice(0, 3).map((weakness, index) => (
            <div key={index} className="flex items-center justify-between">
              <span className="text-sm font-medium">{weakness.subject}</span>
              <Badge variant="outline" className="text-orange-600">
                {weakness.accuracy.toFixed(1)}%
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Study Recommendations Card Component
 */
function StudyRecommendationsCard({ recommendations }: { recommendations: any[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5" />
          Study Recommendations
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {recommendations.map((rec, index) => (
            <div key={index} className="border-l-4 border-blue-500 pl-4">
              <div className="flex items-center gap-2 mb-1">
                <Badge variant={rec.priority === 'High' ? 'destructive' : 
                              rec.priority === 'Medium' ? 'default' : 'secondary'}>
                  {rec.priority}
                </Badge>
                <span className="font-medium">{rec.subject}</span>
              </div>
              <p className="text-sm text-gray-600 mb-2">{rec.reason}</p>
              <p className="text-sm font-medium text-blue-600">{rec.actionTip}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Dashboard Loading Skeleton
 */
function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="animate-pulse space-y-6">
          <div className="h-12 bg-gray-200 rounded-lg w-1/3"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 h-96 bg-gray-200 rounded-lg"></div>
            <div className="h-96 bg-gray-200 rounded-lg"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Error State Component
 */
function ErrorState() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <Card className="max-w-md w-full">
        <CardContent className="p-8 text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Unable to Load Dashboard</h3>
          <p className="text-gray-600 mb-4">
            Take a practice test first to see your performance analytics.
          </p>
          <Link href="/topics">
            <Button>
              Take Your First Test
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}