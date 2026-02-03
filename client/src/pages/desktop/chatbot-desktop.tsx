import { Input } from '@/components/ui/input';
import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2, FilePen, Mic, Check, Pencil, X, Home, Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAuth } from '@/contexts/AuthContext';
import { getAccessToken } from '@/lib/auth';
import { useLocation } from 'wouter';
import { API_CONFIG } from '@/config/api';
import { SPEECH_CONFIG } from '@/config/speech';
import HeaderDesktop from '@/components/header-desktop';
import '@/types/speech.d.ts';

// Mobile-specific styles
const mobileStyles = `
  .safe-area-top {
    padding-top: env(safe-area-inset-top);
  }
  .safe-area-bottom {
    padding-bottom: env(safe-area-inset-bottom);
  }
  @media (max-width: 640px) {
    .chatbot-mobile-optimized {
      font-size: 14px;
    }
  }
  /* Prevent zoom on input focus on iOS */
  @media screen and (max-width: 767px) {
    input, textarea, select, button {
      font-size: 16px !important;
    }
  }
  /* Improve touch targets */
  button, .touch-target {
    min-height: 44px;
    min-width: 44px;
  }
`;

interface ChatMessage {
  id: string;
  messageType: 'user' | 'bot';
  messageContent: string;
  createdAt: string;
  processingTime?: number;
}

interface ChatSession {
  id: number;
  chatSessionId: string;
  sessionTitle: string;
  studentName: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  lastMessage: string | null;
}

// Message Content Component with better formatting
interface MessageContentProps {
  content: string;
  isUser: boolean;
}

function MessageContent({ content, isUser }: MessageContentProps) {
  const formatContent = (text: string) => {
    // Split content into paragraphs
    const paragraphs = text.split('\n\n');

    return paragraphs.map((paragraph, pIndex) => {
      if (paragraph.trim() === '') return null;

      // Check if it's a bullet point section
      if (paragraph.includes('•') || paragraph.includes('*') || paragraph.includes('-')) {
        const lines = paragraph.split('\n').filter(line => line.trim());
        const bulletPoints: string[] = [];
        const regularLines: string[] = [];

        lines.forEach(line => {
          const trimmed = line.trim();
          if (trimmed.startsWith('•') || trimmed.startsWith('*') || trimmed.startsWith('-')) {
            bulletPoints.push(trimmed.replace(/^[•*-]\s*/, ''));
          } else {
            regularLines.push(trimmed);
          }
        });

        return (
          <div key={pIndex} className="mb-4 last:mb-0">
            {regularLines.length > 0 && (
              <div className="mb-3">
                {regularLines.map((line, lIndex) => (
                  <p key={lIndex} className="mb-2 last:mb-0">
                    {line}
                  </p>
                ))}
              </div>
            )}
            {bulletPoints.length > 0 && (
              <ul className="space-y-2 ml-0">
                {bulletPoints.map((point, bIndex) => (
                  <li key={bIndex} className="flex items-start">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full mr-3 mt-2.5 flex-shrink-0 ${isUser ? 'bg-blue-200' : 'bg-gray-400'
                      }`}></span>
                    <span className="flex-1 leading-relaxed">{point}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      }

      // Check if it's a heading (contains colons or all caps words)
      if (paragraph.includes(':') && paragraph.split('\n').length === 1) {
        const parts = paragraph.split(':');
        if (parts.length === 2 && parts[0].trim().length < 50) {
          return (
            <div key={pIndex} className="mb-4 last:mb-0">
              <h3 className={`font-semibold mb-2 ${isUser ? 'text-blue-100' : 'text-gray-800'}`}>
                {parts[0].trim()}:
              </h3>
              <p className="leading-relaxed pl-2">
                {parts[1].trim()}
              </p>
            </div>
          );
        }
      }

      // Regular paragraph
      const lines = paragraph.split('\n').filter(line => line.trim());
      return (
        <div key={pIndex} className="mb-4 last:mb-0">
          {lines.map((line, lIndex) => (
            <p key={lIndex} className="mb-2 last:mb-0 leading-relaxed">
              {line.trim()}
            </p>
          ))}
        </div>
      );
    }).filter(Boolean);
  };

  return (
    <div className="space-y-0">
      {formatContent(content)}
    </div>
  );
}

export default function ChatbotPage() {
  const { isAuthenticated, student } = useAuth();
  const [, navigate] = useLocation();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isNewSession, setIsNewSession] = useState(false); // Track if it's a new session waiting for first message
  const [pendingMessage, setPendingMessage] = useState<string | null>(null); // Store message to send after session creation

  // Speech recognition states
  const [isRecording, setIsRecording] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [recognitionLanguage, setRecognitionLanguage] = useState(SPEECH_CONFIG.DEFAULT_LANGUAGE);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);
  // Lock chatbot feature until released
  const [isLocked] = useState(true);

  // Shared textarea props to avoid duplication
  const textareaKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const textareaProps: any = {
    ref: inputRef,
    value: inputMessage,
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setInputMessage(e.target.value),
    onKeyDown: textareaKeyDown,
    placeholder: 'Ask anything...',
    disabled: isLoading,
    className: "flex-1 rounded-md bg-transparent border-none outline-none shadow-none text-base placeholder-[#6B7280] h-10",
  };

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/');
      return;
    }
  }, [isAuthenticated, navigate]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle URL parameters for direct session creation from home page or session switching from header
  useEffect(() => {
    if (!isAuthenticated) return;

    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('sessionId') || urlParams.get('session');
    const message = urlParams.get('message');

    if (sessionId) {
      // Clear URL parameters
      window.history.replaceState({}, '', '/chatbot');

      // For existing sessions, load them directly
      const handleSessionLoad = async () => {
        try {
          // First load sessions to find the target session
          const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSIONS}`;
          const response = await fetch(url, { headers: getAuthHeaders() });

          if (response.ok) {
            const data = await response.json();
            const targetSession = data.results?.find((s: ChatSession) => s.chatSessionId === sessionId);

            if (targetSession) {
              setCurrentSession(targetSession);
              setIsNewSession(false);
              // Load existing messages
              await loadSessionMessages(targetSession.chatSessionId);

              // If there's also a message to send, send it after loading
              if (message) {
                setTimeout(() => {
                  sendMessageToSession(targetSession, decodeURIComponent(message));
                }, 100);
              }
            } else {
              // Session doesn't exist, create new session
              setPendingMessage(message ? decodeURIComponent(message) : null);
              setIsNewSession(true);
              setCurrentSession(null);
              setMessages([]);
            }
          }
        } catch (error) {
          console.error('Failed to handle session load:', error);
        }
      };

      handleSessionLoad();
    }
  }, [isAuthenticated]);

  // Initialize speech recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      setSpeechSupported(true);
      const recognition = new SpeechRecognition();

      // Configure speech recognition using config
      recognition.continuous = SPEECH_CONFIG.RECOGNITION_SETTINGS.continuous;
      recognition.interimResults = SPEECH_CONFIG.RECOGNITION_SETTINGS.interimResults;
      recognition.lang = recognitionLanguage;
      recognition.maxAlternatives = SPEECH_CONFIG.RECOGNITION_SETTINGS.maxAlternatives;

      // Handle speech recognition results
      recognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }

        // Update input field with transcribed text (real-time)
        setInputMessage(transcript);

        // Don't auto-stop recording - let user manually stop with check icon
      };

      // Handle speech recognition start
      recognition.onstart = () => {
        console.log('🎤 Speech recognition started');
        setIsRecording(true);
      };

      // Handle speech recognition end
      recognition.onend = () => {
        console.log('🎤 Speech recognition ended');
        setIsRecording(false);
      };

      // Handle errors
      recognition.onerror = (event: any) => {
        console.error('🎤 Speech recognition error:', event.error);
        setIsRecording(false);

        // Log specific error types for debugging
        switch (event.error) {
          case 'no-speech':
            console.log('🎤 No speech detected');
            break;
          case 'audio-capture':
            console.error('🎤 Audio capture failed - check microphone permissions');
            break;
          case 'not-allowed':
            console.error('🎤 Microphone permission denied');
            break;
          case 'network':
            console.error('🎤 Network error occurred');
            break;
          case 'aborted':
            console.log('🎤 Speech recognition aborted');
            break;
          default:
            console.error('🎤 Unknown error:', event.error);
        }
      };

      // Handle no match
      recognition.onnomatch = () => {
        console.log('🎤 No speech match found');
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    } else {
      console.warn('🎤 Speech Recognition not supported in this browser');
      setSpeechSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, [recognitionLanguage]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const getAuthHeaders = () => {
    const token = getAccessToken();
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  const loadSessionMessages = async (sessionId: string) => {
    try {
      if (!sessionId || sessionId === 'undefined') {
        console.error('❌ Invalid session ID:', sessionId);
        return;
      }

      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSION_MESSAGES(sessionId)}`;
      console.log('📡 Fetching messages from:', url);

      const response = await fetch(url, { headers: getAuthHeaders() });
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
      } else {
        const errorText = await response.text();
        console.error('Failed to load messages:', response.status, errorText);
      }
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  // Helper to generate a session title like ChatGPT (from first message)
  function generateSessionTitleFromMessage(message: string): string {
    if (!message) return 'New Chat';
    let trimmed = message.trim();
    if (trimmed.length > 30) {
      trimmed = trimmed.slice(0, 30).trim() + '...';
    }
    // Capitalize first letter
    return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
  }

  const createNewSession = async (messageToSend?: string) => {
    try {
      setIsLoading(true);
      // Don't create session immediately - just set up UI state
      setCurrentSession(null);
      setMessages([]);
      setIsNewSession(true);
      setError(null);

      // If there's a message to send, store it for later
      if (messageToSend && typeof messageToSend === 'string' && messageToSend.trim()) {
        setPendingMessage(messageToSend.trim());
        // The message will be sent when sendMessage is called
      }
    } catch (error) {
      setError('Failed to start new chat session');
      console.error('Failed to start session:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessageToSession = async (session: ChatSession, message: string) => {
    setError(null);
    setIsLoading(true);
    // Add user message to UI immediately
    const tempUserMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      messageType: 'user',
      messageContent: message,
      createdAt: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMessage]);

    try {
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSION_SEND_MESSAGE(session.chatSessionId)}`;
      console.log('📤 Sending message to:', url);

      const response = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ message }),
      });

      if (response.ok) {
        const data = await response.json();

        setMessages(prev => {
          const withoutTemp = prev.filter(msg => msg.id !== tempUserMessage.id);
          return [
            ...withoutTemp,
            { id: `user-${Date.now()}`, messageType: 'user', messageContent: data.userMessage, createdAt: new Date().toISOString() },
            { id: `bot-${Date.now()}`, messageType: 'bot', messageContent: data.botResponse, createdAt: new Date().toISOString() },
          ];
        });

        // Update the session title based on the first message
        const newTitle = generateSessionTitleFromMessage(message);
        setCurrentSession(prev => {
          if (prev && prev.sessionTitle === 'New Chat') {
            // Update title on backend as well
            fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSION_DETAIL(prev.chatSessionId)}`, {
              method: 'PATCH',
              headers: getAuthHeaders(),
              body: JSON.stringify({ session_title: newTitle })
            }).catch(error => console.error('Failed to update session title:', error));

            return { ...prev, sessionTitle: newTitle };
          }
          return prev;
        });
      } else {
        const errorText = await response.text();
        console.error('Failed to send message:', response.status, errorText);
        throw new Error('Failed to send message');
      }
    } catch (error) {
      console.error('💥 Send message error:', error);
      setError('Failed to send message. Please try again.');
      console.error('Failed to send message:', error);

      // Remove temp message on error
      setMessages(prev => prev.filter(msg => msg.id !== tempUserMessage.id));
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const sendMessage = async () => {
    // Check if there's a pending message from URL or createNewSession
    const messageToSend = pendingMessage || inputMessage.trim();

    if (!messageToSend || isLoading) return;

    // Clear pending message and input
    setPendingMessage(null);
    setInputMessage('');

    setIsNewSession(false); // Hide "Where should we begin?" after first message

    // If no current session, create one first and send message after
    if (!currentSession) {
      // Create the session first
      try {
        setIsLoading(true);
        const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSIONS}`;
        const response = await fetch(url, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ sessionTitle: 'New Chat' }),
        });

        if (response.ok) {
          const newSession = await response.json();
          setCurrentSession(newSession);
          // Now send the message to the newly created session
          await sendMessageToSession(newSession, messageToSend);
        } else {
          const errorText = await response.text();
          console.error('Failed to create session:', response.status, errorText);
          setError('Failed to create session. Please try again.');
        }
      } catch (error) {
        setError('Failed to create session. Please try again.');
        console.error('Failed to create session:', error);
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // Validate current session has required properties
    if (!currentSession.chatSessionId) {
      console.error('❌ Current session missing chatSessionId:', currentSession);
      setError('Invalid session. Please create a new session.');
      return;
    }

    await sendMessageToSession(currentSession, messageToSend);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const switchSession = (session: ChatSession) => {
    setCurrentSession(session);
    setIsNewSession(false); // Switch to existing session, show normal chat UI
    loadSessionMessages(session.chatSessionId);
  };

  // Speech recognition functions
  const toggleSpeechRecognition = () => {
    if (!speechSupported) {
      console.warn('🎤 Speech recognition not supported');
      return;
    }

    if (isRecording) {
      // Stop recording and automatically send the message if there's content
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }

      // Auto-send the message if there's content when clicking the check icon
      setTimeout(() => {
        if (inputMessage.trim()) {
          sendMessage();
        }
      }, 100);
    } else {
      // Start recording
      if (recognitionRef.current) {
        try {
          // Clear previous input before starting new recording
          setInputMessage('');

          recognitionRef.current.start();
        } catch (error) {
          console.error('🎤 Failed to start speech recognition:', error);
          setIsRecording(false);
        }
      }
    }
  };

  if (!isAuthenticated) {
    return null; // Will redirect via useEffect
  }

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50">
      <style dangerouslySetInnerHTML={{ __html: mobileStyles }} />
      <HeaderDesktop />
      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col mt-20 transition-all duration-300 md:ml-64 relative h-[calc(100vh-5rem)]">

        {/* Messages Area - takes remaining space and scrolls */}
        <div className="flex-1 overflow-hidden pb-24">
          <ScrollArea className="h-full">
            <div className="max-w-full mx-auto px-3 py-4">
              {!currentSession || isNewSession ? (
                <div className="flex flex-col items-center justify-center min-h-[70vh] px-4">
                  <h2 className="text-2xl font-bold text-center">Where should we begin?</h2>
                  <p className="text-md text-[#6B7280] text-center">Ask me anything about your learning journey!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((message, index) => (
                    <div
                      key={message.id || index}
                      className={`group relative flex ${message.messageType === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`flex items-start gap-3 max-w-[90%] ${message.messageType === 'user' ? 'flex-row-reverse' : ''}`}>
                        {/* Bubble - optimized for mobile */}
                        <div className={`rounded-xl px-3 pt-2 pb-1 text-sm shadow-sm border ${message.messageType === 'user'
                          ? 'bg-gradient-to-br from-blue-400 to-blue-600 text-white'
                          : 'bg-white border-white transition-colors'
                          }`}>
                          <MessageContent
                            content={message.messageContent}
                            isUser={message.messageType === 'user'}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="flex items-start gap-3">
                        <div className="rounded-xl px-4 py-3 bg-white text-[#1F2937] shadow-sm border border-[#E2E8F0] flex items-center gap-2">
                          <Loader2 className="h-3.5 w-3.5 animate-spin text-[#4F83FF]" />
                          <span className="text-sm text-[#6B7280]">Thinking...</span>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Input Area - fixed at bottom */}
        <div className="absolute bottom-0 left-0 right-0 bg-white border-t px-2 pt-2 pb-6">
          <div className="w-full">
            {error && (
              <div className="mb-3 p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-lg">
                <p className="text-sm text-[#DC2626]">{error}</p>
              </div>
            )}
            <form className="w-full" onSubmit={e => { e.preventDefault(); sendMessage(); }}>
              <div className="flex items-center gap-2 w-full">
                <div className={`flex-1 bg-[#F8FAFC] border border-[#E2E8F0] rounded-full transition-shadow duration-200 ${isRecording ? 'ring-2 ring-[#10B981] ring-offset-2' : ''}`}>
                  <Input
                    ref={inputRef}
                    value={pendingMessage || inputMessage}
                    onChange={e => {
                      if (pendingMessage) {
                        setPendingMessage(null); // Clear pending message when user starts typing
                      }
                      setInputMessage(e.target.value);
                    }}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                      }
                    }}
                    placeholder="Ask anything..."
                    disabled={isLoading}
                    className="w-full bg-transparent border-none outline-none shadow-none text-base placeholder-[#6B7280] rounded-full"
                  />
                </div>
                <div className="flex items-center gap-2">
                  {speechSupported && (
                    <Button
                      type="button"
                      onClick={toggleSpeechRecognition}
                      disabled={isLoading}
                      variant="outline"
                      size="icon"
                      className={`transition-all duration-200 ${isRecording
                        ? 'bg-[#10B981] hover:bg-[#059669] text-white border-[#10B981]'
                        : 'bg-[#E5E7EB] hover:bg-[#CBD5E1] text-[#6B7280] border-[#E5E7EB]'
                        } rounded-full`}
                      title={isRecording ? 'Stop recording and send' : 'Start voice input'}
                      aria-label={isRecording ? 'Stop recording and send' : 'Start voice input'}
                    >
                      {isRecording ? <Check className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                    </Button>
                  )}
                  <Button
                    type="submit"
                    disabled={!(inputMessage.trim() || pendingMessage) || isLoading}
                    size="icon"
                    className="bg-[#4F83FF] hover:bg-[#3B82F6] text-white transition-all duration-200 disabled:opacity-50 rounded-full"
                  >
                    {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
            </form>
            {speechSupported && isRecording && (
              <div className="mt-3 text-center">
                <span className="text-[#10B981] text-sm">
                  🎤 Listening... Click ✓ to stop and send
                </span>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
