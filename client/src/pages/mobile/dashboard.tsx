import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { useLocation, Link } from "wouter";
import { useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, ArrowRight, UserRound, Trophy, ChevronLeft } from "lucide-react";
import { API_CONFIG } from "@/config/api";
import { authenticatedFetch } from "@/lib/auth";
import TestZoneInsights from "@/components/test-zone-insights";
import TestHistory from "@/components/test-history";
import LatestTestSummary from "@/components/latest-test-summary";
import MobileDock from "@/components/mobile-dock";
import { AnalyticsData, InsightsData } from "@/types/dashboard";

/**
 * Main Landing Dashboard Component
 */
export default function LandingDashboard() {
  const [activeTab, setActiveTab] = useState<'practice' | 'battle'>('practice');
  const { isAuthenticated, loading, student } = useAuth();

  const [, navigate] = useLocation();

  // === NAVIGATION GUARD ===
  // Redirect to home page when user tries to navigate back from landing dashboard
  useEffect(() => {
    const handlePopState = (e: PopStateEvent) => {
      e.preventDefault();
      // When user presses back from the analysis/dashboard page,
      // navigate to the topics (test) page instead of home.
      navigate('/topics', { replace: true });
    };

    // Push current state and listen for back navigation
    window.history.pushState(null, '', window.location.href);
    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, [navigate]);

  // Redirect to home if not authenticated
  if (!loading && !isAuthenticated) {
    navigate('/');
    return null;
  }

  // Fetch comprehensive analytics data
  const { data: analytics, isLoading, error } = useQuery<AnalyticsData>({
    queryKey: ['/api/dashboard/comprehensive-analytics/'],
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: isAuthenticated && !loading, // Only run when authenticated
  });

  // Fetch insights data directly from cache file
  const { data: insights, isLoading: insightsLoading } = useQuery<InsightsData>({
    queryKey: ['/api/insights/cache/'],
    refetchInterval: 30000, // Refresh every 30 seconds for real-time updates
    enabled: isAuthenticated && !loading, // Only run when authenticated
  });

  // (Platform test analytics and per-test subject filters removed - showing Test History instead)

  if (isLoading || insightsLoading) {
    return <DashboardSkeleton />;
  }

  if (error || !analytics) {
    return <ErrorState />;
  }

  return (
    <div
      className="h-screen flex flex-col overflow-hidden bg-cover bg-center bg-no-repeat"
      style={{
        backgroundImage: 'url(/testpage-bg.webp)'
      }}
    >
      {/* Fixed Header (transparent) */}
      <div className="bg-transparent z-10 border-b border-transparent">
        <header className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-xl font-bold text-gray-900">Analysis</h1>
        </header>
      </div>

      {/* Fixed Latest Test Summary */}
      <div className="p-4 flex-shrink-0 max-w-6xl mx-auto w-full">
        <LatestTestSummary />
      </div>

      {/* Scrollable Test History Container */}
      <div className="flex-1 overflow-y-auto pb-20">
        <TestHistory />
      </div>

      <MobileDock />
    </div>
  );
}






/**
 * Dashboard Loading Skeleton
 */
function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="w-full">
        <div className="animate-pulse space-y-6">
          <div className="h-12 bg-gray-200 rounded-lg w-1/3"></div>
          <div className="grid grid-cols-1 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
          <div className="grid grid-cols-1 gap-8">
            <div className="h-96 bg-gray-200 rounded-lg"></div>
            <div className="h-96 bg-gray-200 rounded-lg"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Error State Component
 */
function ErrorState() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <Card className="max-w-md w-full">
        <CardContent className="p-6 text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Unable to Load Dashboard</h3>
          <p className="text-gray-600 mb-4">
            Take a practice test first to see your performance analytics.
          </p>
          <Link href="/topics">
            <Button>
              Take Your First Test
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}