// In Results.tsx

import { useParams, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { ResultsDisplay } from "@/components/results-display";
import { Skeleton } from "@/components/ui/skeleton";
import { useEffect } from "react";
import type { ResultsDisplayProps } from "@/components/results-display";
import { Button } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";

type QueryResultsType = ResultsDisplayProps['results'];

export default function Results() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [, navigate] = useLocation();

  // === NAVIGATION GUARD ===
  // Redirect to landing page when user tries to navigate back from results
  useEffect(() => {
    const handlePopState = (e: PopStateEvent) => {
      e.preventDefault();
      console.log('🔄 Back navigation detected from Results page, redirecting to topics...');
      navigate('/topics', { replace: true });
    };

    // Push current state and listen for back navigation
    window.history.pushState(null, '', window.location.href);
    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, [navigate]);

  // Specify the type of data that useQuery will return (QueryResultsType)
  const { data: results, isLoading } = useQuery<QueryResultsType, Error>({
    queryKey: [`/api/test-sessions/${sessionId}/results/`],
    enabled: !!sessionId,
  });

  const handleReviewClick = () => {
    navigate(`/review/${sessionId}`);
  };

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

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-cover bg-center bg-no-repeat" style={{ backgroundImage: "url('/testpage-bg.webp')" }}>
      <div className="bg-white z-10 flex-shrink-0">
        {/* Header Section */}
        <div className="w-full mx-auto py-3 px-4 border-b border-gray-200 flex items-center justify-between">
          <div className="inline-flex items-center gap-3">
            <Button variant="secondary" size="icon" className="size-8" onClick={() => navigate('/topics')}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-lg font-bold text-gray-900">Test Result</h1>
          </div>
        </div>
      </div>
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <ResultsDisplay results={results} onReviewClick={handleReviewClick} />
      </div>
    </div>
  );
}