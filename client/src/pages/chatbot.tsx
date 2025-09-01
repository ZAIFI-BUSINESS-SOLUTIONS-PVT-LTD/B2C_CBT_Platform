// import { Input } from '@/components/ui/input';
import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle, Send, Bot, User, Loader2, RotateCcw, Plus, Menu, Mic, MicOff, Check, Pencil, X, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAuth } from '@/contexts/AuthContext';
import { getAccessToken } from '@/lib/auth';
import { useLocation } from 'wouter';
import { API_CONFIG } from '@/config/api';
import { SPEECH_CONFIG } from '@/config/speech';
import '@/types/speech.d.ts';

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
                    <span className={`inline-block w-1.5 h-1.5 rounded-full mr-3 mt-2.5 flex-shrink-0 ${
                      isUser ? 'bg-blue-200' : 'bg-gray-400'
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
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true); // Sidebar toggle remains for responsive
  const [editingTitleId, setEditingTitleId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState('');
  const [renaming, setRenaming] = useState(false);
  // PATCH session title
  const renameSessionTitle = async (session: ChatSession, title: string) => {
    setRenaming(true);
    try {
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSION_DETAIL(session.chatSessionId)}`;
      const response = await fetch(url, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ session_title: title })
      });
      if (response.ok) {
        // Update session in state
        setSessions(prev => prev.map(s => s.chatSessionId === session.chatSessionId ? { ...s, sessionTitle: title } : s));
        if (currentSession?.chatSessionId === session.chatSessionId) {
          setCurrentSession(cs => cs ? { ...cs, sessionTitle: title } : cs);
        }
        setEditingTitleId(null);
      } else {
        // Optionally show error toast
        console.error('Failed to rename session title');
      }
    } catch (e) {
      console.error('Rename error', e);
    } finally {
      setRenaming(false);
    }
  };
  const [isNewSession, setIsNewSession] = useState(false); // Track if it's a new session waiting for first message
  
  // Speech recognition states
  const [isRecording, setIsRecording] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [recognitionLanguage, setRecognitionLanguage] = useState(SPEECH_CONFIG.DEFAULT_LANGUAGE);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);

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

  // Load chat sessions on component mount
  useEffect(() => {
    if (isAuthenticated && student) {
      loadChatSessions();
    }
  }, [isAuthenticated, student]);

  // Handle URL parameters for direct session creation from home page
  useEffect(() => {
    if (!isAuthenticated) return;
    
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('sessionId');
    const message = urlParams.get('message');
    
    if (sessionId && message) {
      // Clear URL parameters
      window.history.replaceState({}, '', '/chatbot');
      
      // Find the session and send the message
      const handleRedirectMessage = async () => {
        try {
          // First load sessions to find the new session
          const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSIONS}`;
          const response = await fetch(url, { headers: getAuthHeaders() });
          
          if (response.ok) {
            const data = await response.json();
            const targetSession = data.results?.find((s: ChatSession) => s.chatSessionId === sessionId);
            
            if (targetSession) {
              setCurrentSession(targetSession);
              setSessions(data.results || []);
              setIsNewSession(false);
              
              // Send the message automatically
              setTimeout(() => {
                sendMessageToSession(targetSession, decodeURIComponent(message));
              }, 100);
            }
          }
        } catch (error) {
          console.error('Failed to handle redirect message:', error);
        }
      };
      
      handleRedirectMessage();
    }
  }, [isAuthenticated, student]);

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
        
        // Manually adjust textarea height after setting the transcribed text
        setTimeout(() => {
          if (inputRef.current) {
            inputRef.current.style.height = 'auto';
            inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
          }
        }, 0);
        
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
    console.log('🔑 Auth token:', token ? 'Present' : 'Missing');
    console.log('🌐 API Base URL:', API_CONFIG.BASE_URL);
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  const loadChatSessions = async () => {
    try {
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSIONS}`;
      console.log('📡 Loading chat sessions from:', url);
      
      const response = await fetch(url, {
        headers: getAuthHeaders(),
      });

      console.log('📨 Response status:', response.status);
      console.log('📨 Response headers:', Object.fromEntries(response.headers.entries()));

      if (response.ok) {
        const data = await response.json();
        console.log('📊 Chat sessions data:', data);
        setSessions(data.results || []);
        
        // If there are existing sessions, load the most recent one
        if (data.results && data.results.length > 0) {
          const mostRecent = data.results[0];
          console.log('🔍 Most recent session:', mostRecent);
          console.log('🆔 Session ID:', mostRecent.chatSessionId);
          setCurrentSession(mostRecent);
          
          // Only load messages if chatSessionId exists
          if (mostRecent.chatSessionId) {
            loadSessionMessages(mostRecent.chatSessionId);
          } else {
            console.error('❌ chatSessionId is missing from session data');
          }
        } else {
          console.log('📝 No existing sessions found - ready for new session');
          // Clear current session if no sessions exist
          setCurrentSession(null);
          setMessages([]);
          setIsNewSession(true); // Show "Where should we begin?" for first time users
        }
      } else {
        const errorText = await response.text();
        console.error('❌ Failed to load sessions:', response.status, errorText);
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
    }
  };

  const loadSessionMessages = async (sessionId: string) => {
    try {
      console.log('📥 Loading messages for session ID:', sessionId);
      
      if (!sessionId || sessionId === 'undefined') {
        console.error('❌ Invalid session ID:', sessionId);
        return;
      }
      
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSION_MESSAGES(sessionId)}`;
      console.log('📡 Fetching messages from:', url);
      
      const response = await fetch(url, {
        headers: getAuthHeaders(),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('📨 Messages data:', data);
        setMessages(data.messages || []);
      } else {
        const errorText = await response.text();
        console.error('❌ Failed to load messages:', response.status, errorText);
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
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSIONS}`;
      console.log('🆕 Creating new session at:', url);

      const response = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          sessionTitle: 'New Chat'  // Backend will update this when first message is sent
        }),
      });

      console.log('📨 Create session response status:', response.status);

      if (response.ok) {
        const newSession = await response.json();
        console.log('✅ New session created:', newSession);
        setCurrentSession(newSession);
        setMessages([]);
        setSessions(prev => [newSession, ...prev]);
        setIsNewSession(true); // Show "Where should we begin?" for new session

        // Only send message if it's a valid non-empty string
        if (messageToSend && typeof messageToSend === 'string' && messageToSend.trim()) {
          setTimeout(() => {
            sendMessageToSession(newSession, messageToSend);
          }, 100);
        }
      } else {
        const errorText = await response.text();
        console.error('❌ Failed to create session:', response.status, errorText);
        throw new Error('Failed to create session');
      }
    } catch (error) {
      setError('Failed to create new chat session');
      console.error('Failed to create session:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessageToSession = async (session: ChatSession, message: string) => {
    setError(null);
    setIsLoading(true);

    console.log('📤 Sending message to session:', session.chatSessionId);

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
        body: JSON.stringify({
          message: message,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('✅ Message sent successfully:', data);
        
        // Remove temp message and add actual messages
        setMessages(prev => {
          const withoutTemp = prev.filter(msg => msg.id !== tempUserMessage.id);
          return [
            ...withoutTemp,
            {
              id: `user-${Date.now()}`,
              messageType: 'user',
              messageContent: data.userMessage,
              createdAt: new Date().toISOString(),
            },
            {
              id: `bot-${Date.now()}`,
              messageType: 'bot',
              messageContent: data.botResponse,
              createdAt: new Date().toISOString(),
            }
          ];
        });

        // Update session in list
        setSessions(prev => 
          prev.map(sessionItem => 
            sessionItem.chatSessionId === session.chatSessionId
              ? { 
                  ...sessionItem, 
                  updatedAt: new Date().toISOString(), 
                  lastMessage: data.botResponse,
                  // Update session title if this was the first message (backend updated it)
                  sessionTitle: sessionItem.messageCount === 0 ? generateSessionTitleFromMessage(message) : sessionItem.sessionTitle
                }
              : sessionItem
          )
        );

        // Update current session title if this was the first message
        if (currentSession && currentSession.messageCount === 0) {
          setCurrentSession(prev => prev ? {
            ...prev,
            sessionTitle: generateSessionTitleFromMessage(message)
          } : prev);
        }
      } else {
        const errorText = await response.text();
        console.error('❌ Failed to send message:', response.status, errorText);
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
    if (!inputMessage.trim() || isLoading) return;

    const messageToSend = inputMessage.trim();
    setInputMessage('');
    
    // Reset textarea height after clearing input
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.style.height = 'auto';
        inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
      }
    }, 0);
    
    setIsNewSession(false); // Hide "Where should we begin?" after first message

    // If no current session, create one first and send message after
    if (!currentSession) {
      await createNewSession(messageToSend);
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
          
          // Reset textarea height after clearing input
          setTimeout(() => {
            if (inputRef.current) {
              inputRef.current.style.height = 'auto';
              inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
            }
          }, 0);
          
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
    <div className="flex h-screen bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50 text-[#1F2937]">
      {/* Sidebar - minimal, only new chat and chats */}
      <div className={`${sidebarOpen ? 'w-72' : 'w-0'} transition-all duration-300 bg-white border-r border-[#E2E8F0] flex flex-col overflow-hidden shadow-lg`}>
        <div className="p-4 border-b border-[#E2E8F0]">
          <Button 
            onClick={() => createNewSession()}
            disabled={isLoading}
            className="w-full bg-[#4F83FF] hover:bg-[#3B82F6] text-white rounded-xl py-3 flex items-center justify-center gap-2 font-semibold text-base shadow-md"
          >
            <Plus className="h-5 w-5" />
            New chat
          </Button>
        </div>
        <ScrollArea className="flex-1 px-2 pt-2">
          <div className="space-y-1">
            {sessions.map((session) => {
              const isActive = currentSession?.chatSessionId === session.chatSessionId;
              return (
                <div
                  key={session.chatSessionId}
                  className={`cursor-pointer rounded-lg px-4 py-3 hover:bg-[#F8FAFC] transition-colors font-medium text-base ${
                    isActive ? 'bg-[#E8F0FF] text-[#1F2937]' : 'text-[#6B7280]'
                  } flex items-center justify-between gap-2`}
                  onClick={() => switchSession(session)}
                >
                  <div className="flex-1 truncate">
                    {editingTitleId === session.chatSessionId ? (
                      <form
                        className="flex items-center gap-1"
                        onSubmit={e => {
                          e.preventDefault();
                          if (newTitle.trim() && !renaming) {
                            renameSessionTitle(session, newTitle.trim());
                          }
                        }}
                      >
                        <input
                          value={newTitle}
                          onChange={e => setNewTitle(e.target.value)}
                          autoFocus
                          className="h-7 text-base px-2 py-1 border border-[#CBD5E1] rounded"
                          onClick={e => e.stopPropagation()}
                          onBlur={() => setEditingTitleId(null)}
                          maxLength={40}
                          disabled={renaming}
                          type="text"
                        />
                        <button type="submit" className="ml-1 text-[#4F83FF] hover:text-[#2563EB]" disabled={renaming}>
                          <Check className="h-4 w-4" />
                        </button>
                        <button type="button" className="ml-1 text-[#DC2626] hover:text-[#B91C1C]" onClick={() => setEditingTitleId(null)}>
                          <X className="h-4 w-4" />
                        </button>
                      </form>
                    ) : (
                      <span className="flex items-center gap-1 w-full">
                        <span className="truncate max-w-[120px] md:max-w-[160px] lg:max-w-[200px]">{session.sessionTitle || `Chat ${session.id}`}</span>
                        {isActive && (
                          <button
                            type="button"
                            className="ml-1 flex-shrink-0 text-[#4F83FF] hover:text-[#2563EB]"
                            title="Rename chat"
                            onClick={e => {
                              e.stopPropagation();
                              setEditingTitleId(session.chatSessionId);
                              setNewTitle(session.sessionTitle || '');
                            }}
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                        )}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-[#94A3B8] min-w-[70px] text-right">
                    {new Date(session.updatedAt).toLocaleDateString()}
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header - minimal, centered */}
        <div className="bg-white border-b border-[#E2E8F0] p-6 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/')}
              className="text-[#4F83FF] hover:text-[#2563EB] hover:bg-[#F0F7FF]"
              title="Go to Home"
            >
              <Home className="h-5 w-5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-[#6B7280] hover:text-[#1F2937] hover:bg-[#F8FAFC]"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <h1 className="text-xl font-bold text-[#1F2937] tracking-tight">AI Tutor</h1>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="max-w-5xl mx-auto px-4 py-16">
              {!currentSession || isNewSession ? (
                <div className="flex flex-col items-center justify-center h-[60vh]">
                  <h2 className="text-3xl font-bold text-[#1F2937] mb-6">Where should we begin?</h2>
                  <div className="w-full max-w-xl">
                    <div className="rounded-2xl bg-white border border-[#E2E8F0] shadow-lg px-6 py-8 flex flex-col items-center">
                      <form className="w-full" onSubmit={e => { e.preventDefault(); sendMessage(); }}>
                        <div className={`flex items-center w-full bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-4 py-2 transition-shadow duration-200 ${isRecording ? 'ring-2 ring-[#10B981] ring-offset-2 chatbot-glow' : ''}`}> 
                          <textarea
                            ref={inputRef}
                            value={inputMessage}
                            onChange={e => {
                              setInputMessage(e.target.value);
                              if (inputRef.current) {
                                inputRef.current.style.height = 'auto';
                                inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
                              }
                            }}
                            onInput={() => {
                              if (inputRef.current) {
                                inputRef.current.style.height = 'auto';
                                inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
                              }
                            }}
                            onKeyDown={handleKeyPress}
                            placeholder="Ask anything..."
                            disabled={isLoading}
                            rows={1}
                            className="flex-1 rounded-md bg-transparent border-none outline-none shadow-none text-lg placeholder-[#6B7280] min-h-[44px] max-h-40 resize-none overflow-hidden whitespace-pre-wrap"
                            style={{lineHeight: '1.6'}}
                          />
                          {speechSupported && (
                            <button
                              type="button"
                              onClick={toggleSpeechRecognition}
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
                      {speechSupported && isRecording && (
                        <div className="mt-4 text-center">
                          <span className="text-[#10B981] text-sm">
                            🎤 Listening... Click ✓ to stop and send
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {messages.map((message, index) => (
                    <div
                      key={message.id || index}
                      className={`group relative flex ${message.messageType === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`flex items-start gap-4 max-w-[85%] ${message.messageType === 'user' ? 'flex-row-reverse' : ''}`}>
                        {/* Avatar */}
                        <div className="flex-shrink-0 mt-1">
                          {message.messageType === 'user' ? (
                            <div className="w-8 h-8 bg-[#4F83FF] rounded-full flex items-center justify-center shadow-md">
                              <User className="h-4 w-4 text-white" />
                            </div>
                          ) : (
                            <div className="w-8 h-8 bg-gradient-to-br from-[#10B981] to-[#4F83FF] rounded-full flex items-center justify-center shadow-md">
                              <Bot className="h-4 w-4 text-white" />
                            </div>
                          )}
                        </div>
                        {/* Bubble */}
                        <div className={`rounded-2xl px-6 py-5 text-base shadow-sm border ${
                          message.messageType === 'user' 
                            ? 'bg-[#4F83FF] text-white border-[#4F83FF]' 
                            : 'bg-white text-[#1F2937] border-[#E2E8F0] hover:border-[#CBD5E1] transition-colors'
                        }`}>
                          <MessageContent 
                            content={message.messageContent} 
                            isUser={message.messageType === 'user'} 
                          />
                          <div className={`text-xs mt-3 text-right ${
                            message.messageType === 'user' ? 'text-blue-100' : 'text-[#6B7280]'
                          }`}>
                            {new Date(message.createdAt).toLocaleTimeString()}
                            {message.processingTime && (
                              <span className="ml-2">
                                • {message.processingTime.toFixed(1)}s
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="flex items-start gap-4">
                        <div className="w-8 h-8 bg-gradient-to-br from-[#10B981] to-[#4F83FF] rounded-full flex items-center justify-center shadow-md mt-1">
                          <Bot className="h-4 w-4 text-white" />
                        </div>
                        <div className="rounded-2xl px-6 py-5 bg-white text-[#1F2937] shadow-sm border border-[#E2E8F0] flex items-center gap-3">
                          <Loader2 className="h-4 w-4 animate-spin text-[#4F83FF]" />
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

        {/* Input Area - only show if session is active and not in new session mode */}
        {currentSession && !isNewSession && (
          <div className="bg-white border-t border-[#E2E8F0] p-6 shadow-lg">
            <div className="max-w-2xl mx-auto">
              {error && (
                <div className="mb-3 p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-lg">
                  <p className="text-sm text-[#DC2626]">{error}</p>
                </div>
              )}
              <form className="w-full" onSubmit={e => { e.preventDefault(); sendMessage(); }}>
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
                  <textarea
                    ref={inputRef}
                    value={inputMessage}
                    onChange={e => {
                      setInputMessage(e.target.value);
                      if (inputRef.current) {
                        inputRef.current.style.height = 'auto';
                        inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
                      }
                    }}
                    onInput={() => {
                      if (inputRef.current) {
                        inputRef.current.style.height = 'auto';
                        inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
                      }
                    }}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                      }
                    }}
                    placeholder="Ask anything..."
                    disabled={isLoading}
                    rows={1}
                    className="flex-1 rounded-md bg-transparent border-none outline-none shadow-none text-lg placeholder-[#6B7280] min-h-[44px] max-h-40 resize-none overflow-hidden whitespace-pre-wrap"
                    style={{lineHeight: '1.6'}}
                  />
                  {speechSupported && (
                    <button
                      type="button"
                      onClick={toggleSpeechRecognition}
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
              <p className="text-xs text-[#6B7280] mt-2 text-center">
                Press Enter to send {speechSupported ? '• Click mic for voice input' : ''} - Let your tutor take it from here!
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
