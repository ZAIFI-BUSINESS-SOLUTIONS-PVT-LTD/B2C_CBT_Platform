// In Results.tsx

import { useParams, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { ResultsDisplay } from "@/components/results-display"; // <--- Ensure this import path is correct
import { Skeleton } from "@/components/ui/skeleton";
import { useEffect, useState } from "react";

// --- START NEW/MODIFIED CODE ---
// Import the ResultsDisplayProps interface and extract the type of its 'results' property.
// This assumes ResultsDisplay is in a file like 'src/components/results-display.tsx'
// Adjust the import path if your file structure is different.
import type { ResultsDisplayProps } from "@/components/results-display"; // Use 'type' for type-only import
import { Button } from "@/components/ui/button";
import { ChevronLeft, BarChart3, BookOpen } from "lucide-react";
import { QuestionReview } from "@/components/question-review";

type QueryResultsType = ResultsDisplayProps['results']; // Extract the 'results' part of the interface
// --- END NEW/MODIFIED CODE ---

export default function Results() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [, navigate] = useLocation();
  const [activeTab, setActiveTab] = useState<'overview' | 'review'>('overview');

  // === NAVIGATION GUARD ===
  // Redirect to landing page when user tries to navigate back from results
  useEffect(() => {
    const handlePopState = (e: PopStateEvent) => {
      e.preventDefault();
      console.log('🔄 Back navigation detected from Results page, redirecting to landing...');
      navigate('/', { replace: true });
    };

    // Push current state and listen for back navigation
    window.history.pushState(null, '', window.location.href);
    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, [navigate]);

  const formatDate = (date: Date) => {
    const day = date.getDate().toString().padStart(2, '0');
    const month = date.toLocaleString('default', { month: 'short' });
    const year = date.getFullYear().toString().slice(-2);
    return `${day} ${month} ${year}`;
  };

  // Specify the type of data that useQuery will return (QueryResultsType)
  const { data: results, isLoading } = useQuery<QueryResultsType, Error>({ // <--- CHANGE THIS LINE
    queryKey: [`/api/test-sessions/${sessionId}/results/`],  // Added trailing slash to match DRF router
    enabled: !!sessionId,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50 flex items-center justify-center px-4">
        <div className="space-y-3 w-full max-w-sm">
          <Skeleton className="h-6 w-48 bg-[#E2E8F0] mx-auto" />
          <Skeleton className="h-24 w-full bg-[#E2E8F0]" />
          <Skeleton className="h-4 w-32 bg-[#E2E8F0] mx-auto" />
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50 flex items-center justify-center px-4">
        <div className="text-center bg-white rounded-2xl shadow-lg border border-[#E2E8F0] p-6 max-w-sm mx-4 w-full">
          <h2 className="text-lg font-bold text-[#1F2937] mb-3">
            Results Not Found
          </h2>
          <p className="text-[#6B7280] text-sm">
            The test results you're looking for don't exist.
          </p>
        </div>
      </div>
    );
  }

  const testName = (results as any).testName || (results as any).test_name || 'Test';
  const timestamp = formatDate(new Date((results as any).startTime || (results as any).start_time || Date.now()));

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="sticky top-0 bg-white z-10">
        {/* Header Section */}
        <div className="w-full mx-auto py-3 px-4 border-b border-gray-200 flex items-center justify-between">
          <div className="inline-flex items-center gap-3">
            <Button variant="secondary" size="icon" className="size-8" onClick={() => navigate('/dashboard')}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-lg font-bold text-gray-900">Test Result</h1>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <nav className="flex px-4" aria-label="Tabs">
            <button
              onClick={() => setActiveTab('overview')}
              className={`flex-1 flex items-center justify-center gap-2 py-4 px-2 border-b-2 font-medium text-sm transition-colors duration-200 active:bg-gray-50 ${activeTab === 'overview'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
            >
              <BarChart3 className="h-4 w-4" />
              <span>Overview</span>
            </button>
            <button
              onClick={() => setActiveTab('review')}
              className={`flex-1 flex items-center justify-center gap-2 py-4 px-2 border-b-2 font-medium text-sm transition-colors duration-200 active:bg-gray-50 ${activeTab === 'review'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
            >
              <BookOpen className="h-4 w-4" />
              <span>Review</span>
            </button>
          </nav>
        </div>
      </div>
      {activeTab === 'overview' && <ResultsDisplay results={results} onReviewClick={() => setActiveTab('review')} />}
      {activeTab === 'review' && (
        <QuestionReview
          detailedAnswers={results.detailedAnswers}
          correctAnswers={results.correctAnswers}
          incorrectAnswers={results.incorrectAnswers}
          unansweredQuestions={results.unansweredQuestions}
        />
      )}
    </div>
  );
}