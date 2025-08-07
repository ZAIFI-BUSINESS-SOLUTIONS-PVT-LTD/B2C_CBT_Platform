import React, { useState } from 'react';
import { MessageCircle, X, Bot } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { useLocation } from 'wouter';

export function FloatingChatbot() {
  const { isAuthenticated } = useAuth();
  const [location, navigate] = useLocation();
  const [showTooltip, setShowTooltip] = useState(false);

  // Debug log to check if component is rendering
  console.log('FloatingChatbot - isAuthenticated:', isAuthenticated, 'location:', location);

  // Always render a small test element to debug visibility
  if (!isAuthenticated) {
    return null;
  }

  if (location === '/chatbot') {
    console.log('FloatingChatbot - On chatbot page, showing test element');
    return (
      <div className="fixed top-4 right-4 z-[9999] bg-yellow-500 text-black p-2 rounded text-xs">
        On Chatbot
      </div>
    );
  }

  console.log('FloatingChatbot - Rendering chatbot icon');

  const handleChatbotClick = () => {
    navigate('/chatbot');
  };

  return (
    <div className="fixed bottom-6 right-6 z-[9999]" style={{ zIndex: 9999 }}>
      {/* Speech bubble tooltip */}
      {showTooltip && (
        <div className="absolute bottom-20 right-0 mb-2">
          <div className="bg-white px-4 py-3 rounded-lg shadow-lg border border-gray-200 text-gray-800 text-sm font-medium whitespace-nowrap max-w-xs">
            👋 I'm here to help you with NEET prep!
            {/* Speech bubble tail */}
            <div className="absolute top-full right-6 w-0 h-0 border-l-8 border-r-8 border-t-8 border-transparent border-t-white"></div>
            <div className="absolute top-full right-6 w-0 h-0 border-l-8 border-r-8 border-t-8 border-transparent border-t-gray-200 transform translate-y-px"></div>
          </div>
        </div>
      )}

      {/* Main floating button */}
      <div className="relative">
        {/* Pulsing ring animation */}
        <div className="absolute inset-0 w-16 h-16 bg-blue-400 rounded-full animate-ping opacity-20"></div>
        <div className="absolute inset-0 w-16 h-16 bg-blue-400 rounded-full animate-pulse opacity-30"></div>
        
        {/* Chat button */}
        <Button
          onClick={handleChatbotClick}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          className="relative w-16 h-16 rounded-full bg-gradient-to-br from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 shadow-xl hover:shadow-2xl transition-all duration-300 transform hover:scale-105 flex items-center justify-center group border-4 border-white"
          size="icon"
        >
          {/* Custom chatbot icon */}
          <Bot className="h-8 w-8 text-white drop-shadow-sm" />
          
          {/* Optional notification dot for new messages */}
          {/* <div className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full border-2 border-white text-xs text-white flex items-center justify-center font-bold">
            1
          </div> */}
        </Button>
      </div>
    </div>
  );
}
