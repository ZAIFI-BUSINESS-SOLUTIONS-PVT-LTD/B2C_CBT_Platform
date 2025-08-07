/**
 * NEET Practiimport { 
  BookOpen, Target, Award, Brain, BarChart3, Home, MessageCircle
} from "lucide-react";Platform - Student Dashboard
 * 
 * A clean, simple dashboard that shows essential performance metrics
 * and analytics for student progress tracking. Focuses on clarity and
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={dashboardData.subjectPerformance}> usability with our consistent NEET color theme.
 */

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { authenticatedFetch } from "@/lib/auth";
import { API_CONFIG } from "@/config/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { 
  BookOpen, Target, Award, Brain, BarChart3, Home, MessageCircle
} from 'lucide-react';
import { useLocation } from 'wouter';
import { useEffect } from 'react';

// === TYPE DEFINITIONS ===

interface SubjectPerformance {
  subject: string;
  accuracy: number;
  totalQuestions: number;
  correctAnswers: number;
}

interface ChapterPerformance {
  chapter: string;
  subject: string;
  accuracy: number;
  questionsAttempted: number;
}

interface DashboardData {
  totalTests: number;
  totalQuestions: number;
  overallAccuracy: number;
  averageScore: number;
  completionRate: number;
  subjectPerformance: SubjectPerformance[];
  chapterPerformance: ChapterPerformance[];
  progressTrend: any[];
  sessions: any[];
  totalTimeSpent: number;
}

// === DASHBOARD COMPONENT ===

export default function Dashboard() {
  const [, navigate] = useLocation();
  const { isAuthenticated, loading } = useAuth();

  // === NAVIGATION GUARD ===
  // Redirect to landing page when user tries to navigate back from dashboard
  useEffect(() => {
    const handlePopState = (e: PopStateEvent) => {
      e.preventDefault();
      console.log('🔄 Back navigation detected from Dashboard page, redirecting to landing...');
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

  // Fetch dashboard data
  const { data: dashboardData, isLoading } = useQuery<DashboardData>({
    queryKey: ['/api/dashboard/analytics/'],
    queryFn: async () => {
      const response = await authenticatedFetch(`${API_CONFIG.BASE_URL}/api/dashboard/analytics/`);
      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data');
      }
      return response.json();
    },
    enabled: isAuthenticated && !loading, // Only run when authenticated
  });  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-neet-blue border-t-transparent mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-gray-800">Loading Dashboard...</h2>
          </div>
        </div>
      </div>
    );
  }

  // Use dashboardData directly since backend returns analytics data at root level
  const hasData = dashboardData && dashboardData.totalTests > 0;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
          <p className="text-gray-600">Your NEET preparation progress</p>
        </div>

        {/* Navigation */}
        <div className="text-center">
          <Button
            onClick={() => navigate('/')}
            variant="outline"
            className="mr-4"
          >
            <Home className="h-4 w-4 mr-2" />
            Back to Home
          </Button>
          <Button
            onClick={() => navigate('/chatbot')}
            variant="outline"
            className="mr-4"
          >
            <MessageCircle className="h-4 w-4 mr-2" />
            AI Tutor
          </Button>
        </div>

        {/* Empty State */}
        {!hasData && (
          <Card className="bg-white">
            <CardContent className="p-8 text-center">
              <BarChart3 className="h-16 w-16 text-neet-blue mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 mb-2">No Data Yet</h3>
              <p className="text-gray-600 mb-6">
                Complete your first practice test to see analytics here
              </p>
              <Button
                onClick={() => navigate('/')}
                className="btn-primary"
              >
                Take First Test
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Analytics Content */}
        {hasData && (
          <div className="space-y-6">
            
            {/* Key Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              
              <Card className="bg-white">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Tests</p>
                      <p className="text-2xl font-bold text-gray-900">{dashboardData.totalTests}</p>
                    </div>
                    <BookOpen className="h-8 w-8 text-neet-blue" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Accuracy</p>
                      <p className="text-2xl font-bold text-gray-900">{dashboardData.overallAccuracy.toFixed(1)}%</p>
                    </div>
                    <Target className="h-8 w-8 text-neet-green" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Avg Score</p>
                      {/* averageScore removed: field no longer exists */}
                    </div>
                    <Award className="h-8 w-8 text-neet-purple" />
                  </div>
                </CardContent>
              </Card>

                <Card className="bg-white">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Questions</p>
                      <p className="text-2xl font-bold text-gray-900">{dashboardData.totalQuestions}</p>
                    </div>
                    <Brain className="h-8 w-8 text-neet-amber" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Avg Score</p>
                      <p className="text-2xl font-bold text-gray-900">{dashboardData.averageScore.toFixed(1)}</p>
                    </div>
                    <Award className="h-8 w-8 text-green-600" />
                  </div>
                </CardContent>
              </Card>
            </div>            {/* Subject Performance Chart */}
            <Card className="bg-white">
              <CardHeader>
                <CardTitle>Subject Performance</CardTitle>
              </CardHeader>
              <CardContent>
                {dashboardData.subjectPerformance.length > 0 ? (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={dashboardData.subjectPerformance}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="subject" />
                        <YAxis />
                        <Tooltip 
                          formatter={(value: number) => [`${value.toFixed(1)}%`, 'Accuracy']}
                        />
                        <Bar dataKey="accuracy" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-64 flex items-center justify-center text-gray-500">
                    <p>Subject performance data will be available after completing tests</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Chapter Performance List */}
            <Card className="bg-white">
              <CardHeader>
                <CardTitle>Chapter Performance</CardTitle>
              </CardHeader>
              <CardContent>
                {dashboardData.chapterPerformance.length > 0 ? (
                  <div className="space-y-3">
                    {dashboardData.chapterPerformance.slice(0, 10).map((chapter: any, index: number) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <h4 className="font-medium text-sm">{chapter.chapter}</h4>
                          <p className="text-xs text-gray-500">{chapter.subject}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-medium">{chapter.accuracy.toFixed(1)}%</p>
                          <p className="text-xs text-gray-500">{chapter.questionsAttempted} questions</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <p>Chapter-wise analysis will be available after completing more tests</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Action Buttons */}
            <div className="text-center">
              <Button
                onClick={() => navigate('/')}
                className="btn-primary mr-4"
              >
                Take Another Test
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}