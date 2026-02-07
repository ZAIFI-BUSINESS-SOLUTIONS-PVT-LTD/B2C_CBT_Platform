/**
 * Penguin Overlay Component
 * Shows animated penguin while dictating checkpoint insights
 */

import React, { useEffect, useState } from 'react';
import { Volume2 } from 'lucide-react';

interface PenguinOverlayProps {
  isPlaying: boolean;
  onComplete?: () => void;
}

export default function PenguinOverlay({ isPlaying, onComplete }: PenguinOverlayProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isPlaying) {
      setVisible(true);
    }
  }, [isPlaying]);

  const handleAnimationEnd = () => {
    if (!isPlaying) {
      setVisible(false);
      onComplete?.();
    }
  };

  if (!visible) return null;

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center transition-all duration-500 ${
        isPlaying ? 'opacity-100' : 'opacity-0'
      }`}
      onTransitionEnd={handleAnimationEnd}
    >
      {/* Blurred background */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-md" />

      {/* Penguin content */}
      <div className="relative z-10 flex flex-col items-center justify-center space-y-6 px-4">
        {/* Penguin SVG placeholder - replace with actual welcome penguin SVG */}
        <div className="relative">
          {/* Animated glow effect */}
          {isPlaying && (
            <div className="absolute inset-0 animate-pulse">
              <div className="w-48 h-48 bg-blue-500/30 rounded-full blur-3xl" />
            </div>
          )}
          
          {/* Penguin illustration */}
          <div className="relative w-48 h-48 flex items-center justify-center">
            {/* Simple penguin SVG (replace with your actual penguin asset) */}
            <svg
              viewBox="0 0 200 200"
              className="w-full h-full"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Penguin body */}
              <ellipse cx="100" cy="120" rx="60" ry="80" fill="#2C3E50" />
              <ellipse cx="100" cy="120" rx="40" ry="60" fill="white" />
              
              {/* Penguin head */}
              <circle cx="100" cy="60" r="40" fill="#2C3E50" />
              
              {/* Eyes */}
              <circle cx="85" cy="55" r="8" fill="white" />
              <circle cx="115" cy="55" r="8" fill="white" />
              <circle cx="87" cy="55" r="4" fill="black" />
              <circle cx="117" cy="55" r="4" fill="black" />
              
              {/* Beak */}
              <path d="M 100 65 L 90 75 L 110 75 Z" fill="#F39C12" />
              
              {/* Wings */}
              <ellipse cx="55" cy="120" rx="15" ry="50" fill="#2C3E50" transform="rotate(-20 55 120)" />
              <ellipse cx="145" cy="120" rx="15" ry="50" fill="#2C3E50" transform="rotate(20 145 120)" />
              
              {/* Feet */}
              <ellipse cx="85" cy="195" rx="15" ry="8" fill="#F39C12" />
              <ellipse cx="115" cy="195" rx="15" ry="8" fill="#F39C12" />
              
              {/* Sound waves animation */}
              {isPlaying && (
                <>
                  <circle cx="160" cy="60" r="5" fill="#3498DB" opacity="0.6">
                    <animate
                      attributeName="r"
                      from="5"
                      to="15"
                      dur="1.5s"
                      repeatCount="indefinite"
                    />
                    <animate
                      attributeName="opacity"
                      from="0.6"
                      to="0"
                      dur="1.5s"
                      repeatCount="indefinite"
                    />
                  </circle>
                  <circle cx="160" cy="60" r="5" fill="#3498DB" opacity="0.6">
                    <animate
                      attributeName="r"
                      from="5"
                      to="15"
                      dur="1.5s"
                      begin="0.5s"
                      repeatCount="indefinite"
                    />
                    <animate
                      attributeName="opacity"
                      from="0.6"
                      to="0"
                      dur="1.5s"
                      begin="0.5s"
                      repeatCount="indefinite"
                    />
                  </circle>
                </>
              )}
            </svg>
          </div>
        </div>

        {/* Text message */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center space-x-2 text-white">
            <Volume2 className={`w-6 h-6 ${isPlaying ? 'animate-pulse' : ''}`} />
            <h3 className="text-2xl font-bold">
              {isPlaying ? 'Listening to Insights...' : 'Audio Complete'}
            </h3>
          </div>
          
          {isPlaying && (
            <p className="text-gray-300 text-sm">
              Your performance feedback is being narrated
            </p>
          )}
        </div>

        {/* Audio indicator */}
        {isPlaying && (
          <div className="flex space-x-1">
            {[0, 1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="w-1 h-8 bg-blue-500 rounded-full animate-pulse"
                style={{
                  animationDelay: `${i * 0.1}s`,
                  animationDuration: '0.8s',
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
