/**
 * Test Interface Component
 * 
 * This component handles the core test-taking experience for NEET practice tests.
 * It provides a comprehensive interface for:
 * - Displaying questions with multiple choice options
 * - Managing timer functionality (countdown for time-based tests)
 * - Tracking user answers and progress
 * - Question navigation (next/previous)
 * - Mark for review functionality
 * - Real-time answer submission to the database
 * - Test completion and results navigation
 * 
 * The component supports both time-based and question-based test modes,
 * with automatic submission when time expires.
 */

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Timer } from "@/components/timer";
import { useToast } from "@/hooks/use-toast";
import { API_CONFIG } from "@/config/api";
import { apiRequest } from "@/lib/queryClient";
import { authenticatedFetch } from "@/lib/auth";
import { debugAuthentication, testAuthenticatedRequest } from "@/lib/debug-auth";
import { 
  ChevronLeft, 
  ChevronRight, 
  Bookmark, 
  Check,
  AlertTriangle,
  Clock
} from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

/**
 * Props for the TestInterface component
 */
interface TestInterfaceProps {
  sessionId: number;  // ID of the current test session
}

/**
 * Interface for question data structure
 */
interface Question {
  id: number;
  topicId: number;
  question: string;
  optionA: string;
  optionB: string;
  optionC: string;
  optionD: string;
}

/**
 * Interface for test session data from the API
 */
interface TestSessionData {
  session: {
    id: number;
    selectedTopics: string[];
    timeLimit: number;
    totalQuestions: number;
    startTime: string;
  };
  questions: Question[];
}

/**
 * Main Test Interface Component
 * Handles the complete test-taking experience
 */
export function TestInterface({ sessionId }: TestInterfaceProps) {
  // === NAVIGATION AND UI STATE ===
  const [, navigate] = useLocation();                  // Navigation function
  const { toast } = useToast();                        // Toast notifications
  const queryClient = useQueryClient();                // React Query client for cache management
  
  // === TEST STATE MANAGEMENT ===
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);        // Current question index
  const [answers, setAnswers] = useState<Record<number, string>>({});         // User's answers by question ID
  const [markedForReview, setMarkedForReview] = useState<Set<number>>(new Set()); // Questions marked for review
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);            // Submit confirmation dialog visibility
  const [showTimeOverDialog, setShowTimeOverDialog] = useState(false);        // Time over dialog visibility
  const [timeOverAutoSubmit, setTimeOverAutoSubmit] = useState<NodeJS.Timeout | null>(null); // Auto-submit timeout
  const [showQuitDialog, setShowQuitDialog] = useState(false);                // Quit exam confirmation dialog visibility
  const [isNavigationBlocked, setIsNavigationBlocked] = useState(true);       // Block navigation during test
  
  // === TIME TRACKING ===
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now()); // When current question started
  const [questionTimes, setQuestionTimes] = useState<Record<number, number>>({});  // Time spent on each question

  // === ENHANCED TIME TRACKING (Visit-based) ===
  const [currentVisitStartTime, setCurrentVisitStartTime] = useState<number>(0); // When current visit started
  const [questionVisits, setQuestionVisits] = useState<Record<number, Array<{
    startTime: number;
    endTime?: number;
    duration?: number;
  }>>>({});  // Track all visits to each question

  // === DATA FETCHING ===
  // Fetch test session data and questions from the database
  const { data: testData, isLoading } = useQuery<TestSessionData>({
    queryKey: [`testSession-${sessionId}`], // Changed key for clarity, but old one also works if no clash
    queryFn: async () => {
      // Debug authentication before making request
      debugAuthentication();
      
      // CORRECTED: Use authenticatedFetch for authenticated requests
      const url = `/api/test-sessions/${sessionId}/`; 
      console.log('🔄 Fetching test session:', url);
      
      const response = await authenticatedFetch(`${API_CONFIG.BASE_URL}${url}`);

      if (!response.ok) {
        console.error('❌ Test session fetch failed:', response.status, response.statusText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('✅ Test session fetch successful, data:', data);
      console.log('📊 Questions in response:', data?.questions?.length || 'No questions');
      return data;
    },
    enabled: !!sessionId, // Only fetch if sessionId is available
  });

  // === ANSWER SUBMISSION MUTATION ===
  // This mutation handles real-time answer submission as students answer questions
  const submitAnswerMutation = useMutation({
    mutationFn: async (data: { 
      sessionId: number;       // Which test session this answer belongs to
      questionId: number;      // Which question is being answered
      selectedAnswer: string | null;  // The student's choice (A, B, C, D) or null
      markedForReview?: boolean;      // Whether student marked question for review
      timeSpent?: number;             // Time spent on this question in seconds
    }) => {
      const response = await apiRequest(API_CONFIG.ENDPOINTS.TEST_ANSWERS, "POST", data);
      return response;
    },
  });

  // === ENHANCED TIME LOGGING MUTATION ===
  // New separate mutation for detailed visit-based time tracking
  const logTimeMutation = useMutation({
    mutationFn: async (data: {
      sessionId: number;
      questionId: number;
      timeSpent: number;
      visitStartTime: string;
      visitEndTime: string;
    }) => {
      const response = await apiRequest(API_CONFIG.ENDPOINTS.TEST_SESSION_LOG_TIME, 'POST', data);
      return response;
    },
    onError: (error) => {
      console.error('Failed to log time:', error);
      // Don't show user error for time logging failures to avoid disruption
    }
  });

  const submitTestMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest(`/api/test-sessions/${sessionId}/submit/`, "POST");
      return response;
    },
    onSuccess: () => {
      // Disable navigation blocking before navigating away
      setIsNavigationBlocked(false);
      
      // Invalidate all relevant queries to refresh dashboard data
      queryClient.invalidateQueries({ queryKey: ['/api/dashboard/analytics/'] }); // Main dashboard
      queryClient.invalidateQueries({ queryKey: ['/api/dashboard/comprehensive-analytics/'] }); // Landing dashboard
      queryClient.invalidateQueries({ queryKey: [`testSession-${sessionId}`] }); // Current test session
      queryClient.invalidateQueries({ queryKey: [`/api/test-sessions/${sessionId}/results/`] }); // Results page
      
      // Invalidate any test sessions lists or test-related data
      queryClient.invalidateQueries({ 
        predicate: (query) => {
          const key = query.queryKey[0];
          return (
            typeof key === "string" &&
            (
              key.includes('test-session') || 
              key.includes('/api/test-sessions') ||
              key.includes('dashboard') ||
              key.includes('analytics')
            )
          );
        }
      });
      
      // Navigate to results
      navigate(`/results/${sessionId}`);
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to submit test. Please try again.",
        variant: "destructive",
      });
    },
  });

  // === QUIT TEST MUTATION ===
  // This mutation handles marking the test as incomplete when user quits
  const quitTestMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest(`/api/test-sessions/${sessionId}/quit/`, "POST");
      return response;
    },
    onSuccess: () => {
      // Invalidate all relevant queries to refresh dashboard data
      queryClient.invalidateQueries({ queryKey: ['/api/dashboard/analytics/'] }); // Main dashboard
      queryClient.invalidateQueries({ queryKey: ['/api/dashboard/comprehensive-analytics/'] }); // Landing dashboard
      queryClient.invalidateQueries({ queryKey: [`testSession-${sessionId}`] }); // Current test session
      
      // Invalidate any test sessions lists or test-related data
      queryClient.invalidateQueries({ 
        predicate: (query) => {
          const key = query.queryKey[0];
          return (
            typeof key === "string" &&
            (
              key.includes('test-session') || 
              key.includes('/api/test-sessions') ||
              key.includes('dashboard') ||
              key.includes('analytics')
            )
          );
        }
      });
      
      // Disable navigation blocking and navigate away
      setIsNavigationBlocked(false);
      navigate("/dashboard");
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to quit test. Please try again.",
        variant: "destructive",
      });
    },
  });

    // Current question derived from fetched data and current index
  const currentQuestion = testData?.questions[currentQuestionIndex];
  
  // Debug logging for troubleshooting
  console.log('🐛 Debug TestInterface:');
  console.log('  - sessionId:', sessionId);
  console.log('  - isLoading:', isLoading);
  console.log('  - testData:', testData);
  console.log('  - currentQuestionIndex:', currentQuestionIndex);
  console.log('  - currentQuestion:', currentQuestion);
  console.log('  - questions count:', testData?.questions?.length || 'undefined');
  const totalQuestions = testData?.questions.length || 0;
  const progressPercentage = totalQuestions > 0 ? ((currentQuestionIndex + 1) / totalQuestions) * 100 : 0;

  // === ENHANCED TIME TRACKING HELPER FUNCTIONS ===
  /**
   * Log time spent on current question visit using the new enhanced system
   */
  const logCurrentQuestionTime = (questionId: number, endTime: number = Date.now()) => {
    // Don't log if visit hasn't started or if we don't have a valid session
    if (currentVisitStartTime === 0 || !sessionId) {
      console.log(`⏱️ Enhanced: Skipping log - visit not started or no session (visitStart: ${currentVisitStartTime}, sessionId: ${sessionId})`);
      return;
    }
    
    const duration = Math.round((endTime - currentVisitStartTime) / 1000);
    
    // Only log if user spent at least 1 second on question
    if (duration >= 1) {
      const payload = {
        sessionId: parseInt(sessionId.toString()),
        questionId,
        timeSpent: duration,
        visitStartTime: new Date(currentVisitStartTime).toISOString(),
        visitEndTime: new Date(endTime).toISOString()
      };
      
      console.log(`⏱️ Enhanced: Sending time log payload:`, payload);
      
      logTimeMutation.mutate(payload);

      // Update local visit tracking for analytics
      setQuestionVisits(prev => ({
        ...prev,
        [questionId]: [
          ...(prev[questionId] || []),
          {
            startTime: currentVisitStartTime,
            endTime,
            duration
          }
        ]
      }));
      
      console.log(`⏱️ Enhanced: Logged ${duration} seconds for question ${questionId}`);
    }
  };

  /**
   * Start tracking time for a new question visit
   */
  const startQuestionTimer = (questionId: number) => {
    const now = Date.now();
    setCurrentVisitStartTime(now);
    
    console.log(`⏱️ Enhanced: Started timer for question ${questionId} at ${new Date(now).toISOString()}`);
  };

  // No need to pre-create answers - they will be created when user interacts

  const handleAnswerChange = (questionId: number, answer: string) => {
    // Prevent answering if time is over
    if (showTimeOverDialog) {
      return;
    }

    setAnswers(prev => ({
      ...prev,
      [questionId]: answer
    }));

    // Calculate time spent on this question
    const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
    setQuestionTimes(prev => ({
      ...prev,
      [questionId]: (prev[questionId] || 0) + timeSpent
    }));

    // Submit answer immediately with time tracking
    submitAnswerMutation.mutate({
      sessionId,
      questionId,
      selectedAnswer: answer,
      timeSpent: questionTimes[questionId] || timeSpent,
    });
  };

  const handleMarkForReview = () => {
    if (!currentQuestion || showTimeOverDialog) return; // Prevent interaction when time is over

    const newMarkedSet = new Set(markedForReview);
    if (newMarkedSet.has(currentQuestion.id)) {
      newMarkedSet.delete(currentQuestion.id);
    } else {
      newMarkedSet.add(currentQuestion.id);
    }
    setMarkedForReview(newMarkedSet);

    // Calculate time spent on this question
    const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
    setQuestionTimes(prev => ({
      ...prev,
      [currentQuestion.id]: (prev[currentQuestion.id] || 0) + timeSpent
    }));

    // Submit mark for review status with time tracking
    submitAnswerMutation.mutate({
      sessionId,
      questionId: currentQuestion.id,
      selectedAnswer: answers[currentQuestion.id] || null,
      markedForReview: newMarkedSet.has(currentQuestion.id),
      timeSpent: questionTimes[currentQuestion.id] || timeSpent,
    });
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < totalQuestions - 1 && !showTimeOverDialog) { // Prevent navigation when time is over
      // Enhanced time tracking: log current question visit
      if (currentQuestion) {
        logCurrentQuestionTime(currentQuestion.id);
        
        // Original time tracking - keep for compatibility
        const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
        setQuestionTimes(prev => ({
          ...prev,
          [currentQuestion.id]: (prev[currentQuestion.id] || 0) + timeSpent
        }));
      }
      
      const nextIndex = currentQuestionIndex + 1;
      setCurrentQuestionIndex(nextIndex);
      setQuestionStartTime(Date.now()); // Reset timer for next question
      
      // Enhanced time tracking: start timer for new question
      const nextQuestion = testData?.questions[nextIndex];
      if (nextQuestion) {
        startQuestionTimer(nextQuestion.id);
      }
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0 && !showTimeOverDialog) { // Prevent navigation when time is over
      // Enhanced time tracking: log current question visit
      if (currentQuestion) {
        logCurrentQuestionTime(currentQuestion.id);
        
        // Original time tracking - keep for compatibility
        const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
        setQuestionTimes(prev => ({
          ...prev,
          [currentQuestion.id]: (prev[currentQuestion.id] || 0) + timeSpent
        }));
      }
      
      const prevIndex = currentQuestionIndex - 1;
      setCurrentQuestionIndex(prevIndex);
      setQuestionStartTime(Date.now()); // Reset timer for previous question
      
      // Enhanced time tracking: start timer for new question
      const prevQuestion = testData?.questions[prevIndex];
      if (prevQuestion) {
        startQuestionTimer(prevQuestion.id);
      }
    }
  };

  const navigateToQuestion = (index: number) => {
    if (!showTimeOverDialog) { // Prevent navigation when time is over
      // Enhanced time tracking: log current question visit before navigation
      if (currentQuestion && index !== currentQuestionIndex) {
        logCurrentQuestionTime(currentQuestion.id);
        
        // Original time tracking - keep for compatibility
        const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
        setQuestionTimes(prev => ({
          ...prev,
          [currentQuestion.id]: (prev[currentQuestion.id] || 0) + timeSpent
        }));
      }
      
      setCurrentQuestionIndex(index);
      setQuestionStartTime(Date.now()); // Reset timer for target question
      
      // Enhanced time tracking: start timer for new question
      const targetQuestion = testData?.questions[index];
      if (targetQuestion) {
        startQuestionTimer(targetQuestion.id);
      }
    }
  };

  const handleSubmitTest = () => {
    setShowSubmitDialog(true);
  };

  const confirmSubmit = () => {
    // Enhanced time tracking: Log final question time before submission
    if (currentQuestion) {
      logCurrentQuestionTime(currentQuestion.id);
    }
    
    submitTestMutation.mutate();
    setShowSubmitDialog(false);
  };

  const handleTimeUp = () => {
    // Enhanced time tracking: Log final question time when time runs out
    if (currentQuestion) {
      logCurrentQuestionTime(currentQuestion.id);
    }
    
    // Show time over dialog to inform the user
    setShowTimeOverDialog(true);
    
    // Set auto-submit after 10 seconds if user doesn't manually submit
    const autoSubmitTimeout = setTimeout(() => {
      submitTestMutation.mutate();
      setShowTimeOverDialog(false);
    }, 10000); // 10 seconds delay
    
    setTimeOverAutoSubmit(autoSubmitTimeout);
  };

  const handleTimeOverSubmit = () => {
    // Clear auto-submit timeout since user is manually submitting
    if (timeOverAutoSubmit) {
      clearTimeout(timeOverAutoSubmit);
      setTimeOverAutoSubmit(null);
    }
    
    // Submit the test
    submitTestMutation.mutate();
    setShowTimeOverDialog(false);
  };

  // Clean up timeout on component unmount
  useEffect(() => {
    return () => {
      if (timeOverAutoSubmit) {
        clearTimeout(timeOverAutoSubmit);
      }
    };
  }, [timeOverAutoSubmit]);

  // === NAVIGATION GUARD IMPLEMENTATION ===
  // Prevent browser navigation (back/forward/refresh/close tab) during test
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isNavigationBlocked) {
        e.preventDefault();
        e.returnValue = "Are you sure you want to leave? Your test progress will be lost.";
        return "Are you sure you want to leave? Your test progress will be lost.";
      }
    };

    const handlePopState = (e: PopStateEvent) => {
      if (isNavigationBlocked) {
        e.preventDefault();
        // Push the current state back to prevent navigation
        window.history.pushState(null, "", window.location.href);
        setShowQuitDialog(true);
      }
    };

    if (isNavigationBlocked) {
      // Prevent browser back/forward
      window.history.pushState(null, "", window.location.href);
      window.addEventListener("popstate", handlePopState);
      
      // Prevent browser refresh/close
      window.addEventListener("beforeunload", handleBeforeUnload);
    }

    return () => {
      window.removeEventListener("popstate", handlePopState);
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [isNavigationBlocked]);

  // Enhanced time tracking: Start timer when test data loads and current question is available
  useEffect(() => {
    if (testData?.questions && currentQuestion && currentVisitStartTime === 0) {
      startQuestionTimer(currentQuestion.id);
    }
  }, [testData, currentQuestion]); // Run when test data or current question changes

  // === QUIT DIALOG HANDLERS ===
  const handleQuitConfirm = () => {
    quitTestMutation.mutate();
    setShowQuitDialog(false);
  };

  const handleQuitCancel = () => {
    // Re-push the state to prevent navigation
    window.history.pushState(null, "", window.location.href);
    setShowQuitDialog(false);
  };

  // === UTILITY FUNCTIONS ===
  // Get status for question number buttons (answered, marked, current, etc.)
  const getQuestionStatus = (index: number, questionId: number) => {
    const isAnswered = answers[questionId] !== undefined;
    const isMarked = markedForReview.has(questionId);
    const isCurrent = index === currentQuestionIndex;

    if (isCurrent) return "current";
    if (isAnswered && isMarked) return "answered-marked";
    if (isAnswered) return "answered";
    if (isMarked) return "marked";
    return "default";
  };

  // Get CSS classes for question buttons based on status
  const getQuestionButtonClasses = (status: string) => {
    switch (status) {
      case "current":
        return "bg-[#4F83FF] text-white ring-2 ring-[#4F83FF] ring-offset-2";
      case "answered":
        return "bg-[#10B981] text-white";
      case "answered-marked":
        return "bg-[#8B5CF6] text-white";
      case "marked":
        return "bg-[#FCD34D] text-[#1F2937]";
      default:
        return "bg-[#E2E8F0] text-[#6B7280]";
    }
  };

  // Get CSS classes for question palette buttons
  const getPaletteButtonClasses = (status: string) => {
    switch (status) {
      case "current":
        return "bg-[#4F83FF] text-white";
      case "answered":
        return "bg-[#10B981] text-white";
      case "answered-marked":
        return "bg-[#8B5CF6] text-white";
      case "marked":
        return "bg-[#FCD34D] text-[#1F2937]";
      default:
        return "bg-[#E2E8F0] text-[#6B7280]";
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50 flex items-center justify-center">
        <div className="text-center bg-white rounded-2xl shadow-lg border border-[#E2E8F0] p-8 max-w-md mx-4">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-[#4F83FF] mx-auto"></div>
          <p className="mt-4 text-[#6B7280] font-medium">Loading test...</p>
        </div>
      </div>
    );
  }

  if (!testData || !currentQuestion) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50 flex items-center justify-center">
        <div className="text-center bg-white rounded-2xl shadow-lg border border-[#E2E8F0] p-8 max-w-md mx-4">
          <AlertTriangle className="h-16 w-16 text-[#DC2626] mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-[#1F2937] mb-2">
            Test Not Found
          </h2>
          <p className="text-[#6B7280]">
            Unable to load the test. Please try again.
          </p>
          <button
            onClick={() => window.location.href = '/topics'}
            className="mt-6 px-6 py-3 bg-[#4F83FF] text-white rounded-xl hover:bg-[#3B82F6] transition-colors shadow-md font-medium"
          >
            Return to Topics
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50 p-4">
      {/* Header with Navigation and Profile - matching home page */}
      <header className="w-full bg-white/95 backdrop-blur-sm border-b border-blue-100 sticky top-0 z-50 shadow-sm mb-6 rounded-2xl">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-[#4F83FF] rounded-lg flex items-center justify-center shadow-md">
                <Clock className="h-5 w-5 text-white" />
              </div>
              <h1 className="text-xl font-bold text-[#1F2937] tracking-tight">NEET Practice Test</h1>
            </div>
            <div className="flex items-center space-x-4">
              {testData.session.timeLimit ? (
                <>
                  <span className="text-sm font-medium text-[#1F2937]">Time Remaining:</span>
                  <Timer
                    initialMinutes={testData.session.timeLimit}
                    onTimeUp={handleTimeUp}
                    className="bg-[#FCD34D] text-[#1F2937] px-4 py-2 rounded-xl font-mono text-lg font-bold shadow-md"
                  />
                </>
              ) : (
                <div className="text-sm font-medium bg-[#F3F4F6] text-[#1F2937] px-4 py-2 rounded-xl font-mono text-lg font-bold shadow-md">
                  <Clock className="h-4 w-4 inline mr-1" />
                  No Time Limit
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto">
        <Card className="bg-white border border-[#E2E8F0] shadow-lg rounded-2xl overflow-hidden">
          {/* Test Progress Header */}
          <div className="bg-white text-[#1F2937] p-6 border-b border-[#E2E8F0]">
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-6 min-w-[350px]">
                <span className="font-semibold text-lg text-[#1F2937] whitespace-nowrap">
                  Question <span className="text-[#4F83FF]">{currentQuestionIndex + 1}</span> of {totalQuestions}
                </span>     
                <div className="mt-2">
                  <Progress 
                    value={progressPercentage} 
                    className="h-3 bg-[#E8F0FF] flex-1 min-w-[200px] w-[250px] md:w-[350px] rounded-full overflow-hidden"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Question Content */}
          <CardContent className="p-8">
            <div className="mb-8">
              <span className="inline-block bg-[#E8F0FF] text-[#4F83FF] text-sm px-3 py-1 rounded-full mb-4 font-medium">
                Question {currentQuestionIndex + 1}
              </span>
              <h3 className="text-xl font-semibold text-[#1F2937] leading-relaxed">
                {currentQuestion.question}
              </h3>
            </div>

            {/* Answer Options */}
            <RadioGroup
              value={answers[currentQuestion.id] || ""}
              onValueChange={(value) => handleAnswerChange(currentQuestion.id, value)}
              disabled={showTimeOverDialog} // Disable when time is over
            >
              <div className="space-y-4">
                {["A", "B", "C", "D"].map((option) => (
                  <Label
                    key={option}
                    className="flex items-center p-4 bg-[#F8FAFC] rounded-xl hover:bg-[#E8F0FF] cursor-pointer transition-colors border-2 border-[#E2E8F0] hover:border-[#4F83FF]/30"
                  >
                    <RadioGroupItem value={option} className="mr-4" />
                    <div className="flex items-center">
                      <span className="bg-[#E2E8F0] text-[#1F2937] w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold mr-4">
                        {option}
                      </span>
                      <span className="text-[#1F2937] font-medium">
                        {currentQuestion[`option${option}` as keyof Question]}
                      </span>
                    </div>
                  </Label>
                ))}
              </div>
            </RadioGroup>

            {/* Navigation Buttons */}
            <div className="flex justify-between mt-8">
              <Button
                onClick={handlePreviousQuestion}
                disabled={currentQuestionIndex === 0 || showTimeOverDialog}
                variant="outline"
                className="px-6 py-3 border-[#E2E8F0] text-[#6B7280] hover:bg-[#F8FAFC] hover:border-[#4F83FF]/30"
              >
                <ChevronLeft className="h-4 w-4 mr-2" />
                Previous
              </Button>
              <div className="flex space-x-4">
                <Button
                  onClick={handleMarkForReview}
                  variant="outline"
                  className="px-6 py-3 border-[#F59E0B] text-[#F59E0B] hover:bg-[#FEF3C7]"
                  disabled={showTimeOverDialog}
                >
                  <Bookmark className="h-4 w-4 mr-2" />
                  {markedForReview.has(currentQuestion.id) ? "Unmark" : "Mark for Review"}
                </Button>
                <Button
                  onClick={handleNextQuestion}
                  disabled={currentQuestionIndex === totalQuestions - 1 || showTimeOverDialog}
                  className="bg-[#4F83FF] text-white px-6 py-3 hover:bg-[#3B82F6] shadow-md"
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </div>
          </CardContent>

          {/* Question Navigation Panel */}
          <div className="bg-[#F8FAFC] border-t border-[#E2E8F0] p-6">
            <h4 className="text-sm font-semibold text-[#1F2937] mb-4">
              Question Navigation
            </h4>
            <div className="grid grid-cols-10 gap-2 mb-6">
              {testData.questions.map((question, index) => {
                const status = getQuestionStatus(index, question.id);
                const isCurrentQuestion = index === currentQuestionIndex;
                return (
                  <Button
                    key={question.id}
                    onClick={() => navigateToQuestion(index)}
                    size="sm"
                    disabled={showTimeOverDialog} // Disable question navigation when time is over
                    className={`w-8 h-8 rounded-lg text-xs font-semibold transition-colors ${
                      isCurrentQuestion 
                        ? "ring-2 ring-[#4F83FF] ring-offset-2" 
                        : ""
                    } ${getPaletteButtonClasses(status)} ${showTimeOverDialog ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {index + 1}
                  </Button>
                );
              })}
            </div>
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-6 text-xs text-[#6B7280]">
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-[#10B981] rounded mr-2"></div>
                  <span>Answered</span>
                </div>
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-[#F59E0B] rounded mr-2"></div>
                  <span>Marked for Review</span>
                </div>
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-[#E2E8F0] rounded mr-2"></div>
                  <span>Not Visited</span>
                </div>
              </div>
              <Button
                onClick={showTimeOverDialog ? handleTimeOverSubmit : handleSubmitTest}
                className={`px-6 py-2 font-semibold shadow-md ${
                  showTimeOverDialog 
                    ? 'bg-[#DC2626] hover:bg-[#B91C1C] text-white animate-pulse' 
                    : 'bg-[#DC2626] text-white hover:bg-[#B91C1C]'
                }`}
                disabled={submitTestMutation.isPending}
              >
                <Check className="h-4 w-4 mr-2" />
                {showTimeOverDialog ? 'Submit Test (Time Over)' : 'Submit Test'}
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Submit Confirmation Dialog */}
      <AlertDialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
        <AlertDialogContent className="bg-white border border-[#E2E8F0] rounded-2xl shadow-lg">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-[#1F2937] font-bold">Submit Test?</AlertDialogTitle>
            <AlertDialogDescription className="text-[#6B7280]">
              Are you sure you want to submit your test? This action cannot be undone.
              You have answered {Object.keys(answers).length} out of {totalQuestions} questions.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-[#E2E8F0] text-[#6B7280] hover:bg-[#F8FAFC]">Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={confirmSubmit}
              className="bg-[#DC2626] hover:bg-[#B91C1C] text-white"
            >
              Submit Test
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Time Over Dialog */}
      <AlertDialog open={showTimeOverDialog} onOpenChange={() => {}}>
        <AlertDialogContent className="border-[#FCA5A5] bg-[#FEF2F2] rounded-2xl shadow-lg">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-[#DC2626] flex items-center font-bold">
              <Clock className="h-5 w-5 mr-2" />
              Time Over!
            </AlertDialogTitle>
            <AlertDialogDescription className="text-[#DC2626]">
              Your test time has expired. Your test will be automatically submitted in 10 seconds, 
              or you can submit it now manually. You have answered{" "}
              {Object.keys(answers).length} out of {totalQuestions} questions.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction 
              onClick={handleTimeOverSubmit}
              className="bg-[#DC2626] hover:bg-[#B91C1C] text-white w-full"
            >
              <Check className="h-4 w-4 mr-2" />
              Submit Test Now
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Quit Exam Confirmation Dialog */}
      <AlertDialog open={showQuitDialog} onOpenChange={() => {}}>
        <AlertDialogContent className="border-[#FCD34D] bg-[#FEF3C7] rounded-2xl shadow-lg">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-[#F59E0B] flex items-center font-bold">
              <AlertTriangle className="h-5 w-5 mr-2" />
              Quit Exam?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-[#F59E0B]">
              Are you sure you want to quit the exam? Your test will be marked as incomplete and 
              you won't be able to resume it later. You have answered{" "}
              {Object.keys(answers).length} out of {totalQuestions} questions.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="gap-2">
            <AlertDialogCancel 
              onClick={handleQuitCancel}
              className="bg-[#10B981] hover:bg-[#059669] text-white border-none"
            >
              Continue Exam
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleQuitConfirm}
              className="bg-[#DC2626] hover:bg-[#B91C1C] text-white"
              disabled={quitTestMutation.isPending}
            >
              {quitTestMutation.isPending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Quitting...
                </>
              ) : (
                "Quit Exam"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
