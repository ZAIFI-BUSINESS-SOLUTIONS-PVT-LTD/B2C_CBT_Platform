import { useEffect, useState } from "react";
import { useLocation, useRoute } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "@/lib/auth";
import { API_CONFIG } from "@/config/api";
import LoadingVideo from "@/components/LoadingVideo";

/**
 * Loading Results Page
 * Shows engaging video while zone insights are being generated
 * Redirects to dashboard once insights are ready
 */
export default function LoadingResultsPage() {
  const [, navigate] = useLocation();
  const [, params] = useRoute("/loading-results/:sessionId");
  const sessionId = params?.sessionId;

  // If no session ID, redirect immediately
  useEffect(() => {
    if (!sessionId) {
      console.warn('No session ID provided, redirecting to dashboard');
      navigate('/dashboard', { replace: true });
    }
  }, [sessionId, navigate]);

  // Poll for zone insights status for this test session
  const { data: statusData } = useQuery({
    queryKey: [`/api/zone-insights/status/${sessionId}/`, sessionId],
    queryFn: async () => {
      const url = `${API_CONFIG.BASE_URL}/api/zone-insights/status/${sessionId}/`;
      const response = await authenticatedFetch(url);
      
      if (!response.ok) {
        throw new Error('Failed to fetch zone insights status');
      }
      
      return response.json();
    },
    refetchInterval: 1500, // Poll every 1.5 seconds
    refetchIntervalInBackground: true,
    retry: true,
    enabled: !!sessionId,
  });

  // Redirect to dashboard once zone insights are confirmed generated
  useEffect(() => {
    if (statusData?.insights_generated === true && statusData?.total_subjects > 0) {
      console.log('Zone insights confirmed ready, redirecting to dashboard');
      // Give a small delay to let the video play a bit more smoothly
      const timer = setTimeout(() => {
        navigate('/dashboard', { replace: true });
      }, 1500);
      
      return () => clearTimeout(timer);
    }
  }, [statusData, navigate]);

  // Fallback: redirect after 30 seconds regardless
  useEffect(() => {
    const fallbackTimer = setTimeout(() => {
      console.log('Fallback redirect to dashboard after 30s');
      navigate('/dashboard', { replace: true });
    }, 30000);

    return () => clearTimeout(fallbackTimer);
  }, [navigate]);

  return <LoadingVideo />;
}
