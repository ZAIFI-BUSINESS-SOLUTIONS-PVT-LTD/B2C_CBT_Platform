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
import { TestInterface } from "@/components/test-interface";

/**
 * Test page component that loads and displays the test interface
 * @returns JSX element containing the test interface or loading/error states
 */
export default function Test() {
  // Extract session ID from URL parameters
  const { sessionId } = useParams<{ sessionId: string }>();
  
  // Validate sessionId - if invalid, show error
  if (!sessionId || isNaN(Number(sessionId))) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            Invalid Test Session
          </h2>
          <p className="text-slate-600 mb-4">
            The test session ID is invalid or missing.
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

  // Main test interface - let TestInterface handle all data fetching
  return (
    <div className="min-h-screen bg-slate-50">
      <TestInterface sessionId={parseInt(sessionId)} />
    </div>
  );
}
