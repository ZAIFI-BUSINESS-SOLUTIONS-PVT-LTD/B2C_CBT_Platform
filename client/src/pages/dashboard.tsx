/**
 * NEET Practice Platform - Student Dashboard
 * 
 * A clean, simple dashboard that shows essential performance metrics
 * and analytics for student progress tracking. Focuses on clarity and
 * usability with our consistent NEET color theme.
 */

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { 
  BookOpen, Target, Award, Brain, BarChart3, Home
} from 'lucide-react';
import { useLocation } from 'wouter';

// === TYPE DEFINITIONS ===

interface SubjectPerformance {
  subject: string;
  accuracy: number;
  questionsAttempted: number;
  averageScore: number;
  color: string;
}

interface ChapterPerformance {
  chapter: string;
  subject: string;
  accuracy: number;
  questionsAttempted: number;
}

interface Analytics {
  totalTests: number;
  totalQuestions: number;
  overallAccuracy: number;
  averageScore: number;
  completionRate: number;
  subjectPerformance: SubjectPerformance[];
  chapterPerformance: ChapterPerformance[];
}

interface DashboardData {
  sessions: any[];
  analytics: Analytics;
}

// === DASHBOARD COMPONENT ===

export default function Dashboard() {
  const [, navigate] = useLocation();
  
  // Fetch dashboard data
  const { data: dashboardData, isLoading } = useQuery<DashboardData>({
    queryKey: ['/api/dashboard/analytics'],
    queryFn: async () => {
      const response = await fetch('/api/dashboard/analytics');
      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data');
      }
      return response.json();
    },
  });

  // Loading state
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

  const analytics = dashboardData?.analytics;
  const hasData = analytics && analytics.totalTests > 0;

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
                      <p className="text-2xl font-bold text-gray-900">{analytics.totalTests}</p>
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
                      <p className="text-2xl font-bold text-gray-900">{analytics.overallAccuracy.toFixed(1)}%</p>
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
                      <p className="text-2xl font-bold text-gray-900">{analytics.averageScore.toFixed(1)}</p>
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
                      <p className="text-2xl font-bold text-gray-900">{analytics.totalQuestions}</p>
                    </div>
                    <Brain className="h-8 w-8 text-neet-amber" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Subject Performance Chart */}
            <Card className="bg-white">
              <CardHeader>
                <CardTitle>Subject Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analytics.subjectPerformance}>
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
              </CardContent>
            </Card>

            {/* Chapter Performance List */}
            <Card className="bg-white">
              <CardHeader>
                <CardTitle>Chapter Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {analytics.chapterPerformance.slice(0, 10).map((chapter, index) => (
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