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
import { AlertCircle, Star, Edit3, BookOpen, Crown } from "lucide-react";
import SubscriptionRequiredModal from "@/components/SubscriptionRequiredModal";
import { APIError } from "@/lib/queryClient";

export default function Topics() {
  const [showQuickTest, setShowQuickTest] = useState(false);
  const [showQOD, setShowQOD] = useState(false);
  const [, navigate] = useLocation();
  const { isAuthenticated } = useAuth();

  // Swipe gesture detection for navigation (track both x and y)
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  const [touchEnd, setTouchEnd] = useState<{ x: number; y: number } | null>(null);

  // Minimum swipe distance (in px) to trigger navigation
  const minSwipeDistance = 50;

  const onTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart({ x: e.targetTouches[0].clientX, y: e.targetTouches[0].clientY });
  };

  const onTouchMove = (e: React.TouchEvent) => {
    setTouchEnd({ x: e.targetTouches[0].clientX, y: e.targetTouches[0].clientY });
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;

    const dx = touchStart.x - touchEnd.x;
    const dy = touchStart.y - touchEnd.y;

    // Only consider this a horizontal swipe if horizontal movement is dominant
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > minSwipeDistance) {
      const isLeftSwipe = dx > 0;
      const isRightSwipe = dx < 0;

      // Swipe left = go to Analysis (dashboard)
      if (isLeftSwipe) {
        navigate('/dashboard');
      }
      // Swipe right would go to previous tab, but Test is the first tab so ignore
    }
    // otherwise it was mostly vertical — ignore so normal scrolling works
  };

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

  // Find active tests - prioritize demo test first, then by earliest expires_at
  const activeTest = useMemo(() => {
    if (!platformTests) return null;
    const all = [
      ...(platformTests.scheduledTests ?? []),
      ...(platformTests.openTests ?? []),
    ];

    // Normalize all tests and filter available ones not completed
    const availableTests = [];
    for (const t of all) {
      if ((t as any).hasCompleted) continue;
      const test = {
        ...t,
        timeLimit: t.timeLimit ?? (t as any).duration ?? (t as any).time_limit ?? 0,
        totalQuestions: t.totalQuestions ?? (t as any).total_questions ?? 0,
        scheduledDateTime: t.scheduledDateTime ?? (t as any).scheduled_date_time ?? null,
        expiresAt: (t as any).expiresAt ?? (t as any).expires_at ?? null,
      };
      // Check if active or open
      const backendIsAvailable = (test as any).isAvailableNow ?? (test as any).is_available_now;
      if (backendIsAvailable === true) {
        availableTests.push(test);
        continue;
      }
      if (!test.scheduledDateTime) {
        availableTests.push(test); // open test
        continue;
      }
      // Manual availability check
      const now = new Date();
      const scheduled = new Date(test.scheduledDateTime);
      if (test.expiresAt) {
        const expires = new Date(test.expiresAt);
        if (now >= scheduled && now <= expires) availableTests.push(test);
      } else {
        // Fallback: use timeLimit if expires_at not set
        const endTime = new Date(scheduled.getTime() + (test.timeLimit * 60 * 1000));
        if (now >= scheduled && now <= endTime) availableTests.push(test);
      }
    }

    // If no available tests, return null
    if (availableTests.length === 0) return null;

    // PRIORITY 1: Check if any test is a demo test (name contains "demo")
    const demoTest = availableTests.find(test => {
      const testName = test.testName?.toLowerCase() || '';
      return /demo/i.test(testName);
    });
    
    // If demo test exists and is available, return it immediately
    if (demoTest) return demoTest;

    // PRIORITY 2: Sort remaining tests by expires_at (earliest expiring first)
    availableTests.sort((a, b) => {
      const aExpires = a.expiresAt ? new Date(a.expiresAt).getTime() : Infinity;
      const bExpires = b.expiresAt ? new Date(b.expiresAt).getTime() : Infinity;
      return aExpires - bExpires;
    });

    // Return the test that expires soonest
    return availableTests[0];
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
      style={{ backgroundImage: "url('/testpage-bg.webp')" }}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
    >
      {/* Page header */}
      <header className="sticky top-0 z-10 px-5 pt-5 pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center -mt-4">
            <img src="/NEET Bro.webp" alt="NEET Bro" className="h-[4.4rem] object-contain" />
          </div>
          <div className="flex items-center gap-3 -mt-2">
            {/* 
            <button
              onClick={() => navigate('/payment')}
              aria-label="Go to Payment"
              className="h-8 w-8 rounded-full flex items-center justify-center bg-blue-600 border-2 border-blue-900 shadow-sm"
            >
              <Crown className="h-5 w-5 text-white" />
            </button>
            */}
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
            icon={<Edit3 className="h-5 w-5 text-blue-600" />}
            title="Create Your Own Test"
            buttonLabel="Create"
            onClick={() => setShowQuickTest(true)}
          />
          <BottomCard
            icon={<BookOpen className="h-5 w-5 text-blue-600" />}
            title="Previous Year Papers"
            buttonLabel="View Papers"
            onClick={() => navigate('/pyqs')}
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
  // Truncate for preview: show start then '...' with no trailing text
  const preview = questionText
    ? questionText.length > 30
      ? questionText.slice(0, 30) + '...'
      : questionText
    : 'Test your knowledge daily!';

  return (
    <div className="relative">
      <Card
        onClick={onClick}
            className="rounded-2xl border cursor-pointer overflow-hidden bg-white/30 mt-1"
        style={{
          backgroundImage: "url('/s-penguin.webp')",
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'center',
          backgroundSize: 'cover',
          boxShadow: '0 8px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06)',
          border: '1px solid rgba(255,255,255,0.95)'
        }}
      >
        <CardContent className="p-4 flex items-center gap-3">
          {/* Left content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">⚠️</span>
              <h3 className="text-xl font-extrabold text-slate-800">Question of the Day</h3>
            </div>
            <p className="text-sm text-slate-700 leading-snug truncate whitespace-nowrap">{preview}</p>
            <Button
              size="sm"
              className="mt-3 bg-green-500 hover:bg-green-600 text-white text-xs font-bold rounded-full px-5 py-1 h-7"
            >
              Solve Now
            </Button>
          </div>

          {/* NOTE: Penguin and streak moved out into overlapping container below */}
        </CardContent>
      </Card>

      {/* Streak badge at bottom-right of the QOD card (removed penguin container) */}
      <div className="absolute bottom-3 right-3 z-20 pointer-events-auto">
        <div className="flex items-center gap-2 bg-white text-black text-xs font-bold rounded-full px-3 py-1 shadow-md">
          <span className="text-sm">🔥</span>
          <span className="text-sm">{streak ?? 0}</span>
          <span className="text-[10px] font-medium">Day Streak</span>
        </div>
      </div>
    </div>
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

  // Countdown timer for active test (uses expires_at as end time)
  const [timeLeft, setTimeLeft] = useState('');

  useEffect(() => {
    if (!activeTest) {
      setTimeLeft('');
      return;
    }

    // Get expires_at from backend (authoritative end time)
    const expiresAt = (activeTest as any).expiresAt ?? (activeTest as any).expires_at ?? null;
    
    if (!expiresAt) {
      // Fallback: if expires_at not set, calculate from scheduled + timeLimit
      if (!activeTest.scheduledDateTime) {
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
    }

    // Use expires_at as authoritative end time
    const endTime = new Date(expiresAt);

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
    const isDemoTest = (() => {
      const t: any = activeTest as any;
      if (t?.isDemo || t?.is_demo) return true;
      const name = (activeTest.testName || '') as string;
      return /demo/i.test(name);
    })();
    return (
      <>
        <Card
              onClick={handleStart}
              role="button"
              tabIndex={0}
              className="rounded-2xl border overflow-hidden bg-white/30 cursor-pointer"
                style={{ boxShadow: '0 8px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06)', border: '1px solid rgba(255,255,255,0.95)' }}
              >
          <CardContent className="p-5">
            <div className="flex items-start justify-between mb-1">
              <div>
                <h2 className="text-xl font-extrabold text-slate-800">{testName}</h2>
                <p className="text-sm text-slate-600 mt-0.5">
                  {activeTest.totalQuestions} Questions | {activeTest.timeLimit} Minutes
                </p>
              </div>
              {timeLeft && timeLeft !== 'Expired' && !isDemoTest && (
                <div className="text-right">
                  <p className="text-xs text-red-500 font-semibold">Closes in</p>
                  <p className="text-lg font-bold text-red-600">{timeLeft}</p>
                </div>
              )}
            </div>

            {/* Start test button */}
            <div className="w-full mt-4">
              <Button
                onClick={(e) => {
                  e.stopPropagation();
                  handleStart();
                }}
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
        <Card
           onClick={() => navigate(`/results/${s.id}`)}
           role="button"
           tabIndex={0}
           className="rounded-2xl border overflow-hidden bg-transparent cursor-pointer"
            style={{ boxShadow: '0 8px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06)', border: '1px solid rgba(255,255,255,0.95)' }}
        >
          <CardContent className="p-5">
          <h2 className="text-xl font-extrabold text-slate-800">{testName}</h2>
          <p className="text-sm text-slate-600 mt-0.5">
            {total} Questions · {s.timeLimit ?? s.time_limit ?? '—'} Minutes
          </p>

          <Button
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/results/${s.id}`);
            }}
            variant="outline"
            className="w-full mt-4 border-2 border-blue-600 text-blue-700 font-bold text-base py-3 rounded-full"
          >
            Review Mistakes
          </Button>

          {/* Performance stats */}
          <div className="grid grid-cols-3 gap-3 mt-4">
            <div className="text-center">
              <p className="text-xs text-slate-500 font-medium">Accuracy</p>
              <p className="text-2xl font-extrabold text-slate-800">{accuracy}%</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-500 font-medium">Score</p>
              <p className="text-2xl font-extrabold text-slate-800">{score}</p>
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
    <Card
      className="rounded-2xl border overflow-hidden bg-white/30"
      style={{ boxShadow: '0 8px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06)', border: '1px solid rgba(255,255,255,0.95)' }}
    >
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
  buttonLabel,
  onClick,
}: {
  icon: React.ReactNode;
  title: string;
  buttonLabel: string;
  onClick: () => void;
}) {
  return (
    <Card
      onClick={onClick}
      className="rounded-2xl border cursor-pointer overflow-hidden bg-white/30 mt-3"
      style={{ boxShadow: '0 8px 20px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.06)', border: '1px solid rgba(255,255,255,0.95)' }}
    >
      <CardContent className="p-4 flex flex-col h-full items-center -mb-2">
        <div className="w-16 h-16 rounded-full bg-white flex items-center justify-center shadow-sm mt-2 mb-3">
          {icon}
        </div>
        <h3 className="text-xl font-extrabold text-slate-800 leading-tight text-center">{title}</h3>
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