import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronLeft, Bookmark, SlidersHorizontal, BookOpen, ChevronDown } from "lucide-react";
import { authenticatedFetch } from "@/lib/auth";
import { API_CONFIG } from "@/config/api";
import normalizeImageSrc from "@/lib/media";
import MobileDock from "@/components/mobile-dock";

interface BookmarkedAnswer {
  id: number;
  session: number;
  question: number;
  questionDetails: {  // Changed from question_details to questionDetails (camelCase)
    id: number;
    question: string;
    optionA: string;  // Changed from option_a to optionA (camelCase)
    optionB: string;  // Changed from option_b to optionB
    optionC: string;  // Changed from option_c to optionC
    optionD: string;  // Changed from option_d to optionD
    correctAnswer: string;  // Changed from correct_answer to correctAnswer
    explanation: string;
    questionImage?: string | null;  // Changed from question_image
    optionAImage?: string | null;  // Changed from option_a_image
    optionBImage?: string | null;  // Changed from option_b_image
    optionCImage?: string | null;  // Changed from option_c_image
    optionDImage?: string | null;  // Changed from option_d_image
    explanationImage?: string | null;  // Changed from explanation_image
    subject?: string;
    topicName?: string;  // Changed from topic_name
  };
  selectedAnswer: string | null;  // Changed from selected_answer
  isCorrect: boolean | null;  // Changed from is_correct
  markedForReview: boolean;  // Changed from marked_for_review
}

interface BookmarkedSession {
  id: number;
  test_name: string;
  test_type: string;
  bookmark_count: number;
  start_time: string | null;
  total_questions: number;
}

export default function BookmarkedQuestions() {
  const [, navigate] = useLocation();
  const [selectedSession, setSelectedSession] = useState<number | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handleDocClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('click', handleDocClick);
    return () => document.removeEventListener('click', handleDocClick);
  }, []);

  // Fetch sessions with bookmarks
  const { data: sessions, isLoading: sessionsLoading } = useQuery<BookmarkedSession[]>({
    queryKey: ['bookmarked-sessions'],
    queryFn: async () => {
      const response = await authenticatedFetch(
        `${API_CONFIG.BASE_URL}/api/test-answers/bookmarked-sessions/`
      );
      if (!response.ok) throw new Error('Failed to fetch bookmarked sessions');
      const data = await response.json();
      // DRF may return an array or a paginated object {results: []}.
      const arr = Array.isArray(data) ? data : data.results || [];
      // Normalize keys to ensure `test_name` exists regardless of camelCase/snake_case
      return arr.map((s: any) => ({
        id: s.id,
        test_name: s.test_name ?? s.testName ?? s.name ?? '',
        test_type: s.test_type ?? s.testType ?? '',
        bookmark_count: s.bookmark_count ?? s.bookmarkCount ?? 0,
        start_time: s.start_time ?? s.startTime ?? null,
        total_questions: s.total_questions ?? s.totalQuestions ?? 0,
      }));
    },
  });

  // Fetch bookmarked questions (filtered by session if selected)
  const { data: bookmarksResponse, isLoading: bookmarksLoading } = useQuery<{ results: BookmarkedAnswer[] } | BookmarkedAnswer[]>({
    queryKey: ['bookmarked-questions', selectedSession],
    queryFn: async () => {
      const url = selectedSession
        ? `${API_CONFIG.BASE_URL}/api/test-answers/?is_bookmarked=true&session_id=${selectedSession}`
        : `${API_CONFIG.BASE_URL}/api/test-answers/?is_bookmarked=true`;
      
      console.log('🔍 Fetching bookmarks from:', url);
      const response = await authenticatedFetch(url);
      if (!response.ok) throw new Error('Failed to fetch bookmarked questions');
      const data = await response.json();
      console.log('📦 Raw bookmarks response:', data);
      console.log('📦 Response type:', Array.isArray(data) ? 'Array' : 'Object');
      if (!Array.isArray(data) && data.results) {
        console.log('📦 Paginated response, results count:', data.results?.length || 0);
      }
      // Handle both paginated and non-paginated responses
      return data;
    },
    enabled: true,
  });

  // Extract bookmarks array from response (handle paginated or plain array)
  const bookmarks = bookmarksResponse
    ? Array.isArray(bookmarksResponse)
      ? bookmarksResponse
      : (bookmarksResponse as { results: BookmarkedAnswer[] }).results || []
    : [];

  console.log('✅ Final bookmarks array:', bookmarks);
  console.log('✅ Bookmarks count:', bookmarks.length);

  const isLoading = sessionsLoading || bookmarksLoading;

  const getOptionClass = (option: string, correctAnswer: string, selectedAnswer: string | null) => {
    if (option === correctAnswer) {
      return "border-2 border-green-400 bg-green-500/20";
    }
    if (selectedAnswer && option === selectedAnswer && option !== correctAnswer) {
      return "border-2 border-red-400 bg-red-500/20";
    }
    return "border border-white/40 bg-white/25";
  };

  if (isLoading) {
    return (
      <div 
        className="min-h-screen bg-cover bg-center bg-no-repeat bg-fixed relative pb-20"
        style={{ backgroundImage: "url('/testpage-bg.webp')", backgroundAttachment: 'fixed' }}
      >
        <div className="absolute inset-0 bg-transparent"></div>
        <div className="relative z-10">
          <div className="sticky top-0 bg-transparent z-10 border-b border-transparent">
            <div className="w-full mx-auto py-3 px-4 flex items-center gap-3">
              <Skeleton className="h-8 w-8 rounded-lg bg-transparent" />
              <Skeleton className="h-6 w-48 bg-transparent" />
            </div>
          </div>
          <div className="p-4 space-y-4">
            <Skeleton className="h-12 w-full rounded-lg bg-transparent" />
            <Skeleton className="h-64 w-full rounded-lg bg-transparent" />
            <Skeleton className="h-64 w-full rounded-lg bg-transparent" />
          </div>
        </div>
      </div>
    );
  }

  const totalBookmarks = sessions?.reduce((sum, s) => sum + s.bookmark_count, 0) || 0;

  return (
    <div 
      className="min-h-screen bg-cover bg-center bg-no-repeat bg-fixed relative pb-20"
      style={{ backgroundImage: "url('/testpage-bg.webp')", backgroundAttachment: 'fixed' }}
    >
      {/* Removed overlay so background image shows through */}
      <div className="absolute inset-0 bg-transparent"></div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <div className="sticky top-0 bg-white/90 backdrop-blur-md z-30 border-b border-white/90">
          <div className="w-full mx-auto py-3 px-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                className="bg-transparent border border-transparent text-gray-900 hover:bg-white/5 h-10 w-10"
                onClick={() => navigate('/profile')}
              >
                <ChevronLeft className="h-5 w-5" />
              </Button>
              <h1 className="text-lg font-bold text-gray-900">Bookmarked Questions</h1>
            </div>
            <Badge className="bg-transparent border-transparent text-gray-900 flex items-center gap-1">
              <Bookmark className="h-3 w-3 text-gray-700" />
              {totalBookmarks}
            </Badge>
          </div>
        </div>

        {/* Empty State */}
        {!bookmarks || bookmarks.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-4 py-16">
            <div className="bg-transparent border-2 border-transparent rounded-full p-6 mb-4">
              <Bookmark className="h-12 w-12 text-gray-900" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No Bookmarks Yet</h2>
            <p className="text-gray-700 text-center mb-6 max-w-sm">
              Bookmark questions during tests to review them later. Click the bookmark button next to any question.
            </p>
            <Button 
              onClick={() => navigate('/topics')} 
              className="bg-transparent border border-transparent text-gray-900 hover:bg-white/5"
            >
              <BookOpen className="h-4 w-4 mr-2" />
              Take a Test
            </Button>
          </div>
        ) : (
          <>
            {/* Filter Section */}
            <div className="sticky top-14 bg-white/90 backdrop-blur-md z-30 border-b border-white/90 px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <SlidersHorizontal className="h-4 w-4 text-gray-700" />
                  <span className="text-sm text-gray-700">Filter by test:</span>
                </div>
              <div className="relative inline-block" ref={rootRef}>
                <button
                  type="button"
                  onClick={() => setMenuOpen((s) => !s)}
                  aria-haspopup="menu"
                  aria-expanded={menuOpen}
                  className="flex items-center justify-between w-44 sm:w-56 gap-3 text-sm px-3 py-2 border border-transparent rounded-lg bg-transparent shadow-sm hover:bg-white/5 focus:outline-none focus:ring-0"
                >
                  <span className="truncate text-sm text-gray-900">
                    {selectedSession === null
                      ? `All Tests (${totalBookmarks})`
                      : sessions?.find((s) => s.id === selectedSession)?.test_name || 'Select Test'}
                  </span>
                  <ChevronDown className={`h-4 w-4 text-gray-700 transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
                </button>

                {menuOpen && (
                  <div className="absolute right-0 mt-2 w-44 sm:w-56 bg-white/95 backdrop-blur-md rounded-lg shadow-lg border border-transparent ring-1 ring-black/5 z-40">
                    <ul role="menu" className="max-h-48 overflow-auto">
                      <li
                        role="menuitem"
                        onClick={() => {
                          setSelectedSession(null);
                          setMenuOpen(false);
                        }}
                        className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b last:border-b-0 text-gray-800"
                      >
                        All Tests ({totalBookmarks})
                      </li>
                      {sessions?.map((session) => (
                        <li
                          key={session.id}
                          role="menuitem"
                          onClick={() => {
                            setSelectedSession(session.id);
                            setMenuOpen(false);
                          }}
                          className="px-3 py-2 hover:bg-blue-50 cursor-pointer flex items-center justify-between text-gray-800"
                        >
                          <span className="truncate">{session.test_name}</span>
                          <span className="ml-2 text-xs text-slate-500">{session.bookmark_count}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Questions List */}
          <div className="p-4 space-y-6">
            {bookmarks.map((bookmark, index) => {
              const q = bookmark.questionDetails;  // Changed from question_details to questionDetails
              if (!q) return null; // guard against missing question details
              return (
                <Card key={bookmark.id} className="bg-white/80 backdrop-blur-sm border-transparent hover:bg-white/90 transition-all duration-200 shadow-lg">
                  <CardContent className="p-4">
                    {/* Question Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs bg-transparent text-gray-900 border-transparent">
                          Question {index + 1}
                        </Badge>
                        {q.subject && (
                          <Badge className="text-xs bg-transparent text-gray-900 border-transparent">
                            {q.subject}
                          </Badge>
                        )}
                        {bookmark.markedForReview && (  // Changed from marked_for_review
                          <Badge className="text-xs bg-amber-500/30 text-gray-900 border-amber-400/40">
                            Marked for Review
                          </Badge>
                        )}
                      </div>
                      <Bookmark className="h-4 w-4 text-amber-300 fill-current" />
                    </div>

                    {/* Question Text */}
                    <div className="mb-4">
                      <p className="text-sm text-gray-900 leading-relaxed">{q.question}</p>
                      {q.questionImage && (  // Changed from question_image
                        <img
                          src={normalizeImageSrc(q.questionImage)}
                          alt="Question"
                          className="mt-2 max-w-full h-auto rounded-lg"
                        />
                      )}
                    </div>

                    {/* Options */}
                    <div className="space-y-2 mb-4">
                      {(['A', 'B', 'C', 'D'] as const).map((option) => {
                        const optionKey = `option${option}` as keyof typeof q;  // Changed from option_a to optionA
                        const optionImageKey = `option${option}Image` as keyof typeof q;  // Changed from option_a_image to optionAImage
                        const optionText = q[optionKey] as string;
                        const optionImage = q[optionImageKey] as string | null | undefined;

                        return (
                          <div
                            key={option}
                            className={`p-3 rounded-lg ${getOptionClass(
                              option,
                              q.correctAnswer,  // Changed from correct_answer
                              bookmark.selectedAnswer  // Changed from selected_answer
                            )}`}
                          >
                            <div className="flex items-start gap-2">
                              <span className="font-semibold text-sm text-gray-900">{option}.</span>
                              <div className="flex-1">
                                <p className="text-sm text-gray-900">{optionText}</p>
                                {optionImage && (
                                  <img
                                    src={normalizeImageSrc(optionImage)}
                                    alt={`Option ${option}`}
                                    className="mt-2 max-w-full h-auto rounded-lg"
                                  />
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Answer Status */}
                    <div className="mb-3 p-2 rounded-lg bg-white/90 border border-white/90">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-700">Your Answer:</span>
                        <span className="font-semibold text-gray-900">
                          {bookmark.selectedAnswer || 'Not Answered'}  {/* Changed from selected_answer */}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs mt-1">
                        <span className="text-gray-700">Correct Answer:</span>
                        <span className="font-semibold text-green-600">{q.correctAnswer}</span>  {/* Changed from correct_answer */}
                      </div>
                    </div>

                    {/* Explanation */}
                    {q.explanation && (
                      <div className="border-t border-transparent pt-3">
                        <p className="text-xs font-semibold text-gray-900 mb-2 flex items-center gap-1">
                          <BookOpen className="h-3 w-3" />
                          Explanation
                        </p>
                        <p className="text-sm text-gray-800 leading-relaxed">{q.explanation}</p>
                        {q.explanationImage && (  // Changed from explanation_image
                          <img
                            src={normalizeImageSrc(q.explanationImage)}
                            alt="Explanation"
                            className="mt-2 max-w-full h-auto rounded-lg"
                          />
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </>
      )}

        <MobileDock />
      </div>
    </div>
  );
}
