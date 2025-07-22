/**
 * Home Page Component
 * 
 * The main landing page of the NEET Practice Platform.
 * This page serves as the dashboard-focused landing page with:
 * - Student profile in the top right corner
 * - Performance dashboard as the main content
 * - Navigation to topic selection for taking tests
 * - Quick access to analytics and study resources
 */

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Calendar } from "@/components/ui/calendar";
import { Separator } from "@/components/ui/separator";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "wouter";
import { StudentProfile } from "@/components/student-profile";
import { 
  BarChart3, 
  BookOpen, 
  Target, 
  TrendingUp, 
  Clock,
  PlusCircle,
  Trophy,
  Users,
  Star,
  ArrowRight,
  Activity,
  Calendar as CalendarIcon,
  Zap,
  Home as HomeIcon,
  AlertCircle
} from "lucide-react";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell
} from 'recharts';
interface AnalyticsData {
  totalTests: number;
  totalQuestions: number;
  overallAccuracy: number;
  averageScore: number;
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
    averageScore: number;
  }>;
  studyRecommendations: string[]; // Or Array<{ priority: string; subject: string; reason: string; actionTip: string; }> if detailed
  message?: string; // For the "Take more tests" message
}
/**
 * Home page component that renders the dashboard-focused landing page
 * @returns JSX element containing the main dashboard interface
 */
export default function Home() {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  
  // Fetch comprehensive analytics data
  const { data: analytics, isLoading, error } = useQuery<AnalyticsData>({
    queryKey: ['/api/dashboard/comprehensive-analytics'],
    retry: false,
  });

  // Check if user has previous test data
  const hasData = analytics && analytics.totalTests > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Header with Navigation and Profile */}
      <header className="w-full bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <BookOpen className="h-5 w-5 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900">NEET Practice Platform</h1>
            </div>
            
            {/* Right side with profile */}
            <div className="flex items-center space-x-4">
              <Link href="/topics">
                <Button className="bg-blue-600 hover:bg-blue-700 text-white">
                  <PlusCircle className="h-4 w-4 mr-2" />
                  Take Test
                </Button>
              </Link>
              <StudentProfile />
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {hasData ? (
          <>
            {/* Dashboard Content */}
            <div className="mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">
                Welcome back, NEET Warrior! 🎯
              </h2>
              <p className="text-lg text-gray-600">
                Track your progress and optimize your NEET preparation
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
                icon={<Clock className="h-5 w-5" />}
                color="bg-orange-500"
              />
            </div>

            {/* Main Dashboard Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Left Column - Charts */}
              <div className="lg:col-span-2 space-y-6">
                {/* Performance Chart */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="h-5 w-5" />
                      Subject Performance
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={analytics.subjectPerformance}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="subject" />
                          <YAxis />
                          <Tooltip />
                          <Bar dataKey="accuracy" fill="#3B82F6" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                {/* Strengths and Weaknesses */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-green-600">
                        <Target className="h-5 w-5" />
                        Your Strengths
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {analytics.strengthAreas.slice(0, 3).map((strength: any, index: number) => (
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

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-orange-600">
                        <AlertCircle className="h-5 w-5" />
                        Areas to Improve
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {analytics.challengingAreas.slice(0, 3).map((weakness: any, index: number) => (
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
                </div>
              </div>

              {/* Right Column - Calendar and Actions */}
              <div className="space-y-6">
                {/* Performance Calendar */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <CalendarIcon className="h-5 w-5" />
                      Performance Calendar
                    </CardTitle>
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

                {/* Quick Actions - Centered Test Taking */}
                <Card className="border-2 border-blue-200 bg-blue-50/50">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-blue-600">
                      <Zap className="h-5 w-5" />
                      Quick Actions
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <Link href="/topics">
                      <Button size="lg" className="w-full justify-center bg-blue-600 hover:bg-blue-700 text-white">
                        <PlusCircle className="h-5 w-5 mr-2" />
                        Take New Practice Test
                      </Button>
                    </Link>
                    <Link href="/landing-dashboard">
                      <Button className="w-full justify-start" variant="outline">
                        <BarChart3 className="h-4 w-4 mr-2" />
                        Full Analytics
                      </Button>
                    </Link>
                    <Link href="/dashboard">
                      <Button className="w-full justify-start" variant="outline">
                        <TrendingUp className="h-4 w-4 mr-2" />
                        Test History
                      </Button>
                    </Link>
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
                      <Link href="/topics">
                        <Button className="w-full" size="sm">
                          Continue Learning
                          <ArrowRight className="h-4 w-4 ml-2" />
                        </Button>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </>
        ) : (
          /* Welcome Screen for New Users */
          <div className="max-w-4xl mx-auto text-center">
            <div className="mb-8">
              <h2 className="text-4xl font-bold text-gray-900 mb-4">
                Welcome to NEET Practice Platform! 🎯
              </h2>
              <p className="text-xl text-gray-600 mb-8">
                Start your journey to NEET success with comprehensive practice tests and analytics
              </p>
            </div>

            {/* Getting Started Card - Centered Test Taking */}
            <Card className="bg-white/80 backdrop-blur-sm border-2 border-blue-200 mb-8">
              <CardHeader>
                <CardTitle className="text-2xl text-blue-600">
                  Ready to Begin Your NEET Preparation?
                </CardTitle>
                <CardDescription className="text-lg">
                  Take your first practice test to unlock personalized analytics and insights
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4">
                    <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                      <BookOpen className="h-6 w-6 text-blue-600" />
                    </div>
                    <h3 className="font-semibold mb-2">Choose Topics</h3>
                    <p className="text-sm text-gray-600">Select from Physics, Chemistry, Botany, and Zoology</p>
                  </div>
                  <div className="text-center p-4">
                    <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                      <Clock className="h-6 w-6 text-green-600" />
                    </div>
                    <h3 className="font-semibold mb-2">Take Test</h3>
                    <p className="text-sm text-gray-600">Practice with timed questions and immediate feedback</p>
                  </div>
                  <div className="text-center p-4">
                    <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-3">
                      <BarChart3 className="h-6 w-6 text-purple-600" />
                    </div>
                    <h3 className="font-semibold mb-2">Track Progress</h3>
                    <p className="text-sm text-gray-600">Get detailed analytics and improvement suggestions</p>
                  </div>
                </div>
                
                <div className="flex justify-center">
                  <Link href="/topics">
                    <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white">
                      <PlusCircle className="h-5 w-5 mr-2" />
                      Take Your First Test
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
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
