import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useLocation } from "wouter";
import { StudentProfile } from "@/components/profile-avatar";
import Logo from "@/assets/images/logo.svg";
import MiniChatbot from '@/components/mini-chatbot';
import MiniDashboard from '@/components/mini-dashboard';
import { ArrowRight, History, NotebookPen, Trophy, AlertTriangle, Crown, Lock } from "lucide-react";
import MobileDock from "@/components/mobile-dock";
import { AnalyticsData, InsightsData } from "@/components/insight-card";
import NeetCountdown from '@/components/coundown';
import Share from '@/components/share';

// Utility: format a timestamp into a short relative time string
const formatRelativeTime = (dateString: string | null): string => {
  if (!dateString) return 'just now';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return 'just now';

  const now = Date.now();
  const diffInSeconds = Math.floor((now - date.getTime()) / 1000);
  if (diffInSeconds < 60) return 'just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minute${Math.floor(diffInSeconds / 60) === 1 ? '' : 's'} ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hour${Math.floor(diffInSeconds / 3600) === 1 ? '' : 's'} ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} day${Math.floor(diffInSeconds / 86400) === 1 ? '' : 's'} ago`;
  if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 604800)} week${Math.floor(diffInSeconds / 604800) === 1 ? '' : 's'} ago`;
  if (diffInSeconds < 31536000) return `${Math.floor(diffInSeconds / 2592000)} month${Math.floor(diffInSeconds / 2592000) === 1 ? '' : 's'} ago`;
  return `${Math.floor(diffInSeconds / 31536000)} year${Math.floor(diffInSeconds / 31536000) === 1 ? '' : 's'} ago`;
};

// =============================================================================
// STYLING CONFIGURATIONS
// =============================================================================

// Centralized insight card styling configuration
// To change all insight cards at once, modify the styles below:
// - container: Main card container styles (padding, border, etc.)
// - text: Base text styling
// - variants: Color schemes for different card types
const INSIGHT_CARD_STYLES = {
  // Main card container styles with subtle depth and layered background
  container: "p-4 rounded-2xl shadow-sm ring-1 ring-black/5 bg-gradient-to-tr from-white/80 via-gray-50 to-white",
  text: "text-sm leading-relaxed",

  // Color variants for different insight types with accent border and soft gradient
  variants: {
    blue: {
      container: "bg-gradient-to-br from-blue-50/60 via-white to-white border-l-4 border-blue-300",
      text: "text-slate-800",
      accent: "text-blue-600",
      accentBg: "bg-blue-50/40"
    },
    indigo: {
      container: "bg-gradient-to-br from-indigo-50/60 via-white to-white border-l-4 border-indigo-300",
      text: "text-slate-800",
      accent: "text-indigo-600",
      accentBg: "bg-indigo-50/40"
    },
    green: {
      container: "bg-gradient-to-br from-green-50/60 via-white to-white border-l-4 border-green-300",
      text: "text-slate-800",
      accent: "text-green-600",
      accentBg: "bg-green-50/40"
    },
    red: {
      container: "bg-gradient-to-br from-rose-50/60 via-white to-white border-l-4 border-rose-300",
      text: "text-slate-800",
      accent: "text-rose-600",
      accentBg: "bg-rose-50/40"
    },
    gray: {
      container: "bg-gradient-to-br from-gray-50/80 via-white to-white border-l-4 border-gray-200",
      text: "text-slate-800",
      accent: "text-gray-600",
      accentBg: "bg-gray-50/40"
    }
  }
};

// =============================================================================
// REUSABLE COMPONENTS
// =============================================================================

/**
 * Reusable InsightCard component for displaying insights with consistent styling
 */
interface InsightCardProps {
  children: React.ReactNode;
  variant: keyof typeof INSIGHT_CARD_STYLES.variants;
  className?: string;
}

const InsightCard: React.FC<InsightCardProps> = ({ children, variant, className = "" }) => {
  const styles = INSIGHT_CARD_STYLES.variants[variant];
  return (
    <div className={`${INSIGHT_CARD_STYLES.container} ${styles.container} ${className} transition-shadow duration-200 hover:shadow-md`}>
      <div className={`${INSIGHT_CARD_STYLES.text} ${styles.text}`}>{children}</div>
    </div>
  );
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

/**
 * Home page component that renders the dashboard-focused landing page
 * @returns JSX element containing the main dashboard interface
 */
export default function Home() {
  // =============================================================================
  // HOOKS AND STATE MANAGEMENT
  // =============================================================================

  // Authentication and navigation hooks
  const { isAuthenticated, loading } = useAuth();
  const [, navigate] = useLocation();

  // Tab state for horizontal swipable tabs
  const [activeTab, setActiveTab] = useState(0);

  // Touch/swipe navigation state for mobile
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  const [touchEnd, setTouchEnd] = useState<{ x: number; y: number } | null>(null);

  // Ref for touch container to attach native event listeners
  const touchContainerRef = useRef<HTMLDivElement>(null);

  // Ref for the tab navigation container
  const tabNavRef = useRef<HTMLElement>(null);

  const tabs = useMemo(() => [
    { id: 0, label: 'Study Plan', icon: NotebookPen, color: 'text-blue-600' },
    { id: 1, label: 'Last Test Recommendations', icon: History, color: 'text-indigo-600' },
    { id: 2, label: 'Strengths', icon: Trophy, color: 'text-green-600' },
    { id: 3, label: 'Weaknesses', icon: AlertTriangle, color: 'text-red-600' }
  ], []);

  // =============================================================================
  // UTILITY FUNCTIONS
  // =============================================================================

  // Tab navigation functions
  const nextTab = useCallback(() => {
    setActiveTab(prev => (prev + 1) % 4);
  }, []);

  const prevTab = useCallback(() => {
    setActiveTab(prev => (prev - 1 + 4) % 4);
  }, []);

  // Touch event handlers for swipe navigation
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart({
      x: e.targetTouches[0].clientX,
      y: e.targetTouches[0].clientY
    });
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    setTouchEnd({
      x: e.targetTouches[0].clientX,
      y: e.targetTouches[0].clientY
    });
  }, []);

  const handleTouchEnd = useCallback(() => {
    if (!touchStart || !touchEnd) return;

    const distanceX = touchStart.x - touchEnd.x;
    const distanceY = touchStart.y - touchEnd.y;
    const isLeftSwipe = distanceX > 50;
    const isRightSwipe = distanceX < -50;
    const isVerticalSwipe = Math.abs(distanceY) > Math.abs(distanceX);

    // Only handle horizontal swipes
    if (!isVerticalSwipe) {
      if (isLeftSwipe) {
        nextTab();
      } else if (isRightSwipe) {
        prevTab();
      }
    }
  }, [touchStart, touchEnd, nextTab, prevTab]);

  // =============================================================================
  // DATA FETCHING
  // =============================================================================

  // Dashboard and analytics queries (only when authenticated)
  const { data: analytics } = useQuery<AnalyticsData>({
    queryKey: ['/api/dashboard/comprehensive-analytics/'],
    // match landing-dashboard behavior: refresh periodically and only run when auth state settled
    refetchInterval: 30000,
    enabled: isAuthenticated && !loading, // Only run when authenticated and auth finished loading
  });

  const { data: insights } = useQuery<InsightsData>({
    queryKey: ['/api/insights/student/'],
    refetchInterval: 30000,
    enabled: isAuthenticated && !loading,
  });

  // =============================================================================
  // SIDE EFFECTS
  // =============================================================================

  // Scroll active tab into view when tab changes
  useEffect(() => {
    if (tabNavRef.current) {
      const activeTabButton = tabNavRef.current.querySelector(`[data-tab-id="${activeTab}"]`) as HTMLElement;
      if (activeTabButton) {
        activeTabButton.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'center'
        });
      }
    }
  }, [activeTab]);

  // Dev-only logs for insights
  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return;
    if (!insights) return;
    // eslint-disable-next-line no-console
    console.debug('Insights data:', insights);
    // eslint-disable-next-line no-console
    console.debug('Cache info:', insights.cacheInfo);
    if (insights.cacheInfo?.lastModified) {
      // eslint-disable-next-line no-console
      console.debug('Last modified:', insights.cacheInfo.lastModified);
      // eslint-disable-next-line no-console
      console.debug('Formatted time:', formatRelativeTime(insights.cacheInfo.lastModified));
    }
  }, [insights]);

  // =============================================================================
  // EARLY RETURNS AND COMPUTED VALUES
  // =============================================================================

  // Show login form if not authenticated
  // Redirect to login page if not authenticated
  if (!isAuthenticated) {
    // While auth is loading, keep the placeholder minimal
    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-indigo-50">
          <div className="text-center text-sm text-gray-600">Checking authentication...</div>
        </div>
      );
    }

    // Navigate to login for unauthenticated users
    navigate('/login');
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-indigo-50">
        <div className="text-center text-sm text-gray-600">Redirecting to login...</div>
      </div>
    );
  }

  // Check if user has previous test data
  const hasData = analytics && analytics.totalTests > 0;

  // =============================================================================
  // MAIN RENDER
  // =============================================================================

  return (
    <div className="min-h-screen bg-white">
      {/* ============================================================================= */}
      {/* INLINE STYLES - MOVED TO index.css FOR BETTER ORGANIZATION */}
      {/* Styles for hide-scrollbar, tab-content, insights-container, and tab-content-container */}
      {/* are now located in client/src/index.css under HOME PAGE COMPONENT STYLES */}
      {/* ============================================================================= */}

      {/* ============================================================================= */}
      {/* HEADER SECTION */}
      {/* ============================================================================= */}
      <header className="w-full bg-white/80 backdrop-blur sticky top-0 z-50 border-b border-gray-100">
        <div className="w-full mx-auto px-4 py-3 max-w-5xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center gap-3">
                <img src={Logo} alt="InzightEd" className="h-8 w-auto" />
                <div className="hidden sm:block">
                  <h2 className="text-lg font-semibold text-slate-900">InzightEd</h2>
                  <p className="text-xs text-slate-500 -mt-0.5">Personalized learning, accelerated</p>
                </div>
              </div>
            </div>
            {/* Right side with profile */}
            <div className="flex items-center space-x-3">
              <Button
                variant="default"
                size="sm"
                onClick={() => navigate('/payment')}
                className="bg-amber-100 text-amber-800 hover:bg-amber-200 shadow-sm rounded-full px-3 py-2 border border-amber-200"
                aria-label="Go to Payment"
              >
                <Crown className="h-4 w-4 mr-2 text-amber-600" />
                Upgrade
              </Button>
              <StudentProfile />
            </div>
          </div>
        </div>
      </header>

      {/* ============================================================================= */}
      {/* MAIN CONTENT AREA */}
      {/* ============================================================================= */}
      <div className="w-full bg-gray-100">

        {/* ============================================================================= */}
        {/* INSIGHTS SECTION - Show tabs always; if no tests, show friendly fallback cards */}
        {/* ============================================================================= */}
        <>
          {/* Tab Headers - Outside the card, below header */}
          <div className="border-b border-gray-100 bg-gradient-to-b from-white/60 to-white/40">
            <nav ref={tabNavRef} className="flex gap-3 overflow-x-auto hide-scrollbar px-4 py-3 items-center" aria-label="Tabs">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  data-tab-id={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 py-2 px-3 text-sm font-medium rounded-full transition-all duration-200 focus:outline-none whitespace-nowrap ${activeTab === tab.id
                    ? 'bg-gradient-to-r from-blue-50 to-blue-100 text-blue-700 shadow-sm ring-1 ring-blue-100 scale-100'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-800'
                    }`}
                >
                  <tab.icon className={`h-4 w-4 transition-colors duration-200 ${activeTab === tab.id ? 'text-blue-600' : 'text-slate-400'}`} />
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content Card */}
          <div className="select-none insights-container relative max-w-5xl mx-auto px-4">
            <div
              ref={touchContainerRef}
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
              className="overflow-hidden"
            >
              {/* Tab Content */}
              <div className="px-1 py-2 min-h-[120px]">
                {/* If user has no tests, show a clear fallback CTA card for all tabs */}
                {!hasData ? (
                  <div className="space-y-4">
                    <InsightCard variant={activeTab === 0 ? 'blue' : activeTab === 1 ? 'indigo' : activeTab === 2 ? 'green' : 'red'}>
                      <div className="flex flex-col justify-center items-center gap-3">
                        <div className="p-4 rounded-full bg-white/60 shadow-inner">
                          <Lock className="h-16 w-16 text-slate-400" />
                        </div>
                        <div className="text-center">
                          <p className="font-semibold text-slate-900 text-lg">Get personalized insights</p>
                          <p className="text-xs text-slate-500">Take your first practice test to unlock AI study plans, strengths and weaknesses analysis.</p>
                        </div>
                        <div className="flex w-full">
                          <Button
                            variant="default"
                            size="lg"
                            onClick={() => navigate('/topics')}
                            className="w-full rounded-xl font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-md"
                            aria-label="Take a Test"
                          >
                            Take Unlimited Mock Tests
                          </Button>
                        </div>
                      </div>
                    </InsightCard>

                    {/* Mini card grid to make the insights section feel populated */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <InsightCard variant="gray" className="p-3">
                        <div>
                          <p className="font-medium text-slate-900">What you'll get</p>
                          <ul className="mt-2 text-xs text-slate-600 space-y-1">
                            <li>• AI study plan tailored to your performance</li>
                            <li>• Topic-wise strengths & weaknesses</li>
                            <li>• Short, actionable practice recommendations</li>
                          </ul>
                        </div>
                      </InsightCard>

                      <InsightCard variant="indigo" className="p-3">
                        <div>
                          <p className="font-medium text-slate-900">Sample recommended topics</p>
                          <ul className="mt-2 text-xs text-indigo-700 space-y-1">
                            <li className="flex justify-between"><span>Algebra Basics</span><span className="text-indigo-600">72%</span></li>
                            <li className="flex justify-between"><span>Geometry</span><span className="text-indigo-600">65%</span></li>
                            <li className="flex justify-between"><span>Physics: Motion</span><span className="text-indigo-600">58%</span></li>
                          </ul>
                        </div>
                      </InsightCard>

                      <InsightCard variant="blue" className="p-3">
                        <div>
                          <p className="font-medium text-slate-900">Weekly goal</p>
                          <div className="mt-2">
                            <div className="w-full bg-slate-100 rounded-full h-2">
                              <div className="h-2 rounded-full bg-blue-600" style={{ width: '28%' }} />
                            </div>
                            <p className="text-xs text-slate-500 mt-2">Complete 2 tests this week to unlock insights</p>
                          </div>
                        </div>
                      </InsightCard>
                    </div>

                    <div className="mt-2 text-xs text-slate-500 text-center">
                      Or try a <button onClick={() => navigate('/topics')} className="text-blue-600 underline font-medium">quick demo test</button> to populate your dashboard.
                    </div>
                  </div>
                ) : (
                  // Existing content when user has data
                  <>
                    {/* Study Plan Tab */}
                    {activeTab === 0 && (
                      <div className="space-y-3">
                        {insights?.data?.llmInsights?.studyPlan?.insights ? (
                          <div className="space-y-3">
                            {insights.data.llmInsights.studyPlan.insights.length > 0 && (() => {
                              const firstInsight = insights.data.llmInsights.studyPlan.insights[0] as any;
                              return (
                                <InsightCard key={firstInsight?.id ?? firstInsight} variant="blue">
                                  <div className="flex items-start gap-3">
                                    <div className="flex-shrink-0 mt-0.5">
                                      <div className="h-8 w-8 rounded-full bg-blue-50 flex items-center justify-center">
                                        <NotebookPen className="h-4 w-4 text-blue-600" />
                                      </div>
                                    </div>
                                    <div className="text-slate-800">{firstInsight?.text ?? firstInsight}</div>
                                  </div>
                                </InsightCard>
                              );
                            })()}
                          </div>
                        ) : insights?.data?.improvementTopics && insights.data.improvementTopics.length > 0 ? (
                          <div>
                            <p className="text-xs text-blue-700 mb-2">Recommended focus areas:</p>
                            <ul className="space-y-1 text-xs">
                              {insights.data.improvementTopics.slice(0, 3).map((topic: any, idx: number) => (
                                <li key={idx} className="flex justify-between">
                                  <span>{topic.topic}</span>
                                  <span className="text-blue-600">{topic.accuracy}%</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : insights?.data?.weakTopics && insights.data.weakTopics.length > 0 ? (
                          <div>
                            <p className="text-xs text-blue-700 mb-2">Focus on improving these areas:</p>
                            <ul className="space-y-1 text-xs">
                              {insights.data.weakTopics.slice(0, 2).map((topic: any, idx: number) => (
                                <li key={idx} className="flex justify-between">
                                  <span>{topic.topic}</span>
                                  <span className="text-red-600">{topic.accuracy}%</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            <InsightCard variant="blue">
                              Take some tests to get AI-generated study plans!
                            </InsightCard>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Last Test Tab */}
                    {activeTab === 1 && (
                      <div className="space-y-2">
                        {insights?.data?.llmInsights?.lastTestFeedback?.insights ? (
                          <div className="space-y-2">
                            {insights.data.llmInsights.lastTestFeedback.insights.length > 0 && (() => {
                              const firstInsight = insights.data.llmInsights.lastTestFeedback.insights[0] as any;
                              return (
                                <InsightCard key={firstInsight?.id ?? firstInsight} variant="indigo">
                                  <div className="flex items-start gap-3">
                                    <div className="flex-shrink-0 mt-0.5">
                                      <div className="h-8 w-8 rounded-full bg-indigo-50 flex items-center justify-center">
                                        <History className="h-4 w-4 text-indigo-600" />
                                      </div>
                                    </div>
                                    <div className="text-slate-800">{firstInsight?.text ?? firstInsight}</div>
                                  </div>
                                </InsightCard>
                              );
                            })()}
                          </div>
                        ) : insights?.data?.lastTestTopics && insights.data.lastTestTopics.length > 0 ? (
                          <div>
                            <p className="text-xs text-indigo-700 mb-2">Recent test performance:</p>
                            <ul className="space-y-1 text-xs">
                              {insights.data.lastTestTopics.slice(0, 3).map((topic: any, idx: number) => (
                                <li key={idx} className="flex justify-between">
                                  <span>{topic.topic}</span>
                                  <span className="text-indigo-600">{topic.accuracy}%</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            <InsightCard variant="indigo">
                              Complete a test to get AI feedback on your performance!
                            </InsightCard>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Strengths Tab */}
                    {activeTab === 2 && (
                      <div className="space-y-2">
                        {(!analytics || analytics.totalTests === 0) ? (
                          <div className="space-y-2">
                            <InsightCard variant="gray">
                              Complete practice tests to unlock your strengths!
                            </InsightCard>
                          </div>
                        ) : insights?.data?.llmInsights?.strengths?.insights ? (
                          <div className="space-y-2">
                            {insights.data.llmInsights.strengths.insights.length > 0 && (() => {
                              const firstInsight = insights.data.llmInsights.strengths.insights[0] as any;
                              return (
                                <InsightCard key={firstInsight?.id ?? firstInsight} variant="green">
                                  <div className="flex items-start gap-3">
                                    <div className="flex-shrink-0 mt-0.5">
                                      <div className="h-8 w-8 rounded-full bg-green-50 flex items-center justify-center">
                                        <Trophy className="h-4 w-4 text-green-600" />
                                      </div>
                                    </div>
                                    <div className="text-slate-800">{firstInsight?.text ?? firstInsight}</div>
                                  </div>
                                </InsightCard>
                              );
                            })()}
                          </div>
                        ) : insights?.data?.strengthTopics && insights.data.strengthTopics.length > 0 ? (
                          <div>
                            <p className="text-xs text-green-700 mb-2">Your top performing topics:</p>
                            <ul className="space-y-1 text-xs">
                              {insights.data.strengthTopics.slice(0, 3).map((topic: any, idx: number) => (
                                <li key={idx} className="flex justify-between">
                                  <span>{topic.topic}</span>
                                  <span className="text-green-600">{topic.accuracy}%</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            <InsightCard variant="green">
                              Take some tests to get AI analysis of your strengths!
                            </InsightCard>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Weaknesses Tab */}
                    {activeTab === 3 && (
                      <div className="space-y-2">
                        {insights?.data?.llmInsights?.weaknesses?.insights ? (
                          <div className="space-y-2">
                            {insights.data.llmInsights.weaknesses.insights.length > 0 && (() => {
                              const firstInsight = insights.data.llmInsights.weaknesses.insights[0] as any;
                              return (
                                <InsightCard key={firstInsight?.id ?? firstInsight} variant="red">
                                  <div className="flex items-start gap-3">
                                    <div className="flex-shrink-0 mt-0.5">
                                      <div className="h-8 w-8 rounded-full bg-rose-50 flex items-center justify-center">
                                        <AlertTriangle className="h-4 w-4 text-rose-600" />
                                      </div>
                                    </div>
                                    <div className="text-slate-800">{firstInsight?.text ?? firstInsight}</div>
                                  </div>
                                </InsightCard>
                              );
                            })()}
                          </div>
                        ) : insights?.data?.weakTopics && insights.data.weakTopics.length > 0 ? (
                          <div>
                            <p className="text-xs text-red-700 mb-2">Topics needing focus:</p>
                            <ul className="space-y-1 text-xs">
                              {insights.data.weakTopics.slice(0, 3).map((topic: any, idx: number) => (
                                <li key={idx} className="flex justify-between">
                                  <span>{topic.topic}</span>
                                  <span className="text-red-600">{topic.accuracy}%</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            <InsightCard variant="red">
                              Take some tests to get AI analysis of your weaknesses!
                            </InsightCard>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </>


        {/* ============================================================================= */}
        {/* BODY CONTAINER - Main content area below insights */}
        {/* ============================================================================= */}
        <div className="pb-20 bg-white rounded-2xl max-w-5xl mx-auto mt-6 shadow-lg border border-gray-100">

          {/* ============================================================================= */}
          {/* AI TUTOR CHAT SECTION */}
          {/* ============================================================================= */}
          <div className="px-4 py-4">
            <MiniChatbot className="max-w-full" />
          </div>
          {/* ============================================================================= */}
          {/* MINI DASHBOARD SECTION */}
          {/* ============================================================================= */}
          <div className="px-4 pb-4 pt-4">
            <MiniDashboard analytics={analytics} />
          </div>
          {/* ============================================================================= */}
          {/* TEST SECTION */}
          {/* ============================================================================= */}
          <div className="px-4">
            <div>
              <Button
                variant="default"
                size="lg"
                onClick={() => navigate('/topics')}
                aria-label="View Test ArrowRight"
                className="w-full rounded-xl font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg hover:from-blue-700 hover:to-indigo-700"
              >
                Take a Test
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </div>
          <div className="px-4 mt-3 mb-4 ">
            <div>
              <Button
                variant="default"
                size="lg"
                onClick={() => navigate('/topics')}
                aria-label="View Test History"
                className="w-full rounded-xl font-medium bg-white border border-blue-100 text-blue-600 hover:bg-blue-50 shadow-sm"
              >
                View Test History
                <History className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </div>



          <div className="px-4 pb-4 pt-8">
            <h1 className="text-xl font-bold mb-4">More from InzightEd</h1>
            <NeetCountdown />
          </div>

          {/* ============================================================================= */}
          {/* SHARE SECTION */}
          {/* ============================================================================= */}
          <Share type="app" />

        </div>
      </div>

      {/* ============================================================================= */}
      {/* MOBILE DOCK */}
      {/* ============================================================================= */}
      <MobileDock />
    </div>
  );
}






