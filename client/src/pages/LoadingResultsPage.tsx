import { useEffect, useState } from "react";
import { useLocation, useRoute } from "wouter";
import { Progress } from "@/components/ui/progress";

/**
 * Loading Results Page
 *
 * Flow
 * ────
 * 1. Show loading page with result-bg background for exactly 5 seconds
 * 2. Progress bar animates from 0% to 100% over 5 seconds
 * 3. Automatically redirect to /results/:sessionId after 5 seconds
 * 4. Backend processes zone insights asynchronously in background
 * 5. Results page will display test results and zone insights data
 */
export default function LoadingResultsPage() {
  const [, navigate] = useLocation();
  const [, params] = useRoute("/loading-results/:sessionId");
  const sessionId = params?.sessionId;

  /* ── state ───────────────────────────────────────────── */
  const [progress, setProgress] = useState(0); // animated progress bar

  /* ── redirect if no session ──────────────────────────── */
  useEffect(() => {
    if (!sessionId) {
      console.warn('No session ID provided, redirecting to landing');
      navigate('/', { replace: true });
    }
  }, [sessionId, navigate]);

  /* ── redirect after 5 seconds ────────────────────────── */
  useEffect(() => {
    if (!sessionId) return;

    const redirectTimer = setTimeout(() => {
      console.log('✅ 5 second loading complete – redirecting to results');
      navigate(`/results/${sessionId}`, { replace: true });
    }, 5000); // 5 seconds

    return () => clearTimeout(redirectTimer);
  }, [sessionId, navigate]);

  /* ── animate progress bar ────────────────────────────── */
  useEffect(() => {
    // Smoothly animate progress from 0 to 100% over 5 seconds
    const duration = 5000; // 5 seconds
    const interval = 50; // update every 50ms for smooth animation
    const increment = (100 / duration) * interval;
    
    const timer = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) return 100; // cap at 100%
        return Math.min(prev + increment, 100);
      });
    }, interval);

    return () => clearInterval(timer);
  }, []);

  /* ── render ───────────────────────────────────────────── */
  return (
    <div 
      className="min-h-screen flex items-center justify-center px-4"
      style={{
        backgroundImage: 'url(/loading-bg.png)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat'
      }}
    >
      <div className="w-full max-w-md relative">
        {/* Penguin mascot in a separate div (larger by 100%) */}
        <div className="flex justify-center -mt-12 mb-4 z-20 relative">
          <div className="w-48 h-48 rounded-full flex items-center justify-center bg-transparent">
            <img
              src="/happy-penguin.png"
              alt="Loading"
              className="w-full h-full object-contain animate-bounce"
            />
          </div>
        </div>

        {/* Card with translucent white gradient, white border and subtle shadow */}
        <div className="bg-gradient-to-b from-white/60 to-white/10 backdrop-blur-sm rounded-2xl shadow-md border border-white/40 p-8 relative z-10">
          {/* Loading text */}
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">
              Analyzing Your Performance
            </h2>
            {/* Phrase removed as requested */}
          </div>

          {/* Progress bar */}
          <div className="space-y-2">
            <Progress value={progress} className="h-3" />
            <p className="text-center text-xs text-gray-500">
              {Math.round(progress)}% complete
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
