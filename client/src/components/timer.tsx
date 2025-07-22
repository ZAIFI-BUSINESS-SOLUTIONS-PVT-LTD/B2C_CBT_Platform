/**
 * Timer Component
 * 
 * A countdown timer component specifically designed for NEET practice tests.
 * Features include:
 * - Real-time countdown display in MM:SS format
 * - Visual color coding based on remaining time (red for critical, orange for warning)
 * - Automatic callback when time expires
 * - Responsive design with clock icon
 * - Handles both time-based tests and graceful degradation for question-based tests
 * 
 * The timer updates every second and automatically triggers test submission
 * when time runs out.
 */

import { useState, useEffect } from "react";
import { Clock } from "lucide-react";

/**
 * Props for the Timer component
 */
interface TimerProps {
  initialMinutes: number;  // Initial time in minutes
  onTimeUp: () => void;    // Callback function when timer reaches zero
  className?: string;      // Additional CSS classes
}

/**
 * Timer Component
 * Displays a countdown timer with visual feedback
 */
export function Timer({ initialMinutes, onTimeUp, className = "" }: TimerProps) {
  // === TIMER STATE ===
  const [timeLeft, setTimeLeft] = useState((initialMinutes || 0) * 60);  // Time left in seconds

  // === TIMER LOGIC ===
  useEffect(() => {
    // If time is up, trigger the callback
    if (timeLeft <= 0) {
      onTimeUp();
      return;
    }

    // Set up interval to decrement time every second
    const timer = setInterval(() => {
      setTimeLeft(prev => prev - 1);
    }, 1000);

    // Cleanup interval on component unmount or dependency change
    return () => clearInterval(timer);
  }, [timeLeft, onTimeUp]);

  // === TIME FORMATTING ===
  /**
   * Format seconds into MM:SS display format
   * Examples: 65 seconds → "1:05", 3600 seconds → "60:00"
   */
  const formatTime = (seconds: number) => {
    if (isNaN(seconds) || seconds < 0) return "0:00";  // Handle invalid input
    const mins = Math.floor(seconds / 60);             // Calculate minutes
    const secs = seconds % 60;                         // Calculate remaining seconds
    return `${mins}:${secs.toString().padStart(2, '0')}`;  // Format as MM:SS
  };

  // === VISUAL FEEDBACK ===
  /**
   * Determine timer color based on remaining time
   * This provides visual urgency cues to students:
   * - RED: Critical time (≤5 minutes) - urgent action needed
   * - ORANGE: Warning time (≤15 minutes) - time running low
   * - YELLOW: Normal time (>15 minutes) - plenty of time left
   */
  const getTimeColor = () => {
    if (timeLeft <= 300) {        // 5 minutes or less - CRITICAL
      return "bg-red-500 text-white";
    } else if (timeLeft <= 900) {  // 15 minutes or less - WARNING
      return "bg-orange-500 text-white";
    }
    return "bg-neet-amber text-white";  // More than 15 minutes - NORMAL
  };

  // === RENDER TIMER DISPLAY ===
  return (
    <div className={`${getTimeColor()} px-3 py-1 rounded-lg font-mono text-lg ${className}`}>
      <Clock className="h-4 w-4 inline mr-1" />  {/* Clock icon for visual context */}
      {formatTime(timeLeft)}                      {/* Display formatted time */}
    </div>
  );
}
