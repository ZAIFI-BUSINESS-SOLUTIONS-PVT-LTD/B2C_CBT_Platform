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
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-[#4F83FF] rounded-lg flex items-center justify-center shadow-md">
                <BookOpen className="h-5 w-5 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-[#1F2937]">NEET Practice Platform</h1>
            </div>
            
            {/* Navigation Buttons */}
            <div className="flex items-center space-x-3">
              <Link href="/">
                <Button variant="outline" className="flex items-center gap-2 border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC]">
                  <Home className="h-4 w-4" />
                  Home
                </Button>
              </Link>
              
              {hasData && (
                <Link href="/landing-dashboard">
                  <Button variant="outline" className="flex items-center gap-2 border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC]">
                    <BarChart3 className="h-4 w-4" />
                    Analytics Dashboard
                  </Button>
                </Link>
              )}
              
              <Link href="/dashboard">
                <Button variant="outline" className="flex items-center gap-2 border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC]">
                  <TrendingUp className="h-4 w-4" />
                  Test History
                </Button>
              </Link>
              
              <Button 
                variant="outline" 
                className="flex items-center gap-2 border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC]"
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
          <h2 className="text-4xl font-bold text-[#1F2937] mb-4">
            Create Your Practice Test
          </h2>
          <p className="text-xl text-[#6B7280] mb-6">
            Select topics from Physics, Chemistry, Botany, and Zoology to create a personalized NEET practice test
          </p>
          {hasData && (
            <div className="flex justify-center gap-4 mb-8">
              <Link href="/landing-dashboard">
                <Button size="lg" className="bg-[#4F83FF] hover:bg-[#3B82F6] text-white shadow-md">
                  <BarChart3 className="h-5 w-5 mr-2" />
                  View Analytics Dashboard
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Main Chapter Selection Interface */}
      <div className="max-w-7xl mx-auto px-4 pb-8">
        <ChapterSelection />
      </div>
    </div>
  );
}