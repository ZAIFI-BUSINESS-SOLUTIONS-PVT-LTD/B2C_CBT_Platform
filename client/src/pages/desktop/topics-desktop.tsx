/** Topics page — chapter/topic selection interface. */

import { useQuery } from "@tanstack/react-query";
import HeaderDesktop from "@/components/header-desktop";
import { AnalyticsData } from '@/types/api';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLocation, Link } from "wouter";
import { useState } from "react";
import QuickTestWizard from "@/components/quick-test-wizard";
import QuestionOfTheDayModal from "@/components/QuestionOfTheDayModal";
import { ChevronRight, Shuffle, ClipboardClock, ClipboardList, Trophy, Sparkles } from "lucide-react";

export default function Topics() {
    const [showQuickTest, setShowQuickTest] = useState(false);
    const [showQOD, setShowQOD] = useState(false);

    const { data: hasData } = useQuery<AnalyticsData, Error, boolean>({
        queryKey: ['/api/dashboard/analytics/'],
        select: (response_data) => response_data?.totalTests > 0,
        retry: false,
    });

    // Fetch comprehensive analytics for sidebar summary
    const { data: analytics } = useQuery<AnalyticsData>({
        queryKey: ['/api/dashboard/comprehensive-analytics/'],
    });

    const sidebarMarginClass = 'md:ml-64';

    return (
        <div className="flex min-h-screen bg-cover bg-center bg-no-repeat" style={{ backgroundImage: "url('/testpage-bg.webp')" }}>
            <HeaderDesktop />
            <main className={`flex-1 flex flex-col bg-transparent mt-20 mb-24 transition-all duration-300 ${sidebarMarginClass}`}>
                <div className="max-w-7xl mx-auto px-4">
                    <div className="md:flex md:items-start md:space-x-4">
                        <div className="flex-1">
                            {/* Hero + Test cards section */}
                            <div className="max-w-7xl mx-auto">
                                {/* Hero */}
                                <div className="mt-4">
                                    <Card className="border rounded-2xl">
                                        <CardContent className="p-6 flex flex-col gap-4">
                                            <div>
                                                <h2 className="text-2xl font-semibold text-gray-900">Create or Take Tests</h2>
                                                <p className="text-sm text-gray-600 mt-1">Choose a quick random test, build a custom test, or view your history and scheduled competitions.</p>
                                            </div>
                                            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
                                                <TestCard
                                                    title="Question of the Day"
                                                    subtitle="Challenge yourself with today's question!"
                                                    icon={<Sparkles className="w-4 h-4 text-blue-800" />}
                                                    onClick={() => setShowQOD(true)}
                                                />

                                                <TestCard
                                                    title="Quick Test"
                                                    subtitle="Pick subjects, chapters & questions to get started"
                                                    icon={<Shuffle className="w-4 h-4 text-blue-800" />}
                                                    onClick={() => setShowQuickTest(true)}
                                                />

                                                <TestCard
                                                    title="Scheduled Tests"
                                                    subtitle="Compete with other NEET aspirants and boost your preparation"
                                                    icon={<ClipboardClock className="w-4 h-4 text-blue-800" />}
                                                    href="/scheduled-tests"
                                                />

                                                <TestCard
                                                    title="Previous Year Questions"
                                                    subtitle="Free practice with past year papers get your confidence up"
                                                    icon={<ClipboardList className="w-4 h-4 text-blue-800" />}
                                                />
                                            </div>
                                        </CardContent>
                                    </Card>
                                </div>
                            </div>

                            {/* Test History Section */}
                            <div className="max-w-7xl mx-auto mt-4">
                                {/* TestHistory moved to Analysis page */}

                                {analytics?.totalTests === 0 && (
                                    <Card className="border rounded-2xl">
                                        <CardContent className="p-4 text-center">
                                            <Trophy className="h-6 w-6 text-yellow-500 mx-auto mb-2" />
                                            <p className="text-sm text-gray-700">No tests yet. Take your first test to unlock insights.</p>
                                            <div className="mt-3">
                                                <Link href="/topics">
                                                    <Button className="bg-blue-600 hover:bg-blue-700 text-white w-full">Take a Test</Button>
                                                </Link>
                                            </div>
                                        </CardContent>
                                    </Card>
                                )}
                            </div>

                            {/* Quick Test Wizard */}
                            {showQuickTest && (
                                <QuickTestWizard onClose={() => setShowQuickTest(false)} />
                            )}

                            {/* Question of the Day Modal */}
                            <QuestionOfTheDayModal isOpen={showQOD} onClose={() => setShowQOD(false)} />
                        </div>

                        {/* Right sidebar (desktop only) */}
                        <aside className="hidden md:block w-80 mt-4">
                            <div className="space-y-4">
                                <Card className="border rounded-2xl">
                                    <CardContent className="p-4">
                                        <h3 className="text-sm font-semibold text-gray-900 mb-2">Performance Summary</h3>
                                        <div className="text-sm text-gray-600 space-y-2">
                                            <div className="flex justify-between">
                                                <span className="text-gray-500">Tests Taken</span>
                                                <span className="font-medium text-gray-800">{analytics?.totalTests ?? '—'}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-gray-500">Average Score</span>
                                                <span className="font-medium text-gray-800">{(analytics as any)?.averageScore ?? '—'}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-gray-500">Best Score</span>
                                                <span className="font-medium text-gray-800">{(analytics as any)?.bestScore ?? '—'}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-gray-500">Last Test</span>
                                                <span className="font-medium text-gray-800">{(analytics as any)?.lastTest?.score ?? '—'}</span>
                                            </div>
                                        </div>
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
 * Test Card Component (copied from home.tsx)
 */
interface TestCardProps {
    title: string;
    subtitle?: string;
    icon?: React.ReactNode;
    href?: string;
    onClick?: () => void;
    className?: string;
}

function TestCard({ title, subtitle, icon, href, onClick }: TestCardProps) {
    const [, navigate] = useLocation();
    const handleClick = () => {
        if (href) navigate(href);
        else if (onClick) onClick();
    };

    return (
        <Card onClick={handleClick} className="rounded-2xl border hover:shadow-lg transform hover:-translate-y-1 transition-all duration-150 cursor-pointer">
            <CardContent className="p-4">
                <div className="flex items-center justify-between space-x-4">
                    <div className="flex items-center space-x-4 pr-2">
                        <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center">
                            {icon}
                        </div>
                        <div className="flex-1">
                            <div className="flex items-center gap-2">
                                <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
                            </div>
                            <div className="text-xs text-gray-500 mt-0.5">{subtitle}</div>
                        </div>
                    </div>

                    <div className="flex items-center pr-2">
                        <Button variant="ghost" size="icon" aria-label={`Open ${title}`} onClick={handleClick}>
                            <ChevronRight className="w-4 h-4 text-gray-500" />
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}