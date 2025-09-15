import { Clock, Pause, Play, Check } from "lucide-react";
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
}

export default function TestHeader({
  started,
  paused,
  timeLimit,
  onTimeUp,
  onTogglePause,
  onSubmitTest,
  showTimeOverDialog,
  isSubmitting
}: TestHeaderProps) {
  return (
    <header className="w-full bg-white backdrop-blur-sm border-b border-blue-100 sticky top-0 z-40 shadow-sm mb-2">
      <div className="px-3 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {started && (
              <Button
                onClick={onTogglePause}
                size="icon"
                className="bg-green-500 hover:bg-green-600 aspect-square"
                title={paused ? 'Resume Test' : 'Pause Test'}
              >
                {paused ? <Play /> : <Pause />}
              </Button>
            )}
            {timeLimit ? (
              <>
                <div className="hidden">
                  <span className="text-xs font-medium text-gray-900">Time Remaining:</span>
                </div>
                {started ? (
                  <Timer
                    initialMinutes={timeLimit}
                    onTimeUp={onTimeUp}
                    className="bg-yellow-400 text-gray-900 px-2 py-1 rounded-md text-sm font-bold shadow-md h-9 flex items-center justify-center"
                    paused={paused}
                  />
                ) : (
                  <div className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded-lg font-mono font-bold shadow-md">
                    Start test to begin timer
                  </div>
                )}
              </>
            ) : (
              <div className="text-xs bg-gray-100 text-gray-900 px-2 py-1 rounded-lg font-mono font-bold shadow-md">
                <Clock className="h-3 w-3 inline mr-1" />
                No Time Limit
              </div>
            )}
          </div>
          <div className="flex items-center">
            <Button
              onClick={onSubmitTest}
              className={`px-4 py-2 font-semibold shadow-md text-sm ${showTimeOverDialog
                ? 'bg-green-600 hover:bg-green-700 text-white animate-pulse'
                : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              disabled={isSubmitting}
            >
              <Check className="h-4 w-4 mr-2" />
              {showTimeOverDialog ? 'Submit Test (Time Over)' : 'Submit Test'}
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
