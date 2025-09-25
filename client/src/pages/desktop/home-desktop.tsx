import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useLocation } from "wouter";
import HeaderDesktop from "@/components/header-desktop";
import Carousel from '@/components/carousel-desktop';
import MiniChatbot from '@/components/mini-chatbot-desktop';
import MiniDashboard from '@/components/mini-dashboard-desktop';
import { ArrowRight, History, NotebookPen, Trophy, AlertTriangle, Lock, Copy, Share2, Target, BookOpen } from "lucide-react";
import { AnalyticsData, InsightsData } from "@/components/insight-card";

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

/**
 * Share Component
 *
 * A comprehensive sharing component for the CBT platform
 * Allows users to share achievements, test results, and app content
 */
interface ShareProps {
    title?: string;
    description?: string;
    url?: string;
    type?: 'achievement' | 'result' | 'progress' | 'app';
    score?: number;
    subject?: string;
    className?: string;
}

const Share: React.FC<ShareProps> = ({
    title = "Check out my NEET preparation progress!",
    description = "I'm preparing for NEET 2026 with InzightEd. Join me on this journey!",
    url = window.location.origin,
    type = 'app',
    score,
    subject,
    className = ""
}) => {
    const [copied, setCopied] = useState(false);

    // Generate share content based on type
    const getShareContent = () => {
        switch (type) {
            case 'achievement':
                return {
                    title: `🏆 Achievement Unlocked! ${score ? `Scored ${score}%` : ''}`,
                    description: `I just achieved a milestone in my NEET preparation! ${subject ? `in ${subject}` : ''}`,
                    emoji: '🏆'
                };
            case 'result':
                return {
                    title: `📊 Test Result: ${score ? `${score}%` : 'Completed'}`,
                    description: `Just completed a ${subject || 'practice'} test. ${score ? `Scored ${score}%!` : 'Keep practicing!'} `,
                    emoji: '📊'
                };
            case 'progress':
                return {
                    title: `📈 Study Progress Update`,
                    description: `Making great progress in my NEET preparation journey! ${score ? `${score}% complete` : ''}`,
                    emoji: '📈'
                };
            default:
                return {
                    title,
                    description,
                    emoji: '🎯'
                };
        }
    };

    const shareContent = getShareContent();
    const shareText = `${shareContent.emoji} ${shareContent.title}\n\n${shareContent.description}\n\n${url}`;

    // Copy to clipboard
    const copyToClipboard = async () => {
        try {
            await navigator.clipboard.writeText(shareText);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    // Native Web Share API (if supported)
    const shareNative = async () => {
        if ('share' in navigator) {
            try {
                await navigator.share({
                    title: shareContent.title,
                    text: shareContent.description,
                    url: url,
                });
            } catch (err) {
                console.log('Error sharing:', err);
            }
        }
    };

    const shareOptions = [
        {
            name: 'Copy Link',
            icon: Copy,
            action: copyToClipboard,
            color: 'bg-gray-100 border-gray-200 text-gray-700 hover:bg-gray-200',
            available: true
        }
    ];

    return (
        <div className={`h-full ${className}`}>
            <Card className="bg-white border shadow-lg">
                <CardHeader className='py-4 px-6'>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div>
                                <CardTitle className="text-xl font-semibold text-gray-800">
                                    Study with your friends
                                </CardTitle>
                                <p className="text-base text-gray-600">Share with your friends and prepare with them together</p>
                            </div>
                        </div>
                        {type !== 'app' && (
                            <Badge variant="secondary" className="bg-gray-100 text-gray-700 border-gray-200">
                                {type === 'achievement' && <Trophy className="w-4 h-4 mr-1" />}
                                {type === 'result' && <Target className="w-4 h-4 mr-1" />}
                                {type === 'progress' && <BookOpen className="w-4 h-4 mr-1" />}
                                {type.charAt(0).toUpperCase() + type.slice(1)}
                            </Badge>
                        )}
                    </div>
                </CardHeader>

                <CardContent className="px-6 pb-6">
                    {/* Share Buttons */}
                    <div className="space-y-3">
                        {shareOptions.map((option) => (
                            <Button
                                key={option.name}
                                variant="outline"
                                size="lg"
                                onClick={option.action}
                                className={`${option.color} font-medium w-full`}
                            >
                                <option.icon className="w-5 h-5 mr-2" />
                                {option.name}
                            </Button>
                        ))}

                        {/* Native Share Button for supported devices */}
                        {'share' in navigator && (
                            <Button
                                variant="default"
                                size="lg"
                                onClick={shareNative}
                                className="w-full bg-black text-white hover:bg-gray-800 font-medium"
                            >
                                <Share2 className="w-5 h-5 mr-2" />
                                Share with friends
                            </Button>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

/**
 * NEET Exam Countdown Component
 *
 * A black glassmorphic countdown card with modern dark design
 */
const NeetCountdown: React.FC = () => {
    // Calculate days remaining until NEET exam (May 3, 2026)
    const calculateDaysLeft = (): number => {
        const neetDate = new Date('2026-05-03');
        const today = new Date();
        const timeDiff = neetDate.getTime() - today.getTime();
        const daysLeft = Math.ceil(timeDiff / (1000 * 3600 * 24));
        return Math.max(0, daysLeft);
    };

    const daysLeft = calculateDaysLeft();

    return (
        <div>
            <Card className="bg-black/70 backdrop-blur-xl shadow-2xl">
                <CardHeader className='py-3 px-6'>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div>
                                <CardTitle className="text-xl font-semibold text-white">
                                    NEET 2026
                                </CardTitle>
                                <p className="text-base text-gray-300">Exam date: May 3, 2026</p>
                            </div>
                        </div>
                        <Badge variant="secondary" className="bg-white/10 text-blue-500 border-blue-500 backdrop-blur-sm pt-1">
                            {daysLeft === 1 ? '1 Day Left' : `${daysLeft} Days Left`}
                        </Badge>
                    </div>
                </CardHeader>
            </Card>
        </div>
    );
};

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
    const queryClient = useQueryClient();

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

    // Precompute insight sections (useMemo must be called unconditionally)
    const insightSections = useMemo(() => {
        const sections: any[] = [];

        // Study Plan
        if (insights?.data?.llmInsights?.studyPlan?.insights && insights.data.llmInsights.studyPlan.insights.length > 0) {
            sections.push({ title: 'Study Plan', items: insights.data.llmInsights.studyPlan.insights.map((s: any) => s?.text ?? s), icon: <NotebookPen className="w-4 h-4" />, subtitle: 'Personalized study plan' });
        } else if (insights?.data?.improvementTopics && insights.data.improvementTopics.length > 0) {
            sections.push({ title: 'Study Plan', items: insights.data.improvementTopics.slice(0, 5).map((t: any) => `${t.topic} — ${t.accuracy}%`), icon: <NotebookPen className="w-4 h-4" />, subtitle: 'Recommended focus areas' });
        } else {
            sections.push({ title: 'Study Plan', items: ['Take tests to get AI-generated study plans!'], icon: <NotebookPen className="w-4 h-4" /> });
        }

        // Last Test
        if (insights?.data?.llmInsights?.lastTestFeedback?.insights && insights.data.llmInsights.lastTestFeedback.insights.length > 0) {
            sections.push({ title: 'Last Test Recommendations', items: insights.data.llmInsights.lastTestFeedback.insights.map((s: any) => s?.text ?? s), icon: <History className="w-4 h-4" />, subtitle: 'AI feedback on your last test' });
        } else if (insights?.data?.lastTestTopics && insights.data.lastTestTopics.length > 0) {
            sections.push({ title: 'Last Test Recommendations', items: insights.data.lastTestTopics.slice(0, 5).map((t: any) => `${t.topic} — ${t.accuracy}%`), icon: <History className="w-4 h-4" /> });
        } else {
            sections.push({ title: 'Last Test Recommendations', items: ['Complete a test to get AI feedback!'], icon: <History className="w-4 h-4" /> });
        }

        // Strengths
        if (insights?.data?.llmInsights?.strengths?.insights && insights.data.llmInsights.strengths.insights.length > 0) {
            sections.push({ title: 'Strengths', items: insights.data.llmInsights.strengths.insights.map((s: any) => s?.text ?? s), icon: <Trophy className="w-4 h-4" /> });
        } else if (insights?.data?.strengthTopics && insights.data.strengthTopics.length > 0) {
            sections.push({ title: 'Strengths', items: insights.data.strengthTopics.slice(0, 5).map((t: any) => `${t.topic} — ${t.accuracy}%`), icon: <Trophy className="w-4 h-4" /> });
        } else {
            sections.push({ title: 'Strengths', items: ['Take tests to get AI analysis of your strengths!'], icon: <Trophy className="w-4 h-4" /> });
        }

        // Weaknesses
        if (insights?.data?.llmInsights?.weaknesses?.insights && insights.data.llmInsights.weaknesses.insights.length > 0) {
            sections.push({ title: 'Weaknesses', items: insights.data.llmInsights.weaknesses.insights.map((s: any) => s?.text ?? s), icon: <AlertTriangle className="w-4 h-4" /> });
        } else if (insights?.data?.weakTopics && insights.data.weakTopics.length > 0) {
            sections.push({ title: 'Weaknesses', items: insights.data.weakTopics.slice(0, 5).map((t: any) => `${t.topic} — ${t.accuracy}%`), icon: <AlertTriangle className="w-4 h-4" /> });
        } else {
            sections.push({ title: 'Weaknesses', items: ['Take tests to get AI analysis of your weaknesses!'], icon: <AlertTriangle className="w-4 h-4" /> });
        }

        return sections;
    }, [insights, analytics]);

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

    const sidebarMarginClass = 'md:ml-64';

    return (
        <div className={`flex min-h-screen bg-gray-50 text-text`}>
            <HeaderDesktop />
            <main className={`flex-1 flex flex-col bg-gray-50 mt-28 mb-24 transition-all duration-300 ${sidebarMarginClass}`}>

                {/* ============================================================================= */}
                {/* MAIN CONTENT AREA */}
                {/* ============================================================================= */}
                <div className="w-full max-w-7xl mx-auto">
                    {/* 2x2 Grid: Insights | MiniDashboard */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 px-4 pt-4 items-stretch">
                        {/* 1. Insights */}
                        <div className="h-full">
                            <div className="h-full flex flex-col">
                                {!hasData ? (
                                    <InsightCard variant="blue" className="h-full flex items-center">
                                        <div className="w-full p-6 flex flex-col items-center justify-center gap-4 max-w-xl mx-auto text-center">
                                            <div className="flex items-center justify-center">
                                                <Lock className="h-12 w-12 text-gray-400" />
                                            </div>
                                            <h3 className="text-lg font-semibold">Get personalized insights</h3>
                                            <p className="text-sm text-gray-600">Take your first practice test to unlock AI study plans, strengths and weaknesses analysis.</p>
                                            <div className="w-full mt-3 flex justify-center">
                                                <Button
                                                    variant="default"
                                                    size="lg"
                                                    onClick={() => navigate('/topics')}
                                                    className="rounded-lg font-bold px-6"
                                                >
                                                    Take a Test
                                                </Button>
                                            </div>
                                        </div>
                                    </InsightCard>
                                ) : (
                                    <div className="h-full flex-1 flex">
                                        <div className="flex-1">
                                            <Carousel sections={insightSections} height={'100%'} />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* 2. Mini Dashboard and Action Buttons */}
                        <div className="h-full">
                            <MiniDashboard analytics={analytics} />
                        </div>

                        {/* 3. Chatbot */}
                        <div className="min-h-0 h-full">
                            <MiniChatbot className="max-w-full h-full" />
                        </div>




                        {/* 4. More from InzightEd */}
                        <div>
                            <div className="pb-4">
                                <Share type="app" />
                            </div>
                            <div>
                                <NeetCountdown />
                            </div>

                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}