import React from "react";
import { Clock, Pause, Play, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Timer } from "@/components/timer";

interface TestHeaderProps {
  started: boolean;
  paused: boolean;
  timeLimit?: number | null;
  onTimeUp: () => void;
  onTogglePause: () => void;
  onSubmitTest: () => void;
  showTimeOverDialog: boolean;
  isSubmitting: boolean;
  onQuit: () => void;
  showPause?: boolean;
  onHeightChange?: (height: number) => void;
}

export default function TestHeader({
  started,
  paused,
  timeLimit,
  onTimeUp,
  onTogglePause,
  onSubmitTest,
  showTimeOverDialog,
  isSubmitting,
  onQuit,
  showPause = true,
  onHeightChange,
}: TestHeaderProps) {
  const headerRef = React.useRef<HTMLElement | null>(null);

  React.useEffect(() => {
    if (!headerRef.current) return;
    const el = headerRef.current;
    const report = () => onHeightChange?.(el.getBoundingClientRect().height || 0);

    report();
    const ro = new ResizeObserver(() => report());
    ro.observe(el);
    return () => ro.disconnect();
  }, [onHeightChange]);
  return (
    <header
      ref={headerRef}
      className="w-full fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md pt-4"
      style={{ paddingTop: 'env(safe-area-inset-top, 20px)' }}
    >
      <div className="px-3 pt-2 pb-2">
        <div className="flex items-center justify-between">
          {/* Left: NEET Bro branding */}
          <div className="flex items-center gap-2">
            <span className="text-base font-extrabold text-blue-600 tracking-tight">NEET Bro</span>
          </div>

          {/* Center: Timer */}
          <div className="flex items-center">
            {timeLimit ? (
              started ? (
                <Timer
                  initialMinutes={timeLimit}
                  onTimeUp={onTimeUp}
                  className=""
                  paused={paused}
                />
              ) : (
                <div className="text-xs bg-gray-100 text-gray-500 px-3 py-1 rounded-full font-mono font-bold">
                  Start to begin
                </div>
              )
            ) : (
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border-2 border-dashed border-blue-200 bg-white text-blue-600 text-sm font-medium">
                <Clock className="h-3.5 w-3.5" />
                <span>No Limit</span>
              </div>
            )}
          </div>

          {/* Right: Submit */}
          <button
            onClick={onSubmitTest}
            disabled={isSubmitting}
            className={`text-sm font-semibold px-4 py-2 rounded-lg transition-colors shadow-md focus:outline-none focus:ring-2 focus:ring-blue-300 ${
              showTimeOverDialog
                ? 'bg-green-600 text-white animate-pulse'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {showTimeOverDialog ? 'Submit Test' : 'Submit'}
          </button>
        </div>
      </div>
    </header>
  );
}
