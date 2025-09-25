import React, { useMemo } from 'react';
import { useAuth } from '@/hooks/use-auth';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { GraduationCap, Timer, HelpCircle, ArrowRight, History } from "lucide-react";
import { useLocation } from 'wouter';

interface WelcomeSectionProps {
    analytics?: {
        overallAccuracy?: number;
        averageTimePerQuestion?: number;
        uniqueQuestionsAttempted?: number;
        totalTests?: number;
    } | null;
}

export default function WelcomeSection({ analytics }: WelcomeSectionProps) {
    const { student } = useAuth();
    const [, navigate] = useLocation();

    const displayName = useMemo(() => {
        if (!student) return 'Student';
        if (student.fullName && student.fullName.trim().length > 0) return student.fullName.trim();
        if (student.email && student.email.includes('@')) return student.email.split('@')[0];
        return 'Student';
    }, [student]);

    return (
        <div className="text-left">
            {/* Mini Dashboard (desktop-optimized) */}
            <div>
                <div className="max-w-5xl mx-auto">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {/* Accuracy Card */}
                        <Card className="rounded-2xl border bg-white flex flex-col justify-between overflow-hidden">
                            <CardContent className="p-3 sm:p-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="inline-flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-md bg-blue-100 text-[1rem] sm:text-[1.125rem]">
                                        <GraduationCap className="h-4 w-4 text-blue-600" />
                                    </span>
                                </div>

                                <span className="block text-gray-500 text-sm font-medium mb-1 text-left">
                                    Your Average Score
                                </span>

                                <div className="flex items-center mt-1">
                                    <span className="text-xl sm:text-2xl font-bold text-gray-900 tracking-tight flex-1 text-left">
                                        {analytics ? `${Math.round(analytics.overallAccuracy ?? 0)} %` : '0 %'}
                                    </span>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Avg. Speed Card */}
                        <Card className="rounded-2xl border bg-white flex flex-col justify-between overflow-hidden">
                            <CardContent className="p-3 sm:p-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="inline-flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-md bg-blue-100 text-[1rem] sm:text-[1.125rem]">
                                        <Timer className="h-4 w-4 text-blue-600" />
                                    </span>
                                </div>

                                <span className="block text-gray-500 text-sm font-medium mb-1 text-left">
                                    Avg. Speed /Question
                                </span>

                                <div className="flex items-center mt-1">
                                    <span className="text-xl sm:text-2xl font-bold text-gray-900 tracking-tight flex-1 text-left">
                                        {analytics ? `${Math.round(analytics.averageTimePerQuestion ?? 0)} sec.` : '0 sec.'}
                                    </span>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Questions Card */}
                        <Card className="rounded-2xl border bg-white flex flex-col justify-between overflow-hidden">
                            <CardContent className="p-3 sm:p-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="inline-flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-md bg-blue-100 text-[1rem] sm:text-[1.125rem]">
                                        <HelpCircle className="h-4 w-4 text-blue-600" />
                                    </span>
                                </div>

                                <span className="block text-gray-500 text-sm font-medium mb-1 text-left">
                                    Questions attended
                                </span>

                                <div className="flex items-center mt-1">
                                    <span className="text-xl sm:text-2xl font-bold text-gray-900 tracking-tight flex-1 text-left">
                                        {analytics ? `${analytics.uniqueQuestionsAttempted ?? 0}` : '0'}
                                    </span>
                                </div>
                            </CardContent>
                        </Card>

                        {/* View More Card (filled & aligned) */}
                        <Card
                            className="rounded-2xl border transition-transform duration-150 hover:-translate-y-0.5 hover:shadow-lg cursor-pointer overflow-hidden flex flex-col justify-center h-full bg-white"
                            onClick={() => navigate('/dashboard')}
                        >

                            <CardContent className="relative z-10 p-3 flex items-center justify-center h-28 sm:h-24">
                                <div
                                    role="link"
                                    className="text-sm md:text-base text-black font-bold flex items-center gap-2"
                                    tabIndex={0}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        navigate('/dashboard');
                                    }}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' || e.key === ' ') {
                                            e.preventDefault();
                                            navigate('/dashboard');
                                        }
                                    }}
                                >
                                    View more
                                    <ArrowRight className="h-4 w-4 ml-1 text-black" />
                                </div>
                            </CardContent>

                            {/* Decorative accent strip on desktop (subtle lighter strip) */}
                            <div className="hidden lg:block absolute right-0 top-0 h-full w-1 bg-white/20" aria-hidden />
                        </Card>
                    </div>
                </div>

                {/* Action buttons - responsive row */}
                <div className="max-w-5xl mx-auto px-0 mt-4">
                    <div className="flex flex-col md:flex-row gap-4">
                        <div className="flex-1">
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
                        <div className="flex-1">
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
                    </div>
                </div>
            </div>
        </div>
    );
}
