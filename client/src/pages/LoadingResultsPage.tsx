import { useEffect, useState, useRef, useCallback } from "react";
import { useLocation, useRoute } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "@/lib/auth";
import { API_CONFIG } from "@/config/api";
import LoadingVideo from "@/components/LoadingVideo";
import PenguinOverlay from "@/components/PenguinOverlay";
import { unlockAudio, playAudioWithElement } from "@/utils/tts";
import { Button } from "@/components/ui/button";
import { Volume2 } from "lucide-react";

/**
 * Loading Results Page
 *
 * Flow
 * ────
 * 1. Loading video loops while the backend generates zone insights.
 * 2. We poll `/api/zone-insights/status/<id>/` every 1.5 s.
 * 3. "Ready" means:
 *    • Demo test  → `all_subjects_complete` AND `audio_url` present.
 *    • Normal test → `all_subjects_complete`.
 * 4. Once ready we let the current video play to its natural end (no abrupt cut).
 * 5. After the video ends:
 *    • Demo test  → show PenguinOverlay + play the TTS audio → redirect after
 *                   audio finishes (or on error, show retry button).
 *    • Normal test → redirect straight to dashboard.
 */
export default function LoadingResultsPage() {
  const [, navigate] = useLocation();
  const [, params] = useRoute("/loading-results/:sessionId");
  const sessionId = params?.sessionId;

  /* ── state ───────────────────────────────────────────── */
  const [dataReady, setDataReady] = useState(false);   // backend data is complete
  const [videoEnded, setVideoEnded] = useState(false); // video finished (after dataReady)
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [audioError, setAudioError] = useState(false);
  const [isDemoTest, setIsDemoTest] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const hasTriggeredAudioRef = useRef(false);          // prevent double-trigger

  /* ── redirect if no session ──────────────────────────── */
  useEffect(() => {
    if (!sessionId) {
      console.warn('No session ID provided, redirecting to dashboard');
      navigate('/dashboard', { replace: true });
    }
  }, [sessionId, navigate]);

  /* ── unlock audio on mount (user-gesture chain from submit) ── */
  useEffect(() => {
    if (sessionId) {
      console.log('🔓 Unlocking audio for autoplay…');
      const win = window as any;
      audioRef.current = win.__unlockedAudio || unlockAudio();
      if (!win.__unlockedAudio) win.__unlockedAudio = audioRef.current;
    }
  }, [sessionId]);

  /* ── poll backend for status ─────────────────────────── */
  const { data: statusData } = useQuery({
    queryKey: [`/api/zone-insights/status/${sessionId}/`, sessionId],
    queryFn: async () => {
      const url = `${API_CONFIG.BASE_URL}/api/zone-insights/status/${sessionId}/`;
      const res = await authenticatedFetch(url);
      if (!res.ok) throw new Error('Failed to fetch zone insights status');
      return res.json();
    },
    refetchInterval: dataReady ? false : 1500,   // stop polling once ready
    refetchIntervalInBackground: true,
    retry: true,
    enabled: !!sessionId && !dataReady,
  });

  /* ── determine readiness from poll data ───────────────── */
  useEffect(() => {
    if (!statusData || dataReady) return;

    const allComplete = statusData.all_subjects_complete === true;
    const demo = statusData.is_demo_test === true;
    const audioUrl = statusData.audio_url;

    if (demo) {
      // For demo tests wait for BOTH insights and the audio URL
      if (allComplete && audioUrl) {
        console.log('✅ Demo test ready – insights + audio available');
        audioUrlRef.current = `${API_CONFIG.BASE_URL}${audioUrl}`;
        setIsDemoTest(true);
        setDataReady(true);
      }
    } else {
      // Non-demo: only insights need to be done
      if (allComplete) {
        console.log('✅ Non-demo test ready – all subjects complete');
        setDataReady(true);
      }
    }
  }, [statusData, dataReady]);

  /* ── after video ends + data ready → transition ──────── */
  const startAudioPlayback = useCallback(() => {
    if (hasTriggeredAudioRef.current) return;
    hasTriggeredAudioRef.current = true;

    if (isDemoTest && audioUrlRef.current && audioRef.current) {
      console.log('🎙️ Playing demo TTS audio with penguin overlay');
      setIsPlayingAudio(true);

      // Listen for audio end → redirect
      audioRef.current.onended = () => {
        console.log('🔇 Audio playback completed');
        setIsPlayingAudio(false);
        setTimeout(() => navigate('/dashboard', { replace: true }), 800);
      };

      playAudioWithElement(audioRef.current, audioUrlRef.current!)
        .then((ok) => {
          if (!ok) {
            console.error('Audio playback returned false');
            setAudioError(true);
            setIsPlayingAudio(false);
          }
        })
        .catch((err) => {
          console.error('Audio playback error:', err);
          setAudioError(true);
          setIsPlayingAudio(false);
        });
    } else {
      // Non-demo or fallback — go to dashboard
      console.log('Redirecting to dashboard (non-demo or no audio)');
      setTimeout(() => navigate('/dashboard', { replace: true }), 600);
    }
  }, [isDemoTest, navigate]);

  useEffect(() => {
    if (videoEnded && dataReady) {
      startAudioPlayback();
    }
  }, [videoEnded, dataReady, startAudioPlayback]);

  /* ── fallback: redirect after 60 s regardless ────────── */
  useEffect(() => {
    const t = setTimeout(() => {
      console.log('⏰ Fallback redirect to dashboard after 60 s');
      navigate('/dashboard', { replace: true });
    }, 60_000);
    return () => clearTimeout(t);
  }, [navigate]);

  /* ── manual retry for audio errors ───────────────────── */
  const handleRetryAudio = () => {
    if (audioUrlRef.current && audioRef.current) {
      setAudioError(false);
      setIsPlayingAudio(true);

      audioRef.current.onended = () => {
        setIsPlayingAudio(false);
        setTimeout(() => navigate('/dashboard', { replace: true }), 800);
      };

      playAudioWithElement(audioRef.current, audioUrlRef.current)
        .then((ok) => { if (!ok) { setAudioError(true); setIsPlayingAudio(false); } })
        .catch(() => { setAudioError(true); setIsPlayingAudio(false); });
    }
  };

  /* ── render ───────────────────────────────────────────── */
  return (
    <div className="relative">
      {/* Video loops while waiting, plays to end once data is ready */}
      {!videoEnded && (
        <LoadingVideo
          keepLooping={!dataReady}
          onVideoEnd={() => setVideoEnded(true)}
        />
      )}

      {/* Penguin overlay (visible during TTS audio playback) */}
      {videoEnded && isDemoTest && (
        <PenguinOverlay isPlaying={isPlayingAudio} />
      )}

      {/* Retry button if audio fails */}
      {videoEnded && audioError && !isPlayingAudio && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <Button
            onClick={handleRetryAudio}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg shadow-lg flex items-center space-x-2"
          >
            <Volume2 className="w-5 h-5" />
            <span>Play Insights Audio</span>
          </Button>
        </div>
      )}
    </div>
  );
}
