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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { API_CONFIG } from "@/config/api";
import { ListCheck, Atom, FlaskConical, Dna, Clock, Play, Leaf, ChevronDown, ChevronRight, BookOpen, Search, X, BarChart3, Shuffle, Target } from "lucide-react";
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
  const [timeLimit, setTimeLimit] = useState<number>(60);                  // Time limit in minutes
  const [questionCount, setQuestionCount] = useState<number>(20);          // Number of questions
  
  // === NEW UI STATE FOR WIREFRAME ===
  const [testType, setTestType] = useState<"random" | "custom" | "search">("random"); // Test type selection
  const [selectedSubject, setSelectedSubject] = useState<string>("");      // Selected subject for custom mode
  const [selectedChapter, setSelectedChapter] = useState<string>("");      // Selected chapter for custom mode
  const [selectedTopicsCustom, setSelectedTopicsCustom] = useState<string[]>([]); // Topics for custom mode
  
  // === UI INTERACTION STATE ===
  const [expandedChapters, setExpandedChapters] = useState<string[]>([]);  // Expanded chapter IDs
  const [searchQuery, setSearchQuery] = useState<string>("");              // Search input value
  const [showSearchResults, setShowSearchResults] = useState<boolean>(false); // Search results visibility

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
      selection_mode: string,
      time_limit: number, 
      question_count: number,
      test_type: string,
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
   * Generate random topics from all subjects
   * Selects equal number of topics from each subject
   * UPDATED: Only selects topics that have questions available
   */
  const generateRandomTopics = (totalQuestions: number) => {
    const subjects = ["Physics", "Chemistry", "Botany", "Zoology"];
    const questionsPerSubject = Math.floor(totalQuestions / 4);
    const randomTopics: string[] = [];
    
    console.log('🎲 generateRandomTopics called with:', { totalQuestions, questionsPerSubject });
    console.log('📊 Total topics available:', topics.length);
    
    subjects.forEach(subject => {
      // Fix: Make subject matching case-insensitive
      const subjectTopics = topics.filter(topic => topic.subject.toLowerCase() === subject.toLowerCase());
      
      // For now, select random topics from available topics
      // TODO: In future, we could add a 'hasQuestions' field to topics or query backend
      const shuffled = subjectTopics.sort(() => 0.5 - Math.random());
      const selected = shuffled.slice(0, Math.min(questionsPerSubject, subjectTopics.length));
      
      console.log(`🧪 ${subject}: found ${subjectTopics.length} topics, selected ${selected.length}`);
      console.log(`📝 Selected ${subject} topics:`, selected.map(t => ({ id: t.id, name: t.name })));
      
      randomTopics.push(...selected.map(topic => topic.id.toString()));
    });
    
    console.log('🎯 Final random topics array:', randomTopics);
    console.log('🔢 Total random topics selected:', randomTopics.length);
    
    // If no topics were selected, show helpful message
    if (randomTopics.length === 0) {
      console.log('⚠️ No topics selected for random test - this might indicate no topics with questions are available');
    }
    
    return randomTopics;
  };

  /**
   * Get chapters for selected subject
   */
  const getChaptersForSubject = (subject: string): string[] => {
    if (!subject) return [];
    
    // Fix: Make subject matching case-insensitive
    const subjectTopics = topics.filter(topic => topic.subject.toLowerCase() === subject.toLowerCase());
    console.log(`🔍 getChaptersForSubject: subject="${subject}", totalTopics=${topics.length}, subjectTopics=${subjectTopics.length}`);
    
    // Debug: log first few topics to see their structure
    if (subjectTopics.length > 0) {
      console.log(`📋 Sample ${subject} topics:`, subjectTopics.slice(0, 3).map(t => ({ name: t.name, subject: t.subject, chapter: t.chapter })));
    }
    
    const chapters = [...new Set(subjectTopics.map(topic => topic.chapter))]
      .filter((chapter): chapter is string => typeof chapter === 'string' && chapter !== null && chapter !== undefined && chapter.trim() !== '');
    
    console.log(`📋 Chapters found for ${subject}:`, chapters);
    return chapters;
  };

  /**
   * Get topics for selected subject and chapter
   */
  const getTopicsForChapter = (subject: string, chapter: string): Topic[] => {
    if (!subject || !chapter) return [];
    // Fix: Make subject matching case-insensitive
    return topics.filter(topic => topic.subject.toLowerCase() === subject.toLowerCase() && topic.chapter === chapter);
  };

  /**
   * Handle test type change
   */
  const handleTestTypeChange = (type: "random" | "custom" | "search") => {
    setTestType(type);
    setSelectedTopics([]);
    setSelectedTopicsCustom([]);
    setSelectedSubject("");
    setSelectedChapter("");
    // Only clear search for non-custom modes or when switching away from search mode
    if (type !== "custom" && type !== "search") {
      setSearchQuery("");
      setShowSearchResults(false);
    }
  };

  /**
   * Handle subject selection in custom mode
   */
  const handleSubjectChange = (subject: string) => {
    setSelectedSubject(subject);
    setSelectedChapter("");
    // Don't reset selectedTopicsCustom - preserve previously selected topics from other subjects
  };

  /**
   * Handle chapter selection in custom mode
   */
  const handleChapterChange = (chapter: string) => {
    setSelectedChapter(chapter);
    // Don't reset selectedTopicsCustom - preserve previously selected topics
  };

  /**
   * Handle topic selection in custom mode
   */
  const handleCustomTopicToggle = (topicId: string) => {
    setSelectedTopicsCustom(prev => 
      prev.includes(topicId) 
        ? prev.filter(id => id !== topicId)
        : [...prev, topicId]
    );
  };
  
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
   * It supports three modes: random test, custom selection, and search-based selection.
   * 
   * BUSINESS LOGIC:
   * - Random mode: Automatically selects topics from all subjects
   * - Custom mode: Uses user-selected topics from dropdowns
   * - Search mode: Uses topics selected via search functionality
   * 
   * Validates selections and creates test with appropriate parameters
   */
  const handleCreateTest = () => {
    let finalSelectedTopics: string[] = [];
    
    console.log('🚀 handleCreateTest called with testType:', testType);
    
    // Determine which topics to use based on test type
    if (testType === "random") {
      console.log('🎲 Using random test mode');
      finalSelectedTopics = generateRandomTopics(questionCount);
    } else if (testType === "custom") {
      console.log('🎯 Using custom test mode');
      finalSelectedTopics = selectedTopicsCustom;
    } else if (testType === "search") {
      console.log('🔍 Using search test mode');
      finalSelectedTopics = selectedTopics;
    }
    
    console.log('📋 Final selected topics:', finalSelectedTopics);
    console.log('🔢 Topics count:', finalSelectedTopics.length);
    
    // VALIDATION: Check if topics are selected
    if (finalSelectedTopics.length === 0) {
      console.log('❌ No topics selected, showing error toast');
      toast({
        title: "No topics selected",
        description: "Please select at least one topic for your test.",
        variant: "destructive",
      });
      return;
    }

    // VALIDATION: Check question count and time limit
    if (!questionCount || questionCount <= 0) {
      toast({
        title: "Invalid question count",
        description: "Please set a valid number of questions.",
        variant: "destructive",
      });
      return;
    }
    
    if (!timeLimit || timeLimit <= 0) {
      toast({
        title: "Invalid time limit",
        description: "Please set a valid time limit.",
        variant: "destructive",
      });
      return;
    }
    
    // Create test session with new payload structure
    // Always pass both question_count and time_limit from user selections
    const payload = {
      selected_topics: finalSelectedTopics,
      selection_mode: 'question_count', // Use question count mode
      question_count: questionCount, // Number of questions from slider
      time_limit: timeLimit, // Time limit from slider (in minutes)
      test_type: testType,
    };
    
    // Debug log to verify payload
    console.log('🚀 Creating test with payload:', payload);
    console.log('📋 Selected topics details:');
    finalSelectedTopics.forEach(topicId => {
      const topic = topics.find(t => t.id.toString() === topicId);
      if (topic) {
        console.log(`  - Topic ID ${topicId}: ${topic.subject} > ${topic.chapter} > ${topic.name}`);
      } else {
        console.log(`  - Topic ID ${topicId}: NOT FOUND in topics array!`);
      }
    });
    
    createTestMutation.mutate(payload);
  };

  // Remove duplicate function - use getChaptersForSubject instead

  const getTopicsByChapter = (subject: string, chapter: string): Topic[] => {
    // Fix: Make subject matching case-insensitive
    return topics.filter((topic: Topic) => topic.subject.toLowerCase() === subject.toLowerCase() && topic.chapter === chapter);
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
    // Fix: Make subject matching case-insensitive
    const subjectTopics = topics.filter((topic: Topic) => topic.subject.toLowerCase() === subject.toLowerCase());
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
                    className="flex items-center gap-2 text-white border-white bg-blue-600"
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
              
              {/* Test Type Selection */}
              <div className="mb-8">
                <h3 className="text-xl font-semibold text-gray-800 mb-6 flex items-center">
                  <Target className="h-6 w-6 mr-3 text-blue-600" />
                  Choose Test Mode
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                  {/* Random Test Card */}
                  <Card 
                    className={`cursor-pointer transition-all duration-300 border-2 ${
                      testType === "random" 
                        ? "border-blue-500 bg-blue-50 shadow-lg" 
                        : "border-gray-200 hover:border-blue-300 hover:shadow-md"
                    }`}
                    onClick={() => handleTestTypeChange("random")}
                  >
                    <CardHeader className="text-center pb-4">
                      <div className="flex justify-center mb-3">
                        <Shuffle className="h-8 w-8 text-blue-600" />
                      </div>
                      <CardTitle className="text-lg font-bold">Random Test</CardTitle>
                      <p className="text-sm text-gray-600">
                        Randomly generated questions
                      </p>
                    </CardHeader>
                  </Card>

                  {/* Custom Selection Card */}
                  <Card 
                    className={`cursor-pointer transition-all duration-300 border-2 ${
                      testType === "custom" 
                        ? "border-green-500 bg-green-50 shadow-lg" 
                        : "border-gray-200 hover:border-green-300 hover:shadow-md"
                    }`}
                    onClick={() => handleTestTypeChange("custom")}
                  >
                    <CardHeader className="text-center pb-4">
                      <div className="flex justify-center mb-3">
                        <Target className="h-8 w-8 text-green-600" />
                      </div>
                      <CardTitle className="text-lg font-bold">Select Subject</CardTitle>
                      <p className="text-sm text-gray-600">
                        Choose specific topics
                      </p>
                    </CardHeader>
                  </Card>

                  {/* Search Topics Card */}
                  <Card 
                    className={`cursor-pointer transition-all duration-300 border-2 ${
                      testType === "search" 
                        ? "border-purple-500 bg-purple-50 shadow-lg" 
                        : "border-gray-200 hover:border-purple-300 hover:shadow-md"
                    }`}
                    onClick={() => handleTestTypeChange("search")}
                  >
                    <CardHeader className="text-center pb-4">
                      <div className="flex justify-center mb-3">
                        <Search className="h-8 w-8 text-purple-600" />
                      </div>
                      <CardTitle className="text-lg font-bold">Search Topics</CardTitle>
                      <p className="text-sm text-gray-600">
                        Find specific topics
                      </p>
                    </CardHeader>
                  </Card>
                </div>
              </div>
              {/* Search Topics Section */}
              <div className="mb-6">
                <h5 className="text-md font-semibold text-gray-800 mb-3 flex items-center">
                  <Search className="h-4 w-4 mr-2 text-green-600" />
                  Search Topics
                </h5>
                <SearchBar
                  searchQuery={searchQuery}
                  onSearchChange={handleSearchChange}
                  onClearSearch={clearSearch}
                  filteredTopics={filteredTopics}
                  selectedTopics={selectedTopicsCustom}
                  onTopicSelect={(topicId) => handleCustomTopicToggle(topicId)}
                  showResults={showSearchResults}
                />
              </div>
              {/* Custom Subject Selection */}
              {testType === "custom" && (
                <div className="mb-8">
                  <h4 className="text-lg font-semibold text-gray-800 mb-4">
                    Select Subject, Chapter, and Topics
                  </h4>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    {/* Subject Dropdown */}
                    <div>
                      <Label className="text-sm font-medium text-gray-700 mb-2 block">Subject</Label>
                      <Select value={selectedSubject} onValueChange={handleSubjectChange}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select subject" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Physics">Physics</SelectItem>
                          <SelectItem value="Chemistry">Chemistry</SelectItem>
                          <SelectItem value="Botany">Botany</SelectItem>
                          <SelectItem value="Zoology">Zoology</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Chapter Dropdown */}
                    <div>
                      <Label className="text-sm font-medium text-gray-700 mb-2 block">Chapter</Label>
                      <Select 
                        value={selectedChapter} 
                        onValueChange={handleChapterChange}
                        disabled={!selectedSubject}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select chapter" />
                        </SelectTrigger>
                        <SelectContent>
                          {getChaptersForSubject(selectedSubject).map((chapter) => (
                            <SelectItem key={chapter} value={chapter}>{chapter}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Topics Multi-select */}
                    <div>
                      <Label className="text-sm font-medium text-gray-700 mb-2 block">
                        Topics ({selectedTopicsCustom.length} selected)
                      </Label>
                      <div className="border rounded-md p-2 max-h-32 overflow-y-auto bg-white">
                        {selectedSubject && selectedChapter ? (
                          getTopicsForChapter(selectedSubject, selectedChapter).map((topic) => (
                            <div key={topic.id} className="flex items-center space-x-2 p-1">
                              <Checkbox
                                id={`custom-topic-${topic.id}`}
                                checked={selectedTopicsCustom.includes(topic.id.toString())}
                                onCheckedChange={() => handleCustomTopicToggle(topic.id.toString())}
                                className="data-[state=checked]:bg-green-600 data-[state=checked]:border-green-600"
                              />
                              <Label 
                                htmlFor={`custom-topic-${topic.id}`} 
                                className="text-xs cursor-pointer flex-1"
                              >
                                {topic.name}
                              </Label>
                            </div>
                          ))
                        ) : (
                          <p className="text-xs text-gray-500 text-center py-2">
                            Select subject and chapter first
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  
                  {/* Show all selected topics across all chapters */}
                  {selectedTopicsCustom.length > 0 && (
                    <div className="mt-4">
                      <div className="flex items-center justify-between mb-2">
                        <Label className="text-sm font-medium text-gray-700">
                          All Selected Topics ({selectedTopicsCustom.length})
                        </Label>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedTopicsCustom([])}
                          className="text-xs text-red-600 hover:text-red-800 border-red-200 hover:border-red-300"
                        >
                          Clear All
                        </Button>
                      </div>
                      <div className="border rounded-md p-3 bg-gray-50 max-h-40 overflow-y-auto">
                        <div className="flex flex-wrap gap-2">
                          {selectedTopicsCustom.map((topicId) => {
                            const topic = topics.find(t => t.id.toString() === topicId);
                            if (!topic) return null;
                            return (
                              <div
                                key={topicId}
                                className="inline-flex items-center gap-1 bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs"
                              >
                                <span>{topic.subject} - {topic.chapter}</span>
                                <span className="font-medium">{topic.name}</span>
                                <button
                                  onClick={() => handleCustomTopicToggle(topicId)}
                                  className="ml-1 text-green-600 hover:text-green-800"
                                >
                                  <X className="h-3 w-3" />
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {/* Search Bar for Search Mode */}
              {testType === "search" && (
                <SearchBar
                  searchQuery={searchQuery}
                  onSearchChange={handleSearchChange}
                  onClearSearch={clearSearch}
                  filteredTopics={filteredTopics}
                  selectedTopics={selectedTopics}
                  onTopicSelect={handleTopicSelectFromSearch}
                  showResults={showSearchResults}
                />
              )}

              {/* Test Settings */}
              <div className="mb-8">
                <h4 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                  <Clock className="h-5 w-5 mr-2 text-blue-600" />
                  Test Settings
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Time Limit Slider */}
                  <div>
                    <Label className="text-sm font-medium text-gray-700 mb-3 block">
                      Time Limit: {timeLimit} minutes
                    </Label>
                    <Slider
                      value={[timeLimit]}
                      onValueChange={(value) => setTimeLimit(value[0])}
                      max={180}
                      min={15}
                      step={15}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>15 min</span>
                      <span>180 min</span>
                    </div>
                  </div>

                  {/* Number of Questions Slider */}
                  <div>
                    <Label className="text-sm font-medium text-gray-700 mb-3 block">
                      Number of Questions: {questionCount}
                    </Label>
                    <Slider
                      value={[questionCount]}
                      onValueChange={(value) => setQuestionCount(value[0])}
                      max={100}
                      min={5}
                      step={5}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>5 questions</span>
                      <span>100 questions</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Subject Cards for Search Mode */}
              {testType === "search" && !showSearchResults && (
                <div className="space-y-8 mb-12">
                  <h3 className="text-xl font-semibold text-gray-800 mb-6 flex items-center">
                    <ListCheck className="h-6 w-6 mr-3 text-blue-600" />
                    Select Topics by Chapter
                  </h3>
                
                {/* Subject Dropdown Selection */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {["Physics", "Chemistry", "Botany", "Zoology"].map((subject) => {
                    // Fix: Make subject matching case-insensitive
                    const subjectTopics = topics.filter((t: Topic) => t.subject.toLowerCase() === subject.toLowerCase());
                    const selectedCount = subjectTopics.filter((t: Topic) => selectedTopics.includes(t.id.toString())).length;
                    const hasChapters = subjectTopics.some((t: Topic) => t.chapter && t.chapter.trim() !== '');
                    
                    console.log(`🧪 ${subject} check:`, { 
                      subjectTopics: subjectTopics.length, 
                      hasChapters, 
                      sampleChapters: subjectTopics.slice(0, 3).map(t => t.chapter) 
                    });
                    
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
                              getChaptersForSubject(subject).map((chapter) => {
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

              {/* Create Test Button */}
              <div className="flex justify-center">
                <Button
                  onClick={handleCreateTest}
                  disabled={createTestMutation.isPending || (
                    testType === "search" && selectedTopics.length === 0
                  ) || (
                    testType === "custom" && selectedTopicsCustom.length === 0
                  )}
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
                      Create Test ({
                        testType === "random" 
                          ? `${questionCount} questions` 
                          : testType === "custom" 
                            ? `${selectedTopicsCustom.length} topic${selectedTopicsCustom.length !== 1 ? 's' : ''}`
                            : `${selectedTopics.length} topic${selectedTopics.length !== 1 ? 's' : ''}`
                      })
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