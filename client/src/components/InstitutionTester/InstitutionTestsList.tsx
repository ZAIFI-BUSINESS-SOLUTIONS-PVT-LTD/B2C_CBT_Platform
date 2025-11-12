import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, BookOpen, Clock, FileQuestion, AlertCircle, Play } from 'lucide-react';
import { useLocation } from 'wouter';
import { getAccessToken, authenticatedFetch } from '@/lib/auth';

interface Institution {
  id: number;
  name: string;
  code: string;
  exam_types?: string[]; // optional because some payloads may omit this
}

interface InstitutionTest {
  id: number;
  test_name: string;
  test_code: string;
  exam_type: string;
  total_questions: number;
  time_limit: number;
  instructions: string;
  description: string;
  created_at: string;
  scheduled_date_time?: string | null; // optional - fetch from platform test details when available
}

interface InstitutionTestsListProps {
  institution: Institution;
  onBack: () => void;
}

export function InstitutionTestsList({ institution, onBack }: InstitutionTestsListProps) {
  // Normalize exam types to a stable array so TypeScript can reason about length/map safely
  const examTypes: string[] = institution.exam_types ?? ['neet'];
  const [selectedExamType, setSelectedExamType] = useState<string>(examTypes[0]);
  const [tests, setTests] = useState<InstitutionTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [, setLocation] = useLocation();

  useEffect(() => {
    fetchTests();
  }, [selectedExamType, institution.id]);

  // After loading tests, fetch per-test details to obtain scheduled_date_time when present
  useEffect(() => {
    if (!tests || tests.length === 0) return;

    let mounted = true;

    const fetchDetailsForTests = async () => {
      const toFetch = tests.filter((t) => !t.scheduled_date_time).map((t) => t.id);
      if (toFetch.length === 0) return;

      try {
        const promises = toFetch.map((id) =>
          authenticatedFetch(`/api/platform-tests/${id}/`).then(async (res) => {
            if (!res.ok) return null;
            return res.json();
          }).catch(() => null)
        );

        const results = await Promise.allSettled(promises);

        if (!mounted) return;

        const updated = [...tests];
        results.forEach((r, idx) => {
          if (r.status === 'fulfilled' && r.value) {
            // Support both snake_case and camelCase keys from backend
            const remoteScheduled = r.value.scheduled_date_time ?? r.value.scheduledDateTime ?? null;
            if (typeof remoteScheduled === 'string' && remoteScheduled) {
              const testId = toFetch[idx];
              const i = updated.findIndex((x) => x.id === testId);
              if (i >= 0) {
                updated[i] = { ...updated[i], scheduled_date_time: remoteScheduled };
              }
            }
          }
        });

        setTests(updated);
      } catch (e) {
        // Non-fatal; scheduled time is optional
        console.debug('Failed to fetch platform test details for scheduled times', e);
      }
    };

    fetchDetailsForTests();
    return () => { mounted = false; };
  }, [tests]);

  // Helper: determine test status from scheduled_date_time and time_limit
  const getTestStatus = (test: InstitutionTest) => {
    if (!test.scheduled_date_time) return 'open';

    const scheduledMs = Date.parse(test.scheduled_date_time as string);
    if (isNaN(scheduledMs)) return 'open';

    const nowMs = Date.now();
    const timeLimitMin = typeof test.time_limit === 'number' ? test.time_limit : Number(test.time_limit) || 0;
    const testEndMs = scheduledMs + (timeLimitMin * 60 * 1000);

    if (nowMs < scheduledMs) return 'upcoming';
    if (nowMs >= scheduledMs && (timeLimitMin <= 0 || nowMs <= testEndMs)) return 'active';
    return 'expired';
  };

  const isTestAvailable = (test: InstitutionTest) => {
    // If no scheduled time, treat as open
    if (!test.scheduled_date_time) return true;

    const scheduledMs = Date.parse(test.scheduled_date_time as string);
    if (isNaN(scheduledMs)) return true;

    const nowMs = Date.now();
    // if scheduled time has arrived or passed, allow start (but respect expiry)
    const timeLimitMin = typeof test.time_limit === 'number' ? test.time_limit : Number(test.time_limit) || 0;
    const testEndMs = scheduledMs + (timeLimitMin * 60 * 1000);

    if (nowMs < scheduledMs) return false; // not started yet
    if (timeLimitMin > 0 && nowMs > testEndMs) return false; // expired
    return true; // active or no expiry configured
  };

  // Countdown timer component (same behavior as ScheduledTests page)
  const Countdown = ({ scheduledDateTime }: { scheduledDateTime: string }) => {
    const [remainingMs, setRemainingMs] = useState<number>(() => {
      const now = new Date().getTime();
      const target = new Date(scheduledDateTime).getTime();
      return Math.max(0, target - now);
    });

    useEffect(() => {
      const tick = () => {
        const now = new Date().getTime();
        const target = new Date(scheduledDateTime).getTime();
        setRemainingMs(Math.max(0, target - now));
      };

      tick();
      const id = setInterval(tick, 1000);
      return () => clearInterval(id);
    }, [scheduledDateTime]);

    if (remainingMs <= 0) return <span className="text-sm text-green-600">Available now</span>;

    const totalSeconds = Math.floor(remainingMs / 1000);
    const days = Math.floor(totalSeconds / (24 * 3600));
    const hours = Math.floor((totalSeconds % (24 * 3600)) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    const pad = (n: number) => n.toString().padStart(2, '0');

    let label = '';
    if (days > 0) {
      label = `${days}d ${pad(hours)}:${pad(minutes)}`;
    } else if (hours > 0) {
      label = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    } else {
      label = `${pad(minutes)}:${pad(seconds)}`;
    }

    return <span className="text-sm text-gray-700">Test will be available in {label}</span>;
  };

  const fetchTests = async () => {
    setLoading(true);
    setError(null);

    try {
      // Use authenticatedFetch which handles token refresh
      const response = await authenticatedFetch(`/api/institutions/${institution.id}/tests/?exam_type=${selectedExamType}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Failed to fetch tests');
      }

  // Use scheduled_date_time from API when provided. Do not overwrite with a hard-coded value.
  // The backend may return scheduled_date_time as an ISO string (or null).
  // Normalize response keys to snake_case used throughout this component.
  const normalize = (t: any) => ({
    id: t.id,
    test_name: t.test_name ?? t.testName ?? t.testName ?? t.test_name ?? '',
    test_code: t.test_code ?? t.testCode ?? '',
    exam_type: t.exam_type ?? t.examType ?? t.exam_type ?? selectedExamType,
    total_questions: t.total_questions ?? t.totalQuestions ?? t.total_questions ?? 0,
    time_limit: t.time_limit ?? t.timeLimit ?? t.time_limit ?? 0,
    instructions: t.instructions ?? t.instructions ?? '',
    description: t.description ?? t.description ?? '',
    created_at: t.created_at ?? t.createdAt ?? t.created_at ?? null,
    // scheduled_date_time may come as camelCase (scheduledDateTime) from DRF camel-case renderer
    scheduled_date_time: t.scheduled_date_time ?? t.scheduledDateTime ?? null,
    // preserve any other keys so we don't drop unexpected data
    ...t
  });

  const mapped = (data.tests || []).map((t: any) => normalize(t));
  setTests(mapped);
    } catch (err: any) {
      setError(err.message || 'An error occurred while fetching tests');
    } finally {
      setLoading(false);
    }
  };

  const handleStartTest = async (testId: number) => {
    try {
      // Start test using authenticatedFetch to handle token refresh automatically
      const response = await authenticatedFetch(`/api/platform-tests/${testId}/start/`, { method: 'POST' } as RequestInit);
      const data = await response.json();

      if (!response.ok) {
        // Backend returns standardized AppError shape: { error: { code, message, details } }
        const errCode = data?.error?.code || data?.error;
        const errDetails = data?.error?.details || data?.details;
        if (errDetails?.institution_code_required) {
          throw new Error('Please verify your institution code before starting this test');
        }
        throw new Error(data?.error?.message || data?.message || 'Failed to start test');
      }

      // DEBUG: log response from start endpoint
      console.debug('start test response', data);

      // Navigate to test taking screen with session ID
      const sid = data?.session_id || data?.session?.id || data?.session?.session_id;
      if (sid) {
        // Use wouter navigation setter (app uses Wouter router)
        setLocation(`/test/${sid}`);
      } else {
        console.warn('No session id returned from start endpoint', data);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to start test');
    }
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{institution.name}</h2>
          <p className="text-sm text-muted-foreground">Institution Tests</p>
        </div>
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
      </div>

  {examTypes.length > 1 && (
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium">Select Exam:</label>
          <Select value={selectedExamType} onValueChange={setSelectedExamType}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {examTypes.map((exam) => (
                <SelectItem key={exam} value={exam}>
                  {exam.toUpperCase()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : tests.length === 0 ? (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No tests available for {selectedExamType.toUpperCase()} at this time.
          </AlertDescription>
        </Alert>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {tests.map((test) => (
            <Card key={test.id} className="flex flex-col">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <Badge variant="secondary" className="mb-2">
                    {test.exam_type.toUpperCase()}
                  </Badge>
                </div>
                <CardTitle className="line-clamp-2">{test.test_name}</CardTitle>
                {test.description && (
                  <CardDescription className="line-clamp-2">
                    {test.description}
                  </CardDescription>
                )}
              </CardHeader>
              
              <CardContent className="flex-1 space-y-3">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <FileQuestion className="h-4 w-4" />
                  <span>{test.total_questions} Questions</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>{formatDuration(test.time_limit)}</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <BookOpen className="h-4 w-4" />
                  <span className="text-xs">{test.test_code}</span>
                </div>
              </CardContent>

              {test.scheduled_date_time && (
                <div className="px-4">
                  <div className="text-sm text-gray-600">{new Date(test.scheduled_date_time).toLocaleString()}</div>
                  {getTestStatus(test) === 'upcoming' && (
                    <div className="mt-1">
                      <Countdown scheduledDateTime={test.scheduled_date_time} />
                    </div>
                  )}
                </div>
              )}

              <CardFooter>
                <Button
                  className="w-full"
                  onClick={() => handleStartTest(test.id)}
                  disabled={!isTestAvailable(test)}
                >
                  <Play className="mr-2 h-4 w-4" />
                  {isTestAvailable(test) ? 'Start Test' : (getTestStatus(test) === 'upcoming' ? 'Not Started Yet' : 'Test Expired')}
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
