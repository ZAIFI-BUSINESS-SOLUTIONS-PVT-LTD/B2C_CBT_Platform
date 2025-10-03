import React, { useMemo } from 'react';
import { useAuth } from '@/hooks/use-auth';
import { Card, CardContent } from "@/components/ui/card";
import { GraduationCap, Timer, HelpCircle } from "lucide-react";
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

    const accuracy = Math.max(0, Math.min(100, Math.round(analytics?.overallAccuracy ?? 0)));
    const avgTime = Math.max(0, Math.round(analytics?.averageTimePerQuestion ?? 0));
    const uniqueQuestions = Math.max(0, analytics?.uniqueQuestionsAttempted ?? 0);
    const totalTests = Math.max(0, analytics?.totalTests ?? 0);

    return (
        <div className="text-left">
            <div className="max-w-5xl mx-auto">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div>
                        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 leading-tight">
                            Learn about your performance
                        </h2>
                        <p className="mt-1 text-sm text-slate-500">
                            Hey <span className="font-semibold text-slate-700">{displayName}</span> — a quick summary of your recent activity and progress.
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => navigate('/dashboard')}
                            className="inline-flex items-center gap-2 bg-blue-600 text-white font-semibold text-sm py-2 px-4 rounded-lg shadow-md transition-transform transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-blue-300"
                        >
                            Open Dashboard
                        </button>
                        <button
                            onClick={() => navigate('/tests')}
                            className="hidden sm:inline-flex items-center gap-2 bg-white/90 hover:bg-white text-slate-700 border border-slate-200 py-2 px-3 rounded-lg shadow-sm text-sm transition-colors"
                        >
                            Start a Test
                        </button>
                    </div>
                </div>

                <div className="mt-6">
                    <div className="relative rounded-2xl p-5 bg-gradient-to-br from-sky-50 to-white shadow-inner overflow-hidden">
                        {/* Decorative layered background */}
                        <div className="pointer-events-none absolute -right-10 -top-10 w-72 h-72 bg-gradient-to-tr from-blue-100 to-transparent opacity-60 rounded-full blur-3xl"></div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                            {/* Accuracy Card */}
                            <Card className="relative overflow-visible transform transition-all duration-200 hover:-translate-y-1 hover:shadow-2xl rounded-xl border-0 bg-gradient-to-br from-white via-sky-50 to-sky-100">
                                <CardContent className="p-4">
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <p className="text-sm text-slate-500 font-medium">Average Score</p>
                                            <div className="mt-2 flex items-baseline gap-3">
                                                <GraduationCap className="h-6 w-6 text-sky-600" />
                                                <p className="text-2xl font-extrabold text-slate-900">{accuracy} %</p>
                                            </div>
                                        </div>
                                        <div className="text-right text-xs text-slate-500">Tests: <span className="font-semibold text-slate-700">{totalTests}</span></div>
                                    </div>

                                    <div className="mt-4">
                                        <div className="w-full bg-slate-100 rounded-full h-2">
                                            <div className={`h-2 rounded-full`} style={{ width: `${accuracy}%`, background: 'linear-gradient(90deg,#16a34a,#06038d,#0ea5e9)' }} />
                                        </div>
                                        <div className="mt-2 text-xs text-slate-500">Accuracy across all attempted tests</div>
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Avg. Speed Card */}
                            <Card className="transform transition-all duration-200 hover:-translate-y-1 hover:shadow-2xl rounded-xl border-0 bg-gradient-to-br from-white via-emerald-50 to-emerald-100">
                                <CardContent className="p-4">
                                    <p className="text-sm text-slate-500 font-medium">Avg. Time / Question</p>
                                    <div className="mt-2 flex items-center gap-3">
                                        <Timer className="h-6 w-6 text-emerald-600" />
                                        <p className="text-2xl font-extrabold text-slate-900">{avgTime} sec</p>
                                    </div>
                                    <p className="mt-3 text-xs text-slate-500">Improve speed by practicing timed sections.</p>
                                </CardContent>
                            </Card>

                            {/* Questions Card */}
                            <Card className="transform transition-all duration-200 hover:-translate-y-1 hover:shadow-2xl rounded-xl border-0 bg-gradient-to-br from-white via-yellow-50 to-amber-50">
                                <CardContent className="p-4">
                                    <p className="text-sm text-slate-500 font-medium">Questions Attempted</p>
                                    <div className="mt-2 flex items-center gap-3">
                                        <HelpCircle className="h-6 w-6 text-amber-600" />
                                        <p className="text-2xl font-extrabold text-slate-900">{uniqueQuestions}</p>
                                    </div>
                                    <p className="mt-3 text-xs text-slate-500">Keep a streak going — consistency rewards progress.</p>
                                </CardContent>
                            </Card>

                            {/* View More / CTA Card */}
                            <Card className="relative cursor-pointer transform transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl rounded-xl border-0 bg-gradient-to-br from-white to-sky-50 flex items-center justify-center" onClick={() => navigate('/dashboard')}>
                                <CardContent className="p-4 flex flex-col items-center justify-center gap-3">
                                    <div className="text-center">
                                        <p className="text-sm text-slate-500">Deep dive</p>
                                        <p className="mt-1 text-lg font-semibold text-blue-700">View detailed analytics</p>
                                    </div>

                                    <div className="w-full flex items-center justify-center">
                                        <button
                                            onClick={(e) => { e.stopPropagation(); navigate('/dashboard'); }}
                                            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate('/dashboard'); } }}
                                            className="inline-flex items-center gap-2 bg-blue-600 text-white py-2 px-4 rounded-md shadow-md text-sm font-semibold"
                                        >
                                            View more
                                        </button>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
