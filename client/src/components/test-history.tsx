import { useMemo, useState } from "react";
import { useQuery, useQueries } from "@tanstack/react-query";
import { TestSession } from "@/types/api";
import { API_CONFIG } from "@/config/api";
import { AvailablePlatformTestsResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { BarChart3, CheckCircle, XCircle, Clock, ChevronDown, ChevronUp } from "lucide-react";
import { useLocation } from "wouter";

export default function TestHistory() {
  const [, navigate] = useLocation();
  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set());

  const formatTime = (seconds: number) => {
    if (!seconds || seconds <= 0) return "0:00";
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hrs > 0) return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (date: Date) => {
    const day = date.getDate().toString().padStart(2, '0');
    const month = date.toLocaleString('default', { month: 'short' });
    const year = date.getFullYear().toString().slice(-2);
    return `${day} ${month} ${year}`;
  };

  const toggleCard = (sessionId: number) => {
    setExpandedCards(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sessionId)) {
        newSet.delete(sessionId);
      } else {
        newSet.add(sessionId);
      }
      return newSet;
    });
  };

  const { data, isLoading, error } = useQuery<any, Error>({
    queryKey: [API_CONFIG.ENDPOINTS.TEST_SESSIONS],
  });

  // Fetch available platform tests once to map platformTest id -> testName
  const { data: platformData } = useQuery<AvailablePlatformTestsResponse | any>({
    queryKey: [API_CONFIG.ENDPOINTS.PLATFORM_TESTS_AVAILABLE],
    staleTime: 1000 * 60 * 5, // cache for 5 minutes
  });

  const platformNameMap = useMemo(() => {
    const m = new Map<number, string>();
    if (!platformData) return m;
    const scheduled = platformData.scheduledTests ?? platformData.results?.scheduledTests ?? [];
    const open = platformData.openTests ?? platformData.results?.openTests ?? [];
    const all = Array.isArray(scheduled) ? scheduled.concat(Array.isArray(open) ? open : []) : [];
    for (const p of all) {
      if (p && typeof p.id === 'number' && p.testName) m.set(p.id, p.testName);
    }
    return m;
  }, [platformData]);

  // Normalise paginated or plain-list responses
  const sessions: TestSession[] = useMemo(() => {
    if (!data) return [];
    if (Array.isArray(data)) return data as TestSession[];
    // runtime guards for common paginated shapes
    const anyData = data as any;
    if (anyData.results && Array.isArray(anyData.results)) return anyData.results as TestSession[];
    if (anyData.sessions && Array.isArray(anyData.sessions)) return anyData.sessions as TestSession[];
    return [];
  }, [data]);

  // Helper to detect completed sessions across possible API shapes
  const isCompletedSession = (s: any) => {
    return Boolean(
      s?.is_completed === true ||
      s?.isCompleted === true ||
      s?.status === 'completed' ||
      s?.completed === true ||
      s?.is_completed === 1
    );
  };

  // Only keep completed sessions for the history listing
  const filteredSessions = useMemo(() => {
    return sessions.filter(isCompletedSession);
  }, [sessions]);

  // For each session, fetch the authoritative results payload so counts match Results page
  const resultsQueries = useQueries({
    queries: filteredSessions.map((s) => ({
      queryKey: [API_CONFIG.ENDPOINTS.TEST_SESSION_RESULTS(s.id as number)],
      enabled: !!s.id,
    })),
  });

  return (
    <div className="min-h-screen bg-gray-100 py-2">
      <div className="container mx-auto max-w-6xl ">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-2 px-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">Test History</h1>
          </div>
        </div>

        <div>
          <div>
            {isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-6 w-1/3" />
                <Skeleton className="h-8" />
                <Skeleton className="h-8" />
                <Skeleton className="h-8" />
              </div>
            ) : error ? (
              <div className="text-red-600">Failed to load test history.</div>
            ) : sessions.length === 0 ? (
              <div className="py-12 text-center text-slate-600">
                No tests taken yet
              </div>
            ) : (
              <>
                {/* Mobile Card View */}
                <div className="block md:hidden space-y-2 ">
                  {filteredSessions.map((s, idx) => {
                    const r = resultsQueries[idx];
                    const payload = (r?.data ?? null) as any;
                    const correct = payload?.correct_answers ?? payload?.correctAnswers ?? s.correctAnswers ?? (s as any).correct_answers ?? 0;
                    const incorrect = payload?.incorrect_answers ?? payload?.incorrectAnswers ?? s.incorrectAnswers ?? (s as any).incorrect_answers ?? 0;
                    const unanswered = payload?.unanswered_questions ?? payload?.unansweredQuestions ?? (s as any).unanswered ?? s.unanswered ?? 0;
                    const timeSeconds = payload?.time_taken ?? payload?.timeTaken ?? (s as any).total_time_taken ?? (s as any).totalTimeTaken ?? 0;
                    const timeDisplay = formatTime(Number(timeSeconds) || 0);
                    const testName = (() => {
                      if (s.testType === 'platform') {
                        const name = s.platformTest ? platformNameMap.get(Number(s.platformTest)) : null;
                        return name ?? 'Platform Test';
                      }
                      return 'Practice Test';
                    })();
                    const date = new Date((s as any).startTime || (s as any).start_time || Date.now());
                    const formattedDate = formatDate(date);
                    const isExpanded = expandedCards.has(s.id as number);

                    return (
                      <Card key={s.id} className="bg-white rounded-xl shadow-md mx-4 overflow-hidden">
                        {/* Collapsed Header */}
                        <div
                          className="flex justify-between items-center p-3 cursor-pointer hover:bg-gray-50 transition-colors"
                          onClick={() => toggleCard(s.id as number)}
                        >
                          <div className="flex items-center space-x-3">
                            <h3 className="font-semibold text-slate-800">#{filteredSessions.length - idx}</h3>
                            <p className="text-sm text-slate-600">{testName}</p>
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className="text-sm text-slate-500">{formattedDate}</span>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="p-1 h-8 w-8"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleCard(s.id as number);
                              }}
                            >
                              {isExpanded ? (
                                <ChevronUp className="h-4 w-4" />
                              ) : (
                                <ChevronDown className="h-4 w-4" />
                              )}
                            </Button>
                          </div>
                        </div>

                        {/* Expanded Content */}
                        {isExpanded && (
                          <div className="px-3 pb-3 border-t border-gray-100">
                            <div className="space-y-1 mt-1">
                              <div className="flex justify-between items-center py-0.5 border-b">
                                <span className="text-sm text-slate-600">Total Questions</span>
                                <span className="text-sm font-semibold text-slate-800">{correct + incorrect + unanswered}</span>
                              </div>
                              <div className="flex justify-between items-center py-0.5 border-b">
                                <span className="text-sm text-slate-600">Attended Questions</span>
                                <span className="text-sm font-semibold text-slate-800">{correct + incorrect}</span>
                              </div>
                              <div className="flex justify-between items-center py-0.5 border-b">
                                <span className="text-sm text-slate-600">Correct Answer</span>
                                <span className="text-sm font-semibold text-green-600">{correct}</span>
                              </div>
                              <div className="flex justify-between items-center py-0.5 border-b">
                                <span className="text-sm text-slate-600">Incorrect Answer</span>
                                <span className="text-sm font-semibold text-red-600">{incorrect}</span>
                              </div>
                              <div className="flex justify-between items-center py-0.5 border-b">
                                <span className="text-sm text-slate-600">Total Time Taken</span>
                                <span className="text-sm font-semibold text-slate-800">{timeDisplay}</span>
                              </div>
                              <div className="flex justify-between items-center py-0.5">
                                <span className="text-sm text-slate-600">Total Percentage</span>
                                <span className="text-sm font-semibold text-blue-600">
                                  {correct + incorrect > 0 ? Math.round((correct / (correct + incorrect)) * 100) : 0}%
                                </span>
                              </div>
                              <div className="pt-2">
                                <Button
                                  onClick={() => navigate(`/results/${s.id}`)}
                                  variant="outline"
                                  className="w-full font-bold bg-blue-50 border-blue-200 text-blue-700"
                                >
                                  View more
                                </Button>
                              </div>

                            </div>
                          </div>
                        )}
                      </Card>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
