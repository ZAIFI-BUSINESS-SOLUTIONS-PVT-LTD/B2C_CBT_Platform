import { useEffect, useRef, useState } from "react";

interface UseFullscreenOptions {
  gracePeriod?: number; // milliseconds before auto-submit after exit
  onExit: () => void; // called immediately when fullscreen exit is detected
  onAutoSubmit: () => void; // called when grace period expires
  onFail?: (err?: any) => void; // called when requestFullscreen fails
  toast?: (opts: { title: string; description?: string; variant?: string }) => void;
}

export default function useFullscreenEnforcement({
  gracePeriod = 8000,
  onExit,
  onAutoSubmit,
  onFail,
  toast,
}: UseFullscreenOptions) {
  const [isFullscreenActive, setIsFullscreenActive] = useState<boolean>(!!document.fullscreenElement);
  const autoSubmitTimeout = useRef<number | null>(null);

  useEffect(() => {
    const handler = () => {
      const active = !!document.fullscreenElement;
      setIsFullscreenActive(active);

      if (active) {
        // Cancel any pending auto-submit
        if (autoSubmitTimeout.current) {
          window.clearTimeout(autoSubmitTimeout.current);
          autoSubmitTimeout.current = null;
        }
        // Inform user they returned
        if (toast) {
          try {
            toast({ title: "Fullscreen mode resumed", description: "You may continue the test.", variant: "default" });
          } catch (e) {
            // ignore
          }
        }
      } else {
        // Not fullscreen anymore: call onExit and schedule auto-submit
        try {
          onExit();
        } catch (e) {
          console.error("onExit callback failed", e);
        }

        if (autoSubmitTimeout.current) {
          window.clearTimeout(autoSubmitTimeout.current);
        }
        autoSubmitTimeout.current = window.setTimeout(() => {
          try {
            onAutoSubmit();
          } catch (e) {
            console.error("onAutoSubmit failed", e);
          }
          autoSubmitTimeout.current = null;
        }, gracePeriod);
      }
    };

  document.addEventListener("fullscreenchange", handler);
  // Do not invoke handler immediately on mount. We rely on the initial
  // state from document.fullscreenElement and only react to subsequent
  // fullscreenchange events. Invoking handler() here caused an immediate
  // onExit() when the page mounted while not in fullscreen, which led to
  // premature auto-submit behavior.

    return () => {
      document.removeEventListener("fullscreenchange", handler);
      if (autoSubmitTimeout.current) {
        window.clearTimeout(autoSubmitTimeout.current);
        autoSubmitTimeout.current = null;
      }
    };
  }, [gracePeriod, onExit, onAutoSubmit, toast]);

  const requestFullscreen = async (): Promise<boolean> => {
    try {
      if (!document.fullscreenElement) {
        // Some browsers require a user gesture; caller should handle failures
        // @ts-ignore
        const el = document.documentElement;
        await (el.requestFullscreen ? el.requestFullscreen() : (el as any).webkitRequestFullscreen?.());
      }
      setIsFullscreenActive(true);
      return true;
    } catch (err) {
      console.error("requestFullscreen failed", err);
      if (onFail) onFail(err);
      return false;
    }
  };

  const exitFullscreen = async (): Promise<void> => {
    try {
      if (document.fullscreenElement) {
        // @ts-ignore
        await (document.exitFullscreen ? document.exitFullscreen() : (document as any).webkitExitFullscreen?.());
      }
    } catch (e) {
      console.error("exitFullscreen failed", e);
    }
  };

  const cancelAutoSubmit = () => {
    if (autoSubmitTimeout.current) {
      window.clearTimeout(autoSubmitTimeout.current);
      autoSubmitTimeout.current = null;
    }
  };

  return {
    isFullscreenActive,
    requestFullscreen,
    exitFullscreen,
    cancelAutoSubmit,
  };
}
