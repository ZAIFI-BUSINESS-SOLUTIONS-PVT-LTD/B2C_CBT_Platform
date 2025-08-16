// In Results.tsx

import { useParams, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { ResultsDisplay } from "@/components/results-display"; // <--- Ensure this import path is correct
import { Skeleton } from "@/components/ui/skeleton";
import { useEffect } from "react";

// --- START NEW/MODIFIED CODE ---
// Import the ResultsDisplayProps interface and extract the type of its 'results' property.
// This assumes ResultsDisplay is in a file like 'src/components/results-display.tsx'
// Adjust the import path if your file structure is different.
import type {ResultsDisplayProps} from "@/components/results-display"; // Use 'type' for type-only import

type QueryResultsType = ResultsDisplayProps['results']; // Extract the 'results' part of the interface
// --- END NEW/MODIFIED CODE ---

export default function Results() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [, navigate] = useLocation();

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

  // Specify the type of data that useQuery will return (QueryResultsType)
  const { data: results, isLoading } = useQuery<QueryResultsType, Error>({ // <--- CHANGE THIS LINE
    queryKey: [`/api/test-sessions/${sessionId}/results/`],  // Added trailing slash to match DRF router
    enabled: !!sessionId,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50 flex items-center justify-center">
        <div className="space-y-4">
          <Skeleton className="h-8 w-64 bg-[#E2E8F0]" />
          <Skeleton className="h-32 w-96 bg-[#E2E8F0]" />
          <Skeleton className="h-8 w-48 bg-[#E2E8F0]" />
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50 flex items-center justify-center">
        <div className="text-center bg-white rounded-2xl shadow-lg border border-[#E2E8F0] p-8 max-w-md mx-4">
          <h2 className="text-2xl font-bold text-[#1F2937] mb-4">
            Results Not Found
          </h2>
          <p className="text-[#6B7280]">
            The test results you're looking for don't exist.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50">
      <ResultsDisplay results={results} />
    </div>
  );
}