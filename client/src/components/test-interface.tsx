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

import { useState, useEffect, useRef, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import useFullscreenEnforcement from "@/hooks/useFullscreenEnforcement";
import TestHeader from "./test-interface/TestHeader";
import SecurityBanner from "./test-interface/SecurityBanner";
import { API_CONFIG } from "@/config/api";
import { apiRequest } from "@/lib/queryClient";
import { setPostTestHidden } from "@/lib/postTestHidden";
import { authenticatedFetch } from "@/lib/auth";
import normalizeImageSrc from "@/lib/media";
import { unlockAudio } from "@/utils/tts";
import { ChevronLeft, ChevronRight, Bookmark, AlertTriangle, Info, X, Flag } from "lucide-react";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, } from "@/components/ui/alert-dialog";
import SubmitDialog from "./test-interface/dialogs/SubmitDialog";
import TimeOverDialog from "./test-interface/dialogs/TimeOverDialog";
import QuitDialog from "./test-interface/dialogs/QuitDialog";
import QuestionFeedbackDialog from "./test-interface/dialogs/QuestionFeedbackDialog";

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
  questionType?: string | null;  // Question type: 'NVT' for descriptive, 'Blank'/null for MCQ
  optionA: string;
  optionB: string;
  optionC: string;
  optionD: string;
  // Optional base64 image fields (camelCase for frontend usage)
  questionImage?: string | null;
  optionAImage?: string | null;
  optionBImage?: string | null;
  optionCImage?: string | null;
  optionDImage?: string | null;
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
    testType?: string;  // 'platform' | 'custom' | 'pyq'
  };
  questions: Question[];
}

/**
 * Main Test Interface Component
 * Handles the complete test-taking experience
 */
export function TestInterface({ sessionId }: TestInterfaceProps) {
  // === NAVIGATION AND UI STATE ===
  const [location, navigate] = useLocation();          // Navigation function and current location
  const { toast } = useToast();                        // Toast notifications
  const queryClient = useQueryClient();                // React Query client for cache management

  // === TEST STATE MANAGEMENT ===
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);        // Current question index
  const [answers, setAnswers] = useState<Record<number, string>>({});         // User's MCQ answers by question ID (A/B/C/D)
  const [textAnswers, setTextAnswers] = useState<Record<number, string>>({});  // User's text answers for NVT questions
  const [markedForReview, setMarkedForReview] = useState<Set<number>>(new Set()); // Questions marked for review
  const [bookmarkedQuestions, setBookmarkedQuestions] = useState<Set<number>>(new Set()); // Questions bookmarked by user
  const [answerIds, setAnswerIds] = useState<Record<number, number>>({});     // Map questionId -> answerId for PATCH requests
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);            // Submit confirmation dialog visibility
  const [showTimeOverDialog, setShowTimeOverDialog] = useState(false);        // Time over dialog visibility
  const timeOverAutoSubmitRef = useRef<ReturnType<typeof setTimeout> | null>(null); // Auto-submit timeout (ref for synchronous access)
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

  // === QUESTION FEEDBACK STATE ===
  const [showFeedbackDialog, setShowFeedbackDialog] = useState(false);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [submittedFeedback, setSubmittedFeedback] = useState<Set<number>>(new Set()); // Track which questions have feedback

  // Prevent state updates / handlers from running while a submit is in progress
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Client-side test start timestamp (set when user first lands on first question)
  const [clientTestStartTime, setClientTestStartTime] = useState<number | null>(null);
  // Header measured height (used to offset fixed header)
  const [headerHeight, setHeaderHeight] = useState<number>(0);

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

  // Fetch existing answers to initialize bookmarks and answer IDs
  const { data: existingAnswers } = useQuery({
    queryKey: [`testAnswers-${sessionId}`],
    queryFn: async () => {
      const response = await authenticatedFetch(
        `${API_CONFIG.BASE_URL}/api/test-answers/?session_id=${sessionId}`
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch answers: ${response.status}`);
      }
      return response.json();
    },
    enabled: !!sessionId && !!testData,
  });

  // Initialize bookmarks and answer IDs from existing answers
  useEffect(() => {
    if (existingAnswers && Array.isArray(existingAnswers)) {
      const bookmarks = new Set<number>();
      const ids: Record<number, number> = {};
      
      existingAnswers.forEach((answer: any) => {
        if (answer.is_bookmarked) {
          bookmarks.add(answer.question);
        }
        ids[answer.question] = answer.id;
      });
      
      setBookmarkedQuestions(bookmarks);
      setAnswerIds(ids);
    }
  }, [existingAnswers]);

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
      selectedAnswer?: string | null;  // The student's MCQ choice (A, B, C, D) or null
      textAnswer?: string | null;      // The student's text answer for NVT questions
      markedForReview?: boolean;      // Whether student marked question for review
      isBookmarked?: boolean;         // Whether student bookmarked question
      timeSpent?: number;             // Time spent on this question in seconds
    }) => {
      const response = await apiRequest(API_CONFIG.ENDPOINTS.TEST_ANSWERS, "POST", data);
      return response;
    },
    onSuccess: (data, variables) => {
      // Store answer ID and bookmark status when answer is created/updated
      if (data?.id) {
        setAnswerIds(prev => ({
          ...prev,
          [variables.questionId]: data.id
        }));
        
        // Update bookmark state if returned from server
        if (data.is_bookmarked !== undefined) {
          setBookmarkedQuestions(prev => {
            const newSet = new Set(prev);
            if (data.is_bookmarked) {
              newSet.add(variables.questionId);
            } else {
              newSet.delete(variables.questionId);
            }
            return newSet;
          });
        }
      }
    },
  });

  // Bookmark mutation to toggle bookmark status
  const toggleBookmarkMutation = useMutation({
    mutationFn: async (data: {
      answerId: number;        // The answer ID to update
      isBookmarked: boolean;   // New bookmark state
    }) => {
      const response = await apiRequest(
        `${API_CONFIG.ENDPOINTS.TEST_ANSWERS}${data.answerId}/`,
        "PATCH",
        { is_bookmarked: data.isBookmarked }
      );
      return response;
    },
    onError: (error) => {
      console.error('Failed to toggle bookmark:', error);
      toast({
        title: "Bookmark Failed",
        description: "Could not update bookmark status. Please try again.",
        variant: "destructive",
      });
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

  // === QUESTION FEEDBACK MUTATION ===
  const submitFeedbackMutation = useMutation({
    mutationFn: async (data: {
      questionId: number;
      feedbackType: string;
      remarks: string;
    }) => {
      // Backend will get student_id from authenticated user (JWT token)
      // No need to send studentId in request body
      const response = await apiRequest(API_CONFIG.ENDPOINTS.QUESTION_FEEDBACK, "POST", {
        testId: sessionId,
        questionId: data.questionId,
        feedbackType: data.feedbackType,
        remarks: data.remarks,
      });
      return response;
    },
    onSuccess: (data, variables) => {
      toast({
        title: "Feedback Submitted",
        description: "Thank you for your feedback! We'll review this question.",
        variant: "default",
      });
      // Mark question as having feedback submitted
      setSubmittedFeedback(prev => new Set([...prev, variables.questionId]));
      setShowFeedbackDialog(false);
      setFeedbackSubmitting(false);
    },
    onError: (error: any) => {
      setFeedbackSubmitting(false);
      const errorMessage = error?.message || "Failed to submit feedback";
      toast({
        title: "Feedback Failed",
        description: errorMessage,
        variant: "destructive",
      });
    },
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
      // Navigation already handled in confirmSubmit - no need to navigate again
      // Just invalidate queries to refresh dashboard data
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

      // Clean up state
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
  // This mutation handles marking the test as completed when user quits
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
  // Cache for topic details to avoid repeated network calls
  const [topicCache, setTopicCache] = useState<Record<number, { name: string; subject?: string }>>({});
  const currentTopicId = currentQuestion ? (currentQuestion.topicId ?? (currentQuestion as any).topic) : null;
  const currentTopic = currentTopicId ? topicCache[currentTopicId] : undefined;

  // Ref to track which topic IDs have been fetched (prevents re-fetching)
  const requestedTopicIdsRef = useRef(new Set<number>());

  // Preload topic details for ALL questions (needed for subject tabs)
  useEffect(() => {
    if (!testData?.questions) return;
    const idsToFetch: number[] = [];
    testData.questions.forEach((q: any) => {
      const tid = q.topicId || q.topic;
      if (tid && !requestedTopicIdsRef.current.has(tid)) {
        requestedTopicIdsRef.current.add(tid);
        idsToFetch.push(tid);
      }
    });
    if (idsToFetch.length === 0) return;
    let mounted = true;
    (async () => {
      for (const tid of idsToFetch) {
        try {
          const res = await authenticatedFetch(`${API_CONFIG.BASE_URL}/api/topics/${tid}/`);
          if (!res.ok) continue;
          const data = await res.json();
          if (!mounted) return;
          setTopicCache(prev => ({ ...prev, [tid]: { name: data.name, subject: data.subject } }));
        } catch (e) { /* ignore */ }
      }
    })();
    return () => { mounted = false; };
  }, [testData?.questions]);

  // Get all unique subjects from questions (short form for tabs)
  const allSubjects = useMemo(() => {
    if (!testData?.questions) return [];
    const subjects = new Set<string>();
    testData.questions.forEach((q: any) => {
      const topicId = q.topicId || q.topic;
      const topic = topicCache[topicId];
      if (topic?.subject) {
        const shortSubject = topic.subject === 'Physics' ? 'Phy'
          : topic.subject === 'Chemistry' ? 'Che'
          : topic.subject === 'Botany' ? 'Bot'
          : topic.subject === 'Zoology' ? 'Zoo'
          : topic.subject;
        subjects.add(shortSubject);
      }
    });
    return Array.from(subjects);
  }, [testData?.questions, topicCache]);

  // Get current question's subject (short form)
  const currentSubject = useMemo(() => {
    if (!currentTopic?.subject) return '';
    return currentTopic.subject === 'Physics' ? 'Phy'
      : currentTopic.subject === 'Chemistry' ? 'Che'
      : currentTopic.subject === 'Botany' ? 'Bot'
      : currentTopic.subject === 'Zoology' ? 'Zoo'
      : currentTopic.subject;
  }, [currentTopic?.subject]);

  // Helper: get short subject for a question by index
  const getSubjectForQuestion = (q: any) => {
    const topicId = q.topicId || q.topic;
    const topic = topicCache[topicId];
    if (!topic?.subject) return '';
    return topic.subject === 'Physics' ? 'Phy'
      : topic.subject === 'Chemistry' ? 'Che'
      : topic.subject === 'Botany' ? 'Bot'
      : topic.subject === 'Zoology' ? 'Zoo'
      : topic.subject;
  };

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

    setAnswers(prev => {
      // If clicking the already selected answer, deselect it
      if (prev[questionId] === answer) {
        // Remove the answer
        const { [questionId]: _, ...rest } = prev;
        // Submit null to backend
        submitAnswerMutation.mutate({
          sessionId,
          questionId,
          selectedAnswer: null,
          timeSpent: questionTimes[questionId] || Math.round((Date.now() - questionStartTime) / 1000),
        });
        return rest;
      } else {
        // Set the answer
        // Calculate time spent on this question
        const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
        setQuestionTimes(prevTimes => ({
          ...prevTimes,
          [questionId]: (prevTimes[questionId] || 0) + timeSpent
        }));
        // Submit answer immediately with time tracking
        submitAnswerMutation.mutate({
          sessionId,
          questionId,
          selectedAnswer: answer,
          timeSpent: questionTimes[questionId] || timeSpent,
        });
        return {
          ...prev,
          [questionId]: answer
        };
      }
    });
  };

  // Handler for NVT (descriptive) text answer changes
  const handleTextAnswerChange = (questionId: number, textValue: string) => {
    // Prevent answering if time is over or fullscreen is not active
    if (showTimeOverDialog || !isFullscreenActive || !started || paused) {
      if ((!isFullscreenActive || !started) && !showQuitDialog) setShowQuitDialog(true);
      return;
    }

    // Update local state
    setTextAnswers(prev => ({
      ...prev,
      [questionId]: textValue
    }));
  };

  // Handler to submit NVT text answer (called on blur or explicit submit)
  const submitTextAnswer = (questionId: number) => {
    const textValue = textAnswers[questionId] || '';
    const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
    
    setQuestionTimes(prevTimes => ({
      ...prevTimes,
      [questionId]: (prevTimes[questionId] || 0) + timeSpent
    }));

    // Submit text answer to backend
    submitAnswerMutation.mutate({
      sessionId,
      questionId,
      textAnswer: textValue || null,
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

    // Determine if this is NVT or MCQ question
    const isNVT = currentQuestion.questionType === 'NVT';

    // Submit mark for review status with time tracking
    submitAnswerMutation.mutate({
      sessionId,
      questionId: currentQuestion.id,
      selectedAnswer: isNVT ? undefined : (answers[currentQuestion.id] || null),
      textAnswer: isNVT ? (textAnswers[currentQuestion.id] || null) : undefined,
      markedForReview: newMarkedSet.has(currentQuestion.id),
      timeSpent: questionTimes[currentQuestion.id] || timeSpent,
    });
  };

  const handleToggleBookmark = () => {
    if (!currentQuestion || showTimeOverDialog || !started || paused) {
      return; // Prevent interaction when time is over or test not started
    }

    const questionId = currentQuestion.id;
    const answerId = answerIds[questionId];
    
    // Toggle the bookmark state optimistically
    const isCurrentlyBookmarked = bookmarkedQuestions.has(questionId);
    const newBookmarkState = !isCurrentlyBookmarked;

    setBookmarkedQuestions(prev => {
      const newSet = new Set(prev);
      if (newBookmarkState) {
        newSet.add(questionId);
      } else {
        newSet.delete(questionId);
      }
      return newSet;
    });

    // If we don't have an answer ID yet, create an answer first with bookmark flag
    if (!answerId) {
      const isNVT = currentQuestion.questionType === 'NVT';
      const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
      
      setQuestionTimes(prev => ({
        ...prev,
        [questionId]: (prev[questionId] || 0) + timeSpent
      }));

      // Submit answer WITH is_bookmarked flag to create the answer and set bookmark in one call
      submitAnswerMutation.mutate({
        sessionId,
        questionId,
        selectedAnswer: isNVT ? undefined : (answers[questionId] || null),
        textAnswer: isNVT ? (textAnswers[questionId] || null) : undefined,
        markedForReview: markedForReview.has(questionId),
        isBookmarked: newBookmarkState,  // ADDED: Include bookmark state in initial creation
        timeSpent: questionTimes[questionId] || timeSpent,
      });
    } else {
      // We have an answer ID, just update the bookmark
      toggleBookmarkMutation.mutate({
        answerId,
        isBookmarked: newBookmarkState,
      });
    }
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

    // Cancel any pending auto-submit timers (fullscreen hook)
    cancelAutoSubmit();

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

    // Exit fullscreen and disable navigation blocking immediately
    try { 
      if (document.fullscreenElement) {
        exitFullscreen(); 
      }
    } catch (e) { /* ignore */ }
    setIsNavigationBlocked(false);

    // Navigate based on test type:
    // - Platform tests: show loading page with insights generation
    // - PYQ/Custom tests: skip loading page, go directly to results
    const testType = testData?.session?.testType;
    if (testType === 'platform') {
      navigate(`/loading-results/${sessionId}`);
    } else {
      // Skip loading page for PYQ and custom tests (no insights generation)
      navigate(`/results/${sessionId}`);
    }

    // Submit the test in background (mutation will complete while loading/results page is shown)
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
      // Guard: Don't execute if component unmounted or already handled
      if (!mountedRef.current || timeOverHandled) {
        console.log('⏱️ Auto-submit cancelled: component unmounted or already handled');
        return;
      }

      // Cancel the fullscreen hook's auto-submit timer to avoid double submission
      cancelAutoSubmit();
      
      // Exit fullscreen and disable navigation blocking
      try { 
        if (document.fullscreenElement) {
          exitFullscreen(); 
        }
      } catch (e) { /* ignore */ }
      setIsNavigationBlocked(false);

      // Navigate based on test type (same logic as manual submit)
      const testType = testData?.session?.testType;
      if (testType === 'platform') {
        navigate(`/loading-results/${sessionId}`);
      } else {
        navigate(`/results/${sessionId}`);
      }

      // Submit mutation in background
      submitTestMutation.mutate();

      // only update state if still mounted
      if (mountedRef.current) {
        setShowTimeOverDialog(false);
        setTimeOverHandled(true); // Mark that time over has been handled
      }
    }, 10000); // 10 seconds delay

    // Store in ref for synchronous access (state updates are async)
    timeOverAutoSubmitRef.current = autoSubmitTimeout;
  };

  const handleTimeOverSubmit = () => {
    // Clear auto-submit timeout since user is manually submitting
    if (timeOverAutoSubmitRef.current) {
      clearTimeout(timeOverAutoSubmitRef.current);
      timeOverAutoSubmitRef.current = null;
    }

    // IMPORTANT: Cancel the fullscreen hook's auto-submit timer too
    cancelAutoSubmit();

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

    // Exit fullscreen and disable navigation blocking immediately
    try { 
      if (document.fullscreenElement) {
        exitFullscreen(); 
      }
    } catch (e) { /* ignore */ }
    setIsNavigationBlocked(false);

    // Navigate based on test type (same logic as other submit flows)
    const testType = testData?.session?.testType;
    if (testType === 'platform') {
      navigate(`/loading-results/${sessionId}`);
    } else {
      navigate(`/results/${sessionId}`);
    }

    // Submit the test in background
    submitTestMutation.mutate();
  };
  
  // Clean up timeout on component unmount
  useEffect(() => {
    return () => {
      if (timeOverAutoSubmitRef.current) {
        clearTimeout(timeOverAutoSubmitRef.current);
        timeOverAutoSubmitRef.current = null;
      }
    };
  }, []); // Empty deps - cleanup runs on unmount only

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
    // Guard: Don't execute if component unmounted, already handled, or already submitting
    if (!mountedRef.current || timeOverHandled || isSubmittingRef.current) {
      console.log('⏱️ Fullscreen auto-submit cancelled: component unmounted, already handled, or already submitting');
      return;
    }

    // Guard: Don't execute if we're not on the test page anymore (already navigated)
    if (location !== `/test/${sessionId}`) {
      console.log('⏱️ Fullscreen auto-submit cancelled: already navigated away from test page');
      return;
    }

    // Auto-submit when grace period expires
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
  // Count total answered questions (MCQ + NVT)
  const getTotalAnsweredCount = () => {
    const mcqCount = Object.keys(answers).length;
    const nvtCount = Object.keys(textAnswers).filter(key => textAnswers[parseInt(key)]?.trim() !== '').length;
    return mcqCount + nvtCount;
  };

  // Get status for question number buttons (answered, marked, current, etc.)
  const getQuestionStatus = (index: number, questionId: number) => {
    // Check if question is answered (either MCQ or NVT)
    const isAnswered = answers[questionId] !== undefined || (textAnswers[questionId] && textAnswers[questionId].trim() !== '');
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
        return "bg-blue-500 text-white ring-2 ring-blue-500 ring-offset-2";
      case "answered":
        return "bg-green-500 text-white";
      case "answered-marked":
        return "bg-amber-400 text-gray-900";
      case "marked":
        return "bg-amber-400 text-gray-900";
      default:
        return "bg-gray-200 text-gray-600";
    }
  };

  // Get CSS classes for question palette buttons
  const getPaletteButtonClasses = (status: string) => {
    switch (status) {
      case "current":
        return "bg-blue-500 text-white";
      case "answered":
        return "bg-green-500 text-white";
      case "answered-marked":
        return "bg-amber-400 text-gray-900";
      case "marked":
        return "bg-amber-400 text-gray-900";
      default:
        return "bg-gray-200 text-gray-600";
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundImage: "url('/testpage-bg.webp')", backgroundSize: 'cover', backgroundPosition: 'center' }}>
        <div className="text-center bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg border border-white/50 p-6 max-w-sm mx-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-slate-500 font-medium text-sm">Loading test...</p>
        </div>
      </div>
    );
  }

  if (!testData || !currentQuestion) {
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
          <AlertDialogContent className="bg-white border border-gray-200 rounded-xl shadow-lg max-w-sm mx-4">
            <AlertDialogHeader>
              <div className="flex flex-col items-center justify-center">
                <Info className="h-12 w-12 text-blue-500 mb-2" />
                <AlertDialogTitle className="text-gray-900 font-bold text-lg text-center mb-1">Insufficient Questions</AlertDialogTitle>
                <AlertDialogDescription className="text-gray-500 text-center text-sm">
                  Not enough questions are available for your selected topics.<br />
                  Please choose different topics or broaden your selection.
                </AlertDialogDescription>
              </div>
            </AlertDialogHeader>
            <AlertDialogFooter className="flex justify-center mt-4">
              <AlertDialogAction
                className="bg-blue-500 text-white rounded-xl hover:bg-blue-600 px-4 py-2 font-medium text-sm"
                onClick={() => window.location.href = '/topics'}
              >
                Return to Topic Selection
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      );
    }
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundImage: "url('/testpage-bg.webp')", backgroundSize: 'cover', backgroundPosition: 'center' }}>
        <div className="text-center bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg border border-white/50 p-6 max-w-sm mx-4">
          <AlertTriangle className="h-12 w-12 text-red-600 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-gray-900 mb-2">Test Not Found</h2>
          <p className="text-gray-500 text-sm">Unable to load the test. Please try again.</p>
          <button
            onClick={() => window.location.href = '/topics'}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors shadow-md font-medium text-sm"
          >
            Return to Topics
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 flex flex-col" style={{ backgroundImage: "url('/testpage-bg.webp')", backgroundSize: 'cover', backgroundPosition: 'center', paddingTop: headerHeight }}>
      {/* === OVERLAYS === */}
      {isSubmitting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/90 px-4">
          <div className="text-center px-4 py-6 max-w-sm rounded-2xl">
            <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-600 mx-auto mb-4"></div>
            <h2 className="text-lg font-semibold text-gray-900">Submitting test...</h2>
            <p className="text-xs text-gray-600 mt-2">Redirecting to dashboard...</p>
          </div>
        </div>
      )}
      {!started && testData?.questions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
          <div className="bg-white rounded-2xl p-6 max-w-sm text-center mx-4">
            <h2 className="text-xl font-bold mb-4">Start NEET Practice Test</h2>
            <p className="text-xs text-gray-500 mb-6">This test requires fullscreen mode. Click below to start and enter secure test mode.</p>
            <div className="flex justify-center">
              <Button onClick={startTest} className="bg-blue-500 text-white px-4 py-2 text-sm">Start Test (Enter Fullscreen)</Button>
            </div>
          </div>
        </div>
      )}

      {/* === FIXED TOP SECTION === */}
      <div className="flex-shrink-0 z-40">
        {/* Top bar: Quit | NEET Bro | Timer | Submit */}
        <TestHeader
          started={started}
          paused={paused}
          timeLimit={testData.session.timeLimit}
          onTimeUp={handleTimeUp}
          onTogglePause={() => {
            if (!paused) {
              setPaused(true);
              setPauseStartTime(Date.now());
              cancelAutoSubmit();
            } else {
              const now = Date.now();
              if (pauseStartTime) setAccumulatedPauseMs(prev => prev + (now - pauseStartTime));
              setPauseStartTime(null);
              setPaused(false);
            }
          }}
          onSubmitTest={showTimeOverDialog ? handleTimeOverSubmit : handleSubmitTest}
          showTimeOverDialog={showTimeOverDialog}
          isSubmitting={isSubmitting}
          onQuit={() => setShowQuitDialog(true)}
          showPause={false}
          onHeightChange={setHeaderHeight}
        />

        {/* Security Banner removed */}

        {/* Subject tabs, question numbers and legend (moved down to avoid fixed header) */}
        <div>
        {allSubjects.length > 0 && (
          <div className="flex items-center justify-center gap-2 px-3 py-2 bg-white/70 backdrop-blur-sm">
            {allSubjects.map(sub => (
              <button
                key={sub}
                onClick={() => {
                  const idx = testData.questions.findIndex((q: any) => getSubjectForQuestion(q) === sub);
                  if (idx !== -1) navigateToQuestion(idx);
                }}
                className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                  sub === currentSubject
                    ? 'bg-slate-700 text-white shadow-sm'
                    : 'bg-white/80 text-slate-500 border border-slate-200 hover:bg-slate-100'
                }`}
              >
                {sub}
              </button>
            ))}
          </div>
        )}

        {/* Question numbers - horizontal scroll */}
        <div className="flex items-center gap-1.5 px-3 py-2 overflow-x-auto bg-white/70 backdrop-blur-sm hide-scrollbar" style={{ overscrollBehaviorX: 'auto', WebkitOverflowScrolling: 'touch' }}>
          {testData.questions.map((question, index) => {
            const status = getQuestionStatus(index, question.id);
            const isCurrentQ = index === currentQuestionIndex;
            return (
              <button
                key={question.id}
                onClick={() => navigateToQuestion(index)}
                disabled={showTimeOverDialog}
                className={`w-8 h-8 flex-shrink-0 rounded-lg text-xs font-bold transition-all ${
                  isCurrentQ
                    ? 'bg-blue-500 text-white ring-2 ring-blue-300 ring-offset-1'
                    : status === 'answered'
                      ? 'bg-green-500 text-white'
                      : status === 'answered-marked'
                        ? 'bg-amber-400 text-gray-900'
                        : status === 'marked'
                          ? 'bg-amber-400 text-gray-900'
                          : 'bg-slate-200/80 text-slate-600'
                } ${showTimeOverDialog ? 'opacity-50' : ''}`}
              >
                {index + 1}
              </button>
            );
          })}
        </div>

        {/* Legend row (centered, ellipsis removed) */}
        <div className="flex items-center justify-center px-3 py-1.5 bg-white/70 backdrop-blur-sm border-b border-slate-200/50">
          <div className="flex items-center gap-6 text-[10px] text-slate-500">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-slate-300 inline-block"></span> Not Visited</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 inline-block"></span> Answered</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400 inline-block"></span> Marked</span>
          </div>
        </div>
        </div>
      </div>

      {/* === SCROLLABLE QUESTION AREA === */}
      <div 
        className="flex-1 overflow-y-auto px-3 py-3"
        style={{
          overscrollBehavior: 'auto',
          WebkitOverflowScrolling: 'touch'
        }}
      >
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-lg border border-white/50 p-4">
          {/* Question number + bookmark + badge */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-baseline gap-1">
              <span className="text-lg font-bold text-slate-800">Q{currentQuestionIndex + 1}</span>
              <span className="text-sm text-slate-400 font-medium">/ {totalQuestions}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleMarkForReview}
                disabled={showTimeOverDialog}
                aria-pressed={markedForReview.has(currentQuestion?.id ?? -1)}
                aria-label="Mark for Review"
                title={markedForReview.has(currentQuestion?.id ?? -1) ? 'Marked' : 'Mark for Review'}
                className={`flex items-center gap-2 px-3 py-1 rounded-xl text-sm font-medium transition-colors border disabled:opacity-40 ${
                  markedForReview.has(currentQuestion?.id ?? -1)
                    ? 'bg-amber-50 border-amber-100 text-amber-600'
                    : 'bg-white/90 border-white/30 text-slate-600 hover:bg-white'
                }`}
              >
                <AlertTriangle className={`w-4 h-4 ${markedForReview.has(currentQuestion?.id ?? -1) ? 'text-amber-600' : 'text-slate-500'}`} />
                <span className="whitespace-nowrap">{markedForReview.has(currentQuestion?.id ?? -1) ? 'Marked' : 'Mark for Review'}</span>
              </button>
              <button
                onClick={handleToggleBookmark}
                disabled={showTimeOverDialog}
                aria-pressed={bookmarkedQuestions.has(currentQuestion?.id ?? -1)}
                aria-label="Bookmark"
                className={`size-8 flex items-center justify-center rounded-full transition-colors border ${
                  bookmarkedQuestions.has(currentQuestion?.id ?? -1)
                    ? 'bg-amber-50 border-amber-100 text-amber-600'
                    : 'bg-white/90 border-white/30 text-slate-600 hover:bg-white'
                }`}
                title="Bookmark"
              >
                <Bookmark className="w-4 h-4" />
              </button>
              {/* Question Feedback Button */}
              <button
                onClick={() => {
                  if (!showTimeOverDialog && !submittedFeedback.has(currentQuestion?.id ?? -1)) {
                    setShowFeedbackDialog(true);
                  }
                }}
                disabled={showTimeOverDialog || submittedFeedback.has(currentQuestion?.id ?? -1)}
                aria-label="Report Question Issue"
                className={`size-8 flex items-center justify-center rounded-full transition-colors border ${
                  submittedFeedback.has(currentQuestion?.id ?? -1)
                    ? 'bg-orange-50 border-orange-100 text-orange-400 cursor-not-allowed'
                    : 'bg-white/90 border-white/30 text-slate-600 hover:bg-white hover:text-orange-500'
                }`}
                title={submittedFeedback.has(currentQuestion?.id ?? -1) ? 'Feedback submitted' : 'Report issue with this question'}
              >
                <Flag className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Divider */}
          <div className="h-px bg-slate-200 mb-4"></div>

          {/* Question text */}
          <div className="mb-5">
            <h3 className="text-base font-semibold text-slate-800 leading-relaxed">
              {currentQuestion.question}
            </h3>
            {currentQuestion.questionImage && (
              <div className="my-3">
                <img
                  src={normalizeImageSrc(currentQuestion.questionImage)}
                  alt="question"
                  className="block max-w-full h-auto rounded-lg border border-slate-200"
                  style={{ maxHeight: '300px', objectFit: 'contain' }}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
              </div>
            )}
          </div>

          {/* Answer Options */}
          {currentQuestion.questionType === 'NVT' ? (
            <div className="space-y-3">
              <Label htmlFor="nvt-answer" className="text-sm font-medium text-slate-700">
                Enter your answer:
              </Label>
              <input
                id="nvt-answer"
                type="text"
                value={textAnswers[currentQuestion.id] || ''}
                onChange={(e) => handleTextAnswerChange(currentQuestion.id, e.target.value)}
                onBlur={() => submitTextAnswer(currentQuestion.id)}
                disabled={showTimeOverDialog}
                placeholder="Type your answer here..."
                className="w-full px-4 py-3 border-2 border-slate-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-200 text-base bg-white"
              />
            </div>
          ) : (
            <RadioGroup
              value={answers[currentQuestion.id] || ""}
              onValueChange={(value) => handleAnswerChange(currentQuestion.id, value)}
              disabled={showTimeOverDialog}
            >
              <div className="space-y-2.5">
                {["A", "B", "C", "D"].map((option) => {
                  const isSelected = answers[currentQuestion.id] === option;
                  return (
                    <Label
                      key={option}
                      className={`flex items-center p-3.5 rounded-xl cursor-pointer transition-all border-2 ${
                        isSelected
                          ? 'bg-blue-50 border-blue-400 shadow-sm'
                          : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <RadioGroupItem
                        value={option}
                        className="mr-3"
                        onClick={(e) => {
                          if (answers[currentQuestion.id] === option) {
                            e.preventDefault();
                            handleAnswerChange(currentQuestion.id, option);
                          }
                        }}
                      />
                      <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mr-3 flex-shrink-0 ${
                        isSelected ? 'bg-blue-500 text-white' : 'bg-slate-200 text-slate-700'
                      }`}>
                        {option}
                      </span>
                      <span className="text-sm text-slate-800 font-medium leading-relaxed flex-1">
                        {currentQuestion[`option${option}` as keyof Question]}
                      </span>
                      {(currentQuestion as any)[`option${option}Image`] && (
                        <div className="ml-2 mt-1">
                          <img
                            src={normalizeImageSrc((currentQuestion as any)[`option${option}Image`])}
                            alt={`option ${option}`}
                            className="block max-w-[120px] h-auto rounded-md border border-slate-200"
                            style={{ maxHeight: '100px', objectFit: 'contain' }}
                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                          />
                        </div>
                      )}
                    </Label>
                  );
                })}
              </div>
            </RadioGroup>
          )}
        </div>
        {/* Spacer for bottom bar */}
        <div className="h-4"></div>
      </div>

      {/* === FIXED BOTTOM BAR === */}
      <div className="flex-shrink-0 bg-white/90 backdrop-blur-md border-t border-slate-200 z-40">
        {/* Row 1: (removed Clear button — kept spacing for layout) */}
        <div className="px-3 pt-2 pb-1" />
        {/* Row 2: Previous & Next */}
        <div className="flex items-center gap-2 px-3 pb-3 pt-1">
          <button
            onClick={handlePreviousQuestion}
            disabled={currentQuestionIndex === 0 || showTimeOverDialog}
            className="flex items-center gap-1 flex-none basis-1/3 justify-center px-3 py-2.5 rounded-xl text-sm font-semibold text-slate-600 border border-slate-300 hover:bg-slate-50 disabled:opacity-40 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </button>
          {currentQuestionIndex === totalQuestions - 1 ? (
            <button
              onClick={handleSubmitTest}
              disabled={showTimeOverDialog || isSubmitting}
              className="flex items-center gap-1 flex-none basis-2/3 justify-center px-3 py-2.5 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-md disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Submit
            </button>
          ) : (
            <button
              onClick={handleNextQuestion}
              disabled={currentQuestionIndex === totalQuestions - 1 || showTimeOverDialog}
              className="flex items-center gap-1 flex-none basis-2/3 justify-center px-3 py-2.5 rounded-xl text-sm font-bold text-white bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 shadow-md disabled:opacity-40 transition-colors"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* === DIALOGS === */}
      <SubmitDialog
        isOpen={showSubmitDialog}
        answersCount={getTotalAnsweredCount()}
        totalQuestions={totalQuestions}
        onConfirm={confirmSubmit}
        onCancel={() => setShowSubmitDialog(false)}
      />
      <TimeOverDialog
        isOpen={showTimeOverDialog && !timeOverHandled}
        answersCount={getTotalAnsweredCount()}
        totalQuestions={totalQuestions}
        onSubmit={handleTimeOverSubmit}
      />
      <QuitDialog
        isOpen={showQuitDialog}
        answersCount={getTotalAnsweredCount()}
        totalQuestions={totalQuestions}
        isPending={quitTestMutation.isPending}
        onConfirm={handleQuitConfirm}
        onCancel={handleQuitCancel}
      />
      <QuestionFeedbackDialog
        isOpen={showFeedbackDialog}
        questionId={currentQuestion?.id ?? 0}
        onClose={() => {
          setShowFeedbackDialog(false);
          setFeedbackSubmitting(false);
        }}
        onSubmit={async (feedbackType, remarks) => {
          if (!currentQuestion) return;
          setFeedbackSubmitting(true);
          await submitFeedbackMutation.mutateAsync({
            questionId: currentQuestion.id,
            feedbackType,
            remarks,
          });
        }}
        isSubmitting={feedbackSubmitting}
      />
    </div>
  );
}
