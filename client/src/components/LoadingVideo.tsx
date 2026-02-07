import React from "react";

interface LoadingVideoProps {
  onVideoEnd?: () => void;
}

export default function LoadingVideo({ onVideoEnd }: LoadingVideoProps) {
  return (
    <div className="fixed inset-0 z-50 bg-black">
      {/* Full-screen video (cover) */}
      <video
        src="/videos/loading.mp4"
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 w-full h-full object-cover"
        onEnded={onVideoEnd}
      />

      {/* Overlay content sits above the video */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <div className="w-full max-w-3xl text-center text-white">
          <h2 className="text-2xl md:text-3xl font-bold mb-2 md:mb-3">
            Generating Your Insights...
          </h2>
          <p className="text-gray-200 text-sm md:text-base">
            Analyzing your performance and preparing detailed analytics
          </p>
          {/* Loading animation */}
          <div className="mt-6 flex justify-center">
            <div className="flex space-x-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
        </div>
      </div>
      {/* Gradient footer overlay for legibility */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black/90 to-transparent" />
    </div>
  );
}
