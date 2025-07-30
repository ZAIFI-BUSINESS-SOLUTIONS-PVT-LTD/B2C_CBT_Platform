/**
 * Test Page Component
 * 
 * This page handles the test-taking interface for NEET practice tests.
 * Features include:
 * - Real-time question display with multiple choice options
 * - Timer functionality (countdown or question-based)
 * - Answer selection and submission
 * - Question navigation (next/previous)
 * - Mark for review functionality
 * - Auto-submission when time expires
 */

import { useParams } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { TestInterface } from "@/components/test-interface";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Test page component that loads and displays the test interface
 * @returns JSX element containing the test interface or loading/error states
 */
export default function Test() {
  // Extract session ID from URL parameters
  const { sessionId } = useParams<{ sessionId: string }>();
  
  // Fetch test session data from the server
  const { data: session, isLoading, error } = useQuery({
    queryKey: [`/api/test-sessions/${sessionId}/`],
    enabled: !!sessionId && !isNaN(Number(sessionId)),
  });

  // Loading state with skeleton placeholders
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-32 w-96" />
          <Skeleton className="h-8 w-48" />
        </div>
      </div>
    );
  }

  // Error state when there's an API error
  if (error) {
    console.error('Test session fetch error:', error);
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            Error Loading Test
          </h2>
          <p className="text-slate-600 mb-4">
            There was an error loading your test session. Please try again.
          </p>
          <button
            onClick={() => window.location.href = '/topics'}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Return to Topics
          </button>
        </div>
      </div>
    );
  }

  // Error state when test session is not found or sessionId is invalid
  if (!session || !sessionId || isNaN(Number(sessionId))) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            Test Session Not Found
          </h2>
          <p className="text-slate-600">
            The test session you're looking for doesn't exist or has expired.
          </p>
        </div>
      </div>
    );
  }

  // Main test interface
  return (
    <div className="min-h-screen bg-slate-50">
      <TestInterface sessionId={parseInt(sessionId!)} />
    </div>
  );
}
