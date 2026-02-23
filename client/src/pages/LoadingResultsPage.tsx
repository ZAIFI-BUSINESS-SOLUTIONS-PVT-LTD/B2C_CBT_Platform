import { useEffect, useState } from "react";
import { useLocation, useRoute } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "@/lib/auth";
import { API_CONFIG } from "@/config/api";
import LoadingVideo from "@/components/LoadingVideo";

/**
 * Loading Results Page
 *
 * Flow
 * ────
 * 1. Loading video loops while the backend generates zone insights.
 * 2. Poll `/api/zone-insights/status/<id>/` every 1.5 s.
 * 3. "Ready" means the TestSubjectZoneInsight row for this session has been
 *    written with populated subject_data (mark, accuracy, time_spend, total_mark,
 *    subject_data all present) → backend signals this via `all_subjects_complete`.
 * 4. Once ready, let the current video loop play to its natural end.
 * 5. After the video ends → redirect to /dashboard.
 * 6. Hard fallback: redirect after 60 s regardless (in case pipeline is slow).
 */
export default function LoadingResultsPage() {
  const [, navigate] = useLocation();
  const [, params] = useRoute("/loading-results/:sessionId");
  const sessionId = params?.sessionId;

  /* ── state ───────────────────────────────────────────── */
  const [dataReady, setDataReady] = useState(false); // zone insights written to DB

  /* ── redirect if no session ──────────────────────────── */
  useEffect(() => {
    if (!sessionId) {
      console.warn('No session ID provided, redirecting to dashboard');
      navigate('/dashboard', { replace: true });
    }
  }, [sessionId, navigate]);

  /* ── poll backend for status ─────────────────────────── */
  const { data: statusData } = useQuery({
    queryKey: [`/api/zone-insights/status/${sessionId}/`, sessionId],
    queryFn: async () => {
      const url = `${API_CONFIG.BASE_URL}/api/zone-insights/status/${sessionId}/`;
      const res = await authenticatedFetch(url);
      if (!res.ok) throw new Error('Failed to fetch zone insights status');
      return res.json();
    },
    refetchInterval: dataReady ? false : 1500, // stop polling once ready
    refetchIntervalInBackground: true,
    retry: true,
    enabled: !!sessionId && !dataReady,
  });

  /* ── mark ready when TestSubjectZoneInsight data is complete ── */
  useEffect(() => {
    if (!statusData || dataReady) return;

    // Backend sets all_subjects_complete=true once TestSubjectZoneInsight row
    // has subject_data (with mark, accuracy, time_spend, total_mark) for every
    // expected subject in the test session.
    if (statusData.all_subjects_complete === true) {
      console.log('✅ Zone insights ready – redirecting after video ends');
      setDataReady(true);
    }
  }, [statusData, dataReady]);

  /* ── redirect immediately once data is ready ───────── */
  useEffect(() => {
    if (dataReady) {
      console.log('🚀 Zone insights ready — redirecting to dashboard');
      navigate('/dashboard', { replace: true });
    }
  }, [dataReady, navigate]);

  /* ── fallback: redirect after 60 s regardless ────────── */
  useEffect(() => {
    const t = setTimeout(() => {
      console.log('⏰ Fallback redirect to dashboard after 60 s');
      navigate('/dashboard', { replace: true });
    }, 60_000);
    return () => clearTimeout(t);
  }, [navigate]);

  /* ── render ───────────────────────────────────────────── */
  return (
    <div className="relative">
      {/* Video loops while waiting; we redirect immediately when insights ready */}
      <LoadingVideo keepLooping={!dataReady} />
    </div>
  );
}
