import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { TestSession } from "@/types/api";
import { API_CONFIG } from "@/config/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Clock, Target } from "lucide-react";
import { useLocation } from "wouter";

export default function LatestTestSummary() {
  const [, navigate] = useLocation();

  const { data, isLoading } = useQuery<any, Error>({
    queryKey: [API_CONFIG.ENDPOINTS.TEST_SESSIONS],
  });

  // Normalise paginated or plain-list responses
  const sessions: TestSession[] = useMemo(() => {
    if (!data) return [];
    if (Array.isArray(data)) return data as TestSession[];
    const anyData = data as any;
    if (anyData.results && Array.isArray(anyData.results)) return anyData.results as TestSession[];
    if (anyData.sessions && Array.isArray(anyData.sessions)) return anyData.sessions as TestSession[];
    return [];
  }, [data]);

  // Helper to detect completed sessions
  const isCompletedSession = (s: any) => {
    return Boolean(
      s?.is_completed === true ||
      s?.isCompleted === true ||
      s?.status === 'completed' ||
      s?.completed === true ||
      s?.is_completed === 1
    );
  };

  // Get latest completed session
  const latestSession = useMemo(() => {
    const completed = sessions.filter(isCompletedSession);
    return completed.length > 0 ? completed[0] : null;
  }, [sessions]);

  // Fetch results for latest session
  const { data: resultsData } = useQuery<any>({
    queryKey: [API_CONFIG.ENDPOINTS.TEST_SESSION_RESULTS(latestSession?.id as number)],
    enabled: !!latestSession?.id,
  });

  if (isLoading || !latestSession || !resultsData) {
    return null;
  }

  const s = latestSession as any;
  const payload = resultsData;
  
  const correct = payload?.correct_answers ?? payload?.correctAnswers ?? s.correctAnswers ?? s.correct_answers ?? 0;
  const incorrect = payload?.incorrect_answers ?? payload?.incorrectAnswers ?? s.incorrectAnswers ?? s.incorrect_answers ?? 0;
  const unanswered = payload?.unanswered_questions ?? payload?.unansweredQuestions ?? s.unanswered ?? 0;

  // Compute marks using NEET scoring
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

  if ((!marksObtained || Number(marksObtained) === 0) && (correct || incorrect)) {
    marksObtained = (Number(correct) * 4) - (Number(incorrect) * 1);
  }

  const totalQuestions = (
    payload?.total_questions ??
    payload?.totalQuestions ??
    s.totalQuestions ??
    s.total_questions ??
    (correct + incorrect + unanswered)
  );

  if ((!maxMarks || Number(maxMarks) === 0) && totalQuestions) {
    maxMarks = Number(totalQuestions) * 4;
  }

  const attempted = correct + incorrect;
  const accuracy = totalQuestions > 0 ? Math.round((correct / totalQuestions) * 100) : 0;

  return (
    <Card 
      onClick={() => navigate(`/results/${latestSession.id}`)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') navigate(`/results/${latestSession.id}`); }}
      className="bg-transparent rounded-2xl w-full overflow-visible -mt-3 cursor-pointer"
    >
      <CardContent className="p-3">
        <div
          className="flex items-center justify-between mb-4"
          style={{
            backgroundImage: "url('/mark-bg.webp')",
            backgroundRepeat: 'no-repeat',
            backgroundPosition: 'center',
            backgroundSize: 'cover',
            padding: '18px',
            borderRadius: '12px'
          }}
        >
          {/* Left: Attempted */}
          <div
            className="flex flex-col items-center -ml-2 -mt-5"
            style={{
              backgroundImage: "url('/clock.webp')",
              backgroundRepeat: 'no-repeat',
              backgroundPosition: 'center 6px',
              backgroundSize: '50px',
              paddingTop: '150px'
            }}
          >
            <div className="text-2xl font-bold text-gray-800 -mt-14">
              {attempted}
              <span className="text-lg text-gray-800">/{totalQuestions}</span>
            </div>
            <div className="text-xs text-gray-600 -mt-2">Attempted</div>
          </div>

          {/* Center: Penguin with Marks (uses decorative background) */}
          <div
            className="flex flex-col items-center flex-1 mx-4 pt-28 bg-no-repeat bg-center -mt-16"
            style={{ backgroundImage: "url('/score.webp')", backgroundRepeat: 'no-repeat', backgroundPosition: 'center 6px', backgroundSize: '220px' }}
          >
            <div className="text-3xl font-bold text-white mt-12">
              {marksObtained}
              <span className="text-xl text-white/90">/{maxMarks}</span>
            </div>
          </div>

          {/* Right: Accuracy */}
          <div
            className="flex flex-col items-center -mr-1 -mt-8"
            style={{
              backgroundImage: "url('/target.webp')",
              backgroundRepeat: 'no-repeat',
              backgroundPosition: 'center 6px',
              backgroundSize: '60px',
              paddingTop: '100px'
            }}
          >
            <div className="text-2xl font-bold text-gray-800 -mt-1">{accuracy}%</div>
            <div className="text-xs text-gray-600 -mt-2">Accuracy</div>
          </div>
        </div>

        {/* Bottom label: clickable hint for latest performance */}
        <div className="mt-2 text-center text-sm text-gray-500 font-medium">Your latest test performance</div>
      </CardContent>
    </Card>
  );
}
