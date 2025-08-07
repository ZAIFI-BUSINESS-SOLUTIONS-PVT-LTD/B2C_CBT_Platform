/**
 * Topics Page - Chapter Selection Interface
 * 
 * This page provides the topic/chapter selection interface for creating tests.
 * It displays the hierarchical structure of subjects, chapters, and topics
 * allowing users to select specific topics for their practice tests.
 */

import { ChapterSelection } from "@/components/chapter-selection";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart3, BookOpen, Home, TrendingUp, MessageCircle } from "lucide-react";
import { Link, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { StudentProfile } from "@/components/student-profile";
import { AnalyticsData } from '../types/api';

export default function Topics() {
  const [, navigate] = useLocation();
  
  // Check if user has previous test data for personalized greeting
  // We're telling useQuery that the raw data is AnalyticsData, but the 'select' function
  // will transform it into a boolean. So, the 'data' variable (aliased to 'hasData')
  // will directly be that boolean.
  const { data: hasData } = useQuery<AnalyticsData, Error, boolean>({ // <--- CHANGE THIS LINE
    queryKey: ['/api/dashboard/analytics/'],
    // The 'response_data' parameter here is of type AnalyticsData
    select: (response_data) => response_data?.totalTests > 0, // <--- CHANGE 'totalSessions' to 'totalTests'
    retry: false
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header with Navigation */}
      <div className="w-full bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <BookOpen className="h-5 w-5 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900">NEET Practice Platform</h1>
            </div>
            
            {/* Navigation Buttons */}
            <div className="flex items-center space-x-3">
              <Link href="/">
                <Button variant="outline" className="flex items-center gap-2">
                  <Home className="h-4 w-4" />
                  Home
                </Button>
              </Link>
              
              {hasData && (
                <Link href="/landing-dashboard">
                  <Button variant="outline" className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4" />
                    Analytics Dashboard
                  </Button>
                </Link>
              )}
              
              <Link href="/dashboard">
                <Button variant="outline" className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Test History
                </Button>
              </Link>
              
              <Button 
                variant="outline" 
                className="flex items-center gap-2"
                onClick={() => navigate('/chatbot')}
              >
                <MessageCircle className="h-4 w-4" />
                AI Tutor
              </Button>
              
              <StudentProfile />
            </div>
          </div>
        </div>
      </div>

      {/* Welcome Section */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h2 className="text-4xl font-bold text-gray-800 mb-4">
            Create Your Practice Test
          </h2>
          <p className="text-xl text-gray-600 mb-6">
            Select topics from Physics, Chemistry, Botany, and Zoology to create a personalized NEET practice test
          </p>
          
          {hasData && (
            <div className="flex justify-center gap-4 mb-8">
              <Link href="/landing-dashboard">
                <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white">
                  <BarChart3 className="h-5 w-5 mr-2" />
                  View Analytics Dashboard
                </Button>
              </Link>
            </div>
          )}
        </div>

        {/* Quick Stats Cards (if user has data) */}
        {hasData && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <Card className="bg-white/80 backdrop-blur-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-blue-600" />
                  Your Progress
                </CardTitle>
                <CardDescription>
                  Track your improvement over time
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Link href="/landing-dashboard">
                  <Button variant="outline" className="w-full">
                    View Detailed Analytics
                  </Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="bg-white/80 backdrop-blur-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                  Performance History
                </CardTitle>
                <CardDescription>
                  Review your past test results
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Link href="/dashboard">
                  <Button variant="outline" className="w-full">
                    View Test History
                  </Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="bg-white/80 backdrop-blur-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-purple-600" />
                  Study Areas
                </CardTitle>
                <CardDescription>
                  Focus on challenging topics
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Link href="/landing-dashboard">
                  <Button variant="outline" className="w-full">
                    Get Recommendations
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* Main Chapter Selection Interface */}
      <div className="max-w-7xl mx-auto px-4 pb-8">
        <ChapterSelection />
      </div>
    </div>
  );
}