/** Topics page — chapter/topic selection interface. */

import { ChapterSelection } from "@/components/chapter-selection-desktop";
import { useQuery } from "@tanstack/react-query";
import HeaderDesktop from "@/components/header-desktop";
import { AnalyticsData } from '@/types/api';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useLocation, Link } from "wouter";
import { useState, useRef } from "react";
import RandomTest from "@/components/random-test-desktop";
import TestHistory from "@/components/test-history";
import { ChevronRight, Shuffle, SlidersHorizontal, ClipboardClock, ClipboardList, ChevronLeft, Trophy, Play } from "lucide-react";

export default function Topics() {
    const [showRandomModal, setShowRandomModal] = useState(false);
    const [showChapterModal, setShowChapterModal] = useState(false);
    const [showInsufficientDialog, setShowInsufficientDialog] = useState(false);
    const [insufficientQuestionsData, setInsufficientQuestionsData] = useState<{ available: number; requested: number; message: string } | null>(null);
    const [chapterStep, setChapterStep] = useState(1);
    const [selectedSubjects, setSelectedSubjects] = useState<string[]>([]);
    const [selectedChapters, setSelectedChapters] = useState<string[]>([]);
    const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
    const chapterSelectionRef = useRef<{ handleCreateTest: () => void } | null>(null);
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

    const sidebarMarginClass = 'md:ml-64';

    const handleInsufficientQuestions = (data: { available: number; requested: number; message: string }) => {
        setInsufficientQuestionsData(data);
        setShowInsufficientDialog(true);
    };

    const handleChapterNext = () => {
        if (chapterStep < 6) {
            setChapterStep(chapterStep + 1);
        }
    };

    const handleChapterPrev = () => {
        if (chapterStep > 1) {
            setChapterStep(chapterStep - 1);
        }
    };

    const canGoNext = chapterStep < 6;
    const canGoPrev = chapterStep > 1;

    const handleCreateTest = () => {
        if (chapterSelectionRef.current) {
            chapterSelectionRef.current.handleCreateTest();
        }
    };

    return (
        <div className="flex min-h-screen bg-gray-50">
            <HeaderDesktop />
            <main className={`flex-1 flex flex-col bg-gray-50 mt-20 mb-24 transition-all duration-300 ${sidebarMarginClass}`}>
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
                                        </CardContent>
                                    </Card>
                                </div>
                            </div>

                            {/* Test History Section */}
                            <div className="max-w-7xl mx-auto mt-4">
                                <TestHistory />

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

                            {/* Random Test Modal (opened by Quick Test) */}
                            {showRandomModal && (
                                <div className="fixed inset-0 z-[99999] bg-black bg-opacity-50 flex items-center justify-center p-4">
                                    <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                                        <header className="w-full py-4 px-6 border-b border-gray-200 flex items-center gap-3">
                                            <Button variant="secondary" size="icon" className="size-8" onClick={() => setShowRandomModal(false)}>
                                                <ChevronLeft className="h-4 w-4" />
                                            </Button>
                                            <h1 className="text-xl font-bold text-gray-900">Create Random Test</h1>
                                        </header>
                                        <main className="flex-1 overflow-auto p-6">
                                            <RandomTest testType="random" topics={[]} onCancel={() => setShowRandomModal(false)} onInsufficientQuestions={handleInsufficientQuestions} />
                                        </main>
                                    </div>
                                </div>
                            )}

                            {/* Chapter Selection Modal (opened by Your Choice) */}
                            {showChapterModal && (
                                <div className="fixed inset-0 z-[99999] bg-black bg-opacity-50 flex items-center justify-center p-4">
                                    <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                                        <header className="w-full py-4 px-6 border-b border-gray-200 flex items-center gap-3">
                                            <Button variant="secondary" size="icon" className="size-8" onClick={() => setShowChapterModal(false)}>
                                                <ChevronLeft className="h-4 w-4" />
                                            </Button>
                                            <h1 className="text-xl font-bold text-gray-900">Build Your Own Test</h1>
                                        </header>
                                        <main className="flex-1 overflow-auto p-6">
                                            <ChapterSelection 
                                                ref={chapterSelectionRef}
                                                onInsufficientQuestions={handleInsufficientQuestions}
                                                onNext={handleChapterNext}
                                                onPrev={handleChapterPrev}
                                                canGoNext={canGoNext}
                                                canGoPrev={canGoPrev}
                                                isLastStep={chapterStep === 6}
                                                isCreating={false}
                                                currentStep={chapterStep}
                                                onStepChange={setChapterStep}
                                            />
                                        </main>
                                        <footer className="bg-white border-t border-gray-200 p-4 shadow-lg">
                                            <div className="flex justify-between items-center">
                                                <Button
                                                    variant="outline"
                                                    onClick={handleChapterPrev}
                                                    disabled={!canGoPrev}
                                                    className="flex items-center space-x-2"
                                                >
                                                    <ChevronLeft className="h-4 w-4" />
                                                    <span>Previous</span>
                                                </Button>

                                                <div className="flex space-x-2">
                                                    {chapterStep < 6 ? (
                                                        <Button
                                                            onClick={handleChapterNext}
                                                            disabled={!canGoNext}
                                                            className="flex items-center space-x-2"
                                                        >
                                                            <span>Next</span>
                                                            <ChevronLeft className="h-4 w-4 rotate-180" />
                                                        </Button>
                                                    ) : (
                                                        <Button
                                                            onClick={handleCreateTest}
                                                            className="bg-green-600 hover:bg-green-700 flex items-center space-x-2"
                                                        >
                                                            <Play className="h-4 w-4" />
                                                            <span>Create Test</span>
                                                        </Button>
                                                    )}
                                                </div>
                                            </div>
                                        </footer>
                                    </div>
                                </div>
                            )}
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

            {/* Insufficient questions dialog */}
            <Dialog open={showInsufficientDialog} onOpenChange={setShowInsufficientDialog}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>Insufficient Questions</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                            <div className="flex justify-between items-center">
                                <span className="text-sm font-medium text-orange-800">Available Questions:</span>
                                <span className="text-lg font-bold text-orange-600">{insufficientQuestionsData?.available}</span>
                            </div>
                            <div className="flex justify-between items-center mt-2">
                                <span className="text-sm font-medium text-orange-800">Requested Questions:</span>
                                <span className="text-lg font-bold text-red-600">{insufficientQuestionsData?.requested}</span>
                            </div>
                        </div>
                        <p className="text-sm text-gray-700">You can reduce the number of questions, or use the available questions to continue the test.</p>
                    </div>
                    <div className="flex gap-3 pt-4">
                        <Button variant="outline" onClick={() => setShowInsufficientDialog(false)} className="flex-1">
                            Back to Selection
                        </Button>
                        <Button
                            onClick={() => {
                                // Note: This action would need to be handled by passing a callback to RandomTest
                                // For now, just close the dialog
                                setShowInsufficientDialog(false);
                            }}
                            className="flex-1 bg-blue-600 hover:bg-blue-700"
                        >
                            Use {insufficientQuestionsData?.available} Questions
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
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
                        <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center">
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