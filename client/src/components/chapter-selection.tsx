/**
 * Chapter Selection Component
 * 
 * This is the main component for the NEET Practice Platform's topic selection interface.
 * It provides a hierarchical selection system where users can:
 * - Bro   * BACKEND API PAYLOAD STRUCTURE:
   * - Time-based: { selection_mode: 'time_limit', time_limit: userSpecifiedMinutes }
   * - Question-based: { selection_mode: 'question_count', question_count: N }e topics organized by subject (Physics, Chemistry, Botany, Zoology)
 * - Expand chapters to view individual topics
 * - Search for specific topics across all subjects
 * - Select multiple topics for their test session
 * - Configure test parameters (time-based or question-based)
 * - Create and start a new test session
 * 
 * The component uses PostgreSQL database for persistent topic storage and
 * provides real-time search functionality with proper state management.
 */

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { API_CONFIG } from "@/config/api";
import { ListCheck, Atom, FlaskConical, Dna, Clock, Play, Leaf, ChevronDown, ChevronRight, BookOpen, Search, X, BarChart3 } from "lucide-react";
import { ChapterSelector } from "./chapter-selector";
import { SearchBar } from "./search-bar";
import { Topic, CreateTestSessionRequest, CreateTestSessionResponse } from '../types/api'; // Adjust path as needed
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
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);      // Selected topic IDs
  const [timeLimit, setTimeLimit] = useState<string>("");                  // Time limit input value
  const [testMode, setTestMode] = useState<"time" | "questions">("time");  // Test mode selection
  const [questionCount, setQuestionCount] = useState<string>("20");        // Question count input value
  
  // === UI INTERACTION STATE ===
  const [expandedChapters, setExpandedChapters] = useState<string[]>([]);  // Expanded chapter IDs
  const [searchQuery, setSearchQuery] = useState<string>("");              // Search input value
  const [showSearchResults, setShowSearchResults] = useState<boolean>(false); // Search results visibility

  // === DATA FETCHING ===
  // Fetch all available topics from the PostgreSQL database
  const { data: topicsResponse, isLoading, error } = useQuery({
    queryKey: ["allTopics"], // Use a distinct key if you're fetching all topics now
    queryFn: async () => {
      let allTopics: Topic[] = [];
      let nextUrl: string | null = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.TOPICS}`;

      while (nextUrl) {
        // Explicitly type 'response' here as 'Response'
        const response: Response = await fetch(nextUrl);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status} for URL: ${nextUrl}`);
        }

        // Explicitly type 'data' here as 'PaginatedTopicsResponse'
        const data: PaginatedTopicsResponse = await response.json();

        // Add the results from the current page to our accumulator
        allTopics = allTopics.concat(data.results);

        // Update nextUrl for the next iteration
        nextUrl = data.next;
      }

      return { results: allTopics }; // Return in a consistent format
    },
});

  // Extract topics from response (Django format: { results: [...] })
  const topics = topicsResponse?.results || [];
  
  // === CHAPTER EXPANSION LOGIC ===
  // Start with all chapters collapsed for better user experience
  // This encourages users to drill down through the hierarchy: Subject → Chapter → Topics
  useEffect(() => {
    if (topics.length > 0 && expandedChapters.length === 0) {
      // Initialize with all chapters collapsed - user must click to expand
      setExpandedChapters([]);
    }
  }, [topics]);

  // === TEST SESSION CREATION ===
  // This mutation handles creating a new test session when user clicks "Start Test"
  const { student } = useAuth();
  const createTestMutation = useMutation({
    mutationFn: async (data: { 
      selected_topics: string[], 
      selection_mode: 'question_count' | 'time_limit',
      time_limit?: number, 
      question_count?: number 
    }) => {
      // Add studentId to the payload if available
      const payload = {
        ...data,
        studentId: student?.studentId,
      };
      const response = await apiRequest(API_CONFIG.ENDPOINTS.TEST_SESSIONS, "POST", payload);
      return response as CreateTestSessionResponse;
    },
    onSuccess: (data) => {
      // Test session created successfully - navigate to the test interface
      navigate(`/test/${data.session.id}`);
    },
    onError: () => {
      // Show error toast if test creation fails
      toast({
        title: "Error",
        description: "Failed to create test session. Please try again.",
        variant: "destructive",
      });
    },
  });

  // === EVENT HANDLERS ===
  
  /**
   * Toggle topic selection on/off
   * When a topic is clicked, either add it to or remove it from selectedTopics array
   */
  const handleTopicToggle = (topicId: string) => {
    setSelectedTopics(prev => 
      prev.includes(topicId) 
        ? prev.filter(id => id !== topicId)  // Remove if already selected
        : [...prev, topicId]                 // Add if not selected
    );
  };

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

  /**
   * Handle creating a new test session
   * 
   * DETAILED EXPLANATION:
   * This function validates user selections and creates a new test session.
   * It implements the "1 minute per question" timing logic for question-based tests.
   * The function handles both time-based and question-based test configurations.
   * 
   * BUSINESS LOGIC:
   * - Validates that at least one topic is selected
   * - Validates test configuration parameters (time limit or question count)
   * - Applies 1-minute-per-question rule for question-based tests
   * - Submits test creation request to backend API
   * 
   * TIMING LOGIC IMPLEMENTATION:
   * - Time-based tests: Uses user-specified time limit directly
   * - Question-based tests: Automatically calculates time as questionCount * 1 minute
   * - This ensures consistent timing across both test modes
   * 
   * USER EXPERIENCE:
   * - Shows validation errors through toast notifications
   * - Prevents test creation if validation fails
   * - Provides clear feedback on what needs to be corrected
   * 
   * API INTEGRATION:
   * - Uses React Query mutation for test creation
   * - Sends structured test data to /api/test-sessions endpoint
   * - Handles both successful creation and error scenarios
   * 
   * VALIDATION FLOW:
   * 1. Check if topics are selected
   * 2. Validate test mode parameters (time limit or question count)
   * 3. Apply timing logic based on test mode
   * 4. Submit request to backend
   * 5. Handle success/error responses
   * 
   * TIMING RULE APPLICATION:
   * - Time-based: { time_limit: userSpecifiedMinutes }
   * - Question-based: { question_count: N, time_limit: N } (1 min per question)
   * 
   * Validates selections and creates test with appropriate parameters
   * Implements 1 minute per question timing logic
   */
  const handleCreateTest = () => {
    // VALIDATION STEP 1: Check if user has selected at least one topic
    // This prevents creating empty tests and ensures valid test content
    if (selectedTopics.length === 0) {
      toast({
        title: "No topics selected",
        description: "Please select at least one topic for your test.",
        variant: "destructive",
      });
      return; // Exit early if validation fails
    }

    // VALIDATION STEP 2: Validate test mode parameters and apply timing logic
    if (testMode === "time") {
      // TIME-BASED TEST VALIDATION
      if (!timeLimit) {
        toast({
          title: "No time limit selected",
          description: "Please select a time limit for your test.",
          variant: "destructive",
        });
        return; // Exit early if validation fails
      }
      
      // Time-based test: use user-specified time limit directly
      // User chooses how many minutes they want for the test
      createTestMutation.mutate({
        selected_topics: selectedTopics,
        selection_mode: 'time_limit',
        time_limit: parseInt(timeLimit), // Backend will calculate question_count = time_limit
      });
    } else {
      // QUESTION-BASED TEST VALIDATION AND TIMING LOGIC
      if (!questionCount) {
        toast({
          title: "No question count selected",
          description: "Please select the number of questions for your test.",
          variant: "destructive",
        });
        return; // Exit early if validation fails
      }
      
      // Question-based test: send question count, backend won't calculate time limit
      // This implements the core business rule: user specifies exact question count
      const questionCountValue = parseInt(questionCount);
      createTestMutation.mutate({
        selected_topics: selectedTopics,
        selection_mode: 'question_count',
        question_count: questionCountValue,
      });
    }
  };

const getChaptersBySubject = (subject: string): string[] => { // <-- Explicitly state string[] return type
  const subjectTopics = topics.filter((topic: Topic) => topic.subject === subject);
  const chapters = [...new Set(subjectTopics.map((topic: Topic) => topic.chapter))]
    .filter((chapter): chapter is string => chapter !== null && chapter !== undefined); // <-- Stronger type guard
  return chapters;
};

  const getTopicsByChapter = (subject: string, chapter: string) => {
    return topics.filter((topic: Topic) => topic.subject === subject && topic.chapter === chapter);
  };

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

  const handleSelectAllInChapter = (subject: string, chapter: string) => {
    const chapterTopics = getTopicsByChapter(subject, chapter);
    const chapterTopicIds = chapterTopics.map((t: Topic) => t.id.toString());
    const allSelected = chapterTopicIds.every((id: string) => selectedTopics.includes(id));
    
    if (allSelected) {
      setSelectedTopics(prev => prev.filter(id => !chapterTopicIds.includes(id)));
    } else {
      setSelectedTopics(prev => [...new Set([...prev, ...chapterTopicIds])]);
    }
  };

  const handleSelectAllInSubject = (subject: string) => {
    const subjectTopics = topics.filter((topic: Topic) => topic.subject === subject);
    const subjectTopicIds = subjectTopics.map((t: Topic) => t.id.toString());
    const allSelected = subjectTopicIds.every((id: string) => selectedTopics.includes(id));
    
    if (allSelected) {
      setSelectedTopics(prev => prev.filter(id => !subjectTopicIds.includes(id)));
    } else {
      setSelectedTopics(prev => [...new Set([...prev, ...subjectTopicIds])]);
    }
  };

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
    handleTopicToggle(topicId);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-4xl mx-auto">
            <Card className="shadow-xl">
              <CardHeader>
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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          <Card className="shadow-xl">
            <CardHeader className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
              <div className="flex justify-between items-center mb-4">
                <div className="flex-1"></div>
                <CardTitle className="text-3xl font-bold text-center flex-1">
                  Create Your NEET Practice Test
                </CardTitle>
                <div className="flex-1 flex justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate("/dashboard")}
                    className="flex items-center gap-2 text-white border-white hover:bg-white hover:text-blue-600"
                  >
                    <BarChart3 className="h-4 w-4" />
                    Dashboard
                  </Button>
                </div>
              </div>
              <p className="text-center text-blue-100 mt-2">
                Select chapters and topics to create a personalized test experience
              </p>
            </CardHeader>
            <CardContent className="p-8">
              
              {/* Search Bar */}
              <SearchBar
                searchQuery={searchQuery}
                onSearchChange={handleSearchChange}
                onClearSearch={clearSearch}
                filteredTopics={filteredTopics}
                selectedTopics={selectedTopics}
                onTopicSelect={handleTopicSelectFromSearch}
                showResults={showSearchResults}
              />
              
              {/* Subject Cards with Chapter Drill-down */}
              {!showSearchResults && (
                <div className="space-y-8 mb-12">
                  <h3 className="text-xl font-semibold text-gray-800 mb-6 flex items-center">
                    <ListCheck className="h-6 w-6 mr-3 text-blue-600" />
                    Select Topics by Chapter
                  </h3>
                
                {/* Subject Dropdown Selection */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {["Physics", "Chemistry", "Botany", "Zoology"].map((subject) => {
                    const subjectTopics = topics.filter((t: Topic) => t.subject === subject);
                    const selectedCount = subjectTopics.filter((t: Topic) => selectedTopics.includes(t.id.toString())).length;
                    const hasChapters = subjectTopics.some((t: Topic) => t.chapter);
                    
                    return (
                      <Card key={subject} className={`${getSubjectColor(subject)} border-2 transition-all duration-300`}>
                        <CardHeader className="pb-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center">
                              <div className="mr-3">{getSubjectIcon(subject)}</div>
                              <div>
                                <CardTitle className="text-xl font-bold text-gray-800">{subject}</CardTitle>
                                <p className="text-sm text-gray-600 mt-1">{getSubjectDescription(subject)}</p>
                              </div>
                            </div>
                            <Badge variant="secondary" className="text-sm">
                              {selectedCount}/{subjectTopics.length}
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent className="pt-0">
                          <div className="space-y-3">
                            {hasChapters ? (
                              // Chapter dropdown sections
                              getChaptersBySubject(subject).map((chapter) => {
                                const chapterTopics = getTopicsByChapter(subject, chapter);
                                const chapterSelectedCount = chapterTopics.filter((t: Topic) => selectedTopics.includes(t.id.toString())).length;
                                const isChapterExpanded = expandedChapters.includes(`${subject}-${chapter}`);
                                
                                return (
                                  <div key={chapter} className="border rounded-lg bg-white/50 overflow-hidden">
                                    <div 
                                      className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/80 transition-colors"
                                      onClick={() => handleChapterToggle(`${subject}-${chapter}`)}
                                    >
                                      <div className="flex items-center">
                                        <BookOpen className="h-4 w-4 mr-2 text-gray-600" />
                                        <span className="font-medium text-gray-800">{chapter}</span>
                                      </div>
                                      <div className="flex items-center gap-2">
                                        <Badge variant="outline" className="text-xs">
                                          {chapterSelectedCount}/{chapterTopics.length}
                                        </Badge>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            handleSelectAllInChapter(subject, chapter);
                                          }}
                                          className="text-xs px-2 py-1 h-auto"
                                        >
                                          {chapterSelectedCount === chapterTopics.length ? "Deselect All" : "Select All"}
                                        </Button>
                                        {isChapterExpanded ? (
                                          <ChevronDown className="h-4 w-4 text-gray-500" />
                                        ) : (
                                          <ChevronRight className="h-4 w-4 text-gray-500" />
                                        )}
                                      </div>
                                    </div>
                                    
                                    {isChapterExpanded && (
                                      <div className="border-t bg-gray-50/50 p-3">
                                        <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto">
                                          {chapterTopics.map((topic: Topic) => (
                                            <div key={topic.id} className="flex items-center space-x-2 p-2 hover:bg-white rounded-md transition-colors">
                                              <Checkbox
                                                id={`topic-${topic.id}`}
                                                checked={selectedTopics.includes(topic.id.toString())}
                                                onCheckedChange={() => handleTopicToggle(topic.id.toString())}
                                                className="data-[state=checked]:bg-blue-600 data-[state=checked]:border-blue-600"
                                              />
                                              <Label htmlFor={`topic-${topic.id}`} className="text-sm cursor-pointer flex-1">
                                                <div className="flex items-center">
                                                  <span className="mr-2">{topic.icon}</span>
                                                  {topic.name}
                                                </div>
                                              </Label>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                );
                              })
                            ) : (
                              // Fallback for subjects without chapters
                              <div className="text-center py-6">
                                <p className="text-sm text-gray-500">Loading chapters...</p>
                                <Button 
                                  variant="outline" 
                                  size="sm" 
                                  onClick={() => window.location.reload()}
                                  className="mt-2"
                                >
                                  Refresh
                                </Button>
                              </div>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </div>
              )}

              {/* Test Mode Selection */}
              <div className="mb-8">
                <h4 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                  <Clock className="h-5 w-5 mr-2 text-blue-600" />
                  Test Configuration
                </h4>
                
                {/* Mode Toggle */}
                <div className="mb-6">
                  <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
                    <Button
                      variant={testMode === "time" ? "default" : "ghost"}
                      onClick={() => setTestMode("time")}
                      className={`flex-1 ${testMode === "time" ? "bg-blue-600 text-white" : "text-gray-600"}`}
                    >
                      <Clock className="h-4 w-4 mr-2" />
                      Time Limit
                    </Button>
                    <Button
                      variant={testMode === "questions" ? "default" : "ghost"}
                      onClick={() => setTestMode("questions")}
                      className={`flex-1 ${testMode === "questions" ? "bg-blue-600 text-white" : "text-gray-600"}`}
                    >
                      <ListCheck className="h-4 w-4 mr-2" />
                      Question Count
                    </Button>
                  </div>
                </div>

                {/* Time Limit Options */}
                {testMode === "time" && (
                  <div>
                    <h5 className="text-sm font-medium text-gray-700 mb-3">Select Time Limit:</h5>
                    <RadioGroup value={timeLimit} onValueChange={setTimeLimit}>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {[
                          { value: "15", label: "15 minutes", description: "Quick practice" },
                          { value: "30", label: "30 minutes", description: "Standard test" },
                          { value: "60", label: "1 hour", description: "Extended practice" },
                          { value: "90", label: "1.5 hours", description: "Full length test" },
                        ].map((option) => (
                          <div key={option.value} className="flex items-center space-x-2">
                            <RadioGroupItem value={option.value} id={`time-${option.value}`} />
                            <Label htmlFor={`time-${option.value}`} className="cursor-pointer">
                              <div className="text-sm font-medium text-gray-800">{option.label}</div>
                              <div className="text-xs text-gray-500">{option.description}</div>
                            </Label>
                          </div>
                        ))}
                      </div>
                    </RadioGroup>
                  </div>
                )}

                {/* Question Count Options */}
                {testMode === "questions" && (
                  <div>
                    <h5 className="text-sm font-medium text-gray-700 mb-3">Select Number of Questions:</h5>
                    <RadioGroup value={questionCount} onValueChange={setQuestionCount}>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {[
                          { value: "10", label: "10 questions", description: "Quick quiz" },
                          { value: "20", label: "20 questions", description: "Short test" },
                          { value: "30", label: "30 questions", description: "Medium test" },
                          { value: "50", label: "50 questions", description: "Long test" },
                        ].map((option) => (
                          <div key={option.value} className="flex items-center space-x-2">
                            <RadioGroupItem value={option.value} id={`questions-${option.value}`} />
                            <Label htmlFor={`questions-${option.value}`} className="cursor-pointer">
                              <div className="text-sm font-medium text-gray-800">{option.label}</div>
                              <div className="text-xs text-gray-500">{option.description}</div>
                            </Label>
                          </div>
                        ))}
                      </div>
                    </RadioGroup>
                  </div>
                )}
              </div>

              {/* Create Test Button */}
              <div className="flex justify-center">
                <Button
                  onClick={handleCreateTest}
                  disabled={createTestMutation.isPending || selectedTopics.length === 0 || (testMode === "time" && !timeLimit) || (testMode === "questions" && !questionCount)}
                  className="bg-blue-600 hover:bg-blue-700 px-8 py-3 text-lg font-semibold shadow-lg hover:shadow-xl transform hover:scale-[1.02] transition-all duration-200"
                >
                  {createTestMutation.isPending ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
                      Creating Test...
                    </>
                  ) : (
                    <>
                      <Play className="h-5 w-5 mr-2" />
                      Create Test ({selectedTopics.length} topic{selectedTopics.length !== 1 ? 's' : ''})
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}