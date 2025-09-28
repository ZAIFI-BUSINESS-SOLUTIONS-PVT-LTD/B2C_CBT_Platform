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
import PracticeArena from "@/components/your-space-desktop";
import BattleArena from "@/components/battle-arena-desktop";
import HeaderDesktop from "@/components/header-desktop";
import { AnalyticsData, InsightsData, PlatformTestAnalyticsData } from "@/types/dashboard";

/**
 * Main Landing Dashboard Component
 */
export default function LandingDashboard() {
    const [timeDistSubject, setTimeDistSubject] = useState<string>('All');
    const [selectedPlatformTestId, setSelectedPlatformTestId] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'practice' | 'battle'>('practice');
    const { isAuthenticated, loading, student } = useAuth();

    const [, navigate] = useLocation();

    // === NAVIGATION GUARD ===
    // Redirect to home page when user tries to navigate back from landing dashboard
    useEffect(() => {
        const handlePopState = (e: PopStateEvent) => {
            e.preventDefault();
            navigate('/', { replace: true });
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

    // Fetch platform test analytics data
    const { data: platformTestData } = useQuery<PlatformTestAnalyticsData>({
        queryKey: [API_CONFIG.ENDPOINTS.DASHBOARD_PLATFORM_TEST_ANALYTICS, selectedPlatformTestId],
        queryFn: async () => {
            const endpoint = selectedPlatformTestId
                ? `${API_CONFIG.ENDPOINTS.DASHBOARD_PLATFORM_TEST_ANALYTICS}?test_id=${selectedPlatformTestId}`
                : API_CONFIG.ENDPOINTS.DASHBOARD_PLATFORM_TEST_ANALYTICS;
            const url = `${API_CONFIG.BASE_URL}${endpoint}`;

            const response = await authenticatedFetch(url);

            if (!response.ok) {
                throw new Error('Failed to fetch platform test analytics');
            }

            return response.json();
        },
        enabled: isAuthenticated && !loading,
        refetchInterval: 30000,
    });

    // Local state for selected subject within selected-test view (for time distribution slicer)
    const [selectedTestSubjectFilter, setSelectedTestSubjectFilter] = useState<string>('All');

    if (isLoading || insightsLoading) {
        return <DashboardSkeleton />;
    }

    if (error || !analytics) {
        return <ErrorState />;
    }

    return (
        <div className="flex min-h-screen bg-gray-50">
            <HeaderDesktop />
            <main className="flex-1 flex flex-col bg-gray-50 mt-24 mb-24 transition-all duration-300 md:ml-64">
                <div className="w-full max-w-7xl mx-auto px-4">
                    <div className="md:flex md:items-start md:space-x-6">
                        <div className="flex-1">
                            {/* Your-space Content */}
                            <div>
                                {activeTab === 'practice' && (
                                    <div className="space-y-4">
                                        {/* Insights Container */}
                                        {/* Fallback card if no tests written */}
                                        {(analytics?.totalTests === 0) && (
                                            <Card className="mt-4">
                                                <CardContent className="p-6 text-center">
                                                    <Trophy className="h-10 w-10 text-yellow-500 mx-auto mb-2" />
                                                    <h3 className="text-lg font-semibold mb-2">No Tests Taken Yet</h3>
                                                    <p className="text-gray-600 mb-4">Take your first test to see your performance analytics and unlock insights!</p>
                                                    <Link href="/topics">
                                                        <Button className="bg-blue-600 hover:bg-blue-700 text-white">Take a Test</Button>
                                                    </Link>
                                                </CardContent>
                                            </Card>
                                        )}

                                        {insights && analytics?.totalTests > 0 && (
                                            <PracticeArena
                                                analytics={analytics}
                                                insights={insights}
                                                timeDistSubject={timeDistSubject}
                                                setTimeDistSubject={setTimeDistSubject}
                                            />
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Right sidebar (desktop only) */}
                        <aside className="hidden md:block w-80">
                            <div>
                                <Card className="bg-white rounded-xl border mb-6">
                                    <CardContent className="p-0">
                                        <BattleArena
                                            platformTestData={platformTestData}
                                            selectedPlatformTestId={selectedPlatformTestId}
                                            setSelectedPlatformTestId={setSelectedPlatformTestId}
                                            selectedTestSubjectFilter={selectedTestSubjectFilter}
                                            setSelectedTestSubjectFilter={setSelectedTestSubjectFilter}
                                        />
                                    </CardContent>
                                </Card>
                            </div>
                        </aside>
                    </div>
                </div>
            </main>
        </div>
    );
}




/**
 * Dashboard Loading Skeleton
 */
function DashboardSkeleton() {
    return (
        <div className="flex min-h-screen bg-gray-50">
            <HeaderDesktop />
            <main className="flex-1 flex flex-col bg-gray-50 mt-28 mb-24 transition-all duration-300 md:ml-64">
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
            </main>
        </div>
    );
}

/**
 * Error State Component
 */
function ErrorState() {
    return (
        <div className="flex min-h-screen bg-gray-50">
            <HeaderDesktop />
            <main className="flex-1 flex flex-col bg-gray-50 mt-20 mb-24 transition-all duration-300 md:ml-64">
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
            </main>
        </div>
    );
}