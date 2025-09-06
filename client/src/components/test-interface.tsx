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

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Timer } from "@/components/timer";
import { useToast } from "@/hooks/use-toast";
import useFullscreenEnforcement from "@/hooks/useFullscreenEnforcement";
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
  Clock,
  Info
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
  const [timeOverHandled, setTimeOverHandled] = useState(false); // Track if time over has been handled
  const [showQuitDialog, setShowQuitDialog] = useState(false);                // Quit exam confirmation dialog visibility
  const [isNavigationBlocked, setIsNavigationBlocked] = useState(true);       // Block navigation during test
  const [started, setStarted] = useState(false); // Has the user started the test (entered fullscreen)
  const [isAwaitingFocusReturn, setIsAwaitingFocusReturn] = useState(false);   // Track if user tried to leave and needs to return
  const [lastFocusTime, setLastFocusTime] = useState<number>(Date.now());     // Track when window was last focused
  const [suppressFullscreenExitDialog, setSuppressFullscreenExitDialog] = useState(false); // Temporarily suppress quit dialog (e.g. during intentional submit)
  const [paused, setPaused] = useState(false); // Is the test paused by user
  const [pauseStartTime, setPauseStartTime] = useState<number | null>(null); // When the current pause started
  const [accumulatedPauseMs, setAccumulatedPauseMs] = useState<number>(0); // Total paused ms to subtract from timers
  
  // Prevent state updates / handlers from running while a submit is in progress
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Client-side test start timestamp (set when user first lands on first question)
  const [clientTestStartTime, setClientTestStartTime] = useState<number | null>(null);
  
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

  // Track mounted state to avoid updating state after unmount
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // Keep a ref mirror of isSubmitting to avoid stale closures in effects/cleanup
  const isSubmittingRef = useRef(isSubmitting);
  useEffect(() => { isSubmittingRef.current = isSubmitting; }, [isSubmitting]);

  // Ref for synchronous fullscreen exit suppression (to avoid race conditions)
  const suppressFullscreenExitDialogRef = useRef(suppressFullscreenExitDialog);
  useEffect(() => { suppressFullscreenExitDialogRef.current = suppressFullscreenExitDialog; }, [suppressFullscreenExitDialog]);

  // Track last logged visit start per question to prevent duplicate logs
  const lastLoggedVisitStartRef = useRef<Record<number, number>>({});
  // Track which question currently has an active visit (ref avoids stale closures)
  const currentVisitQuestionRef = useRef<number | null>(null);
  // Track current visit start time with ref for immediate access
  const currentVisitStartTimeRef = useRef<number>(0);

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

  // Reset time over handled flag when new test data loads
  useEffect(() => {
    if (testData) {
      setTimeOverHandled(false);
    }
  }, [testData]);

  // Set client-side test start timestamp when user first lands on the first question
  useEffect(() => {
    // Only set once: when testData is available, started (entered fullscreen or clicked start),
    // and we are on the first question (index 0)
    if (!clientTestStartTime && testData && started && currentQuestionIndex === 0) {
      const now = Date.now();
      console.log('⏱️ Client test start time set:', new Date(now).toISOString());
      setClientTestStartTime(now);
    }
  }, [clientTestStartTime, testData, started, currentQuestionIndex]);

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
      // Send client-side start/end timestamps to ensure server computes duration based on active test time
      const payload: any = {};
      if (clientTestStartTime) payload.clientStartTime = new Date(clientTestStartTime).toISOString();
      // client end time should be recorded at moment of submit click (avoid including post-processing time)
      payload.clientEndTime = new Date().toISOString();

      const response = await apiRequest(`/api/test-sessions/${sessionId}/submit/`, "POST", payload);
      return response;
    },
    onSuccess: () => {
      // Exit fullscreen (best-effort) before navigating away
      // Only exit if we're still in fullscreen and not already exiting
      if (document.fullscreenElement && !suppressFullscreenExitDialogRef.current) {
        try { exitFullscreen(); } catch (e) { /* ignore */ }
      }

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
  // Clean up state after navigation
  setIsSubmitting(false);
  setSuppressFullscreenExitDialog(false);
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to submit test. Please try again.",
        variant: "destructive",
      });
  // Clear suppression if submission failed
  setSuppressFullscreenExitDialog(false);
  setIsSubmitting(false);
  setTimeOverHandled(false); // Reset time over handled flag on error
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
  setSuppressFullscreenExitDialog(true);
  // Exit fullscreen (best-effort) before navigating away
  try { exitFullscreen(); } catch (e) { /* ignore */ }

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
  // Clean up state after navigation
  setIsSubmitting(false);
  setSuppressFullscreenExitDialog(false);
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to quit test. Please try again.",
        variant: "destructive",
      });
  setSuppressFullscreenExitDialog(false);
  setIsSubmitting(false);
  setTimeOverHandled(false); // Reset time over handled flag on error
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
    // Only log if this question currently has an active visit start recorded
    if (currentVisitQuestionRef.current !== questionId || currentVisitStartTimeRef.current === 0 || !sessionId) {
      console.log(`⏱️ Enhanced: Skipping log - no active visit for question ${questionId} (visitStart: ${currentVisitStartTimeRef.current}, activeQuestion: ${currentVisitQuestionRef.current}, sessionId: ${sessionId})`);
      // Reset visit marker cleanly
      currentVisitStartTimeRef.current = 0;
      currentVisitQuestionRef.current = null;
      if (mountedRef.current) {
        setCurrentVisitStartTime(0);
      }
      return;
    }

    // Prevent duplicate logs for the same question visit start
    const lastLoggedStart = lastLoggedVisitStartRef.current[questionId];
    if (lastLoggedStart && lastLoggedStart === currentVisitStartTimeRef.current) {
      console.log(`⏱️ Enhanced: Duplicate log suppressed for question ${questionId} (start ${currentVisitStartTimeRef.current})`);
      // Reset visit marker to allow fresh starts later
      currentVisitStartTimeRef.current = 0;
      currentVisitQuestionRef.current = null;
      if (mountedRef.current) {
        setCurrentVisitStartTime(0);
      }
      return;
    }

    // Subtract paused duration that occurred during this visit
    const effectiveEnd = endTime - accumulatedPauseMs;
    const effectiveStart = currentVisitStartTimeRef.current;
    const duration = Math.round((effectiveEnd - effectiveStart) / 1000);
    
    // Only log if user spent at least 1 second on question
    if (duration >= 1) {
      const payload = {
        sessionId: parseInt(sessionId.toString()),
        questionId,
        timeSpent: duration,
        visitStartTime: new Date(currentVisitStartTimeRef.current).toISOString(),
        visitEndTime: new Date(endTime).toISOString()
      };
      
      console.log(`⏱️ Enhanced: Sending time log payload:`, payload);
      
      // Mark as logged for this visit start before mutating to avoid races
      lastLoggedVisitStartRef.current[questionId] = currentVisitStartTimeRef.current;
      logTimeMutation.mutate(payload);

      // Update local visit tracking for analytics (guard with mountedRef)
      if (mountedRef.current) {
        setQuestionVisits(prev => ({
          ...prev,
          [questionId]: [
            ...(prev[questionId] || []),
            {
              startTime: currentVisitStartTimeRef.current,
              endTime,
              duration
            }
          ]
        }));

        console.log(`⏱️ Enhanced: Logged ${duration} seconds for question ${questionId}`);
      }
    }

    // Reset current visit marker so next question visit can start cleanly.
    // Do this outside the duration branch to avoid carrying start timestamps
    // into subsequent visits when duration < 1s.
    currentVisitStartTimeRef.current = 0;
    currentVisitQuestionRef.current = null;
    if (mountedRef.current) {
      setCurrentVisitStartTime(0);
    }
  };

  /**
   * Start tracking time for a new question visit
   */
  const startQuestionTimer = (questionId: number) => {
    const now = Date.now();
    setCurrentVisitStartTime(now);
    currentVisitStartTimeRef.current = now;
    // mark which question we are actively tracking
    currentVisitQuestionRef.current = questionId;
    // Reset pause accounting for the new visit
    setAccumulatedPauseMs(0);
    setPauseStartTime(null);
    
    console.log(`⏱️ Enhanced: Started timer for question ${questionId} at ${new Date(now).toISOString()}`);
  };

  // No need to pre-create answers - they will be created when user interacts

  const handleAnswerChange = (questionId: number, answer: string) => {
    // Prevent answering if time is over or fullscreen is not active
  if (showTimeOverDialog || !isFullscreenActive || !started || paused) {
      if ((!isFullscreenActive || !started) && !showQuitDialog) setShowQuitDialog(true);
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
    if (!currentQuestion || showTimeOverDialog || !isFullscreenActive || !started || paused) {
      if ((!isFullscreenActive || !started) && !showQuitDialog) setShowQuitDialog(true);
      return; // Prevent interaction when time is over or not fullscreen
    }

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
  if (currentQuestionIndex < totalQuestions - 1 && !showTimeOverDialog && isFullscreenActive && started && !paused) { // Prevent navigation when time is over or not fullscreen
  // Only change the current index and reset local start time.
  // Actual logging and visit-start for the previous/new question
  // is handled centrally in the effect that watches `currentQuestionIndex`.
  const nextIndex = currentQuestionIndex + 1;
  setCurrentQuestionIndex(nextIndex);
  setQuestionStartTime(Date.now()); // Reset local timer for next question
    }
  };

  const handlePreviousQuestion = () => {
  if (currentQuestionIndex > 0 && !showTimeOverDialog && isFullscreenActive && started && !paused) { // Prevent navigation when time is over or not fullscreen
  // Only change the current index and reset local start time.
  // Centralized effect will log the previous visit and start tracking the new one.
  const prevIndex = currentQuestionIndex - 1;
  setCurrentQuestionIndex(prevIndex);
  setQuestionStartTime(Date.now()); // Reset local timer for previous question
    }
  };

  const navigateToQuestion = (index: number) => {
  if (!showTimeOverDialog && isFullscreenActive && started && !paused) { // Prevent navigation when time is over or not fullscreen
      // Only change index and reset start time. The index-change effect
      // will handle logging the previous visit and starting the new visit.
      if (index !== currentQuestionIndex) {
        setCurrentQuestionIndex(index);
        setQuestionStartTime(Date.now()); // Reset local timer for target question
      }
    }
  };

  const handleSubmitTest = () => {
    if (!isFullscreenActive || !started) {
      if (!showQuitDialog) setShowQuitDialog(true);
      return;
    }

    setShowSubmitDialog(true);
  };

  const confirmSubmit = () => {
    // Enhanced time tracking: Log final question time before submission
    if (currentQuestion) {
      logCurrentQuestionTime(currentQuestion.id);
    }

    // Suppress fullscreen-exit dialog while performing intentional submit
    suppressFullscreenExitDialogRef.current = true;
    setSuppressFullscreenExitDialog(true);
    setIsSubmitting(true);

    // Close submit dialog immediately
    setShowSubmitDialog(false);

    // If paused, resume before submitting so timers and logs are consistent
    if (paused) {
      // end pause accounting
      const now = Date.now();
      if (pauseStartTime) setAccumulatedPauseMs(prev => prev + (now - pauseStartTime));
      setPaused(false);
      setPauseStartTime(null);
    }

    // Submit the test immediately without exiting fullscreen here
    // The fullscreen exit will be handled in the mutation success callback
    submitTestMutation.mutate();
  };

  const handleTimeUp = () => {
    // Enhanced time tracking: Log final question time when time runs out
    if (currentQuestion) {
      logCurrentQuestionTime(currentQuestion.id);
    }
    
    // Show time over dialog to inform the user
    setShowTimeOverDialog(true);
    
    // Set auto-submit after 10 seconds if user doesn't manually submit
    // Suppress fullscreen-exit dialogs while auto-submitting to avoid
    // fullscreen change handlers from opening modals or toggling state
    suppressFullscreenExitDialogRef.current = true;
    setSuppressFullscreenExitDialog(true);
    // mark submitting to prevent other handlers from running
    setIsSubmitting(true);
    const autoSubmitTimeout = setTimeout(() => {
      submitTestMutation.mutate();
      // only update state if still mounted
      if (mountedRef.current) {
        setShowTimeOverDialog(false);
        setTimeOverHandled(true); // Mark that time over has been handled
      }
    }, 10000); // 10 seconds delay
    
    setTimeOverAutoSubmit(autoSubmitTimeout);
  };

  const handleTimeOverSubmit = () => {
    // Clear auto-submit timeout since user is manually submitting
    if (timeOverAutoSubmit) {
      clearTimeout(timeOverAutoSubmit);
      setTimeOverAutoSubmit(null);
    }

    // Submit the test (intentional) - suppress exit dialog
    // Set suppression flags synchronously to prevent race conditions
    suppressFullscreenExitDialogRef.current = true;
    setSuppressFullscreenExitDialog(true);
    setIsSubmitting(true);
    setTimeOverHandled(true); // Mark that time over has been handled

    // Close the time over dialog immediately to prevent re-showing
    setShowTimeOverDialog(false);

    if (paused) {
      const now = Date.now();
      if (pauseStartTime) setAccumulatedPauseMs(prev => prev + (now - pauseStartTime));
      setPaused(false);
      setPauseStartTime(null);
    }

    // Submit the test immediately without exiting fullscreen here
    // The fullscreen exit will be handled in the mutation success callback
    submitTestMutation.mutate();
  };  // Clean up timeout on component unmount
  useEffect(() => {
    return () => {
      if (timeOverAutoSubmit) {
        clearTimeout(timeOverAutoSubmit);
      }
    };
  }, [timeOverAutoSubmit]);

  // === NAVIGATION GUARD IMPLEMENTATION ===
  // Enhanced but functional browser navigation prevention
  useEffect(() => {
    if (!isNavigationBlocked) return;

    // === AGGRESSIVE EVENT HANDLERS ===
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isNavigationBlocked) {
        e.preventDefault();
        e.returnValue = "TEST IN PROGRESS - You cannot leave during the exam!";
        return "TEST IN PROGRESS - You cannot leave during the exam!";
      }
    };

    const handlePopState = (e: PopStateEvent) => {
      if (isNavigationBlocked) {
        e.preventDefault();
        window.history.pushState(null, "", window.location.href);
        if (!isSubmitting) setShowQuitDialog(true);
        window.focus();
      }
    };

    // Detect when user switches tabs or minimizes window
    const handleWindowBlur = () => {
      if (isNavigationBlocked && !showQuitDialog && !showSubmitDialog && !showTimeOverDialog && !isSubmitting) {
        // Show quit dialog immediately - no delay
        setShowQuitDialog(true);
        document.title = "🚨 RETURN TO TEST - NEET Ninja";
      }
    };

    const handleWindowFocus = () => {
      if (isNavigationBlocked) {
        document.title = "NEET Test - NEET Ninja";
      }
    };

    const handleVisibilityChange = () => {
      if (isNavigationBlocked && document.hidden && !showQuitDialog && !showSubmitDialog && !showTimeOverDialog && !isSubmitting) {
        // Show quit dialog immediately when tab becomes hidden - no delay
        setShowQuitDialog(true);
        document.title = "🚨 RETURN TO TEST - NEET Ninja";
      } else if (isNavigationBlocked && !document.hidden) {
        document.title = "NEET Test - NEET Ninja";
      }
    };

    // Block common navigation keyboard shortcuts
    const handleKeyDown = (e: KeyboardEvent) => {
  if (isNavigationBlocked) {
        // Block critical navigation shortcuts including tab switching
        const shouldBlock = (
          (e.ctrlKey && ['w', 'W', 't', 'T', 'n', 'N'].includes(e.key)) ||
          (e.altKey && e.key === 'F4') ||
          (e.metaKey && ['w', 'W', 't', 'T', 'n', 'N'].includes(e.key)) ||
          e.key === 'F5' ||
          (e.ctrlKey && e.key === 'r') ||
          (e.ctrlKey && e.key === 'R') ||
          (e.ctrlKey && e.shiftKey && e.key === 'Tab') || // Ctrl+Shift+Tab
          (e.ctrlKey && e.key === 'Tab') || // Ctrl+Tab
          (e.altKey && e.key === 'Tab')    // Alt+Tab
        );
        
        if (shouldBlock) {
          e.preventDefault();
          e.stopPropagation();
          
          // Show quit dialog immediately for keyboard shortcuts
          if (!showQuitDialog && !showSubmitDialog && !showTimeOverDialog && !isSubmitting) {
            setShowQuitDialog(true);
          }
          
          // Show warning toast
          toast({
            title: "🚫 Navigation Blocked",
            description: "You cannot leave the test. Choose 'Return to Test' or 'End Test'.",
            variant: "destructive",
            duration: 2000,
          });
        }
      }
    };

    // Block right-click context menu
    const handleContextMenu = (e: MouseEvent) => {
      if (isNavigationBlocked) {
        e.preventDefault();
        return false;
      }
    };

    // === SETUP EVENT LISTENERS ===
    if (isNavigationBlocked) {
      // Setup history blocking
      window.history.pushState(null, "", window.location.href);
      window.addEventListener("popstate", handlePopState);
      
      // Setup unload blocking
      window.addEventListener("beforeunload", handleBeforeUnload);
      
      // Setup focus management (less aggressive)
      window.addEventListener("blur", handleWindowBlur);
      window.addEventListener("focus", handleWindowFocus);
      document.addEventListener("visibilitychange", handleVisibilityChange);
      
      // Setup keyboard blocking (only critical shortcuts)
      document.addEventListener("keydown", handleKeyDown);
      
      // Block context menu
      document.addEventListener("contextmenu", handleContextMenu);
      
      // Set initial page title
      document.title = "NEET Test - NEET Ninja";
    }

    return () => {
      // Cleanup all event listeners
      window.removeEventListener("popstate", handlePopState);
      window.removeEventListener("beforeunload", handleBeforeUnload);
      window.removeEventListener("blur", handleWindowBlur);
      window.removeEventListener("focus", handleWindowFocus);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("contextmenu", handleContextMenu);
    };
  }, [isNavigationBlocked, showQuitDialog, showSubmitDialog, showTimeOverDialog, isSubmitting]);

  // === QUIT DIALOG HANDLERS ===
  const handleQuitConfirm = () => {
    // Disable navigation blocking since user is intentionally leaving
    setIsNavigationBlocked(false);
    setShowQuitDialog(false);
    suppressFullscreenExitDialogRef.current = true;
    setSuppressFullscreenExitDialog(true);
  try { exitFullscreen(); } catch (e) { /* ignore */ }
  quitTestMutation.mutate();
  };

  // === FULLSCREEN ENFORCEMENT ===
  // Request fullscreen on test start and detect exits
  const onFullscreenExit = () => {
    // When fullscreen exit detected, show quit dialog and pause interactions
    // If suppression flag is set (we're intentionally submitting), do nothing
    // Use ref for synchronous check to avoid race conditions
    if (suppressFullscreenExitDialogRef.current || isSubmittingRef.current || timeOverHandled) {
      console.log('Fullscreen exit suppressed - intentional submission in progress or time over handled', {
        suppressFullscreenExitDialogRef: suppressFullscreenExitDialogRef.current,
        isSubmitting: isSubmittingRef.current,
        timeOverHandled
      });
      return;
    }

    // Don't show quit dialog if we're already handling time over or submit dialogs
    // Also check if time over dialog was just closed (prevent re-showing)
    if (!showQuitDialog && !showSubmitDialog && !showTimeOverDialog) {
      console.log('Showing quit dialog due to fullscreen exit');
      setShowQuitDialog(true);
    } else {
      console.log('Quit dialog not shown - another dialog is active:', {
        showQuitDialog,
        showSubmitDialog,
        showTimeOverDialog,
        timeOverHandled
      });
    }
  };

  const onFullscreenAutoSubmit = () => {
    // Auto-submit when grace period expires
    if (isSubmittingRef.current) return; // already submitting
    if (!showTimeOverDialog) {
      // Log current question time first
      if (currentQuestion) {
        logCurrentQuestionTime(currentQuestion.id);
      }
      // Suppress fullscreen-exit dialogs while auto-submitting to avoid
      // the fullscreen exit handler from showing dialogs and causing
      // conflicting state updates.
      // Set ref synchronously to prevent race conditions
      suppressFullscreenExitDialogRef.current = true;
      setSuppressFullscreenExitDialog(true);
      setIsSubmitting(true);
      setTimeOverHandled(true); // Mark that time over has been handled
      submitTestMutation.mutate();
      if (mountedRef.current) setShowTimeOverDialog(false);
      if (mountedRef.current) setShowQuitDialog(false);
    }
  };

  const { isFullscreenActive, requestFullscreen, exitFullscreen, cancelAutoSubmit } = useFullscreenEnforcement({
    gracePeriod: 10000, // 10s grace before auto-submit
    onExit: onFullscreenExit,
    onAutoSubmit: onFullscreenAutoSubmit,
    onFail: (err) => {
      // If request fails, show blocking modal using quit dialog with message
      setShowQuitDialog(true);
      toast({
        title: "Fullscreen Required",
        description: "This test requires fullscreen mode. Please allow fullscreen to continue.",
        variant: "destructive",
      });
    },
    toast: ({ title, description }) => {
      try {
        toast({ title, description });
      } catch (e) {
        // ignore
      }
    },
  });


  // === ENHANCED TIME TRACKING INITIALIZATION ===
  // Enhanced time tracking: Start timer when test data loads and current question is available
  useEffect(() => {
  // This effect used to start the visit timer when data first loads.
  // Timer start is now managed in the `currentQuestionIndex` effect to avoid
  // duplicate starts. Keep this effect for any future initialization needs.
  }, [testData, currentQuestion, isSubmitting]); // Run when test data or current question changes
  // NOTE: isSubmitting intentionally excluded previously; add it so handlers see the latest value

  // START TEST: request fullscreen via user gesture
  const startTest = async () => {
    if (!testData?.questions || !currentQuestion) return;
    try {
      const ok = await requestFullscreen();
      // requestFullscreen returns boolean from hook; treat truthy as success
      setStarted(!!ok);
      if (ok) {
        // Enable navigation blocking only after entering fullscreen
        setIsNavigationBlocked(true);
        // Start timers for current question
        startQuestionTimer(currentQuestion.id);
        setQuestionStartTime(Date.now());
      }
    } catch (e) {
      // onFail in hook already shows dialog/toast
      console.error("Start fullscreen failed", e);
    }
  };

  // Whenever the current question index changes, log the previous question's visit and start a new timer
  useEffect(() => {
    // If we have a previous question (index > 0), log its time
    const prevIndex = currentQuestionIndex - 1;
    const prevQuestion = testData?.questions?.[prevIndex];
    // Log the previous question once when index changes.
    if (prevQuestion && !isSubmitting) {
      logCurrentQuestionTime(prevQuestion.id);
    }

    // Start timer for the new current question only if we aren't already tracking a visit
    if (currentQuestion && currentVisitStartTimeRef.current === 0) {
      startQuestionTimer(currentQuestion.id);
    }
    setQuestionStartTime(Date.now());

    return () => {
      // On unmount: log current question time (avoid during submitting)
      if (currentQuestion && !isSubmitting) {
        logCurrentQuestionTime(currentQuestion.id);
      }
    };
  }, [currentQuestionIndex, isSubmitting]);

  // === DOCUMENT TITLE MANAGEMENT ===
  // Update document title to encourage return when user switches tabs
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (isNavigationBlocked) {
        if (document.hidden) {
          document.title = "🔴 NEET Test - Please Return to Complete Your Exam";
        } else {
          document.title = "NEET Practice Test";
        }
      }
    };

    if (isNavigationBlocked) {
      document.addEventListener("visibilitychange", handleVisibilityChange);
      // Set initial title
      document.title = "NEET Practice Test";
    }

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      // Restore original title when component unmounts
      document.title = "NEET Ninja";
    };
  }, [isNavigationBlocked]);

  // === QUIT DIALOG HANDLERS ===
  const handleQuitCancel = () => {
    // User chose to continue the exam
    setShowQuitDialog(false);
    setIsAwaitingFocusReturn(false);
    
    // Re-push the state to prevent navigation
    window.history.pushState(null, "", window.location.href);
    
    // Refocus the window and bring user back to test
    window.focus();
    
    // Reset page title
    document.title = "NEET Test - NEET Ninja";
    
    // Show encouraging message
    toast({
      title: "Welcome Back!",
      description: "Continue with your test. Stay focused to achieve your best score!",
      variant: "default",
    });
    
    // Re-request fullscreen and re-enable navigation blocking
    (async () => {
      try {
        await requestFullscreen();
        setIsNavigationBlocked(true);
        // Cancel any pending auto-submit scheduled by fullscreen hook
        cancelAutoSubmit();
      } catch (e) {
        // If fullscreen re-request fails, keep quit dialog closed but navigation stays blocked
        console.error("Failed to re-enter fullscreen on cancel", e);
      }
    })();
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
      // If testData exists but has no questions, or not enough questions, show a themed popup
      if (
        testData &&
        testData.questions &&
        (
          testData.questions.length === 0 ||
          (testData.session && testData.questions.length < testData.session.totalQuestions)
        )
      ) {
        return (
          <AlertDialog open={true}>
            <AlertDialogContent className="bg-white border border-[#E2E8F0] rounded-2xl shadow-lg max-w-md mx-auto">
              <AlertDialogHeader>
                <div className="flex flex-col items-center justify-center">
                  <Info className="h-14 w-14 text-blue-500 mb-2" />
                  <AlertDialogTitle className="text-[#1F2937] font-bold text-lg text-center mb-1">Insufficient Questions</AlertDialogTitle>
                  <AlertDialogDescription className="text-[#6B7280] text-center">
                    Not enough questions are available for your selected topics.<br />
                    Please choose different topics or broaden your selection.
                  </AlertDialogDescription>
                </div>
              </AlertDialogHeader>
              <AlertDialogFooter className="flex justify-center mt-4">
                <AlertDialogAction 
                  className="bg-[#4F83FF] text-white rounded-xl hover:bg-[#3B82F6] px-6 py-2 font-medium"
                  onClick={() => window.location.href = '/topics'}
                >
                  Return to Topic Selection
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        );
      }
    // Fallback for other errors
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
      {/* Preparing results overlay: shown while submit is in progress to improve UX */}
      {isSubmitting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/90">
          <div className="text-center px-6 py-8 max-w-sm rounded-lg">
            <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-[#1F2937]">Preparing your results...</h2>
            <p className="text-sm text-gray-600 mt-2">We are finalizing your test results. This may take a few seconds.</p>
          </div>
        </div>
      )}
      {/* START OVERLAY: require user gesture to enter fullscreen */}
      {!started && testData?.questions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-white rounded-2xl p-8 max-w-lg text-center">
            <h2 className="text-2xl font-bold mb-4">Start NEET Practice Test</h2>
            <p className="text-sm text-[#6B7280] mb-6">This test requires fullscreen mode. Click below to start and enter secure test mode.</p>
            <div className="flex justify-center">
              <Button onClick={startTest} className="bg-[#4F83FF] text-white px-6 py-3">Start Test (Enter Fullscreen)</Button>
            </div>
          </div>
        </div>
      )}
      {/* Secure Test Mode Banner */}
      {isNavigationBlocked && (
        <div className="w-full bg-blue-600 text-white px-4 py-2 text-center text-sm font-medium mb-2 rounded-xl shadow-lg">
          🔒 SECURE TEST MODE - Navigation shortcuts are restricted during the exam
        </div>
      )}
      
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
                  <div className="flex items-center space-x-3">
                    {started ? (
                      <Timer
                        initialMinutes={testData.session.timeLimit}
                        onTimeUp={handleTimeUp}
                        className="bg-[#FCD34D] text-[#1F2937] px-4 py-2 rounded-xl font-mono text-lg font-bold shadow-md"
                        paused={paused}
                      />
                    ) : (
                      <div className="text-sm font-medium bg-[#F3F4F6] text-[#6B7280] px-4 py-2 rounded-xl font-mono text-lg font-bold shadow-md">
                        Start test to begin timer
                      </div>
                    )}
                    {/* Pause / Resume button */}
                    {started && (
                      <Button
                        onClick={() => {
                          if (!paused) {
                            setPaused(true);
                            setPauseStartTime(Date.now());
                            // While paused, we should cancel any pending auto-submit scheduled by fullscreen hook
                            cancelAutoSubmit();
                          } else {
                            // resuming
                            const now = Date.now();
                            if (pauseStartTime) {
                              setAccumulatedPauseMs(prev => prev + (now - pauseStartTime));
                            }
                            setPauseStartTime(null);
                            setPaused(false);
                          }
                        }}
                        className="px-3 py-2 bg-[#10B981] text-white rounded-lg"
                      >
                        {paused ? 'Resume' : 'Pause'}
                      </Button>
                    )}
                  </div>
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

      {/* Security Warning Banner */}
      {isNavigationBlocked && (
        <div className="max-w-7xl mx-auto mb-4">
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3 flex items-center space-x-3">
            <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0" />
            <div className="text-sm text-yellow-800">
              <span className="font-medium">Secure Test Mode:</span> Tab switching and window navigation are blocked during the test. Use "Quit Exam" to leave.
            </div>
          </div>
        </div>
      )}

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
      <AlertDialog open={showTimeOverDialog && !timeOverHandled} onOpenChange={() => {}}>
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
        <AlertDialogContent className="border-[#4F83FF] bg-[#E8F0FF] rounded-2xl shadow-lg">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-[#2563EB] flex items-center font-bold">
              <AlertTriangle className="h-5 w-5 mr-2 text-[#4F83FF]" />
              Quit Exam?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-[#2563EB]">
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
              className="bg-[#4F83FF] hover:bg-[#2563EB] text-white"
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
