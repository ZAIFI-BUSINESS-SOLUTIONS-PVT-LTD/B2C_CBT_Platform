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

    return (
        <div className="text-center">
            {/* Mini Dashboard */}
            <div>
                <div className="max-w-4xl mx-auto">
                    <h2 className="text-xl font-bold text-gray-900 mb-3 text-start">
                        Learn about your performance
                    </h2>
                    <div className="grid grid-cols-2 gap-3">
                        {/* Accuracy Card */}
                        <Card className="transition-all duration-300 bg-gradient-to-br from-sky-50 via-blue-50 to-white shadow-lg">
                            <CardContent className="p-3 text-start">
                                <p className="text-2xl font-bold text-blue-900 flex items-baseline gap-2">
                                    <GraduationCap className="h-5 w-5 text-blue-900 pt-1" />
                                    {analytics ? `${Math.round(analytics.overallAccuracy ?? 0)} %` : '0 %'}
                                </p>
                                <p className="text-sm text-gray-400 mt-1 font-medium">
                                    Your Average Score
                                </p>
                            </CardContent>
                        </Card>

                        {/* Avg. Speed Card */}
                        <Card className="transition-all duration-300 bg-gradient-to-br from-sky-50 via-blue-50 to-white border-0 shadow-lg">
                            <CardContent className="p-3 text-start">
                                <p className="text-2xl font-bold text-blue-900 flex items-baseline gap-2">
                                    <Timer className="h-5 w-5 text-blue-900 pt-1" />
                                    {analytics ? `${Math.round(analytics.averageTimePerQuestion ?? 0)} sec.` : '0 sec.'}
                                </p>
                                <p className="text-sm text-gray-400 mt-1 font-medium">
                                    Avg. Speed /Question
                                </p>
                            </CardContent>
                        </Card>

                        {/* Questions Card */}
                        <Card className="transition-all duration-300 bg-gradient-to-br from-sky-50 via-blue-50 to-white border-0 shadow-lg">
                            <CardContent className="p-3 text-start">
                                <p className="text-2xl font-bold text-blue-900 flex items-baseline gap-2">
                                    <HelpCircle className="h-5 w-5 text-blue-900 pt-1" />
                                    {analytics ? `${analytics.uniqueQuestionsAttempted ?? 0}` : '0'}
                                </p>
                                <p className="text-sm text-gray-400 mt-1 font-medium">
                                    Questions attended
                                </p>
                            </CardContent>
                        </Card>

                        {/* View More Card */}
                        <Card className="transition-all duration-300 cursor-pointer bg-white border-0 shadow-lg relative overflow-hidden" onClick={() => navigate('/dashboard')}>
                            <CardContent className="p-3 text-center flex items-center justify-center h-full relative z-10">
                                <a
                                    role="link"
                                    className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-2"
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
                                    View more {">>"}
                                </a>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    );
}
