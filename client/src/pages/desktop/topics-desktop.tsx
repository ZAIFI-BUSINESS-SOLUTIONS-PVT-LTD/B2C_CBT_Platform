/** Topics page — chapter/topic selection interface. */

import { ChapterSelection } from "@/components/chapter-selection";
import { useQuery } from "@tanstack/react-query";
import MobileDock from "@/components/mobile-dock";
import HeaderDesktop from "@/components/header-desktop";
import { AnalyticsData } from '@/types/api';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLocation, Link } from "wouter";
import { useState } from "react";
import RandomTest from "@/components/random-test";
import TestHistory from "@/components/test-history";
import { ChevronRight, Shuffle, SlidersHorizontal, ClipboardClock, ClipboardList, ChevronLeft, Trophy } from "lucide-react";

export default function Topics() {
    const [showRandomModal, setShowRandomModal] = useState(false);
    const [showChapterModal, setShowChapterModal] = useState(false);
    const { data: hasData } = useQuery<AnalyticsData, Error, boolean>({
        queryKey: ['/api/dashboard/analytics/'],
        select: (response_data) => response_data?.totalTests > 0,
        retry: false,
    });

    // Fetch comprehensive analytics for sidebar summary
    const { data: analytics } = useQuery<AnalyticsData>({
        queryKey: ['/api/dashboard/comprehensive-analytics/'],
        // Only needed for display; keep defaults
    });

    return (
        <div className="flex min-h-screen bg-gray-50">
            <HeaderDesktop />

            <main className="flex-1 flex flex-col bg-gray-50 mt-28 mb-24 transition-all duration-300 md:ml-64">
                <div className="max-w-7xl mx-auto px-4">
                    <div className="md:flex md:items-start md:space-x-6">
                        <div className="flex-1">
                            {/* Page header */}
                            <header className="sticky top-0 max-w-7xl mx-auto px-4 py-4 border-b bg-white">
                                <h1 className="text-xl font-bold text-gray-900">Mock Tests & History</h1>
                            </header>

                            {/* Hero + Test cards section */}
                            <div className="max-w-7xl mx-auto px-3">
                                {/* Hero */}
                                <div className="mt-4">
                                    <Card className="bg-gradient-to-r from-white to-slate-50">
                                        <CardContent className="p-6 flex items-center justify-between gap-4">
                                            <div>
                                                <h2 className="text-2xl font-semibold text-gray-900">Create or Take Tests</h2>
                                                <p className="text-sm text-gray-600 mt-1">Choose a quick random test, build a custom test, or view your history and scheduled competitions.</p>
                                                <div className="mt-3 flex items-center gap-3">
                                                    <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={() => setShowRandomModal(true)}>Quick Test</Button>
                                                    <Button variant="outline" onClick={() => setShowChapterModal(true)}>Build Test</Button>
                                                </div>
                                            </div>
                                            <div className="hidden md:flex items-center">
                                                <img src="/assets/illustrations/tests-hero.svg" alt="tests" className="w-48 h-auto opacity-90" />
                                            </div>
                                        </CardContent>
                                    </Card>
                                </div>

                                {/* Search / Filters */}
                                <div className="mt-4 flex items-center justify-between gap-4">
                                    <div className="flex items-center gap-3 flex-1">
                                        <input aria-label="Search tests" className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm" placeholder="Search tests, chapters or topics" />
                                        <Button variant="ghost" className="hidden md:inline-flex">Filters</Button>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Button variant="ghost" size="icon">Sort</Button>
                                    </div>
                                </div>

                                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <TestCard
                                        title="Quick Random Test"
                                        subtitle="Just choose the no. of questions and get started"
                                        icon={<Shuffle className="w-4 h-4 text-blue-800" />}
                                        onClick={() => setShowRandomModal(true)}
                                    />

                                    <TestCard
                                        title="Build Your Own Test"
                                        subtitle="Select subjects, chapters & topics of your choice"
                                        icon={<SlidersHorizontal className="w-4 h-4 text-blue-800" />}
                                        onClick={() => setShowChapterModal(true)}
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
                            </div>

                            {/* Test History Section */}
                            <div className="max-w-7xl mx-auto mt-4 pb-20">
                                <TestHistory />
                            </div>

                            <MobileDock />

                            {/* Random Test Modal (opened by Quick Test) */}
                            {showRandomModal && (
                                <div className="fixed inset-0 z-[99999] bg-white h-screen overflow-hidden">
                                    <div className="h-full flex flex-col">
                                        <header className="w-full mx-auto py-3 px-4 border-b border-gray-200 inline-flex items-center gap-3">
                                            <Button variant="secondary" size="icon" className="size-8" onClick={() => setShowRandomModal(false)}>
                                                <ChevronLeft className="h-4 w-4" />
                                            </Button>
                                            <h1 className="text-lg font-bold text-gray-900">Create Random Test</h1>
                                        </header>
                                        <main className="flex-1 overflow-auto p-4">
                                            <RandomTest testType="random" topics={[]} onCancel={() => setShowRandomModal(false)} />
                                        </main>
                                    </div>
                                </div>
                            )}

                            {/* Chapter Selection Modal (opened by Your Choice) */}
                            {showChapterModal && (
                                <div className="fixed inset-0 z-[99999] bg-white h-screen overflow-hidden">
                                    <div className="h-full flex flex-col">
                                        <header className="w-full mx-auto py-3 px-4 border-b border-gray-200 inline-flex items-center gap-3">
                                            <Button variant="secondary" size="icon" className="size-8" onClick={() => setShowChapterModal(false)}>
                                                <ChevronLeft className="h-4 w-4" />
                                            </Button>
                                            <h1 className="text-lg font-bold text-gray-900">Build Your Own Test</h1>
                                        </header>
                                        <main className="flex-1 overflow-auto p-4">
                                            <ChapterSelection />
                                        </main>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Right sidebar (desktop only) */}
                        <aside className="hidden md:block w-80 mt-6 md:mt-0">
                            <div className="space-y-4">
                                <Card>
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

                                {analytics?.totalTests === 0 && (
                                    <Card>
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
        <Card onClick={handleClick} className="rounded-2xl shadow-sm hover:shadow-lg transform hover:-translate-y-1 transition-all duration-150 cursor-pointer">
            <CardContent className="p-4">
                <div className="flex items-center justify-between space-x-4">
                    <div className="flex items-center space-x-4 pr-2">
                        <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center">
                            {icon}
                        </div>
                        <div className="flex-1">
                            <div className="flex items-center gap-2">
                                <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
                                <ChevronRight className="w-3 h-3 text-gray-400" />
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