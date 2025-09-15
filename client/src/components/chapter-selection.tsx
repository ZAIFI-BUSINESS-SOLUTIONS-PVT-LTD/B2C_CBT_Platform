/**
 * ChapterSelection
 *
 * Topic/chapter selection UI for creating practice tests.
 * Provides search, subject/chapter drilldown, and test creation flows.
 */

import { useState, useEffect, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { API_CONFIG } from "@/config/api";
import { ListCheck, Atom, FlaskConical, Dna, Clock, Play, Leaf, BookOpen, Search, X, Target, ChevronLeft } from "lucide-react";
import { SearchBar } from "./search-bar";
import { Slider } from "@/components/ui/slider";
import { Topic, CreateTestSessionResponse } from '../types/api';
import { useAuth } from "@/hooks/use-auth";

interface PaginatedTopicsResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Topic[];
}

/**
 * Main Chapter Selection Component
 * Handles topic selection, search, and test session creation
 */
export function ChapterSelection() {
  // === NAVIGATION AND UI STATE ===
  const [, navigate] = useLocation();          // Navigation function from wouter
  const { toast } = useToast();                // Toast notifications

  // === SELECTION AND FORM STATE ===
  // removed legacy `selectedTopics` state (using `selectedTopicsCustom` for custom selection)
  // Slider bounds (keep centralised for easy changes)
  const SLIDER_MIN = 5;
  const SLIDER_MAX = 180;
  const SLIDER_STEP = 5;
  const MAX_TIME_MULTIPLIER = 1.5; // 1 minute actual + 0.5 minute buffer per question

  // === STEP WIZARD STATE ===
  const [currentStep, setCurrentStep] = useState<number>(1);
  const totalSteps = 6;

  // === NEW UI STATE FOR WIREFRAME ===
  const [testType, setTestType] = useState<"custom">("custom"); // Test type selection (only custom)
  const [selectedSubjects, setSelectedSubjects] = useState<string[]>([]);      // Selected subjects for custom mode (multiple)
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);  // Selected chapters for custom mode (multiple)
  const [selectedTopicsCustom, setSelectedTopicsCustom] = useState<string[]>([]); // Topics for custom mode
  const [timeLimit, setTimeLimit] = useState<number>(60);                  // Time limit in minutes
  const [questionCount, setQuestionCount] = useState<number>(20);          // Number of questions
  const [lastChanged, setLastChanged] = useState<'time' | 'questions'>('questions');

  // === STEP NAVIGATION FUNCTIONS ===
  const nextStep = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const goToStep = (step: number) => {
    if (step >= 1 && step <= totalSteps) {
      setCurrentStep(step);
    }
  };
  const [expandedChapters, setExpandedChapters] = useState<string[]>([]);  // Expanded chapter IDs
  const [expandedSubjects, setExpandedSubjects] = useState<string[]>([]); // Expanded subject cards
  const [searchQuery, setSearchQuery] = useState<string>("");              // Search input value
  const [showSearchResults, setShowSearchResults] = useState<boolean>(false); // Search results visibility

  // === INSUFFICIENT QUESTIONS DIALOG STATE ===
  const [showInsufficientDialog, setShowInsufficientDialog] = useState<boolean>(false);
  const [insufficientQuestionsData, setInsufficientQuestionsData] = useState<{
    available: number;
    requested: number;
    message: string;
  } | null>(null);

  // === DATA FETCHING ===
  // Fetch all available topics from the PostgreSQL database
  const { data: topicsResponse, isLoading, error } = useQuery({
    queryKey: ["allTopics"], // Use a distinct key for fetching all topics
    queryFn: async () => {
      let allTopics: Topic[] = [];
      let nextUrl: string | null = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOPICS}`;

      console.log("🔄 Starting to fetch all topics...");

      while (nextUrl) {
        console.log("📡 Fetching page:", nextUrl);

        // Use fetch directly to handle pagination properly
        const response: Response = await fetch(nextUrl);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status} for URL: ${nextUrl}`);
        }

        const data: PaginatedTopicsResponse = await response.json();
        console.log(`✅ Fetched ${data.results.length} topics from this page. Total so far: ${allTopics.length + data.results.length}`);

        // Add the results from the current page to our accumulator
        allTopics = allTopics.concat(data.results);

        // Update nextUrl for the next iteration (null if no more pages)
        nextUrl = data.next;
      }

      console.log(`🎉 Finished fetching all topics. Total: ${allTopics.length}`);
      return { results: allTopics, count: allTopics.length }; // Return in consistent format
    },
  });

  // Debug logging
  console.log("📊 Topics query state:", { isLoading, error, totalTopics: topicsResponse?.results?.length });

  // Extract topics from response (Django format: { results: [...] })
  const topics = topicsResponse?.results || [];

  // Debug logging for topics data
  useEffect(() => {
    if (topics.length > 0) {
      const subjects = [...new Set(topics.map(t => t.subject))];
      const totalChapters = [...new Set(topics.map(t => `${t.subject}-${t.chapter}`))].length;
      console.log("📚 Topics loaded:", {
        totalTopics: topics.length,
        subjects: subjects,
        totalChapters: totalChapters,
        sampleTopics: topics.slice(0, 3)
      });

      // Debug specific subject data
      subjects.forEach(subject => {
        const subjectTopics = topics.filter(t => t.subject === subject);
        const subjectChapters = [...new Set(subjectTopics.map(t => t.chapter))];
        console.log(`📖 ${subject}: ${subjectTopics.length} topics, ${subjectChapters.length} chapters`, subjectChapters);
      });

      // Extra debug: Check data structure
      console.log("🔬 Raw topic sample:", JSON.stringify(topics.slice(0, 2), null, 2));
    }
  }, [topics]);

  const { student } = useAuth();

  // Query to get exact available questions count for individual topics
  const { data: topicQuestionCounts, isLoading: isLoadingTopicCounts } = useQuery({
    queryKey: ["topicQuestionCounts", selectedSubjects, selectedChapters, currentStep],
    queryFn: async () => {
      if (currentStep !== 3 || selectedSubjects.length === 0 || selectedChapters.length === 0) {
        return {} as Record<string, number>;
      }

      const selTopics = getTopicsForChapters(selectedSubjects, selectedChapters);
      const topicIds = selTopics.map(t => t.id);

      if (topicIds.length === 0) return {} as Record<string, number>;

      const params = new URLSearchParams();
      topicIds.forEach(id => params.append('topic_ids', String(id)));

      const endpoint = `${API_CONFIG.ENDPOINTS.TOPIC_QUESTION_COUNTS}?${params.toString()}`;
      console.log('📡 Fetching exact question counts:', endpoint);
      const res = await apiRequest(endpoint, 'GET');
      const counts = (res?.counts || {}) as Record<string, number>;
      console.log('✅ Received exact topic counts:', counts);
      return counts;
    },
    enabled: currentStep === 3 && selectedSubjects.length > 0 && selectedChapters.length > 0,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
  });

  // Initialize topic question counts as empty object when not available
  const topicQuestionCountsData = topicQuestionCounts || {};

  // Query to get total available questions for selected topics (sum of per-topic counts)
  const { data: availableQuestionsData, isLoading: isLoadingAvailableQuestions, error: availableQuestionsError } = useQuery({
    queryKey: ["availableQuestions", selectedTopicsCustom],
    queryFn: async () => {
      if (selectedTopicsCustom.length === 0) return { available: 0 };

      // Build params with selected topic ids
      const params = new URLSearchParams();
      selectedTopicsCustom.forEach(id => params.append('topic_ids', String(id)));

      const endpoint = `${API_CONFIG.ENDPOINTS.TOPIC_QUESTION_COUNTS}?${params.toString()}`;
      console.log('📡 Fetching total available questions for selected topics:', endpoint);
      const res = await apiRequest(endpoint, 'GET');
      const counts = (res?.counts || {}) as Record<string, number>;

      // Sum all counts for the selected topics
      const total = Object.values(counts).reduce((sum, n) => sum + (typeof n === 'number' ? n : 0), 0);
      console.log('✅ Total available questions for selected topics:', total);
      return { available: total };
    },
    enabled: selectedTopicsCustom.length > 0 && currentStep === 4,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
  });

  // Use nullish coalescing so 0 is respected; default to 0 until data arrives
  const availableQuestions = availableQuestionsData?.available ?? 0;

  // Debug: Check if query should be running
  const shouldQueryRun = selectedTopicsCustom.length > 0 && currentStep === 4;
  console.log('🔧 Query debug:', {
    selectedTopicsCount: selectedTopicsCustom.length,
    currentStep,
    shouldQueryRun,
    isLoading: isLoadingAvailableQuestions,
    hasData: !!availableQuestionsData,
    availableQuestions
  });

  // Debug: Log available questions
  console.log('🎯 Available questions:', availableQuestions, 'Query enabled:', selectedTopicsCustom.length > 0 && currentStep === 4);

  const createTestMutation = useMutation({
    mutationFn: async (payload: any) => {
      const body = { ...payload, studentId: student?.studentId };
      const res = await apiRequest(API_CONFIG.ENDPOINTS.TEST_SESSIONS, "POST", body);
      return res as CreateTestSessionResponse;
    },
    onSuccess: (data) => {
      navigate(`/test/${data.session.id}`);
    },
    onError: (err: any) => {
      console.log('❌ Test creation failed in mutation:', err.message);
      console.log('❌ Full error object:', err);
      console.log('❌ Error details:', err.details);

      let errorData = null;

      try {
        // First try the expected format: "400: {json_data}"
        if (err.message) {
          const match = err.message.match(/^\d+:\s*(.+)$/);
          if (match) {
            errorData = JSON.parse(match[1]);
          }
        }

        // If that didn't work, check the error details
        if (!errorData && err.details) {
          if (typeof err.details === 'string') {
            try {
              errorData = JSON.parse(err.details);
            } catch (detailsParseError) {
              console.log('❌ Could not parse error.details as JSON');
            }
          } else if (typeof err.details === 'object') {
            errorData = err.details;
          }
        }

        console.log('🔍 Final error data:', errorData);

      } catch (e) {
        console.error('Error parsing mutation error:', err.message);
      }

      if (errorData?.error === "Insufficient questions available") {
        setInsufficientQuestionsData({
          available: errorData.available_questions,
          requested: errorData.requested_questions,
          message: errorData.message || "Not enough questions available for this test configuration."
        });
        setShowInsufficientDialog(true);
      } else {
        toast({ title: "Failed to create test", description: "Could not create test session.", variant: "destructive" });
      }
    }
  });

  // === CHAPTER EXPANSION LOGIC ===
  // Start with all chapters collapsed for better user experience
  // This encourages users to drill down through the hierarchy: Subject → Chapter → Topics
  useEffect(() => {
    if (topics.length > 0 && expandedChapters.length === 0) {
      // Initialize with all chapters collapsed - user must click to expand
      setExpandedChapters([]);
    }
  }, [topics]);

  // Compute dynamic bounds for the time slider
  const timeMin = SLIDER_MIN;
  const timeMax = useMemo(() => Math.max(SLIDER_MIN, Math.ceil(questionCount * MAX_TIME_MULTIPLIER)), [questionCount]);

  // When available questions change, adjust question count if it exceeds available
  useEffect(() => {
    if (availableQuestions > 0) {
      let newQuestionCount = questionCount;

      if (availableQuestions < 5) {
        // If available questions is less than 5, use the exact available count
        newQuestionCount = availableQuestions;
      } else if (questionCount > availableQuestions) {
        // Find the largest available option that doesn't exceed available questions
        const validOptions = [5, 10, 15, 20, 25, 30, 60, 90, 180].filter(count => count <= availableQuestions);
        if (validOptions.length > 0) {
          newQuestionCount = Math.max(...validOptions);
        } else {
          // Fallback to available questions if no valid options
          newQuestionCount = availableQuestions;
        }
      }

      if (newQuestionCount !== questionCount) {
        setQuestionCount(newQuestionCount);
        setTimeLimit(newQuestionCount);
      }
    }
  }, [availableQuestions, questionCount]);

  // Set reasonable default question count when user first moves to step 4
  useEffect(() => {
    if (currentStep === 4 && availableQuestions > 0) {
      let defaultQuestionCount = 20; // Default fallback

      if (availableQuestions < 5) {
        // If available questions is less than 5, use the exact available count
        defaultQuestionCount = availableQuestions;
      } else {
        // Choose a reasonable default based on available questions
        const validOptions = [5, 10, 15, 20, 25, 30, 60, 90, 180].filter(count => count <= availableQuestions);
        if (validOptions.length > 0) {
          // Prefer 20 if available, otherwise the largest option that's reasonable
          if (validOptions.includes(20)) {
            defaultQuestionCount = 20;
          } else {
            // Choose the middle option or the largest that's not too big
            const midIndex = Math.floor(validOptions.length / 2);
            defaultQuestionCount = validOptions[Math.min(midIndex, validOptions.length - 1)];
          }
        }
      }

      // Only set if current question count is still the initial 20 and we have a better default
      if (questionCount === 20 && defaultQuestionCount !== 20) {
        setQuestionCount(defaultQuestionCount);
        setTimeLimit(defaultQuestionCount);
      }
    }
  }, [currentStep, availableQuestions, questionCount]);

  // Test session creation for custom mode will use API via handleCreateTest

  // === EVENT HANDLERS ===

  /**
   * Topic generation and selection helpers
   */

  /**
   * Get chapters for selected subjects
   */
  const getChaptersForSubjects = (subjects: string[]): string[] => {
    if (subjects.length === 0) return [];

    // Use case-insensitive matching to find topics for selected subjects
    const subjectTopics = topics.filter(topic =>
      subjects.some(selectedSubject =>
        topic.subject && topic.subject.toLowerCase() === selectedSubject.toLowerCase()
      )
    );

    // Extract chapters, filtering out null/empty values
    const chapters = [...new Set(
      subjectTopics
        .map(topic => topic.chapter)
        .filter((chapter): chapter is string =>
          chapter !== null &&
          chapter !== undefined &&
          typeof chapter === 'string' &&
          chapter.trim() !== ''
        )
    )];

    return chapters;
  };

  /**
   * Get topics for selected subjects and chapter
   */
  const getTopicsForChapter = (subjects: string[], chapter: string): Topic[] => {
    if (subjects.length === 0 || !chapter) return [];

    return topics.filter(topic =>
      subjects.some(selectedSubject =>
        topic.subject && topic.subject.toLowerCase() === selectedSubject.toLowerCase()
      ) && topic.chapter === chapter
    );
  };

  /**
   * Get topics for selected subjects and multiple chapters
   */
  const getTopicsForChapters = (subjects: string[], chapters: string[]): Topic[] => {
    if (subjects.length === 0 || chapters.length === 0) return [];

    return topics.filter(topic =>
      subjects.some(selectedSubject =>
        topic.subject && topic.subject.toLowerCase() === selectedSubject.toLowerCase()
      ) &&
      topic.chapter &&
      chapters.includes(topic.chapter)
    );
  };

  /**
   * Handle test type change
   */
  const handleTestTypeChange = (type: "custom") => {
    setTestType(type);
    setSelectedTopicsCustom([]);
    setSelectedSubjects([]);
    setSelectedChapters([]);
    // keep search state as-is for custom mode
  };

  /**
   * Handle subject selection in custom mode
   */
  const handleSubjectChange = (subject: string) => {
    setSelectedSubjects(prev =>
      prev.includes(subject)
        ? prev.filter(s => s !== subject)
        : [...prev, subject]
    );
    setSelectedChapters([]);
    // Don't reset selectedTopicsCustom - preserve previously selected topics from other subjects
  };

  /**
   * Handle chapter selection in custom mode
   */
  const handleChapterChange = (chapter: string) => {
    setSelectedChapters(prev =>
      prev.includes(chapter)
        ? prev.filter(c => c !== chapter)
        : [...prev, chapter]
    );
    // Don't reset selectedTopicsCustom - preserve previously selected topics
  };

  /**
   * Handle select all chapters
   */
  const handleSelectAllChapters = () => {
    const allChapters = getChaptersForSubjects(selectedSubjects);
    if (selectedChapters.length === allChapters.length) {
      // If all are selected, deselect all
      setSelectedChapters([]);
    } else {
      // If not all are selected, select all
      setSelectedChapters(allChapters);
    }
  };

  /**
   * Handle topic selection in custom mode
   */
  // topic toggle handled inline where needed (modal-only component)

  /**
   * Toggle topic selection on/off
   * When a topic is clicked, either add it to or remove it from selectedTopics array
   */
  // legacy topic toggle removed; custom selection uses selectedTopicsCustom

  /**
   * Toggle chapter expansion on/off
   * When a chapter header is clicked, either expand or collapse it
   */
  const handleChapterToggle = (chapterId: string) => {
    setExpandedChapters(prev =>
      prev.includes(chapterId)
        ? prev.filter(id => id !== chapterId)  // Collapse if already expanded
        : [...prev, chapterId]                 // Expand if currently collapsed
    );
  };

  const handleSubjectToggle = (subject: string) => {
    setExpandedSubjects(prev =>
      prev.includes(subject) ? prev.filter(s => s !== subject) : [...prev, subject]
    );
  };

  /**
   * Handle creating a new test session
   * 
   * DETAILED EXPLANATION:
   * This function validates user selections and creates a new test session.
  * It supports test creation using custom selection.
  * 
  * BUSINESS LOGIC:
  * - Custom mode: Uses user-selected topics from dropdowns
   * 
   * Validates selections and creates test with appropriate parameters
   */
  const handleCreateTest = () => {

    const finalSelectedTopics = selectedTopicsCustom;
    if (finalSelectedTopics.length === 0) {
      toast({ title: "No topics selected", description: "Please select at least one topic for your test.", variant: "destructive" });
      return;
    }

    // Validate lastChanged-driven selection
    if (lastChanged === 'questions') {
      if (!questionCount || questionCount <= 0) {
        toast({ title: "Invalid question count", description: "Please set a valid number of questions.", variant: "destructive" });
        return;
      }
    } else {
      if (!timeLimit || timeLimit <= 0) {
        toast({ title: "Invalid time limit", description: "Please set a valid time limit.", variant: "destructive" });
        return;
      }
    }

    const selection_mode = lastChanged === 'questions' ? 'question_count' : 'time_limit';
    const payload: any = {
      selected_topics: finalSelectedTopics,
      selection_mode,
      test_type: testType,
    };

    if (selection_mode === 'question_count') payload.question_count = questionCount;
    else payload.time_limit = timeLimit;

    console.log('🚀 Creating custom test with payload:', payload);
    createTestMutation.mutate(payload);
  };

  // helper duplication removed; use `getTopicsForChapter` for topic lists by chapter

  const getSubjectIcon = (subject: string) => {
    switch (subject) {
      case "Physics":
        return <Atom className="h-6 w-6 text-blue-600" />;
      case "Chemistry":
        return <FlaskConical className="h-6 w-6 text-green-600" />;
      case "Botany":
        return <Leaf className="h-6 w-6 text-emerald-600" />;
      case "Zoology":
        return <Dna className="h-6 w-6 text-purple-600" />;
      default:
        return <ListCheck className="h-6 w-6 text-gray-600" />;
    }
  };

  const getSubjectColor = (subject: string) => {
    switch (subject) {
      case "Physics":
        return "border-blue-200 bg-blue-50 hover:bg-blue-100";
      case "Chemistry":
        return "border-green-200 bg-green-50 hover:bg-green-100";
      case "Botany":
        return "border-emerald-200 bg-emerald-50 hover:bg-emerald-100";
      case "Zoology":
        return "border-purple-200 bg-purple-50 hover:bg-purple-100";
      default:
        return "border-gray-200 bg-gray-50 hover:bg-gray-100";
    }
  };

  const getSubjectDescription = (subject: string) => {
    switch (subject) {
      case "Physics":
        return "Mechanics, Thermodynamics, Waves & Optics";
      case "Chemistry":
        return "Physical, Inorganic, Organic Chemistry";
      case "Botany":
        return "Plant Structure, Physiology, Reproduction";
      case "Zoology":
        return "Animal Structure, Physiology, Genetics";
      default:
        return "Select topics from this subject";
    }
  };

  // select-all handlers removed; custom selection uses `selectedTopicsCustom`

  // Search functionality
  const filteredTopics = topics.filter((topic: Topic) => {
    if (!searchQuery) return false;
    const query = searchQuery.toLowerCase();
    return (
      topic.name.toLowerCase().includes(query) ||
      topic.subject.toLowerCase().includes(query) ||
      (topic.chapter && topic.chapter.toLowerCase().includes(query))
    );
  });

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setShowSearchResults(value.length > 0);
  };

  const clearSearch = () => {
    setSearchQuery("");
    setShowSearchResults(false);
  };

  const handleTopicSelectFromSearch = (topicId: string) => {
    setSelectedTopicsCustom(prev => prev.includes(topicId) ? prev.filter(id => id !== topicId) : [...prev, topicId]);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen">
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-4xl mx-auto">
            <Card className="shadow-xl">
              <CardHeader className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-4 w-96" />
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[1, 2, 3, 4].map((i) => (
                    <Skeleton key={i} className="h-32 w-full" />
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="text-red-600">Error Loading Topics</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">
              Failed to load topics. Please try refreshing the page.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Fixed Progress Header */}
      <div className="fixed top-12 left-0 right-0 z-50 bg-white border-b border-gray-200 p-4 shadow-sm">
        <div className="container mx-auto px-2.5">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Step {currentStep} of {totalSteps}</span>
              <span className="text-sm text-gray-500">
                {currentStep === 1 && "Select Subjects"}
                {currentStep === 2 && "Select Chapters"}
                {currentStep === 3 && "Select Topics"}
                {currentStep === 4 && "Configure Test"}
                {currentStep === 5 && "Review Test"}
                {currentStep === 6 && "Create Test"}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(currentStep / totalSteps) * 100}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto pb-3 pt-20">
        <div className="max-w-4xl mx-auto">

          <Card>
            <CardContent className="px-2 pb-24">

              {/* Step Content */}

              {currentStep === 2 && (
                <div className="space-y-4">
                  <div className="text-start">
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">Select Chapters</h3>
                    <p className="text-gray-600">Choose one or more chapters from {selectedSubjects.map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(", ")}</p>
                  </div>

                  {/* Search Bar */}
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Search className="h-4 w-4 text-gray-400" />
                    </div>
                    <input
                      type="text"
                      placeholder="Search chapters..."
                      value={searchQuery}
                      onChange={(e) => handleSearchChange(e.target.value)}
                      className="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                    {searchQuery && (
                      <button
                        onClick={clearSearch}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                      >
                        <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                      </button>
                    )}
                  </div>

                  {/* Select All Option */}
                  <div className="bg-gray-50 p-3 rounded-lg border">
                    <div className="flex items-center space-x-3 cursor-pointer" onClick={handleSelectAllChapters}>
                      <Checkbox
                        checked={selectedChapters.length === getChaptersForSubjects(selectedSubjects).length && getChaptersForSubjects(selectedSubjects).length > 0}
                        className="data-[state=checked]:bg-blue-600 data-[state=checked]:border-blue-600"
                      />
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-800">Select All Chapters</h4>
                        <p className="text-sm text-gray-600">
                          {getChaptersForSubjects(selectedSubjects).length} chapters available
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-3">
                    {(() => {
                      const chapters = getChaptersForSubjects(selectedSubjects)
                        .filter((chapter: string) => !searchQuery || chapter.toLowerCase().includes(searchQuery.toLowerCase()));

                      if (chapters.length === 0) {
                        return (
                          <div className="text-center py-8 text-gray-500">
                            <p className="text-lg mb-2">No chapters found</p>
                            <p className="text-sm">
                              {selectedSubjects.length === 0
                                ? "Please select at least one subject first"
                                : topics.length === 0
                                  ? "Loading topics..."
                                  : "No chapters available for the selected subjects"
                              }
                            </p>
                          </div>
                        );
                      }

                      return chapters.map((chapter: string) => (
                        <div
                          key={chapter}
                          className={`p-4 rounded-lg border-2 transition-all duration-200 cursor-pointer ${selectedChapters.includes(chapter)
                            ? "border-blue-500 bg-blue-50 shadow-md"
                            : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                            }`}
                          onClick={() => handleChapterChange(chapter)}
                        >
                          <div className="flex items-center space-x-3">
                            <Checkbox
                              checked={selectedChapters.includes(chapter)}
                              className="data-[state=checked]:bg-blue-600 data-[state=checked]:border-blue-600"
                            />
                            <div className="flex-1">
                              <h4 className="font-medium text-gray-800">{chapter}</h4>
                              <p className="text-sm text-gray-600">
                                {getTopicsForChapter(selectedSubjects, chapter).length} topics available
                              </p>
                            </div>
                          </div>
                        </div>
                      ));
                    })()}
                  </div>

                </div>
              )}

              {currentStep === 3 && (
                <div className="space-y-4">
                  <div className="text-start">
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">Select Topics</h3>
                    <p className="text-gray-600">Choose topics from {selectedSubjects.join(", ")} - {selectedChapters.join(", ")}</p>
                  </div>

                  {/* Search Bar */}
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Search className="h-4 w-4 text-gray-400" />
                    </div>
                    <input
                      type="text"
                      placeholder="Search topics..."
                      value={searchQuery}
                      onChange={(e) => handleSearchChange(e.target.value)}
                      className="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                    {searchQuery && (
                      <button
                        onClick={clearSearch}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                      >
                        <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                      </button>
                    )}
                  </div>

                  {/* Select All Option */}
                  <div className="bg-gray-50 p-3 rounded-lg border">
                    <div className="flex items-center space-x-3 cursor-pointer" onClick={() => {
                      const allTopics = getTopicsForChapters(selectedSubjects, selectedChapters);
                      const allTopicIds = allTopics.map(t => t.id.toString());
                      if (selectedTopicsCustom.length === allTopicIds.length) {
                        setSelectedTopicsCustom([]);
                      } else {
                        setSelectedTopicsCustom(allTopicIds);
                      }
                    }}>
                      <Checkbox
                        checked={selectedTopicsCustom.length === getTopicsForChapters(selectedSubjects, selectedChapters).length && getTopicsForChapters(selectedSubjects, selectedChapters).length > 0}
                        className="data-[state=checked]:bg-green-600 data-[state=checked]:border-green-600"
                      />
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-800">Select All Topics</h4>
                        <div className="flex items-center justify-between">
                          <p className="text-sm text-gray-600">
                            {getTopicsForChapters(selectedSubjects, selectedChapters).length} topics available
                          </p>
                          <span className="text-xs text-blue-600 font-medium bg-blue-50 px-2 py-1 rounded">
                            {isLoadingTopicCounts ? (
                              '...'
                            ) : (
                              `${Object.values(topicQuestionCountsData).reduce((sum, count) => sum + count, 0)} total questions`
                            )}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-3">
                    {getTopicsForChapters(selectedSubjects, selectedChapters)
                      .filter(topic => !searchQuery || topic.name.toLowerCase().includes(searchQuery.toLowerCase()) || topic.chapter?.toLowerCase().includes(searchQuery.toLowerCase()))
                      .map((topic) => (
                        <div
                          key={topic.id}
                          className={`p-4 rounded-lg border-2 transition-all duration-200 cursor-pointer ${selectedTopicsCustom.includes(topic.id.toString())
                            ? "border-green-500 bg-green-50 shadow-md"
                            : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                            }`}
                          onClick={() => setSelectedTopicsCustom(prev =>
                            prev.includes(topic.id.toString())
                              ? prev.filter(id => id !== topic.id.toString())
                              : [...prev, topic.id.toString()]
                          )}
                        >
                          <div className="flex items-center space-x-3">
                            <Checkbox
                              checked={selectedTopicsCustom.includes(topic.id.toString())}
                              className="data-[state=checked]:bg-green-600 data-[state=checked]:border-green-600"
                            />
                            <div className="flex-1">
                              <h4 className="font-medium text-gray-800">{topic.name}</h4>
                              <div className="flex items-center justify-between">
                                <p className="text-sm text-gray-500">{topic.chapter}</p>
                                <span className="text-xs text-blue-600 font-medium bg-blue-50 px-2 py-1 rounded">
                                  {isLoadingTopicCounts ? (
                                    '...'
                                  ) : (
                                    `${topicQuestionCountsData[topic.id.toString()] || 0} questions`
                                  )}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>

                </div>
              )}

              {currentStep === 4 && (
                <div className="pb-60">
                  {/* Questions Selection - Positioned above time slider */}
                  <div className="fixed bottom-40 left-0 right-0 z-30 p-4 bg-white border-t">
                    <div className="text-sm font-medium text-gray-700 mb-3">Number of Questions</div>
                    <div className="grid grid-cols-3 gap-2">
                      {(() => {
                        // Always show the standard set; optionally add a custom small-count first
                        const standardOptions = [5, 10, 15, 20, 25, 30, 60, 90, 180];
                        const buttonOptions = (availableQuestions > 0 && availableQuestions < 5)
                          ? [availableQuestions, ...standardOptions]
                          : standardOptions;

                        return buttonOptions.map((count) => {
                          const isDisabled = availableQuestions > 0 ? count > availableQuestions : true;
                          const isActive = !isDisabled && questionCount === count;

                          return (
                            <Button
                              key={count}
                              variant={isActive ? "default" : "outline"}
                              size="sm"
                              disabled={isDisabled}
                              onClick={() => {
                                if (isDisabled) return;
                                setQuestionCount(count);
                                setTimeLimit(count);
                                setLastChanged('questions');
                              }}
                              className={`text-sm ${isDisabled ? 'opacity-50 cursor-not-allowed line-through' : ''}`}
                            >
                              {count} Qs
                            </Button>
                          );
                        });
                      })()}
                    </div>
                    {selectedTopicsCustom.length > 0 && (
                      <div className="text-xs text-gray-500 mt-2 text-center">
                        {isLoadingAvailableQuestions ? (
                          'Checking available questions...'
                        ) : availableQuestions > 0 ? (
                          `${availableQuestions} questions available for selected topics`
                        ) : (
                          'No questions available for selected topics'
                        )}
                      </div>
                    )}
                  </div>

                  {/* Time Limit Slider - Positioned above footer */}
                  <div className="fixed bottom-20 left-0 right-0 z-40 p-4 bg-white border-t">
                    <div className="text-sm font-medium text-gray-700 mb-2">Time Limit: {timeLimit} minutes</div>
                    <Slider value={[timeLimit]} onValueChange={(v) => { let val = v[0]; if (val < timeMin) val = timeMin; if (val > timeMax) val = timeMax; setTimeLimit(val); setLastChanged('time'); }} min={timeMin} max={timeMax} step={SLIDER_STEP} />
                  </div>
                </div>
              )}

              {currentStep === 5 && (
                <div className="space-y-6">
                  <div className="text-center">
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">Review Your Test</h3>
                    <p className="text-gray-600">Please review your selections before creating the test</p>
                  </div>

                  <div className="space-y-4">
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-medium text-gray-800 mb-2">Subject & Chapters</h4>
                      <p className="text-gray-600">{selectedSubjects.map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(", ")} - {selectedChapters.join(", ")}</p>
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-medium text-gray-800 mb-2">Selected Topics ({selectedTopicsCustom.length})</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedTopicsCustom.map((topicId) => {
                          const topic = topics.find(t => t.id.toString() === topicId);
                          if (!topic) return null;
                          return (
                            <Badge key={topicId} variant="secondary" className="text-xs">
                              {topic.name}
                            </Badge>
                          );
                        })}
                      </div>
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg">
                      <h4 className="font-medium text-gray-800 mb-2">Test Configuration</h4>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">Questions:</span>
                          <span className="font-medium ml-2">{questionCount}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Time Limit:</span>
                          <span className="font-medium ml-2">{timeLimit} minutes</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {currentStep === 6 && (
                <div className="space-y-6">
                  <div className="text-center">
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">Create Your Test</h3>
                    <p className="text-gray-600">Ready to start your practice test?</p>
                  </div>

                  <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
                    <div className="text-green-600 mb-4">
                      <Play className="h-12 w-12 mx-auto" />
                    </div>
                    <h4 className="font-semibold text-green-800 mb-2">Test Ready!</h4>
                    <p className="text-green-700">
                      Your {selectedSubjects.map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(", ")} test with {questionCount} questions and {timeLimit} minute time limit is ready to begin.
                    </p>
                  </div>
                </div>
              )}

            </CardContent>
          </Card>
        </div>
      </div>
      {/* Fixed Subject Selection - Above Bottom Navigation */}
      {currentStep === 1 && (
        <div className="fixed bottom-20 left-0 right-0 z-40 bg-white border-t border-gray-200 p-4">
          <div className="container mx-auto px-2.5">
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-2 gap-3">
                {[
                  { display: "Physics", value: "physics" },
                  { display: "Chemistry", value: "chemistry" },
                  { display: "Botany", value: "botany" },
                  { display: "Zoology", value: "zoology" }
                ].map((subject) => (
                  <button
                    key={subject.value}
                    onClick={() => handleSubjectChange(subject.value)}
                    className={`p-3 rounded-lg border-2 transition-all duration-200 cursor-pointer ${selectedSubjects.includes(subject.value)
                      ? "border-blue-500 bg-blue-50 shadow-sm"
                      : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                      }`}
                  >
                    <div className="flex items-center space-x-2">
                      {getSubjectIcon(subject.display)}
                      <div className="text-left">
                        <h4 className="font-medium text-gray-800 text-sm">{subject.display}</h4>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Selected Chapters Counter - Above Navigation */}
      {currentStep === 2 && (
        <div className="fixed bottom-16 left-0 right-0 z-30 bg-white border-t border-gray-200 p-3">
          <div className="container mx-auto px-2.5">
            <div className="max-w-4xl mx-auto">
              <div className="bg-blue-50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-blue-800 font-medium">
                    {selectedChapters.length} chapter{selectedChapters.length !== 1 ? 's' : ''} selected
                  </p>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleSelectAllChapters}
                      className="text-xs h-7 px-2"
                    >
                      Select All
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedChapters([])}
                      className="text-xs h-7 px-2"
                    >
                      Clear All
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Selected Topics Counter - Above Navigation */}
      {currentStep === 3 && (
        <div className="fixed bottom-16 left-0 right-0 z-30 bg-white border-t border-gray-200 p-3">
          <div className="container mx-auto px-2.5">
            <div className="max-w-4xl mx-auto">
              <div className="bg-green-50 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-green-800 font-medium">
                    {selectedTopicsCustom.length} topic{selectedTopicsCustom.length !== 1 ? 's' : ''} selected
                  </p>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const allTopics = getTopicsForChapters(selectedSubjects, selectedChapters);
                        const allTopicIds = allTopics.map(t => t.id.toString());
                        setSelectedTopicsCustom(allTopicIds);
                      }}
                      className="text-xs h-7 px-2"
                    >
                      Select All
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedTopicsCustom([])}
                      className="text-xs h-7 px-2"
                    >
                      Clear All
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Buttons - Fixed at bottom */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 shadow-lg">
        <div className="container mx-auto px-2.5">
          <div className="max-w-4xl mx-auto">
            <div className="flex justify-between items-center">
              <Button
                variant="outline"
                onClick={prevStep}
                disabled={currentStep === 1}
                className="flex items-center space-x-2"
              >
                <ChevronLeft className="h-4 w-4" />
                <span>Previous</span>
              </Button>

              <div className="flex space-x-2">
                {currentStep < totalSteps ? (
                  <Button
                    onClick={nextStep}
                    disabled={
                      (currentStep === 1 && selectedSubjects.length === 0) ||
                      (currentStep === 2 && selectedChapters.length === 0) ||
                      (currentStep === 3 && selectedTopicsCustom.length === 0)
                    }
                    className="flex items-center space-x-2"
                  >
                    <span>Next</span>
                    <ChevronLeft className="h-4 w-4 rotate-180" />
                  </Button>
                ) : (
                  <Button
                    onClick={handleCreateTest}
                    disabled={createTestMutation.isPending}
                    className="bg-green-600 hover:bg-green-700 flex items-center space-x-2"
                  >
                    {createTestMutation.isPending ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                        <span>Creating...</span>
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" />
                        <span>Create Test</span>
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Insufficient Questions Dialog */}
      <Dialog open={showInsufficientDialog} onOpenChange={setShowInsufficientDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-orange-500" />
              Insufficient Questions Available
            </DialogTitle>
            <DialogDescription>
              {insufficientQuestionsData?.message}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-orange-800">Available Questions:</span>
                <span className="text-lg font-bold text-orange-600">{insufficientQuestionsData?.available}</span>
              </div>
              <div className="flex justify-between items-center mt-1">
                <span className="text-sm font-medium text-orange-800">Requested Questions:</span>
                <span className="text-lg font-bold text-red-600">{insufficientQuestionsData?.requested}</span>
              </div>
            </div>

            <div className="text-sm text-gray-600">
              <p className="font-medium mb-2">What you can do:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Reduce the number of questions to {insufficientQuestionsData?.available} or fewer</li>
                <li>Select additional topics to get more questions</li>
                <li>Choose different topics that might have more questions</li>
              </ul>
            </div>
          </div>

          <DialogFooter className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setShowInsufficientDialog(false);
                // Reset to step 1
                setCurrentStep(1);
                setSelectedSubjects([]);
                setSelectedChapters([]);
                setSelectedTopicsCustom([]);
              }}
              className="flex-1"
            >
              <BookOpen className="h-4 w-4 mr-2" />
              Back to Selection
            </Button>
            <Button
              onClick={() => {
                setShowInsufficientDialog(false);
                // Set question count to available questions
                if (insufficientQuestionsData?.available) {
                  setQuestionCount(insufficientQuestionsData.available);
                }
              }}
              className="flex-1 bg-blue-600 hover:bg-blue-700"
            >
              <Target className="h-4 w-4 mr-2" />
              Use {insufficientQuestionsData?.available} Questions
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}