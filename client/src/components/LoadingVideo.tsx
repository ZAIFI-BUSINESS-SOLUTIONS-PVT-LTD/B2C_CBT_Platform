import React from "react";

export default function LoadingVideo() {
  return (
    <div className="fixed inset-0 z-50 bg-black flex flex-col items-center justify-center">
      {/* Full-screen video container */}
      <div className="w-full h-full flex items-center justify-center">
        <video
          src="/videos/loading.mp4"
          autoPlay
          loop
          muted
          playsInline
          className="w-full h-full object-contain md:object-cover"
        />
      </div>
      
      {/* Overlay text */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/50 to-transparent p-6 md:p-8">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-2 md:mb-3">
            Generating Your Insights...
          </h2>
          <p className="text-gray-200 text-sm md:text-base">
            Analyzing your performance and preparing detailed analytics
          </p>
          {/* Loading animation */}
          <div className="mt-4 md:mt-6 flex justify-center">
            <div className="flex space-x-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
