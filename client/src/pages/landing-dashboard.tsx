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
import { useLocation } from "wouter";
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
  Lightbulb
} from "lucide-react";
import { Link } from "wouter";
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
const CHART_COLORS = [COLORS.primary, COLORS.success, COLORS.warning, COLORS.purple];

/**
 * Main Landing Dashboard Component
 */
export default function LandingDashboard() {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const { isAuthenticated, loading } = useAuth();
  const [, navigate] = useLocation();

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

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error || !analytics) {
    return <ErrorState />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Header with Navigation */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/">
                <Button variant="ghost" className="flex items-center gap-2">
                  <Home className="h-4 w-4" />
                  Home
                </Button>
              </Link>
              <Separator orientation="vertical" className="h-6" />
              <div className="flex items-center space-x-2">
                <BarChart3 className="h-6 w-6 text-blue-600" />
                <h1 className="text-2xl font-bold text-gray-900">Performance Dashboard</h1>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <Link href="/topics">
                <Button className="bg-blue-600 hover:bg-blue-700 text-white">
                  <PlusCircle className="h-4 w-4 mr-2" />
                  Take New Test
                </Button>
              </Link>
              <StudentProfile />
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            Welcome back, NEET Warrior! 🎯
          </h2>
          <p className="text-lg text-gray-600">
            Track your progress and optimize your NEET preparation with detailed analytics
          </p>
        </div>

        {/* Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total Tests"
            value={analytics.totalTests}
            icon={<Trophy className="h-5 w-5" />}
            color="bg-blue-500"
          />
          <MetricCard
            title="Questions Attempted"
            value={analytics.totalQuestions}
            icon={<BookOpen className="h-5 w-5" />}
            color="bg-green-500"
          />
          <MetricCard
            title="Overall Accuracy"
            value={`${analytics.overallAccuracy.toFixed(1)}%`}
            icon={<Target className="h-5 w-5" />}
            color="bg-purple-500"
          />
          <MetricCard
            title="Avg. Speed"
            value={`${Math.round(analytics.averageTimePerQuestion)}s`}
            icon={<Timer className="h-5 w-5" />}
            color="bg-orange-500"
          />
        </div>

        {/* Main Dashboard Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Charts and Analytics */}
          <div className="lg:col-span-2 space-y-6">
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
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="subjects">Subjects</TabsTrigger>
                    <TabsTrigger value="trends">Trends</TabsTrigger>
                    <TabsTrigger value="speed">Speed Analysis</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="subjects" className="space-y-4">
                    <SubjectPerformanceChart data={analytics.subjectPerformance} />
                  </TabsContent>
                  
                  <TabsContent value="trends" className="space-y-4">
                    <PerformanceTrendsChart data={analytics.timeBasedTrends} />
                  </TabsContent>
                  
                  <TabsContent value="speed" className="space-y-4">
                    <SpeedAnalysisCard speedData={analytics.speedVsAccuracy} />
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            {/* Strengths and Weaknesses */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <StrengthsCard strengths={analytics.strengthAreas} />
              <WeaknessesCard weaknesses={analytics.challengingAreas} />
            </div>

            {/* Study Recommendations */}
            <StudyRecommendationsCard recommendations={analytics.studyRecommendations} />
          </div>

          {/* Right Column - Calendar and Quick Stats */}
          <div className="space-y-6">
            {/* Performance Calendar */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CalendarIcon className="h-5 w-5" />
                  Performance Calendar
                </CardTitle>
                <CardDescription>
                  View your test history and performance over time
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={setSelectedDate}
                  className="rounded-md border"
                />
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Tests this month</span>
                    <Badge variant="outline">{analytics.totalTests}</Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span>Best accuracy</span>
                    <Badge variant="outline" className="text-green-600">
                      {analytics.overallAccuracy.toFixed(1)}%
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  Quick Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Link href="/topics">
                  <Button className="w-full justify-start" variant="outline">
                    <PlusCircle className="h-4 w-4 mr-2" />
                    Take Practice Test
                  </Button>
                </Link>
                <Link href="/dashboard">
                  <Button className="w-full justify-start" variant="outline">
                    <BarChart3 className="h-4 w-4 mr-2" />
                    Detailed Analytics
                  </Button>
                </Link>
                <Button className="w-full justify-start" variant="outline">
                  <Users className="h-4 w-4 mr-2" />
                  Study Groups
                </Button>
                <Button className="w-full justify-start" variant="outline">
                  <BookOpen className="h-4 w-4 mr-2" />
                  Study Materials
                </Button>
              </CardContent>
            </Card>

            {/* Today's Goal */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Star className="h-5 w-5" />
                  Today's Goal
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium">Daily Practice</span>
                      <span className="text-sm text-gray-500">1/3 tests</span>
                    </div>
                    <Progress value={33} className="h-2" />
                  </div>
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium">Study Time</span>
                      <span className="text-sm text-gray-500">2h 30m / 4h</span>
                    </div>
                    <Progress value={62} className="h-2" />
                  </div>
                  <Button className="w-full" size="sm">
                    Continue Learning
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
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
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
          </div>
          <div className={`p-3 rounded-full ${color} text-white`}>
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
          <XAxis dataKey="subject" />
          <YAxis />
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
          <XAxis dataKey="date" />
          <YAxis />
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