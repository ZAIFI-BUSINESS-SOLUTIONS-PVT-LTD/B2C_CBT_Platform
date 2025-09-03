import { useMemo } from "react";
import { useQuery, useQueries } from "@tanstack/react-query";
import { TestSession } from "@/types/api";
import { API_CONFIG } from "@/config/api";
import { AvailablePlatformTestsResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { BarChart3, CheckCircle, XCircle, Clock } from "lucide-react";
import { useLocation } from "wouter";

export default function TestHistory() {
  const [, navigate] = useLocation();

  const formatTime = (seconds: number) => {
    if (!seconds || seconds <= 0) return "0:00";
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hrs > 0) return `${hrs}:${mins.toString().padStart(2,'0')}:${secs.toString().padStart(2,'0')}`;
    return `${mins}:${secs.toString().padStart(2,'0')}`;
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

  // For each session, fetch the authoritative results payload so counts match Results page
  const resultsQueries = useQueries({
    queries: sessions.map((s) => ({
      queryKey: [API_CONFIG.ENDPOINTS.TEST_SESSION_RESULTS(s.id as number)],
      enabled: !!s.id,
    })),
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 py-6">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900">Test History</h1>
            <p className="text-sm text-slate-500 mt-1">Your recent practice tests and quick access to detailed analytics.</p>
          </div>
          <div className="flex items-center space-x-3">
            <Badge className="text-sm">Total: {sessions.length}</Badge>
            <Button onClick={() => navigate('/dashboard')} className="px-3 py-2 text-sm bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg hover:shadow-xl"> 
              <BarChart3 className="h-4 w-4 mr-2 inline" /> Analytics
            </Button>
          </div>
        </div>

        <Card className="shadow-2xl rounded-2xl border border-[#E6EEF8]">
          <CardContent className="p-4">
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
              <div className="overflow-x-auto">
                <table className="w-full table-auto border-separate" style={{ borderSpacing: '0 10px' }}>
                  <thead>
                    <tr className="text-left text-sm text-slate-600">
                      <th className="py-3 px-4">Test Number</th>
                      <th className="py-3 px-4">Test Name</th>
                      <th className="py-3 px-4">Correct</th>
                      <th className="py-3 px-4">Incorrect</th>
                      <th className="py-3 px-4">Unanswered</th>
                      <th className="py-3 px-4">Time Taken</th>
                      <th className="py-3 px-4">Date</th>
                      <th className="py-3 px-4"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map((s, idx) => (
                      <tr
                        key={s.id}
                        className={`transform transition-all hover:shadow-md hover:-translate-y-0.5 bg-white rounded-lg`}
                      >
                        {/* Display sequential test number per-student where top row = latest test number */}
                        <td className="py-4 px-4 align-middle font-medium text-slate-800">#{sessions.length - idx}</td>
                        <td className="py-4 px-4 align-middle text-slate-700">
                          {(() => {
                            if (s.testType === 'platform') {
                              const name = s.platformTest ? platformNameMap.get(Number(s.platformTest)) : null;
                              return name ?? 'Platform Test';
                            }
                            return 'Practice Test';
                          })()}
                        </td>
                        {/* Use authoritative results when available */}
                        {(() => {
                          const r = resultsQueries[idx];
                          const payload = (r?.data ?? null) as any;
                          const correct = payload?.correct_answers ?? payload?.correctAnswers ?? s.correctAnswers ?? (s as any).correct_answers ?? 0;
                          const incorrect = payload?.incorrect_answers ?? payload?.incorrectAnswers ?? s.incorrectAnswers ?? (s as any).incorrect_answers ?? 0;
                          const unanswered = payload?.unanswered_questions ?? payload?.unansweredQuestions ?? (s as any).unanswered ?? s.unanswered ?? 0;
                          const timeSeconds = payload?.time_taken ?? payload?.timeTaken ?? (s as any).total_time_taken ?? (s as any).totalTimeTaken ?? 0;
                          const timeDisplay = formatTime(Number(timeSeconds) || 0);
                          return (
                            <>
                              <td className="py-4 px-4 align-middle"> 
                                <div className="inline-flex items-center space-x-2">
                                  <CheckCircle className="h-4 w-4 text-green-600" />
                                  <span className="text-slate-800 font-semibold">{correct}</span>
                                </div>
                              </td>
                              <td className="py-4 px-4 align-middle"> 
                                <div className="inline-flex items-center space-x-2">
                                  <XCircle className="h-4 w-4 text-rose-600" />
                                  <span className="text-slate-800 font-semibold">{incorrect}</span>
                                </div>
                              </td>
                              <td className="py-4 px-4 align-middle"> 
                                <div className="inline-flex items-center space-x-2">
                                  <Clock className="h-4 w-4 text-amber-500" />
                                  <span className="text-slate-800 font-semibold">{unanswered}</span>
                                </div>
                              </td>
                              <td className="py-4 px-4 align-middle text-sm text-slate-700">{timeDisplay}</td>
                            </>
                          );
                        })()}
                        <td className="py-4 px-4 align-middle text-sm text-slate-600">{new Date((s as any).startTime || (s as any).start_time || Date.now()).toLocaleString()}</td>
                        <td className="py-4 px-4 align-middle text-right">
                          <div className="flex items-center justify-end">
                            <Button
                              onClick={() => navigate(`/results/${s.id}`)}
                              className="px-4 py-2 text-sm bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow hover:shadow-xl rounded-lg"
                            >
                              View Details
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
