/**
 * Home Page Component
 *
 * This file contains the main dashboard page for the B2C CBT Platform.
 * It displays user insights, analytics, and provides navigation to tes  // Accordion state for collapsible cards
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set(['study-plan']));Features:
 * - User authentication check
 * - Dashboard analytics and insights
 * - Tabbed interface for different insight categories
 * - Mobile-friendly swipe navigation
 * - AI-powered study recommendations
 */

import { Button } from "@/components/ui/button";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, useRef, useCallback } from "react";
import { useAuth } from '@/contexts/AuthContext';
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

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Formats a date string into a human-readable relative time string
 * @param dateString - ISO date string or null
 * @returns Relative time string (e.g., "2 hours ago", "just now")
 */
const formatRelativeTime = (dateString: string | null): string => {
  if (!dateString) return 'just now';

  try {
    const date = new Date(dateString);

    // Check if date is valid
    if (isNaN(date.getTime())) return 'just now';

    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    // Handle future dates (shouldn't happen but just in case)
    if (diffInSeconds < 0) return 'just now';

    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minute${Math.floor(diffInSeconds / 60) === 1 ? '' : 's'} ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hour${Math.floor(diffInSeconds / 3600) === 1 ? '' : 's'} ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} day${Math.floor(diffInSeconds / 86400) === 1 ? '' : 's'} ago`;
    if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 604800)} week${Math.floor(diffInSeconds / 604800) === 1 ? '' : 's'} ago`;
    if (diffInSeconds < 31536000) return `${Math.floor(diffInSeconds / 2592000)} month${Math.floor(diffInSeconds / 2592000) === 1 ? '' : 's'} ago`;
    return `${Math.floor(diffInSeconds / 31536000)} year${Math.floor(diffInSeconds / 31536000) === 1 ? '' : 's'} ago`;
  } catch (error) {
    console.warn('Error parsing date for relative time:', dateString, error);
    return 'just now';
  }
};

/**
 * Test function to verify the formatRelativeTime function works correctly
 * Logs various test cases to the console
 */
const testRelativeTime = () => {
  const now = new Date();
  console.log('Testing formatRelativeTime function:');
  console.log('Just now:', formatRelativeTime(now.toISOString()));
  console.log('5 minutes ago:', formatRelativeTime(new Date(now.getTime() - 5 * 60 * 1000).toISOString()));
  console.log('2 hours ago:', formatRelativeTime(new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString()));
  console.log('1 day ago:', formatRelativeTime(new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString()));
  console.log('Invalid date:', formatRelativeTime('invalid-date'));
  console.log('Null:', formatRelativeTime(null));
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
  // Main card container styles
  container: "p-3 rounded-xl",
  text: "text-sm",

  // Color variants for different insight types
  variants: {
    blue: {
      container: "bg-gray-200",
      text: "text-gray-700",
      accent: "text-blue-600",
      accentBg: "bg-blue-50"
    },
    indigo: {
      container: "bg-gray-200",
      text: "text-gray-700",
      accent: "text-indigo-600",
      accentBg: "bg-indigo-50"
    },
    green: {
      container: "bg-gray-200",
      text: "text-gray-700",
      accent: "text-green-600",
      accentBg: "bg-green-50"
    },
    red: {
      container: "bg-gray-200",
      text: "text-gray-700",
      accent: "text-red-600",
      accentBg: "bg-red-50"
    },
    gray: {
      container: "bg-gray-200",
      text: "text-gray-700",
      accent: "text-gray-600",
      accentBg: "bg-gray-50"
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
    <div className={`${INSIGHT_CARD_STYLES.container} ${styles.container} ${className}`}>
      <div className={`${INSIGHT_CARD_STYLES.text} ${styles.text}`}>
        {children}
      </div>
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
  const { isAuthenticated, loading, student } = useAuth();
  const [, navigate] = useLocation();
  const queryClient = useQueryClient();

  // Check if user is institution student
  const hasInstitution = !!student?.institution;

  // Debug: Log institution status
  useEffect(() => {
    console.log('🏫 Institution check:', { 
      student, 
      hasInstitution,
      institutionData: student?.institution 
    });
  }, [student, hasInstitution]);

  // Tab state for horizontal swipable tabs
  const [activeTab, setActiveTab] = useState(0);

  // Touch/swipe navigation state for mobile
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  const [touchEnd, setTouchEnd] = useState<{ x: number; y: number } | null>(null);
  const [isSwiping, setIsSwiping] = useState(false);

  // Ref for touch container to attach native event listeners
  const touchContainerRef = useRef<HTMLDivElement>(null);

  // Ref for the tab navigation container
  const tabNavRef = useRef<HTMLElement>(null);

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

  // Debug insights data and test relative time function
  useEffect(() => {
    // Test the relative time function
    testRelativeTime();

    if (insights) {
      console.log('Insights data:', insights);
      console.log('Cache info:', insights.cacheInfo);
      if (insights.cacheInfo?.lastModified) {
        console.log('Last modified:', insights.cacheInfo.lastModified);
        console.log('Formatted time:', formatRelativeTime(insights.cacheInfo.lastModified));
      }
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
      <header className="w-full bg-white border-b sticky top-0 z-50">
        <div className="w-full mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <img src={Logo} alt="InzightEd" className="h-6 w-auto" />
              {/* Debug indicator */}
              {hasInstitution && (
                <span className="text-xs bg-red-500 text-white px-2 py-1 rounded">INSTITUTION</span>
              )}
            </div>
            {/* Right side with profile */}
            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate('/payment')}
                className="aspect-square bg-orange-100 rounded-full h-10 w-10"
                aria-label="Go to Payment"
              >
                <Crown className="h-5 w-5 text-amber-600" />
              </Button>
              <StudentProfile />
            </div>
          </div>
        </div>
      </header>

      {/* ============================================================================= */}
      {/* MAIN CONTENT AREA */}
      {/* ============================================================================= */}
      <div className="w-full bg-gray-100 relative">
        {/* Blur overlay for institution students */}
        {hasInstitution && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-white/60 backdrop-blur-sm min-h-screen">
            <div className="bg-white p-8 rounded-2xl shadow-2xl border-2 border-gray-300 max-w-md mx-4">
              <div className="flex flex-col items-center gap-4 text-center">
                <div className="bg-gray-100 p-4 rounded-full">
                  <Lock className="h-16 w-16 text-gray-500" />
                </div>
                <div>
                  <h3 className="font-bold text-xl text-gray-900 mb-2"></h3>
                  <p className="text-base text-gray-600 leading-relaxed">This feature is not available for institution-enrolled students. Please access your institution-specific tests and resources.</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Content wrapper with conditional blur */}
        <div className={hasInstitution ? 'blur-lg pointer-events-none select-none' : ''} aria-hidden={hasInstitution}>

        {/* ============================================================================= */}
        {/* INSIGHTS SECTION - Show tabs always; if no tests, show friendly fallback cards */}
        {/* ============================================================================= */}
        <>
          {/* Tab Headers - Outside the card, below header */}
          <div className="border-b border-gray-200 bg-gray-50">
            <nav ref={tabNavRef} className="flex overflow-x-auto hide-scrollbar px-4" aria-label="Tabs">
              {[
                { id: 0, label: 'Study Plan', icon: NotebookPen, color: 'text-blue-600' },
                { id: 1, label: 'Last Test Recommendations', icon: History, color: 'text-indigo-600' },
                { id: 2, label: 'Strengths', icon: Trophy, color: 'text-green-600' },
                { id: 3, label: 'Weaknesses', icon: AlertTriangle, color: 'text-red-600' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  data-tab-id={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center justify-center gap-2 py-3 px-4 border-b-2 font-medium text-sm transition-colors duration-200 active:bg-gray-50 whitespace-nowrap ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                >
                  <tab.icon className={`h-4 w-4 transition-colors duration-200 ${activeTab === tab.id ? 'text-blue-600' : 'text-gray-500 hover:text-gray-700'}`} />
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content Card */}
          <div className="select-none insights-container relative">
            <div
              ref={touchContainerRef}
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
              className="overflow-hidden"
            >
              {/* Tab Content */}
              <div className="p-4 min-h-[120px]">
                {/* If user has no tests, show a clear fallback CTA card for all tabs */}
                {!hasData ? (
                  <div className="space-y-3">
                    <InsightCard variant={activeTab === 0 ? 'blue' : activeTab === 1 ? 'indigo' : activeTab === 2 ? 'green' : 'red'}>
                      <div className="flex flex-col  justify-center items-center gap-3">
                        <div>

                          <Lock className="h-16 w-16 text-gray-400" />

                        </div>
                        <div className="text-center">
                          <p className="font-semibold">Get personalized insights</p>
                          <p className="text-xs text-gray-600">Take your first practice test to unlock AI study plans, strengths and weaknesses analysis.</p>
                        </div>
                        <div className="flex">
                          <Button
                            variant="default"
                            size="lg"
                            onClick={() => navigate('/topics')}
                            className="w-full rounded-lg font-bold"
                            aria-label="Take a Test"
                          >
                            Take Unlimited Mock Tests
                          </Button>
                        </div>
                      </div>
                    </InsightCard>
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
                                  {firstInsight?.text ?? firstInsight}
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
                                  {firstInsight?.text ?? firstInsight}
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
                                  {firstInsight?.text ?? firstInsight}
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
                                  {firstInsight?.text ?? firstInsight}
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
        <div className="pb-20 bg-white rounded-t-3xl w-full shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1),0_10px_15px_-3px_rgba(0,0,0,0.1),0_4px_6px_-2px_rgba(0,0,0,0.05)]">

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
                className="w-full rounded-xl font-bold"
              >
                Take a Test
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </div>
          <div className="px-4 mt-3 mb-4 ">
            <div>
              <Button
                variant="outline"
                size="lg"
                onClick={() => navigate('/topics')}
                aria-label="View Test History"
                className="w-full rounded-xl border border-blue-500 bg-blue-50 text-blue-600"
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
        {/* End content wrapper */}
      </div>

      {/* ============================================================================= */}
      {/* MOBILE DOCK */}
      {/* ============================================================================= */}
      <MobileDock />
    </div>
  );
}






