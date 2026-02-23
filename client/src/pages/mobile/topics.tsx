/** Topics page — redesigned test selection interface matching NEET Bro theme. */

import { useQuery } from "@tanstack/react-query";
import MobileDock from "@/components/mobile-dock";
import { PlatformTest, AvailablePlatformTestsResponse, TestSession } from "@/types/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLocation } from "wouter";
import { useState, useEffect, useMemo } from "react";
import QuickTestWizard from "@/components/quick-test-wizard";
import { StudentProfile } from "@/components/profile-avatar";
import QuestionOfTheDayModal from "@/components/QuestionOfTheDayModal";
import { getAvailablePlatformTests, startPlatformTest } from "@/config/api";
import { API_CONFIG } from "@/config/api";
import { authenticatedFetch } from "@/lib/auth";
import { useAuth } from "@/contexts/AuthContext";
import { AlertCircle, Star } from "lucide-react";
import SubscriptionRequiredModal from "@/components/SubscriptionRequiredModal";
import { APIError } from "@/lib/queryClient";

export default function Topics() {
  const [showQuickTest, setShowQuickTest] = useState(false);
  const [showQOD, setShowQOD] = useState(false);
  const [, navigate] = useLocation();
  const { isAuthenticated } = useAuth();

  // Fetch QOD data for streak display
  const { data: qodData } = useQuery<any>({
    queryKey: ['question-of-the-day'],
    queryFn: async () => {
      const response = await authenticatedFetch(`${API_CONFIG.BASE_URL}/api/qod/`);
      if (!response.ok) return null;
      return response.json();
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  // Fetch available platform tests
  const { data: platformTests } = useQuery<AvailablePlatformTestsResponse>({
    queryKey: [API_CONFIG.ENDPOINTS.PLATFORM_TESTS_AVAILABLE],
    queryFn: () => getAvailablePlatformTests(),
    enabled: isAuthenticated,
    refetchInterval: 60000,
  });

  // Fetch test sessions for last performance fallback
  const { data: sessionsData } = useQuery<any>({
    queryKey: [API_CONFIG.ENDPOINTS.TEST_SESSIONS],
    enabled: isAuthenticated,
  });

  const streak = qodData?.streak ?? 0;

  // Find the first active/open test that student hasn't completed
  const activeTest = useMemo(() => {
    if (!platformTests) return null;
    const all = [
      ...(platformTests.scheduledTests ?? []),
      ...(platformTests.openTests ?? []),
    ];

    // Normalize and find first available test not completed
    for (const t of all) {
      if ((t as any).hasCompleted) continue;
      const test = {
        ...t,
        timeLimit: t.timeLimit ?? (t as any).duration ?? (t as any).time_limit ?? 0,
        totalQuestions: t.totalQuestions ?? (t as any).total_questions ?? 0,
        scheduledDateTime: t.scheduledDateTime ?? (t as any).scheduled_date_time ?? null,
      };
      // Check if active or open
      const backendIsAvailable = (test as any).isAvailableNow ?? (test as any).is_available_now;
      if (backendIsAvailable === true) return test;
      if (!test.scheduledDateTime) return test; // open test
      const now = new Date();
      const scheduled = new Date(test.scheduledDateTime);
      const endTime = new Date(scheduled.getTime() + (test.timeLimit * 60 * 1000));
      if (now >= scheduled && now <= endTime) return test;
    }
    return null;
  }, [platformTests]);

  // Get last completed session for performance fallback
  const lastCompletedSession = useMemo(() => {
    if (!sessionsData) return null;
    const sessions: TestSession[] = Array.isArray(sessionsData)
      ? sessionsData
      : sessionsData?.results ?? sessionsData?.sessions ?? [];

    const completed = sessions.filter((s: any) =>
      s?.is_completed === true || s?.isCompleted === true || s?.status === 'completed'
    );
    if (completed.length === 0) return null;
    // Sort by start time descending and take the first
    return completed.sort((a: any, b: any) => {
      const ta = new Date(a.startTime || a.start_time || 0).getTime();
      const tb = new Date(b.startTime || b.start_time || 0).getTime();
      return tb - ta;
    })[0];
  }, [sessionsData]);

  // Fetch results for the last completed session
  const lastSessionId = (lastCompletedSession as any)?.id;
  const { data: lastResults } = useQuery<any>({
    queryKey: [`/api/test-sessions/${lastSessionId}/results/`],
    enabled: !!lastSessionId && !activeTest,
  });

  // Platform test name map
  const platformNameMap = useMemo(() => {
    const m = new Map<number, string>();
    if (!platformTests) return m;
    for (const p of [...(platformTests.scheduledTests ?? []), ...(platformTests.openTests ?? [])]) {
      if (p && typeof p.id === 'number' && p.testName) m.set(p.id, p.testName);
    }
    return m;
  }, [platformTests]);

  return (
    <div
      className="min-h-screen bg-cover bg-center bg-no-repeat bg-fixed pb-20"
      style={{ backgroundImage: "url('/testpage-bg.png')" }}
    >
      {/* Page header */}
      <header className="sticky top-0 z-10 px-5 pt-5 pb-3">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">NEET Bro</h1>
          <div className="flex items-center gap-3">
            <StudentProfile avatarClassName="h-8 w-8" />
          </div>
        </div>
      </header>

      <div className="px-4 space-y-4">
        {/* ──── 1. Question of the Day Card ──── */}
        <QODCard
          streak={streak}
          qodData={qodData}
          onClick={() => setShowQOD(true)}
        />

        {/* ──── 2. Center Card: Active Test OR Last Performance ──── */}
        <div className="mt-6">
          <CenterTestCard
            activeTest={activeTest}
            lastSession={lastCompletedSession}
            lastResults={lastResults}
            platformNameMap={platformNameMap}
          />
        </div>

        {/* ──── 3. Bottom: Create Test + Previous Year Papers ──── */}
        <div className="grid grid-cols-2 gap-3 mt-6">
          <BottomCard
            icon="🎯"
            title="Create Your Own Test"
            subtitle="Choose chapters, number of questions and time"
            buttonLabel="Create"
            onClick={() => setShowQuickTest(true)}
          />
          <BottomCard
            icon="📋"
            title="Previous Year Papers"
            subtitle="Practice real NEET question papers"
            buttonLabel="View Papers"
            onClick={() => {/* PYQs route – TODO */}}
          />
        </div>
      </div>

      <MobileDock />

      {/* Modals */}
      {showQuickTest && (
        <QuickTestWizard onClose={() => setShowQuickTest(false)} />
      )}
      <QuestionOfTheDayModal isOpen={showQOD} onClose={() => setShowQOD(false)} />
    </div>
  );
}


/* ──────────────────────────────────────────────
   Question of the Day card
   ────────────────────────────────────────────── */
function QODCard({ streak, qodData, onClick }: { streak: number; qodData: any; onClick: () => void }) {
  const questionText = qodData?.qod?.questionData?.question;
  // Truncate for preview
  const preview = questionText
    ? questionText.length > 60 ? questionText.slice(0, 60) + '…' : questionText
    : 'Test your knowledge daily!';

  return (
    <Card
      onClick={onClick}
      className="rounded-2xl border-0 cursor-pointer overflow-hidden shadow-md bg-white/40 backdrop-blur-md"
    >
      <CardContent className="p-4 flex items-center gap-3">
        {/* Left content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">⚠️</span>
            <h3 className="text-base font-bold text-slate-800">Question of the Day</h3>
          </div>
          <p className="text-xs text-slate-600 mb-2">Solve:</p>
          <p className="text-sm text-slate-700 leading-snug truncate">{preview}</p>
          <Button
            size="sm"
            className="mt-3 bg-green-500 hover:bg-green-600 text-white text-xs font-bold rounded-full px-5 py-1 h-7"
          >
            Solve Now
          </Button>
        </div>

        {/* Right: Penguin + Streak */}
        <div className="flex-shrink-0 flex flex-col items-center">
          <img
            src="/streak-penguin.png"
            alt="Penguin mascot"
            className="object-contain"
            style={{ width: '6.5rem', height: '6.5rem' }}
          />
          {streak > 0 && (
            <div className="flex items-center gap-1 bg-white text-black text-xs font-bold rounded-full px-3 py-1 -mt-1 shadow-md">
              <span className="text-sm">🔥</span>
              <span>{streak}</span>
              <span className="text-[10px] font-medium">Day Streak</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}


/* ──────────────────────────────────────────────
   Center card: Active Test  /  Last Performance
   ────────────────────────────────────────────── */
function CenterTestCard({
  activeTest,
  lastSession,
  lastResults,
  platformNameMap,
}: {
  activeTest: PlatformTest | null;
  lastSession: TestSession | null;
  lastResults: any;
  platformNameMap: Map<number, string>;
}) {
  const [, navigate] = useLocation();
  const [startingTest, setStartingTest] = useState(false);
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false);
  const [subscriptionMessage, setSubscriptionMessage] = useState('');

  // Countdown timer for active test
  const [timeLeft, setTimeLeft] = useState('');

  useEffect(() => {
    if (!activeTest?.scheduledDateTime) {
      setTimeLeft('');
      return;
    }
    const endTime = new Date(
      new Date(activeTest.scheduledDateTime).getTime() + (activeTest.timeLimit ?? 0) * 60 * 1000
    );

    const tick = () => {
      const diff = endTime.getTime() - Date.now();
      if (diff <= 0) {
        setTimeLeft('Expired');
        return;
      }
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      setTimeLeft(`${h}h ${m.toString().padStart(2, '0')}m`);
    };
    tick();
    const id = setInterval(tick, 30000);
    return () => clearInterval(id);
  }, [activeTest]);

  const handleStart = async () => {
    if (!activeTest) return;
    try {
      setStartingTest(true);
      const response = await (startPlatformTest as any)({ testId: activeTest.id });
      navigate(`/test/${response.session.id}`);
    } catch (err: any) {
      const maybeDetails = err?.details || err?.error?.details || err?.response?.data?.details;
      if (maybeDetails?.requires_subscription || maybeDetails?.requiresSubscription) {
        setSubscriptionMessage(err?.message || 'Active subscription required.');
        setShowSubscriptionModal(true);
        return;
      }
      if (err instanceof APIError && err.status === 409 && err.details?.sessionId) {
        navigate(`/test/${err.details.sessionId}`);
        return;
      }
    } finally {
      setStartingTest(false);
    }
  };

  // ─── Active test card ───
  if (activeTest) {
    const testName = activeTest.testName || 'Platform Test';
    return (
      <>
        <Card className="rounded-2xl border-0 shadow-md bg-white/40 backdrop-blur-md overflow-hidden mt-8">
          <CardContent className="p-5">
            <div className="flex items-start justify-between mb-1">
              <div>
                <h2 className="text-xl font-extrabold text-slate-800">{testName}</h2>
                <p className="text-sm text-slate-600 mt-0.5">
                  {activeTest.totalQuestions} Questions · {activeTest.timeLimit} Minutes
                </p>
              </div>
              {timeLeft && timeLeft !== 'Expired' && (
                <div className="text-right">
                  <p className="text-xs text-red-500 font-semibold">Closes in</p>
                  <p className="text-lg font-bold text-red-600">{timeLeft}</p>
                </div>
              )}
            </div>

            {/* Start test button */}
            <div className="w-full mt-4">
              <Button
                onClick={handleStart}
                disabled={startingTest}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-bold text-base py-3 rounded-xl flex items-center justify-center gap-2"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>
                </svg>
                {startingTest ? 'Starting...' : 'Start Test'}
              </Button>
            </div>

            {activeTest.description && (
              <p className="text-xs text-center text-slate-500 mt-2">{activeTest.description}</p>
            )}
          </CardContent>
        </Card>
        {showSubscriptionModal && (
          <SubscriptionRequiredModal
            open={showSubscriptionModal}
            onOpenChange={(v) => setShowSubscriptionModal(v)}
            message={subscriptionMessage}
          />
        )}
      </>
    );
  }

  // ─── Fallback: Last completed test performance ───
  if (lastSession) {
    const s = lastSession as any;
    const correct = lastResults?.correct_answers ?? lastResults?.correctAnswers ?? s.correctAnswers ?? s.correct_answers ?? 0;
    const incorrect = lastResults?.incorrect_answers ?? lastResults?.incorrectAnswers ?? s.incorrectAnswers ?? s.incorrect_answers ?? 0;
    const total = correct + incorrect + (lastResults?.unanswered_questions ?? lastResults?.unansweredQuestions ?? s.unanswered ?? 0);
    const accuracy = total > 0 ? Math.round((correct / total) * 100) : 0;
    const timeSeconds = lastResults?.time_taken ?? lastResults?.timeTaken ?? s.total_time_taken ?? s.totalTimeTaken ?? 0;
    const timeMins = Math.round(Number(timeSeconds) / 60);
    // NEET scoring: +4 correct, -1 incorrect
    const score = correct * 4 - incorrect * 1;

    const testName = (() => {
      if (s.testType === 'platform' || s.test_type === 'platform') {
        const pId = s.platformTest || s.platform_test;
        return pId ? (platformNameMap.get(Number(pId)) ?? 'Platform Test') : 'Platform Test';
      }
      return 'Practice Test';
    })();

    return (
      <Card className="rounded-2xl border-0 shadow-lg bg-white/70 backdrop-blur-md overflow-hidden">
        <CardContent className="p-5">
          <h2 className="text-xl font-extrabold text-slate-800">{testName}</h2>
          <p className="text-sm text-slate-600 mt-0.5">
            {total} Questions · {s.timeLimit ?? s.time_limit ?? '—'} Minutes
          </p>

          <Button
            onClick={() => navigate(`/results/${s.id}`)}
            variant="outline"
            className="w-full mt-4 border-2 border-blue-600 text-blue-700 font-bold text-base py-3 rounded-full"
          >
            Review Mistakes
          </Button>

          {/* Performance stats */}
          <div className="grid grid-cols-3 gap-3 mt-4">
            <div className="text-center">
              <p className="text-xs text-slate-500 font-medium">Score</p>
              <p className="text-2xl font-extrabold text-slate-800">{score}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-500 font-medium">Accuracy</p>
              <p className="text-2xl font-extrabold text-slate-800">{accuracy}%</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-500 font-medium">Time</p>
              <p className="text-2xl font-extrabold text-slate-800">{timeMins} min</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // ─── No data at all ───
  return (
    <Card className="rounded-2xl border-0 shadow-md bg-white/40 backdrop-blur-md overflow-hidden">
      <CardContent className="p-6 text-center">
        <p className="text-slate-600 text-sm">No tests available yet. Check back soon!</p>
      </CardContent>
    </Card>
  );
}


/* ──────────────────────────────────────────────
   Bottom cards (Create Test / PYQs)
   ────────────────────────────────────────────── */
function BottomCard({
  icon,
  title,
  subtitle,
  buttonLabel,
  onClick,
}: {
  icon: string;
  title: string;
  subtitle: string;
  buttonLabel: string;
  onClick: () => void;
}) {
  return (
    <Card
      onClick={onClick}
      className="rounded-2xl border-0 shadow-md bg-white/40 backdrop-blur-md cursor-pointer overflow-hidden mt-8"
    >
      <CardContent className="p-4 flex flex-col h-full">
        <h3 className="text-sm font-bold text-slate-800 leading-tight">{title}</h3>
        <p className="text-[11px] text-slate-500 mt-1 flex-1">{subtitle}</p>
        <Button
          size="sm"
          variant="outline"
          className="mt-3 border-blue-400 text-blue-700 font-bold text-xs rounded-full w-full"
        >
          {buttonLabel}
        </Button>
      </CardContent>
    </Card>
  );
}