/**
 * AppTourOverlay — First-time login onboarding tour (4 steps).
 *
 * Flow:
 *   Step 1 – Welcome screen (centered penguin + subtitle + audio auto-play)
 *   Step 2 – Highlight "Test" tab in the bottom dock; wait for user click
 *   Step 3 – Highlight "Scheduled Tests" card on the Topics page; wait for click
 *   Step 4 – Highlight demo test's "Start Test" button; wait for click → end tour
 *
 * The overlay renders a full-screen dimmed backdrop that blocks background
 * interactions except for the highlighted target element in each step.
 * Simple CSS animations are used (no animation libraries).
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useLocation } from "wouter";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
export type TourStep = 1 | 2 | 3 | 4;

interface AppTourOverlayProps {
  /** Callback fired when the tour ends (Step 4 complete or user skips).
   *  Parent should persist `isFirstLogin = false` and unmount this overlay. */
  onTourComplete: () => void;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */
const PENGUIN_WELCOME   = "/penguin_welcome.png";
const PENGUIN_TEST      = "/penguin_pointing_test.png";
const PENGUIN_STEP3     = "/penguin_test.png";
const PENGUIN_START     = "/penguin_pointing_start.png";

// SVG fallbacks if PNG assets are not yet available
const PENGUIN_WELCOME_SVG  = "/penguin_welcome.svg";
const PENGUIN_TEST_SVG     = "/penguin_pointing_test.svg";
const PENGUIN_START_SVG    = "/penguin_pointing_start.svg";
// filenames in `public/` use a hyphen
const PENGUIN_PAPER     = "/penguin-paper.png";
const PENGUIN_PAPER_SVG    = "/penguin-paper.svg";

// public/ contains these files at the root — attempt autoplay with gesture fallback
const AUDIO_WELCOME     = "/welcome_voice.mp3";
const AUDIO_TEST_TAB    = "/test_tab_voice.mp3";
const AUDIO_START_TEST  = "/start_test_voice.mp3";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Play an audio file; resolves when playback ends (or immediately on error). */
function playAudio(src: string): Promise<void> {
  return new Promise((resolve) => {
    try {
      const audio = new Audio(src);
      audio.addEventListener("ended", () => resolve());
      audio.addEventListener("error", () => resolve()); // don't block on missing file
      // Attempt to play — if autoplay is blocked the promise will reject.
      audio.play().then(() => {
        // playback started
      }).catch(() => {
        // autoplay blocked — resolve immediately but leave audio instance usable
        resolve();
      });
    } catch {
      resolve();
    }
  });
}

/** Try to play audio immediately; if autoplay is blocked, retry once on the next user interaction. */
function tryPlayWithGestureFallback(src: string) {
  try {
    const audio = new Audio(src);
    audio.addEventListener('error', () => {});
    const p = audio.play();
    if (p && typeof p.catch === 'function') {
      p.catch(() => {
        const resume = () => {
          audio.play().catch(() => {});
          window.removeEventListener('click', resume, true);
          window.removeEventListener('touchstart', resume, true);
        };
        window.addEventListener('click', resume, { capture: true, passive: true });
        window.addEventListener('touchstart', resume, { capture: true, passive: true });
      });
    }
  } catch {
    // ignore
  }
}

/** Get bounding-client-rect of the *first* element matching `selector`,
 *  or null if not found. */
function getRect(selector: string): DOMRect | null {
  const el = document.querySelector(selector);
  return el ? el.getBoundingClientRect() : null;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export default function AppTourOverlay({ onTourComplete }: AppTourOverlayProps) 
{

  const [step, setStep] = useState<TourStep>(1);
  const [fadeIn, setFadeIn] = useState(false);
  const [location] = useLocation();
  const audioPlayedRef = useRef<Set<number>>(new Set());

  // Trigger entrance animation
  useEffect(() => {
    requestAnimationFrame(() => setFadeIn(true));
  }, []);

  /* ---- Step 1: play welcome audio (fire-and-forget, no auto-advance) ---- */
  useEffect(() => {
    if (step !== 1) return;
    if (audioPlayedRef.current.has(1)) return;
    audioPlayedRef.current.add(1);

    // Small delay so user sees the welcome screen before audio starts
    const timer = setTimeout(() => {
      tryPlayWithGestureFallback(AUDIO_WELCOME); // play with gesture-fallback
    }, 800);

    return () => clearTimeout(timer);
  }, [step]);

  /* ---- Step 2: play test-tab audio (once) ---- */
  useEffect(() => {
    if (step !== 2) return;
    if (audioPlayedRef.current.has(2)) return;
    audioPlayedRef.current.add(2);
    tryPlayWithGestureFallback(AUDIO_TEST_TAB);
  }, [step]);

  /* ---- Step 3: play audio for scheduled tests ---- */
  useEffect(() => {
    if (step !== 3) return;
    if (audioPlayedRef.current.has(3)) return;
    audioPlayedRef.current.add(3);
    playAudio(AUDIO_TEST_TAB); // reuse same voice or use a separate file
  }, [step]);

  /* ---- Step 4: play start-test audio ---- */
  useEffect(() => {
    if (step !== 4) return;
    if (audioPlayedRef.current.has(4)) return;
    audioPlayedRef.current.add(4);
    tryPlayWithGestureFallback(AUDIO_START_TEST);
  }, [step]);

  /* ---- Watch route changes to advance from step 2→3 ---- */
  useEffect(() => {
    if (step === 2 && location === "/topics") {
      // User navigated to topics page (clicked Test tab) → move to step 3
      const delay = setTimeout(() => setStep(3), 400);
      return () => clearTimeout(delay);
    }
  }, [step, location]);

  /* ---- Watch route changes to advance from step 3→4 ---- */
  useEffect(() => {
    if (step === 3 && location === "/scheduled-tests") {
      // User navigated to scheduled-tests page → move to step 4
      const delay = setTimeout(() => setStep(4), 400);
      return () => clearTimeout(delay);
    }
  }, [step, location]);

  /* ---- Step 4: listen for "Start Test" button click ---- */
  useEffect(() => {
    if (step !== 4) return;

    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      // Detect click on a Start Test button (or its children)
      const btn = target.closest("[data-tour-start-test]") || target.closest("button");
      if (btn && btn.textContent?.toLowerCase().includes("start test")) {
        onTourComplete();
      }
    };

    // Use capture so we intercept before React handlers
    document.addEventListener("click", handler, true);
    return () => document.removeEventListener("click", handler, true);
  }, [step, onTourComplete]);

  /* ================================================================ */
  /*  Render helpers per step                                          */
  /* ================================================================ */

  /** Reusable highlight "hole" style — positions an element on screen
   *  that lets clicks through to the underlying UI. */
  const Spotlight = ({ selector, padding = 8, borderRadius = 16 }: { selector: string; padding?: number; borderRadius?: number }) => {
    const [rect, setRect] = useState<DOMRect | null>(null);

    useEffect(() => {
      const update = () => setRect(getRect(selector));
      update();
      // Re-measure on scroll / resize
      window.addEventListener("resize", update);
      window.addEventListener("scroll", update, true);
      const interval = setInterval(update, 300);
      return () => {
        window.removeEventListener("resize", update);
        window.removeEventListener("scroll", update, true);
        clearInterval(interval);
      };
    }, [selector]);

    if (!rect) return null;

    return (
      <div
        className="tour-spotlight"
        style={{
          position: "fixed",
          top: rect.top - padding,
          left: rect.left - padding,
          width: rect.width + padding * 2,
          height: rect.height + padding * 2,
          borderRadius,
          boxShadow: "0 0 0 9999px rgba(0,0,0,0.55)",
          zIndex: 99998,
          pointerEvents: "none",
          transition: "all 0.35s ease",
        }}
      >
        {/* Glow ring */}
        <div
          style={{
            position: "absolute",
            inset: -4,
            borderRadius: borderRadius + 4,
            border: "2px solid rgba(99,102,241,0.7)",
            animation: "tour-glow 1.5s ease-in-out infinite",
          }}
        />
      </div>
    );
  };

  /** Clickable transparent area matching the spotlight so user can interact with the real button beneath */
  const SpotlightClickThrough = ({ selector, padding = 8 }: { selector: string; padding?: number }) => {
    const [rect, setRect] = useState<DOMRect | null>(null);

    useEffect(() => {
      const update = () => setRect(getRect(selector));
      update();
      window.addEventListener("resize", update);
      window.addEventListener("scroll", update, true);
      const interval = setInterval(update, 300);
      return () => {
        window.removeEventListener("resize", update);
        window.removeEventListener("scroll", update, true);
        clearInterval(interval);
      };
    }, [selector]);

    if (!rect) return null;

    return (
      <div
        style={{
          position: "fixed",
          top: rect.top - padding,
          left: rect.left - padding,
          width: rect.width + padding * 2,
          height: rect.height + padding * 2,
          zIndex: 100000,
          pointerEvents: "none", // let clicks pass through to real element
        }}
      />
    );
  };

  /* ================================================================ */
  /*  Step renderers                                                   */
  /* ================================================================ */

  const renderStep1 = () => (
    <div className="fixed inset-0 z-[99997] flex flex-col items-center justify-center">
      {/* Dimmed background */}
      <div className="absolute inset-0 bg-black/60" />

      {/* Content */}
      <div
        className="relative z-10 flex flex-col items-center gap-6 px-6"
        style={{ animation: "tour-fadeIn 0.6s ease-out both" }}
      >
        <img
          src={PENGUIN_WELCOME}
          alt="Welcome penguin"
          className="w-48 h-auto max-h-[40vh] object-contain drop-shadow-xl"
          style={{ animation: "tour-bounceIn 0.7s ease-out both" }}
          onError={(e) => { (e.target as HTMLImageElement).src = PENGUIN_WELCOME_SVG; }}
        />
        <p className="text-white text-lg font-medium text-center max-w-xs leading-relaxed">
          Welcome! Let me guide you through the app. 🎉
        </p>
        <button
          onClick={() => setStep(2)}
          className="mt-2 px-8 py-3 bg-indigo-500 hover:bg-indigo-600 active:scale-95 text-white font-semibold rounded-full shadow-lg transition-all duration-200"
        >
          Let's Go! 🚀
        </button>
        <button
          onClick={onTourComplete}
          className="mt-3 text-white/50 hover:text-white text-xs underline transition-colors"
        >
          Skip Tour
        </button>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <>
      {/* Full dim overlay — pointer-events active so background is blocked */}
      <div className="fixed inset-0 z-[99997] pointer-events-auto" />

      {/* Spotlight on the Test tab button (second item in the dock) */}
      <Spotlight selector='nav[aria-label="Mobile navigation"] li:nth-child(2) button' padding={6} borderRadius={20} />
      <SpotlightClickThrough selector='nav[aria-label="Mobile navigation"] li:nth-child(2) button' padding={6} />

      {/* Let the dock itself receive clicks */}
      <style>{`nav[aria-label="Mobile navigation"] { z-index: 100001 !important; pointer-events: auto !important; }`}</style>

      {/* Penguin (left) + instruction text (right) */}
      <div
        className="fixed z-[100002] pointer-events-none"
        style={{ bottom: 100, right: 16, animation: "tour-fadeIn 0.5s ease-out both" }}
      >
        <div className="flex items-end gap-2">
          <img
            src={PENGUIN_TEST}
            alt="Penguin pointing to test"
            // increase size ~20% from w-24 -> w-28 and move further left
            className="w-32 h-auto drop-shadow-lg"
            style={{ transform: 'translateX(-28px)', animation: "tour-bounceIn 0.5s ease-out both" }}
            onError={(e) => { (e.target as HTMLImageElement).src = PENGUIN_TEST_SVG; }}
          />
          <div className="bg-white rounded-2xl px-4 py-3 shadow-lg max-w-[200px]">
            <p className="text-sm font-medium text-gray-800">
              👆 Click the <span className="text-blue-600 font-bold">Test</span> tab to begin.
            </p>
          </div>
        </div>
      </div>

      {/* Highlight the Test tab itself with a gentle glow */}
      <style>{`
        nav[aria-label="Mobile navigation"] li:nth-child(2) button {
          z-index: 100002 !important;
          border-radius: 9999px !important;
          /* tighter glow to better fit the button */
          box-shadow: 0 0 0 4px rgba(99,102,241,0.28), 0 4px 18px rgba(99,102,241,0.12);
          animation: tour-glow 1.2s ease-in-out infinite;
        }
        nav[aria-label="Mobile navigation"] li:nth-child(2) button > div {
          transform-origin: center;
        }
      `}</style>

      {/* Skip button */}
      <button
        onClick={onTourComplete}
        className="fixed top-4 right-4 z-[100003] text-white/60 hover:text-white bg-black/30 hover:bg-black/50 rounded-full px-3 py-1.5 text-xs transition-colors pointer-events-auto"
      >
        Skip Tour ✕
      </button>
    </>
  );

  const renderStep3 = () => (
    <>
      {/* Full dim overlay */}
      <div className="fixed inset-0 z-[99997] pointer-events-auto" />

      {/* Spotlight on the "Scheduled Tests" card — 3rd card in the topics grid */}
      <Spotlight selector='[data-tour-scheduled-tests]' padding={6} borderRadius={16} />
      <SpotlightClickThrough selector='[data-tour-scheduled-tests]' padding={6} />

      {/* Let the scheduled tests card receive clicks */}
      <style>{`[data-tour-scheduled-tests] { position: relative; z-index: 100001 !important; pointer-events: auto !important; }`}</style>

      {/* Penguin + text */}
      <div
        className="fixed z-[100002] pointer-events-none"
        style={{ bottom: 100, left: "50%", transform: "translateX(-50%)", animation: "tour-fadeIn 0.5s ease-out both" }}
      >
        <div className="flex flex-col items-center gap-2">
          <div className="bg-white rounded-2xl px-4 py-3 shadow-lg">
            <p className="text-sm font-medium text-gray-800">
              👆 Now tap <span className="text-purple-600 font-bold">Scheduled Tests</span>
            </p>
          </div>
          <img
            src={PENGUIN_PAPER}
            alt="Penguin with clipboard"
            className="w-40 h-auto drop-shadow-lg"
            style={{ transform: 'translateY(-18px)', animation: "tour-bounceIn 0.5s ease-out both", maxWidth: 260 }}
            onError={(e) => { (e.target as HTMLImageElement).src = PENGUIN_PAPER_SVG; }}
          />
        </div>
      </div>

      {/* Skip button */}
      <button
        onClick={onTourComplete}
        className="fixed top-4 right-4 z-[100003] text-white/60 hover:text-white bg-black/30 hover:bg-black/50 rounded-full px-3 py-1.5 text-xs transition-colors pointer-events-auto"
      >
        Skip Tour ✕
      </button>
    </>
  );

  const renderStep4 = () => (
    <>
      {/* Full dim overlay */}
      <div className="fixed inset-0 z-[99997] pointer-events-auto" />

      {/* Spotlight on first test card (contains "Start Test" button) */}
      <Spotlight selector='[data-tour-demo-test]' padding={8} borderRadius={16} />
      <SpotlightClickThrough selector='[data-tour-demo-test]' padding={8} />

      {/* Allow the test card to receive clicks */}
      <style>{`[data-tour-demo-test] { position: relative; z-index: 100001 !important; pointer-events: auto !important; } [data-tour-demo-test] button { pointer-events: auto !important; }`}</style>

      {/* Penguin to the left of the text box, slightly larger (≈ +20%) */}
      <div
        className="fixed z-[100002] pointer-events-none flex items-center gap-3"
        style={{ bottom: 80, left: 8, transform: 'none', animation: "tour-fadeIn 0.5s ease-out both" }}
      >
        <img
          src={PENGUIN_START}
          alt="Penguin pointing at start"
          className="h-auto drop-shadow-lg"
          style={{ width: '8.9rem', animation: "tour-bounceIn 0.5s ease-out both" }}
          onError={(e) => { (e.target as HTMLImageElement).src = PENGUIN_START_SVG; }}
        />
        <div className="bg-white rounded-2xl px-4 py-3 shadow-lg" style={{ maxWidth: 'calc(100vw - 140px)' }}>
          <p className="text-sm font-medium text-gray-800">
            🚀 Now click <span className="text-blue-600 font-bold">Start Test</span>.
          </p>
        </div>
      </div>

      {/* Skip button */}
      <button
        onClick={onTourComplete}
        className="fixed top-4 right-4 z-[100003] text-white/60 hover:text-white bg-black/30 hover:bg-black/50 rounded-full px-3 py-1.5 text-xs transition-colors pointer-events-auto"
      >
        Skip Tour ✕
      </button>
    </>
  );

  /* ================================================================ */
  /*  Main render                                                      */
  /* ================================================================ */
  return (
    <>
      {/* Global keyframes injected once */}
      <style>{`
        @keyframes tour-fadeIn {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes tour-bounceIn {
          0%   { opacity: 0; transform: scale(0.7); }
          60%  { opacity: 1; transform: scale(1.05); }
          100% { transform: scale(1); }
        }
        @keyframes tour-glow {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50%      { opacity: 1;   transform: scale(1.03); }
        }
      `}</style>

      <div
        style={{
          opacity: fadeIn ? 1 : 0,
          transition: "opacity 0.4s ease",
          position: "fixed",
          inset: 0,
          zIndex: 99997,
          // Allow interactions only for Step 1 (welcome screen). Other steps
          // use their own overlay elements with pointer-events enabled/disabled
          // so we keep the original click-through behaviour for them.
          pointerEvents: step === 1 ? "auto" : "none",
        }}
      >
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
        {step === 4 && renderStep4()}
      </div>

      {/* Step indicator dots */}
      <div
        className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[100003] flex gap-2 pointer-events-none"
        style={{ opacity: step === 1 ? 0 : 1, transition: "opacity 0.3s" }}
      >
        {[2, 3, 4].map((s) => (
          <div
            key={s}
            className={`h-2 rounded-full transition-all duration-300 ${
              step >= s ? "w-6 bg-indigo-500" : "w-2 bg-white/50"
            }`}
          />
        ))}
      </div>
    </>
  );
}
