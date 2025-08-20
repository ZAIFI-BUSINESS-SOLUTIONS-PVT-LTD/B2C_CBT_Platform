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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50">
      {/* Header with Navigation */}
      <div className="w-full bg-white/95 backdrop-blur-sm border-b border-blue-100 sticky top-0 z-50 shadow-sm">
        <div className="max-w-6xl mx-auto px-3 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1.5">
              <div className="w-6 h-6 bg-[#4F83FF] rounded-lg flex items-center justify-center shadow-md">
                <BookOpen className="h-4 w-4 text-white" />
              </div>
              <h1 className="text-xl font-bold text-[#1F2937]">NEET Practice Platform</h1>
            </div>
            {/* Navigation Buttons */}
            <div className="flex items-center space-x-2.5">
              <Link href="/">
                <Button variant="outline" className="flex items-center gap-1.5 border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC] text-sm px-2 py-1.5">
                  <Home className="h-3 w-3" />
                  <span className="text-xs">Home</span>
                </Button>
              </Link>
              {hasData && (
                <Link href="/dashboard">
                  <Button variant="outline" className="flex items-center gap-1.5 border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC] text-sm px-2 py-1.5">
                    <BarChart3 className="h-3 w-3" />
                    <span className="text-xs">Analytics Dashboard</span>
                  </Button>
                </Link>
              )}
              <Link href="/dashboard">
                <Button variant="outline" className="flex items-center gap-1.5 border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC] text-sm px-2 py-1.5">
                  <TrendingUp className="h-3 w-3" />
                  <span className="text-xs">Test History</span>
                </Button>
              </Link>
              <Button 
                variant="outline" 
                className="flex items-center gap-1 border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC] text-xs px-1.5 py-1"
                onClick={() => navigate('/chatbot')}
              >
                <MessageCircle className="h-3 w-3" />
                <span className="text-xs">AI Tutor</span>
              </Button>
              <StudentProfile />
            </div>
          </div>
        </div>
      </div>
      {/* Main Chapter Selection Interface */}
      <div className="max-w-7xl mx-auto px-4 pb-8">
        <ChapterSelection />
      </div>
    </div>
  );
}