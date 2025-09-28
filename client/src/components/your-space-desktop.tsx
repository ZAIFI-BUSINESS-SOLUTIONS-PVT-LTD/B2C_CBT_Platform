import { useState } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Label, LabelList } from 'recharts';
import { Activity, GraduationCap, Timer, HelpCircle, Filter, SlidersHorizontal, LogOut } from "lucide-react";
import { AnalyticsData } from "./insight-card";
import { InsightsData } from "@/types/dashboard";
import { useAuth } from "@/contexts/AuthContext";
import FilterTopicPerformance from './filter-topic-performance';

const CHART_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6'];

const TOPIC_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16'];


function PerformanceTrendsChart({ data }: { data: any[] }) {
    return (
        <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} margin={{ top: 20, right: 30, bottom: 5, left: 30 }}>
                    <CartesianGrid strokeDasharray="2 2" />
                    <XAxis
                        dataKey="testNumber"
                        type="number"
                        domain={["dataMin", "dataMax"]}
                        allowDecimals={false}
                        tickFormatter={(v) => (v != null ? `${v}` : '')}
                        fontSize={12}
                    >
                        <Label value="Practice test" offset={-5} position="insideBottom" fontSize={12} />
                    </XAxis>
                    <YAxis fontSize={12} hide={true}>
                        <Label value="Accuracy (%)" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} fontSize={12} />
                    </YAxis>
                    <Tooltip
                        labelFormatter={(label) => (label != null ? `Practice test ${label}` : '')}
                        contentStyle={{ fontSize: '14px' }}
                    />
                    <Bar dataKey="accuracy" fill="#3B82F6" barSize={20} radius={[4, 4, 0, 0]}>
                        <LabelList
                            dataKey="accuracy"
                            position="top"
                            formatter={(value: any) => `${value}%`}
                            style={{ fontSize: '12px', fontWeight: 'bold', fill: '#0f172a' }}
                        />
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

function QuestionDistributionChart({ correct, incorrect, skipped }: { correct: number; incorrect: number; skipped: number }) {
    const total = correct + incorrect + skipped;
    const data = [
        { name: 'Correct', value: correct, color: '#10B981' },
        { name: 'Incorrect', value: incorrect, color: '#F59E0B' },
        { name: 'Skipped', value: skipped, color: '#8B5CF6' }
    ].filter(item => item.value > 0);

    if (total === 0) {
        // Render an empty donut with 0 in center when there are no questions practiced
        const outerRadius = 75;
        const innerRadius = 63;
        return (
            <div className="flex items-center justify-center">
                <svg width="120" height="120" viewBox="0 0 160 160" className="sm:w-44 sm:h-44">
                    <g>
                        <circle cx="80" cy="80" r={outerRadius} fill="#f3f4f6" />
                        <circle cx="80" cy="80" r={innerRadius} fill="#fff" />
                    </g>
                    <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle" fontSize="45" fill="#0f172a" fontWeight={700} className="sm:text-lg">0</text>
                </svg>
            </div>
        );
    }

    return (
        <div className="flex items-center justify-center">
            <svg width="120" height="120" viewBox="0 0 160 160" className="sm:w-44 sm:h-44">

                {/* Donut segments */}
                {data.length === 1 ? (
                    // Single segment (100%) — draw full donut using two circles to avoid arc edge-case
                    (() => {
                        const entry = data[0];
                        const outerRadius = 75;
                        const innerRadius = 63;
                        return (
                            <g key={entry.name}>
                                <circle cx="80" cy="80" r={outerRadius} fill={entry.color} />
                                <circle cx="80" cy="80" r={innerRadius} fill="#fff" />
                            </g>
                        );
                    })()
                ) : (
                    data.map((entry, index) => {
                        const prevTotal = data.slice(0, index).reduce((sum, d) => sum + d.value, 0);
                        const percentage = entry.value / total;
                        const startAngle = (prevTotal / total) * 360 - 90;
                        const endAngle = ((prevTotal + entry.value) / total) * 360 - 90;

                        const largeArcFlag = percentage > 0.5 ? 1 : 0;
                        const outerRadius = 75;
                        const innerRadius = 63;

                        // Calculate outer arc points
                        const x1 = 80 + outerRadius * Math.cos(startAngle * Math.PI / 180);
                        const y1 = 80 + outerRadius * Math.sin(startAngle * Math.PI / 180);
                        const x2 = 80 + outerRadius * Math.cos(endAngle * Math.PI / 180);
                        const y2 = 80 + outerRadius * Math.sin(endAngle * Math.PI / 180);

                        // Calculate inner arc points
                        const x3 = 80 + innerRadius * Math.cos(endAngle * Math.PI / 180);
                        const y3 = 80 + innerRadius * Math.sin(endAngle * Math.PI / 180);
                        const x4 = 80 + innerRadius * Math.cos(startAngle * Math.PI / 180);
                        const y4 = 80 + innerRadius * Math.sin(startAngle * Math.PI / 180);

                        return (
                            <path
                                key={entry.name}
                                d={`M ${x1} ${y1} A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${x4} ${y4} Z`}
                                fill={entry.color}
                            />
                        );
                    })
                )}


                {/* Center text */}
                <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle" fontSize="45" fill="#0f172a" fontWeight={700} className="sm:text-lg">{total}</text>
            </svg>
        </div>
    );
}

interface PracticeArenaProps {
    analytics: AnalyticsData;
    insights: InsightsData;
    timeDistSubject: string;
    setTimeDistSubject: (value: string) => void;
}

export default function PracticeArena({ analytics, insights, timeDistSubject, setTimeDistSubject }: PracticeArenaProps) {
    const [selectedSubject, setSelectedSubject] = useState('Overall');
    const [showFilter, setShowFilter] = useState(false);
    const [filterSubject, setFilterSubject] = useState<string[]>(['All Subjects']);
    const [sortOption, setSortOption] = useState<'none' | 'accuracy-high-low' | 'accuracy-low-high'>('none');
    const { logout } = useAuth();

    const subjects = ['Overall', ...(analytics.timeDistributionPast7?.subjects || [])];

    // Get unique subjects for filter
    const topicSubjects = analytics.topicPerformance ? [...new Set(analytics.topicPerformance.map(t => t.subject))] : [];
    const filterSubjects = ['All Subjects', ...topicSubjects];

    const handleApplyFilter = (subjects: string[], sort: 'none' | 'accuracy-high-low' | 'accuracy-low-high') => {
        setFilterSubject(subjects);
        setSortOption(sort);
    };

    // Filter and sort topics based on selected filter and sort option
    const filteredAndSortedTopics = analytics.topicPerformance ? (() => {
        // If no subjects are selected, automatically select all subjects
        const effectiveFilterSubject = filterSubject.length === 0 ? filterSubjects : filterSubject;

        let topics = effectiveFilterSubject.includes('All Subjects') ? analytics.topicPerformance :
            analytics.topicPerformance.filter(t => effectiveFilterSubject.includes(t.subject));

        // Sort based on accuracy
        if (sortOption === 'accuracy-high-low') {
            topics = topics.sort((a, b) => {
                const accuracyA = a.correctAnswers && a.totalQuestions ? (a.correctAnswers / a.totalQuestions) * 100 : 0;
                const accuracyB = b.correctAnswers && b.totalQuestions ? (b.correctAnswers / b.totalQuestions) * 100 : 0;
                return accuracyB - accuracyA;
            });
        } else if (sortOption === 'accuracy-low-high') {
            topics = topics.sort((a, b) => {
                const accuracyA = a.correctAnswers && a.totalQuestions ? (a.correctAnswers / a.totalQuestions) * 100 : 0;
                const accuracyB = b.correctAnswers && b.totalQuestions ? (b.correctAnswers / b.totalQuestions) * 100 : 0;
                return accuracyA - accuracyB;
            });
        }

        return topics;
    })() : [];

    const getPerformanceScore = () => {
        if (selectedSubject === 'Overall') {
            const total = analytics.subjectAccuracyPast7?.reduce((sum, s) => sum + s.accuracy, 0) || 0;
            const count = analytics.subjectAccuracyPast7?.length || 0;
            return count > 0 ? `${Math.round(total / count)}%` : 'N/A';
        } else {
            const subj = analytics.subjectAccuracyPast7?.find(s => s.subject === selectedSubject);
            return subj ? `${Math.round(subj.accuracy)}%` : 'N/A';
        }
    };

    const getTimePerCorrect = () => {
        const totalCorrect = getTotalCorrect();
        if (totalCorrect > 0 && analytics.totalTimeSpent) {
            return `${Math.round(analytics.totalTimeSpent / totalCorrect)}s`;
        }
        // Fallback to time distribution data
        let data;
        if (selectedSubject === 'Overall') {
            data = analytics.timeDistributionPast7?.overall;
        } else {
            data = analytics.timeDistributionPast7?.bySubject[selectedSubject];
        }
        if (!data) return 'N/A';
        const correct = data.find(d => d.status === 'correct');
        return correct ? `${Math.round(correct.avgTimeSec || correct.timeSec || 0)}s` : 'N/A';
    };

    const getTimePerIncorrectUnattempted = () => {
        let data;
        if (selectedSubject === 'Overall') {
            data = analytics.timeDistributionPast7?.overall;
        } else {
            data = analytics.timeDistributionPast7?.bySubject[selectedSubject];
        }
        if (!data) return 'N/A';

        const incorrect = data.find(d => d.status === 'incorrect');
        const unattempted = data.find(d => d.status === 'unattempted');

        // Get time values, defaulting to 0 if not available
        const incorrectTime = incorrect?.avgTimeSec || incorrect?.timeSec || 0;
        const unattemptedTime = unattempted?.avgTimeSec || unattempted?.timeSec || 0;

        // Only include times that are greater than 0
        const validTimes = [incorrectTime, unattemptedTime].filter(t => t > 0);

        if (validTimes.length === 0) return 'N/A';

        // Calculate weighted average based on available data
        const avg = validTimes.reduce((sum, t) => sum + t, 0) / validTimes.length;
        return `${Math.round(avg)}s`;

        // Alternative: Show separate values
        // const incorrectStr = incorrectTime > 0 ? `Inc: ${Math.round(incorrectTime)}s` : '';
        // const unattemptedStr = unattemptedTime > 0 ? `Unatt: ${Math.round(unattemptedTime)}s` : '';
        // if (!incorrectStr && !unattemptedStr) return 'N/A';
        // return [incorrectStr, unattemptedStr].filter(Boolean).join(', ');
    };

    const getTotalQuestions = () => {
        if (!analytics.topicPerformance) return 'N/A';
        let topics;
        if (selectedSubject === 'Overall') {
            topics = analytics.topicPerformance;
        } else {
            topics = analytics.topicPerformance.filter(t => t.subject === selectedSubject);
        }
        const total = topics.reduce((sum, t) => sum + (t.totalQuestions || 0), 0);
        return total.toString();
    };

    // Helpers for the new performance card
    const sumTopic = (fn: (t: any) => number) => {
        if (!analytics.topicPerformance) return 0;
        const topics = selectedSubject === 'Overall' ? analytics.topicPerformance : analytics.topicPerformance.filter(t => t.subject === selectedSubject);
        return topics.reduce((s, t) => s + (fn(t) || 0), 0);
    };

    const getPerformancePercent = () => {
        const score = getPerformanceScore();
        if (!score || score === 'N/A') return 0;
        const num = Number(String(score).replace('%', ''));
        if (isNaN(num)) return 0;
        return Math.max(0, Math.min(1, num / 100));
    };

    const getQuestionsProgress = () => {
        const total = Number(getTotalQuestions() === 'N/A' ? 0 : getTotalQuestions());
        const target = 100; // arbitrary target for progress bar
        return Math.min(1, total / target);
    };

    const getAvgTimePerQuestion = () => {
        if (typeof analytics.averageTimePerQuestion === 'number' && analytics.averageTimePerQuestion > 0) return analytics.averageTimePerQuestion;
        if (typeof analytics.totalTimeSpent === 'number' && typeof analytics.totalQuestions === 'number' && analytics.totalQuestions > 0) {
            return analytics.totalTimeSpent / analytics.totalQuestions;
        }
        return 0;
    };

    const formatSeconds = (s: number) => (s && s > 0 ? `${Math.round(s)}s` : 'N/A');

    const getTimeBarValue = (s: number) => {
        if (!s || s <= 0) return 0;
        const max = 60; // map to 0..1 where 60s is full
        return Math.min(1, s / max);
    };

    const getTotalCorrect = () => sumTopic(t => t.correctAnswers || 0);
    const getTotalIncorrect = () => sumTopic(t => (t.totalQuestions || 0) - (t.correctAnswers || 0));
    const getTotalSkipped = () => 0; // skipped not available in topicPerformance; default 0

    const getTotalIncorrectStr = () => String(getTotalIncorrect());
    const getTotalSkippedStr = () => (getTotalSkipped() > 0 ? String(getTotalSkipped()) : '0');

    const getCorrectProportion = () => {
        const total = sumTopic(t => t.totalQuestions || 0);
        if (total === 0) return 0;
        return Math.min(1, getTotalCorrect() / total);
    };
    const getIncorrectProportion = () => {
        const total = sumTopic(t => t.totalQuestions || 0);
        if (total === 0) return 0;
        return Math.min(1, getTotalIncorrect() / total);
    };
    const getSkippedProportion = () => {
        const total = sumTopic(t => t.totalQuestions || 0);
        if (total === 0) return 0;
        return Math.min(1, getTotalSkipped() / total);
    };

    const extractSeconds = (s: any) => {
        if (!s) return 0;
        if (typeof s === 'number') return s;
        const m = String(s).match(/(\d+)/);
        return m ? Number(m[1]) : 0;
    };

    const getTimePerSkippedStr = () => {
        let data;
        if (selectedSubject === 'Overall') data = analytics.timeDistributionPast7?.overall;
        else data = analytics.timeDistributionPast7?.bySubject?.[selectedSubject];
        if (!data) return 'N/A';
        const entry = data.find((d: any) => d.status === 'unattempted' || d.status === 'skipped');
        if (!entry) return 'N/A';
        return `${Math.round(entry.avgTimeSec ?? entry.timeSec ?? 0)}s`;
    };

    // Small presentational row used inside the card
    function MetricRow({ label, value, barValue = 0, maxLabel, secondaryLabel, secondaryValue }: { label: string; value: any; barValue?: number; maxLabel?: string; secondaryLabel?: string; secondaryValue?: any }) {
        return (
            <div className="flex items-center justify-between">
                <div className="flex-1 pr-4">
                    <div className="text-sm font-medium">{label}</div>
                    {barValue > 0 && (
                        <div className="mt-2 h-2 bg-white/20 rounded-full overflow-hidden">
                            <div className="h-2 bg-white rounded-full" style={{ width: `${Math.round(barValue * 100)}%` }} />
                        </div>
                    )}
                </div>
                <div className="w-36 text-right text-sm font-semibold">
                    <div>{value} {maxLabel ? <span className="text-xs font-normal">{maxLabel}</span> : null}</div>
                    {secondaryLabel && secondaryValue && (
                        <div className="text-xs text-white/80 mt-1">{secondaryLabel}: {secondaryValue}</div>
                    )}
                </div>
            </div>
        );
    }

    return (
        <>
            <div className="w-full space-y-4">
                {/* Performance Overview card */}
                <Card className="bg-white rounded-2xl p-6 border">
                    <CardContent className="p-0">
                        <div className="pb-3">
                            <h2 className="flex items-center gap-2 text-xl font-bold">
                                Performance Overview <Badge variant="outline" className='bg-blue-100 text-blue-600 border border-blue-600'>Past 7 tests</Badge>
                            </h2>
                        </div>
                        <div className="space-y-4">
                            {/* Subject selection + charts/metrics */}
                            <div className="w-full mb-4 ">
                                <div className="flex flex-col items-center space-y-4">
                                    {/* Subject selection buttons */}
                                    <div className="w-full flex items-center justify-start">
                                        <div className="flex gap-3 overflow-x-auto max-w-full hide-scrollbar">
                                            {subjects.map((s) => (
                                                <Button
                                                    key={s}
                                                    variant={s === selectedSubject ? "default" : "outline"}
                                                    size="default"
                                                    className='rounded-lg'
                                                    onClick={() => setSelectedSubject(s)}>{s}
                                                </Button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Manipulatable Data Container */}
                                    <div className="bg-white w-full rounded-2xl pt-10 pb-4 px-3 space-y-6">
                                        {/* Charts + Metrics Row: stack on small screens, row on sm+ */}
                                        <div className="flex flex-col sm:flex-row items-start justify-center gap-20">
                                            {/* Performance circle */}
                                            <div className="flex flex-col items-center mt-3">
                                                <svg width="120" height="120" viewBox="0 0 160 160" className="sm:w-44 sm:h-44">
                                                    <defs>
                                                        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
                                                            <stop offset="0%" stopColor="#2563eb" />
                                                            <stop offset="100%" stopColor="#60a5fa" />
                                                        </linearGradient>
                                                    </defs>
                                                    <circle cx="80" cy="80" r="70" stroke="#0f172a" strokeOpacity="0.08" strokeWidth="12" fill="none" />
                                                    <circle
                                                        cx="80"
                                                        cy="80"
                                                        r="70"
                                                        stroke="url(#grad)"
                                                        strokeWidth="12"
                                                        strokeLinecap="round"
                                                        fill="none"
                                                        strokeDasharray={`${2 * Math.PI * 70}`}
                                                        strokeDashoffset={`${2 * Math.PI * 70 * (1 - getPerformancePercent())}`}
                                                        transform="rotate(-90 80 80)"
                                                    />
                                                    <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle" fontSize="45" fill="#0f172a" fontWeight={700} className="sm:text-xl">{getPerformanceScore()}</text>
                                                </svg>
                                                <div className="text-center mt-2">
                                                    <div className="text-xs sm:text-sm text-gray-600 font-medium">Performance<br />Score</div>
                                                </div>
                                            </div>

                                            {/* Question Distribution Donut Chart */}
                                            <div className="flex flex-col items-center mt-3">
                                                <QuestionDistributionChart
                                                    correct={getTotalCorrect()}
                                                    incorrect={getTotalIncorrect()}
                                                    skipped={getTotalSkipped()}
                                                />
                                                <div className="text-center mt-2">
                                                    <div className="text-xs sm:text-sm text-gray-600 font-medium">Total Questions<br />Practiced</div>
                                                </div>
                                            </div>

                                            {/* Metrics cards placed to the right on larger screens, below on small screens */}
                                            <div className="w-64 max-w-4xl">
                                                <div className="grid grid-cols-1 gap-4">
                                                    {/* Correct Answers Card */}
                                                    <div className="bg-white text-gray-800 rounded-xl p-2 shadow-md border border-green-500">
                                                        <div className="flex items-center justify-between">
                                                            <div className="flex-1">
                                                                <div className="text-lg font-bold mb-1">Correct Answers</div>
                                                                <div className="text-sm text-gray-600">
                                                                    <span className="font-bold">Time per question:</span> {getTimePerCorrect()}
                                                                </div>
                                                            </div>
                                                            <div className="text-3xl font-bold mr-4 ">{String(getTotalCorrect())}</div>
                                                        </div>
                                                    </div>

                                                    {/* Incorrect Answers Card */}
                                                    <div className="bg-white text-gray-800 rounded-xl p-2 shadow-md border border-orange-500">
                                                        <div className="flex items-center justify-between">
                                                            <div className="flex-1">
                                                                <div className="text-lg font-bold mb-1">Incorrect Answers</div>
                                                                <div className="text-sm text-gray-600">
                                                                    <span className="font-bold">Time per question:</span> {getTimePerIncorrectUnattempted()}
                                                                </div>
                                                            </div>
                                                            <div className="text-3xl font-bold mr-4">{getTotalIncorrectStr()}</div>
                                                        </div>
                                                    </div>

                                                    {/* Skipped Questions Card */}
                                                    <div className="bg-white text-gray-800 rounded-xl p-2 shadow-md border border-purple-500">
                                                        <div className="flex items-center justify-between">
                                                            <div className="flex-1">
                                                                <div className="text-lg font-bold mb-1">Skipped Questions</div>
                                                                <div className="text-sm text-gray-600">
                                                                    <span className="font-bold">Time per question:</span> {getTimePerSkippedStr()}
                                                                </div>
                                                            </div>
                                                            <div className="text-3xl font-bold mr-4">{getTotalSkippedStr()}</div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Performance Score card */}
                <Card className="bg-white rounded-2xl p-6 border">
                    <CardContent className="p-0">
                        <div className="pb-2">
                            <h2 className="flex items-center gap-2 text-xl font-bold">
                                Performance Score <Badge variant="outline" className='bg-blue-100 text-blue-600 border border-blue-600'>Past 7 tests</Badge>
                            </h2>
                        </div>
                        <div className='rounded-2xl px-2 py-4'>
                            <PerformanceTrendsChart data={analytics.timeBasedTrends} />
                        </div>
                    </CardContent>
                </Card>

                {/* Topic Performance Score card */}
                <Card className="bg-white rounded-2xl p-4 border">
                    <CardContent className="p-0">
                        <div className="flex items-center gap-2 text-xl font-bold px-0 md:px-2">
                            Topic Performance Score<Badge variant="outline" className='bg-blue-100 text-blue-600 border border-blue-600'>All tests</Badge>
                        </div>

                        {/* Filter Section */}
                        <div className="sticky top-14 z-40 -mx-3 mt-5 px-3 py-3 border-b border-gray-200 ">
                            <div className="flex items-center gap-2">
                                {/* Filter label (button removed) */}
                                <div className="flex items-center gap-2 text-sm font-medium rounded-xl px-3 py-1">
                                    <SlidersHorizontal className="w-4 h-4" />
                                    <span>Filter</span>
                                </div>

                                {/* Horizontal Scroll Container for Filter Options */}
                                <div className="flex-1 overflow-x-auto hide-scrollbar">
                                    <div className="flex items-center gap-2 min-w-max">
                                        {/* Combined Filter Options - Selected first */}
                                        <div className="flex items-center gap-1">
                                            {[
                                                // Sort options
                                                { type: 'sort', key: 'accuracy-high-low', label: 'High to low Performance', isSelected: sortOption === 'accuracy-high-low' },
                                                { type: 'sort', key: 'accuracy-low-high', label: 'Low to high Performance', isSelected: sortOption === 'accuracy-low-high' },
                                                // Subject options
                                                ...filterSubjects.map(subject => ({
                                                    type: 'subject',
                                                    key: subject,
                                                    label: subject,
                                                    isSelected: filterSubject.length === 0 && subject === 'All Subjects' ? true : filterSubject.includes(subject)
                                                }))
                                            ]
                                                .sort((a, b) => {
                                                    if (a.isSelected && !b.isSelected) return -1;
                                                    if (!a.isSelected && b.isSelected) return 1;
                                                    return 0;
                                                })
                                                .map((option) => {
                                                    if (option.type === 'sort') {
                                                        return (
                                                            <Button
                                                                key={option.key}
                                                                variant={option.isSelected ? "default" : "outline"}
                                                                size="sm"
                                                                onClick={() => setSortOption(option.isSelected ? 'none' : option.key as 'accuracy-high-low' | 'accuracy-low-high')}
                                                                className="rounded-lg text-xs px-3 py-1 flex items-center gap-1"
                                                            >
                                                                {option.label}
                                                                {option.isSelected && (
                                                                    <span className="text-white hover:text-gray-200 cursor-pointer ml-1"
                                                                        onClick={(e) => {
                                                                            e.stopPropagation();
                                                                            setSortOption('none');
                                                                        }}>×</span>
                                                                )}
                                                            </Button>
                                                        );
                                                    } else {
                                                        return (
                                                            <Button
                                                                key={option.key}
                                                                variant={option.isSelected ? "default" : "outline"}
                                                                size="sm"
                                                                onClick={() => {
                                                                    if (option.key === 'All Subjects') {
                                                                        setFilterSubject(['All Subjects']);
                                                                    } else if (option.isSelected) {
                                                                        setFilterSubject(prev => prev.filter(s => s !== option.key));
                                                                    } else {
                                                                        setFilterSubject(prev => prev.filter(s => s !== 'All Subjects').concat(option.key));
                                                                    }
                                                                }}
                                                                className="rounded-lg text-xs px-3 py-1 flex items-center gap-1 whitespace-nowrap"
                                                            >
                                                                {option.label}
                                                                {option.isSelected && option.key !== 'All Subjects' && (
                                                                    <span className="text-white hover:text-gray-200 cursor-pointer ml-1"
                                                                        onClick={(e) => {
                                                                            e.stopPropagation();
                                                                            setFilterSubject(prev => prev.filter(s => s !== option.key));
                                                                        }}>×</span>
                                                                )}
                                                            </Button>
                                                        );
                                                    }
                                                })}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Filter Modal */}
                        <FilterTopicPerformance
                            isOpen={showFilter}
                            onClose={() => setShowFilter(false)}
                            subjects={filterSubjects}
                            currentFilter={filterSubject}
                            currentSort={sortOption}
                            onApplyFilter={handleApplyFilter}
                        />

                        <div className="relative px-0 md:px-2">
                            {analytics.topicPerformance && analytics.topicPerformance.length > 0 ? (
                                <div className="grid grid-cols-1 gap-4">
                                    {filteredAndSortedTopics.map((row: any, index: number) => (
                                        <Card key={row.topicId || row.topic} className="shadow-sm">
                                            <CardContent className="p-4">
                                                <div className="flex items-center justify-between mb-3">
                                                    <h3 className="font-bold text-md">{row.topic}</h3>
                                                    <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                                                        {row.subject}
                                                    </Badge>
                                                </div>
                                                <div className="mt-3">
                                                    <div className="flex justify-between items-center mb-1">
                                                        <span className="text-sm text-gray-600">Accuracy</span>
                                                        <span className="text-sm font-semibold">
                                                            {row.accuracy != null ? `${row.accuracy.toFixed(1)}%` : 'N/A'}
                                                        </span>
                                                    </div>
                                                    <div className="w-full bg-gray-200 rounded-full h-3">
                                                        <div
                                                            className="h-3 rounded-full transition-all duration-300"
                                                            style={{
                                                                width: `${row.accuracy || 0}%`,
                                                                backgroundColor: TOPIC_COLORS[index % TOPIC_COLORS.length]
                                                            }}
                                                        ></div>
                                                    </div>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-gray-500">
                                    No topic data yet. Take tests to populate topic performance.
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </>
    );
}
