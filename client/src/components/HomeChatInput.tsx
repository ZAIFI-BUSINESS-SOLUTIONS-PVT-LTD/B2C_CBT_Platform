import React, { useState, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { Loader2, Mic, Check, Send } from 'lucide-react';

interface HomeChatInputProps {
  isLoading: boolean;
  onSend: (message: string) => void;
  speechSupported: boolean;
  isRecording: boolean;
  onMicClick: () => void;
  inputMessage: string;
  setInputMessage: (msg: string) => void;
}

export const HomeChatInput: React.FC<HomeChatInputProps> = ({
  isLoading,
  onSend,
  speechSupported,
  isRecording,
  onMicClick,
  inputMessage,
  setInputMessage,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (inputMessage.trim()) onSend(inputMessage.trim());
    }
  };

  return (
    <form
      className="w-full"
      onSubmit={e => {
        e.preventDefault();
        if (inputMessage.trim()) onSend(inputMessage.trim());
      }}
    >
      <div className={`flex items-center w-full bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-4 py-2 transition-shadow duration-200 ${isRecording ? 'ring-2 ring-[#10B981] ring-offset-2 chatbot-glow' : ''}`}> 
        {/* Smooth green glow animation for mic listening */}
        <style>{`
          .chatbot-glow {
            animation: chatbot-glow-anim 1.6s ease-in-out infinite;
          }
          @keyframes chatbot-glow-anim {
            0% { box-shadow: 0 0 0 0 #10B98133, 0 0 0 0 #10B98133; }
            50% { box-shadow: 0 0 12px 4px #10B98166, 0 0 24px 8px #10B98133; }
            100% { box-shadow: 0 0 0 0 #10B98133, 0 0 0 0 #10B98133; }
          }
        `}</style> 
        <Input
          ref={inputRef}
          value={inputMessage}
          onChange={e => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask anything..."
          disabled={isLoading}
          className="flex-1 bg-transparent border-none outline-none shadow-none text-lg placeholder-[#6B7280]"
        />
        {speechSupported && (
          <button
            type="button"
            onClick={onMicClick}
            disabled={isLoading}
            className={`ml-2 p-2 rounded-full transition-all duration-200 ${
              isRecording 
                ? 'bg-[#10B981] hover:bg-[#059669] text-white' 
                : 'bg-[#E5E7EB] hover:bg-[#CBD5E1] text-[#6B7280]'
            }`}
            title={isRecording ? 'Stop recording and send' : 'Start voice input'}
            aria-label={isRecording ? 'Stop recording and send' : 'Start voice input'}
          >
            {isRecording ? <Check className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </button>
        )}
        <button
          type="submit"
          disabled={!inputMessage.trim() || isLoading}
          className="ml-2 p-2 rounded-full bg-[#4F83FF] hover:bg-[#3B82F6] text-white transition-all duration-200 disabled:opacity-50"
        >
          {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
        </button>
      </div>
    </form>
  );
};
