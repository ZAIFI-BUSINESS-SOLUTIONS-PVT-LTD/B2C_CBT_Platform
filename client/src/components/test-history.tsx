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
    <div className="px-4">
      <h2
        className="text-lg font-bold text-slate-900 sticky top-0 z-20 -mx-4 px-4 py-3 mb-2"
        style={{
          background: 'linear-gradient(180deg, rgba(234,249,255,1), rgba(221,244,255,0.95))',
          boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.6), 0 4px 12px rgba(0,0,0,0.06)',
          borderBottom: '1px solid rgba(255,255,255,0.6)',
          borderTopLeftRadius: '0.75rem',
          borderTopRightRadius: '0.75rem',
          backdropFilter: 'saturate(180%) blur(8px)',
        }}
      >
        Test History
      </h2>
      {isLoading ? (
        <div className="space-y-3 pt-2">
          <Skeleton className="h-6 w-1/3" />
          <Skeleton className="h-8" />
          <Skeleton className="h-8" />
          <Skeleton className="h-8" />
        </div>
      ) : error ? (
        <div className="text-red-600 pt-2">Failed to load test history.</div>
      ) : sessions.length === 0 ? (
        <div className="py-12 text-center text-slate-600">
          No tests taken yet
        </div>
      ) : (
        <>
          {/* Mobile Card View */}
          <div className="block space-y-2 pt-2">
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

                    // Robustly derive marks and max from multiple possible payload shapes
                    let marksObtained = (
                      payload?.marks ??
                      payload?.score ??
                      payload?.marks_obtained ??
                      payload?.total_marks_obtained ??
                      payload?.result?.marks ??
                      payload?.result?.score ??
                      payload?.test_info?.marks ??
                      payload?.test_info?.total_marks ??
                      0
                    );

                    let maxMarks = (
                      payload?.max_marks ??
                      payload?.maxMarks ??
                      payload?.total_marks ??
                      payload?.totalMarks ??
                      payload?.total_marks_possible ??
                      payload?.result?.max_marks ??
                      payload?.test_info?.max_marks ??
                      0
                    );

                    // If marks are not provided by API, compute using correct/incorrect (NEET scoring: +4 for correct, -1 for incorrect)
                    if ((!marksObtained || Number(marksObtained) === 0) && (correct || incorrect)) {
                      marksObtained = (Number(correct) * 4) - (Number(incorrect) * 1);
                    }

                    // Derive total questions and compute maxMarks if not present
                    const totalQuestions = (
                      payload?.total_questions ??
                      payload?.totalQuestions ??
                      s.totalQuestions ??
                      (s as any).total_questions ??
                      (correct + incorrect + unanswered)
                    );

                    if ((!maxMarks || Number(maxMarks) === 0) && totalQuestions) {
                      maxMarks = Number(totalQuestions) * 4; // assume +4 per question
                    }

                    // Derive accuracy using the same logic as Results page:
                    // Prefer percentage provided in payload.testInfo/test_info, then payload.percentage/accuracy,
                    // otherwise fall back to correctAnswers / totalQuestions.
                    const payloadTestInfo = payload?.testInfo ?? payload?.test_info ?? null;
                    const payloadPercentage = payloadTestInfo?.percentage ?? payloadTestInfo?.percentage ?? payload?.percentage ?? payload?.accuracy ?? null;
                    const accuracy = payloadPercentage != null
                      ? Math.round(Number(payloadPercentage))
                      : (Number(totalQuestions) > 0 ? Math.round((Number(correct) / Number(totalQuestions)) * 100) : (correct + incorrect > 0 ? Math.round((Number(correct) / (Number(correct) + Number(incorrect))) * 100) : 0));

                    return (
                      <Card
                        key={s.id} 
                        onClick={() => navigate(`/results/${s.id}`)}
                        className="bg-blue-50 rounded-2xl mx-4 overflow-visible"
                        style={{ boxShadow: '0 8px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06)', border: '1px solid rgba(219,234,254,0.9)' }}
                      >
                        <div className="px-3 pt-3 pb-2" style={{ fontSize: '0.8rem' }}>
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-3">
                                <div>
                                  <p className="text-sm font-semibold text-slate-800">{testName}</p>
                                  <p className="text-xs font-semibold text-slate-900 mt-0.5">{formattedDate}</p>
                                </div>
                              </div>
                            </div>

                            <div className="text-right">
                              <div className="text-lg font-semibold text-slate-900">{marksObtained} / {maxMarks || '—'}</div>
                            </div>
                          </div>

                          <div className="mt-0 flex items-center justify-end">
                            <Button 
                              onClick={() => navigate(`/results/${s.id}`)} 
                              variant="outline" 
                              size="sm"
                              className="border-blue-400 text-blue-700 font-bold text-xs rounded-full px-6 -mr-1"
                            >
                              View Analysis
                            </Button>
                          </div>
                        </div>
                      </Card>
                    );
            })}
          </div>
        </>
      )}
    </div>
  );
}
