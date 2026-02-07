import { useEffect, useState, useRef } from "react";
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
 * Shows engaging video while zone insights are being generated
 * For demo tests from Neet Bro Institute: plays audio with penguin overlay
 * Redirects to dashboard once insights are ready
 */
export default function LoadingResultsPage() {
  const [, navigate] = useLocation();
  const [, params] = useRoute("/loading-results/:sessionId");
  const sessionId = params?.sessionId;

  // Audio state
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [audioError, setAudioError] = useState(false);
  const [videoEnded, setVideoEnded] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  // If no session ID, redirect immediately
  useEffect(() => {
    if (!sessionId) {
      console.warn('No session ID provided, redirecting to dashboard');
      navigate('/dashboard', { replace: true });
    }
  }, [sessionId, navigate]);

  // Unlock audio on mount (during user gesture flow from test submit)
  useEffect(() => {
    if (sessionId) {
      console.log('🔓 Unlocking audio for autoplay...');
      audioRef.current = unlockAudio();
    }
  }, [sessionId]);

  // Poll for zone insights status for this test session
  const { data: statusData } = useQuery({
    queryKey: [`/api/zone-insights/status/${sessionId}/`, sessionId],
    queryFn: async () => {
      const url = `${API_CONFIG.BASE_URL}/api/zone-insights/status/${sessionId}/`;
      const response = await authenticatedFetch(url);
      
      if (!response.ok) {
        throw new Error('Failed to fetch zone insights status');
      }
      
      return response.json();
    },
    refetchInterval: 1500, // Poll every 1.5 seconds
    refetchIntervalInBackground: true,
    retry: true,
    enabled: !!sessionId,
  });

  // When insights are ready and video ends, play audio if available
  useEffect(() => {
    if (!statusData || !videoEnded || isPlayingAudio || audioError) {
      return;
    }

    const insightsReady = statusData.insights_generated === true && statusData.total_subjects > 0;
    const audioUrl = statusData.audio_url;
    const isDemoTest = statusData.is_demo_test === true;

    if (insightsReady) {
      // If demo test with audio URL, play it
      if (isDemoTest && audioUrl && audioRef.current) {
        console.log('🎙️ Demo test detected - playing audio with penguin overlay');
        
        // Store audio URL
        audioUrlRef.current = `${API_CONFIG.BASE_URL}${audioUrl}`;
        
        // Play audio
        setIsPlayingAudio(true);
        playAudioWithElement(audioRef.current, audioUrlRef.current)
          .then((success) => {
            if (!success) {
              console.error('Audio playback failed');
              setAudioError(true);
              setIsPlayingAudio(false);
            }
          })
          .catch((error) => {
            console.error('Audio playback error:', error);
            setAudioError(true);
            setIsPlayingAudio(false);
          });

        // Listen for audio end
        if (audioRef.current) {
          audioRef.current.onended = () => {
            console.log('🔇 Audio playback completed');
            setIsPlayingAudio(false);
            // Redirect after audio ends
            setTimeout(() => {
              navigate('/dashboard', { replace: true });
            }, 1000);
          };
        }
      } else {
        // Non-demo test or audio not available - redirect immediately
        console.log('Redirecting to dashboard (no audio)');
        setTimeout(() => {
          navigate('/dashboard', { replace: true });
        }, 1000);
      }
    }
  }, [statusData, videoEnded, isPlayingAudio, audioError, navigate]);

  // Fallback: redirect after 45 seconds regardless
  useEffect(() => {
    const fallbackTimer = setTimeout(() => {
      console.log('Fallback redirect to dashboard after 45s');
      navigate('/dashboard', { replace: true });
    }, 45000);

    return () => clearTimeout(fallbackTimer);
  }, [navigate]);

  // Manual retry audio playback
  const handleRetryAudio = () => {
    if (audioUrlRef.current && audioRef.current) {
      setAudioError(false);
      setIsPlayingAudio(true);
      playAudioWithElement(audioRef.current, audioUrlRef.current)
        .then((success) => {
          if (!success) {
            setAudioError(true);
            setIsPlayingAudio(false);
          }
        })
        .catch(() => {
          setAudioError(true);
          setIsPlayingAudio(false);
        });
    }
  };

  return (
    <div className="relative">
      {/* Loading video (plays while insights generate) */}
      <LoadingVideo onVideoEnd={() => setVideoEnded(true)} />

      {/* Penguin overlay (shows during audio playback) */}
      {videoEnded && <PenguinOverlay isPlaying={isPlayingAudio} />}

      {/* Retry button (shows if audio fails) */}
      {videoEnded && audioError && !isPlayingAudio && (
        <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-50">
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
