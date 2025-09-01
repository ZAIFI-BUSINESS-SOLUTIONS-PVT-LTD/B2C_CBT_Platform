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
import { Separator } from "@/components/ui/separator";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/hooks/use-auth";
import { LoginForm } from "@/components/LoginForm";
import { Link, useLocation } from "wouter";
import { HomeChatInput } from "@/components/HomeChatInput";
import { getAccessToken } from "@/lib/auth";
import { API_CONFIG } from "@/config/api";
import { SPEECH_CONFIG } from "@/config/speech";
import '@/types/speech.d.ts';
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
  CalendarIcon,
  Zap,
  Home as HomeIcon,
  AlertCircle,
  MessageCircle
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
/**
 * Home page component that renders the dashboard-focused landing page
 * @returns JSX element containing the main dashboard interface
 */
export default function Home() {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const { isAuthenticated } = useAuth();
  const [, navigate] = useLocation();

  // Chat functionality states
  const [inputMessage, setInputMessage] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [recognitionLanguage, setRecognitionLanguage] = useState(SPEECH_CONFIG.DEFAULT_LANGUAGE);
  const recognitionRef = useRef<any>(null);

  // Debug: Log authentication state
  console.log("Home component - isAuthenticated:", isAuthenticated);

  // Dashboard and analytics logic (only when authenticated)
  const { data: analytics, isLoading, error } = useQuery<AnalyticsData>({
    queryKey: ['/api/dashboard/comprehensive-analytics/'],
    retry: false,
    enabled: isAuthenticated, // Only run this query when user is authenticated
  });

  // Initialize speech recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (SpeechRecognition) {
      setSpeechSupported(true);
      const recognition = new SpeechRecognition();
      
      recognition.continuous = SPEECH_CONFIG.RECOGNITION_SETTINGS.continuous;
      recognition.interimResults = SPEECH_CONFIG.RECOGNITION_SETTINGS.interimResults;
      recognition.lang = recognitionLanguage;
      recognition.maxAlternatives = SPEECH_CONFIG.RECOGNITION_SETTINGS.maxAlternatives;
      
      recognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        setInputMessage(transcript);
        
        // Manually adjust textarea height after setting transcribed text
        setTimeout(() => {
          const textarea = document.querySelector('textarea[placeholder="Ask anything..."]') as HTMLTextAreaElement;
          if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
          }
        }, 0);
      };
      
      recognition.onstart = () => setIsRecording(true);
      recognition.onend = () => setIsRecording(false);
      recognition.onerror = () => setIsRecording(false);
      
      recognitionRef.current = recognition;
    } else {
      setSpeechSupported(false);
    }
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, [recognitionLanguage]);

  // Chat functions
  const getAuthHeaders = () => {
    const token = getAccessToken();
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  const generateSessionTitleFromMessage = (message: string): string => {
    if (!message) return 'New Chat';
    let trimmed = message.trim();
    if (trimmed.length > 40) {
      trimmed = trimmed.slice(0, 40).trim() + '...';
    }
    return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
  };

  const createNewSessionAndRedirect = async (messageToSend: string) => {
    try {
      setIsChatLoading(true);
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSIONS}`;
      
      const sessionTitle = generateSessionTitleFromMessage(messageToSend);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ sessionTitle }),
      });

      if (response.ok) {
        const newSession = await response.json();
        // Redirect to chatbot page with the new session and message
        navigate(`/chatbot?sessionId=${newSession.chatSessionId}&message=${encodeURIComponent(messageToSend)}`);
      } else {
        console.error('Failed to create session');
      }
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleChatSend = (message: string) => {
    if (!message.trim()) return;
    setInputMessage('');
    
    // Reset textarea height after clearing input
    setTimeout(() => {
      const textarea = document.querySelector('textarea[placeholder="Ask anything..."]') as HTMLTextAreaElement;
      if (textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
      }
    }, 0);
    
    createNewSessionAndRedirect(message);
  };

  const toggleSpeechRecognition = () => {
    if (!speechSupported) return;
    
    if (isRecording) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setTimeout(() => {
        if (inputMessage.trim()) {
          handleChatSend(inputMessage.trim());
        }
      }, 100);
    } else {
      if (recognitionRef.current) {
        try {
          setInputMessage('');
          
          // Reset textarea height after clearing input
          setTimeout(() => {
            const textarea = document.querySelector('textarea[placeholder="Ask anything..."]') as HTMLTextAreaElement;
            if (textarea) {
              textarea.style.height = 'auto';
              textarea.style.height = textarea.scrollHeight + 'px';
            }
          }, 0);
          
          recognitionRef.current.start();
        } catch (error) {
          console.error('Failed to start speech recognition:', error);
          setIsRecording(false);
        }
      }
    }
  };

  // Show login form if not authenticated
  if (!isAuthenticated) {
    console.log("Showing login form - user not authenticated");
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
        <LoginForm />
      </div>
    );
  }

  console.log("Showing dashboard - user is authenticated");

  // Check if user has previous test data
  const hasData = analytics && analytics.totalTests > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50">
      {/* Header with Navigation and Profile */}
      <header className="w-full bg-white/95 backdrop-blur-sm border-b border-blue-100 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-[#4F83FF] rounded-lg flex items-center justify-center shadow-md">
                <BookOpen className="h-5 w-5 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-[#1F2937]">NEET Practice Platform</h1>
            </div>
            {/* Right side with profile */}
            <div className="flex items-center space-x-4">
              <StudentProfile />
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Welcome Section */}
        <div className="text-center mb-8 mt-14">
          <h2 className="text-2xl font-bold text-[#1F2937] mb-4">
            Welcome to NEET Practice Platform! 🎯
          </h2>
          <p className="text-l text-[#6B7280]">
            Start your journey to NEET success with comprehensive practice tests and analytics
          </p>
        </div>

        {/* Navigation Container */}
        <div className="mb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Take Test Button - Always Active */}
            <NavigationBox
              title="Take Test"
              description="Start practicing with NEET questions"
              icon={<BookOpen className="h-8 w-8" />}
              href="/topics"
              isLocked={false}
              color="bg-[#4F83FF]"
              hoverColor="hover:bg-[#3B82F6]"
            />

            {/* Dashboard Button - Locked if no data */}
            <NavigationBox
              title="Dashboard"
              description="View your performance analytics"
              icon={<BarChart3 className="h-8 w-8" />}
              href="/dashboard"
              isLocked={!hasData}
              color="bg-[#8B5CF6]"
              hoverColor="hover:bg-[#7C3AED]"
              lockMessage="Take your first practice test to unlock personalized analytics and insights!"
            />
          </div>

          {/* AI Tutor Chat Input - Centered */}
          <div className="flex justify-center">
            <div className="w-full md:w-[500px]">
              <div className="rounded-2xl bg-blue-50 border border-blue-100 shadow-lg px-6 py-8 flex flex-col items-center">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-[#F59E0B] rounded-lg flex items-center justify-center shadow-md">
                    <MessageCircle className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-[#1F2937]">AI Tutor</h3>
                    <p className="text-sm text-[#6B7280]">Ask anything to get instant help</p>
                  </div>
                </div>
                
                <div className="w-full">
                  <HomeChatInput
                    isLoading={isChatLoading}
                    onSend={handleChatSend}
                    speechSupported={speechSupported}
                    isRecording={isRecording}
                    onMicClick={toggleSpeechRecognition}
                    inputMessage={inputMessage}
                    setInputMessage={setInputMessage}
                  />
                  {speechSupported && isRecording && (
                    <div className="mt-4 text-center">
                      <span className="text-[#10B981] text-sm">
                        🎤 Listening... Click ✓ to stop and send
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
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
 * Navigation Box Component
 */
interface NavigationBoxProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  isLocked: boolean;
  color: string;
  hoverColor: string;
  lockMessage?: string;
}

function NavigationBox({ title, description, icon, href, isLocked, color, hoverColor, lockMessage }: NavigationBoxProps) {
  const [, navigate] = useLocation();
  const [showLockModal, setShowLockModal] = useState(false);

  const handleClick = () => {
    if (isLocked) {
      setShowLockModal(true);
    } else {
      navigate(href);
    }
  };

  return (
    <>
      <div className="relative">
        <button
          onClick={handleClick}
          className={`w-full p-3 rounded-2xl shadow-lg border-2 transition-all duration-300 text-left ${
            isLocked 
              ? 'bg-[#E8F0FF] border-[#4F83FF]/20 cursor-pointer' 
              : 'bg-[#E8F0FF] border-[#4F83FF]/20 hover:bg-[#DBEAFE] transform hover:scale-105 hover:shadow-xl'
          }`}
        >
          <div className="flex items-center space-x-4">
            <div className={`p-2 rounded-full ${color} text-white shadow-md`}>
              {icon}
            </div>
            <div>
              <h3 className="text-l font-bold text-[#1F2937]">
                {title}
              </h3>
              <p className="text-sm text-[#6B7280]">
                {description}
              </p>
            </div>
          </div>
        </button>
        
        {isLocked && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur-sm rounded-2xl z-10 border-2 border-[#4F83FF]/20">
            <div className="text-center px-4">
              <AlertCircle className="h-6 w-6 text-[#4F83FF] mx-auto mb-2" />
              <p className="text-[#1F2937] font-medium text-sm">
                Complete your First Test to unlock Dashboard
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Lock Modal */}
      {showLockModal && (
        <div className="fixed inset-0 bg-[#0F172A]/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-md mx-4 border-2 border-[#4F83FF]/20">
            <div className="text-center">
              <div className="w-16 h-16 bg-[#E8F0FF] rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="h-8 w-8 text-[#4F83FF]" />
              </div>
              <h3 className="text-xl font-bold text-[#1F2937] mb-2">
                Feature Locked
              </h3>
              <p className="text-[#6B7280] mb-6">
                {lockMessage || "Take your first practice test to unlock this feature!"}
              </p>
              <div className="flex space-x-3">
                <Button
                  variant="outline"
                  onClick={() => setShowLockModal(false)}
                  className="flex-1 border-[#E2E8F0] text-[#64748B] hover:bg-[#F8FAFC]"
                >
                  Close
                </Button>
                <Button
                  onClick={() => {
                    setShowLockModal(false);
                    navigate('/topics');
                  }}
                  className="flex-1 bg-[#4F83FF] hover:bg-[#3B82F6] text-white"
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
 * Insight Card Component
 */
interface InsightCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  isLocked: boolean;
  lockMessage?: string;
}

function InsightCard({ title, description, icon, isLocked, lockMessage }: InsightCardProps) {
  const [showLockModal, setShowLockModal] = useState(false);

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
          className="p-6 rounded-2xl shadow-lg border-2 border-blue-200 transition-all duration-300 bg-blue-50 hover:bg-blue-100 hover:shadow-xl cursor-pointer"
        >
          <div className="flex items-center space-x-4">
            <div className="p-3 rounded-full bg-blue-600 text-white">
              {icon}
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-bold text-blue-800">
                {title}
              </h3>
              <p className="text-sm text-blue-600">
                {description}
              </p>
            </div>
          </div>
          
          {/* Content container - only this part gets blurred */}
          <div className="mt-4 relative">
            <div className="h-32 bg-white rounded-lg flex items-center justify-center border">
              <p className="text-gray-400 text-sm">
                {isLocked ? "Complete tests to unlock insights" : "Coming soon..."}
              </p>
            </div>
            
            {isLocked && (
              <div className="absolute inset-0 flex items-center justify-center bg-white/70 backdrop-blur-sm rounded-lg z-10">
                <div className="text-center px-4">
                  <AlertCircle className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                  <p className="text-blue-800 font-medium">
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
                    window.location.href = '/topics';
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
