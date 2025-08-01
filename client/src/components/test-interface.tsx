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
      
      console.log('✅ Test session fetch successful');
      return response.json();
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

  const currentQuestion = testData?.questions[currentQuestionIndex];
  const totalQuestions = testData?.questions.length || 0;
  const progressPercentage = totalQuestions > 0 ? ((currentQuestionIndex + 1) / totalQuestions) * 100 : 0;

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
      // Track time spent on current question
      if (currentQuestion) {
        const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
        setQuestionTimes(prev => ({
          ...prev,
          [currentQuestion.id]: (prev[currentQuestion.id] || 0) + timeSpent
        }));
      }
      
      setCurrentQuestionIndex(prev => prev + 1);
      setQuestionStartTime(Date.now()); // Reset timer for next question
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0 && !showTimeOverDialog) { // Prevent navigation when time is over
      // Track time spent on current question
      if (currentQuestion) {
        const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
        setQuestionTimes(prev => ({
          ...prev,
          [currentQuestion.id]: (prev[currentQuestion.id] || 0) + timeSpent
        }));
      }
      
      setCurrentQuestionIndex(prev => prev - 1);
      setQuestionStartTime(Date.now()); // Reset timer for previous question
    }
  };

  const navigateToQuestion = (index: number) => {
    if (!showTimeOverDialog) { // Prevent navigation when time is over
      setCurrentQuestionIndex(index);
    }
  };

  const handleSubmitTest = () => {
    setShowSubmitDialog(true);
  };

  const confirmSubmit = () => {
    submitTestMutation.mutate();
    setShowSubmitDialog(false);
  };

  const handleTimeUp = () => {
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
      
      // Prevent tab close/refresh
      window.addEventListener("beforeunload", handleBeforeUnload);
    }

    return () => {
      window.removeEventListener("popstate", handlePopState);
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [isNavigationBlocked]);

  // Disable navigation blocking when component unmounts or test completes
  useEffect(() => {
    return () => {
      setIsNavigationBlocked(false);
    };
  }, []);

  // === QUIT EXAM HANDLERS ===
  const handleQuitExam = () => {
    setShowQuitDialog(false);
    quitTestMutation.mutate();
  };

  const handleContinueExam = () => {
    setShowQuitDialog(false);
  };

  const getQuestionStatus = (questionId: number) => {
    if (answers[questionId]) {
      return markedForReview.has(questionId) ? "answered-marked" : "answered";
    }
    return markedForReview.has(questionId) ? "marked" : "not-visited";
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "answered":
        return "bg-neet-blue text-white";
      case "answered-marked":
        return "bg-purple-500 text-white";
      case "marked":
        return "bg-amber-200 text-amber-800";
      default:
        return "bg-slate-200 text-slate-700";
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-neet-blue"></div>
          <p className="mt-4 text-slate-600">Loading test...</p>
        </div>
      </div>
    );
  }

  if (!testData || !currentQuestion) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-slate-900 mb-2">
            Test Not Found
          </h2>
          <p className="text-slate-600">
            Unable to load the test. Please try again.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neet-gray-50">
      <Card className="dashboard-card shadow-xl overflow-hidden">
        {/* Test Header */}
        <div className="bg-gradient-to-r from-neet-gray-50 to-neet-gray-100 border-b border-neet-gray-200 px-6 py-5">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-6">
              <div className="text-sm text-neet-gray-600 font-medium">
                Question{" "}
                <span className="font-bold text-neet-gray-900 text-lg">
                  {currentQuestionIndex + 1}
                </span>{" "}
                of <span className="font-semibold">{totalQuestions}</span>
              </div>
              <Progress value={progressPercentage} className="w-64 h-2" />
            </div>
            <div className="flex items-center space-x-4">
              {testData.session.timeLimit ? (
                <>
                  <div className="text-sm text-neet-gray-600 font-medium">Time Remaining:</div>
                  <Timer
                    initialMinutes={testData.session.timeLimit}
                    onTimeUp={handleTimeUp}
                    className="bg-gradient-to-r from-neet-amber to-amber-500 text-white px-4 py-2 rounded-xl font-mono text-lg font-bold shadow-md"
                  />
                </>
              ) : (
                <div className="text-sm text-neet-gray-600 font-medium bg-neet-blue text-white px-4 py-2 rounded-xl font-mono text-lg font-bold shadow-md">
                  <Clock className="h-4 w-4 inline mr-1" />
                  No Time Limit
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Question Content */}
        <CardContent className="p-8">
          <div className="mb-6">
            <span className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full mb-4">
              Question {currentQuestionIndex + 1}
            </span>
            <h3 className="text-xl font-medium text-slate-900 leading-relaxed">
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
                  className="flex items-center p-4 bg-slate-50 rounded-lg hover:bg-blue-50 cursor-pointer transition-colors border-2 border-transparent hover:border-blue-200"
                >
                  <RadioGroupItem value={option} className="mr-4" />
                  <div className="flex items-center">
                    <span className="bg-slate-200 text-slate-700 w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold mr-3">
                      {option}
                    </span>
                    <span className="text-slate-800">
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
              className="px-6 py-3"
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Previous
            </Button>
            <div className="flex space-x-4">
              <Button
                onClick={handleMarkForReview}
                variant="outline"
                className="px-6 py-3"
                disabled={showTimeOverDialog}
              >
                <Bookmark className="h-4 w-4 mr-2" />
                {markedForReview.has(currentQuestion.id) ? "Unmark" : "Mark for Review"}
              </Button>
              <Button
                onClick={handleNextQuestion}
                disabled={currentQuestionIndex === totalQuestions - 1 || showTimeOverDialog}
                className="bg-neet-blue text-white px-6 py-3 hover:bg-blue-700"
              >
                Next
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </div>
        </CardContent>

        {/* Question Navigation Panel */}
        <div className="bg-slate-50 border-t border-slate-200 p-6">
          <h4 className="text-sm font-medium text-slate-700 mb-4">
            Question Navigation
          </h4>
          <div className="grid grid-cols-10 gap-2 mb-6">
            {testData.questions.map((question, index) => {
              const status = getQuestionStatus(question.id);
              const isCurrentQuestion = index === currentQuestionIndex;
              return (
                <Button
                  key={question.id}
                  onClick={() => navigateToQuestion(index)}
                  size="sm"
                  disabled={showTimeOverDialog} // Disable question navigation when time is over
                  className={`w-8 h-8 rounded text-xs font-semibold transition-colors ${
                    isCurrentQuestion 
                      ? "ring-2 ring-neet-blue ring-offset-2" 
                      : ""
                  } ${getStatusColor(status)} ${showTimeOverDialog ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {index + 1}
                </Button>
              );
            })}
          </div>
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-6 text-xs text-slate-600">
              <div className="flex items-center">
                <div className="w-4 h-4 bg-neet-blue rounded mr-2"></div>
                <span>Answered</span>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 bg-amber-200 rounded mr-2"></div>
                <span>Marked for Review</span>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 bg-slate-200 rounded mr-2"></div>
                <span>Not Visited</span>
              </div>
            </div>
            <Button
              onClick={showTimeOverDialog ? handleTimeOverSubmit : handleSubmitTest}
              className={`px-6 py-2 font-medium ${
                showTimeOverDialog 
                  ? 'bg-red-600 hover:bg-red-700 text-white animate-pulse' 
                  : 'bg-neet-red text-white hover:bg-red-700'
              }`}
              disabled={submitTestMutation.isPending}
            >
              <Check className="h-4 w-4 mr-2" />
              {showTimeOverDialog ? 'Submit Test (Time Over)' : 'Submit Test'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Submit Confirmation Dialog */}
      <AlertDialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Submit Test?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to submit your test? This action cannot be undone.
              You have answered {Object.keys(answers).length} out of {totalQuestions} questions.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={confirmSubmit}
              className="bg-neet-red hover:bg-red-700"
            >
              Submit Test
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Time Over Dialog */}
      <AlertDialog open={showTimeOverDialog} onOpenChange={() => {}}>
        <AlertDialogContent className="border-red-200 bg-red-50">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-red-700 flex items-center">
              <Clock className="h-5 w-5 mr-2" />
              Time Over!
            </AlertDialogTitle>
            <AlertDialogDescription className="text-red-600">
              Your test time has expired. Your test will be automatically submitted in 10 seconds, 
              or you can submit it now manually. You have answered{" "}
              {Object.keys(answers).length} out of {totalQuestions} questions.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction 
              onClick={handleTimeOverSubmit}
              className="bg-red-600 hover:bg-red-700 text-white w-full"
            >
              <Check className="h-4 w-4 mr-2" />
              Submit Test Now
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Quit Exam Confirmation Dialog */}
      <AlertDialog open={showQuitDialog} onOpenChange={() => {}}>
        <AlertDialogContent className="border-amber-200 bg-amber-50">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-amber-700 flex items-center">
              <AlertTriangle className="h-5 w-5 mr-2" />
              Quit Exam?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-amber-600">
              Are you sure you want to quit the exam? Your test will be marked as incomplete and 
              you won't be able to resume it later. You have answered{" "}
              {Object.keys(answers).length} out of {totalQuestions} questions.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="gap-2">
            <AlertDialogCancel 
              onClick={handleContinueExam}
              className="bg-green-600 hover:bg-green-700 text-white border-none"
            >
              Continue Exam
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleQuitExam}
              className="bg-red-600 hover:bg-red-700 text-white"
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
