import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle, Send, Bot, User, Loader2, RotateCcw, Plus, Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAuth } from '@/contexts/AuthContext';
import { getAccessToken } from '@/lib/auth';
import { useLocation } from 'wouter';
import { API_CONFIG } from '@/config/api';

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
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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

  const createNewSession = async (messageToSend?: string) => {
    try {
      setIsLoading(true);
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSIONS}`;
      console.log('🆕 Creating new session at:', url);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          sessionTitle: `Chat Session ${new Date().toLocaleDateString()}`
        }),
      });

      console.log('📨 Create session response status:', response.status);

      if (response.ok) {
        const newSession = await response.json();
        console.log('✅ New session created:', newSession);
        setCurrentSession(newSession);
        setMessages([]);
        setSessions(prev => [newSession, ...prev]);
        
        // Only load welcome message if no message to send
        if (!messageToSend) {
          loadSessionMessages(newSession.chatSessionId);
        }
        
        // If there's a message to send after session creation, send it
        if (messageToSend) {
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
              ? { ...sessionItem, updatedAt: new Date().toISOString(), lastMessage: data.botResponse }
              : sessionItem
          )
        );
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
    loadSessionMessages(session.chatSessionId);
  };

  if (!isAuthenticated) {
    return null; // Will redirect via useEffect
  }

  return (
    <div className="flex h-screen bg-[#23272f] text-white">
      {/* Sidebar - minimal, only new chat and chats */}
      <div className={`${sidebarOpen ? 'w-72' : 'w-0'} transition-all duration-300 bg-[#18181c] border-r border-[#23272f] flex flex-col overflow-hidden shadow-lg`}>
        <div className="p-4 border-b border-[#23272f]">
          <Button 
            onClick={createNewSession}
            disabled={isLoading}
            className="w-full bg-[#23272f] hover:bg-[#23272f] text-white rounded-xl py-3 flex items-center justify-center gap-2 font-semibold text-base"
          >
            <Plus className="h-5 w-5" />
            New chat
          </Button>
        </div>
        <ScrollArea className="flex-1 px-2 pt-2">
          <div className="space-y-1">
            {sessions.map((session) => (
              <div
                key={session.chatSessionId}
                className={`cursor-pointer rounded-lg px-4 py-3 hover:bg-[#23272f] transition-colors font-medium text-base ${
                  currentSession?.chatSessionId === session.chatSessionId 
                    ? 'bg-[#23272f] text-white' 
                    : 'text-gray-300'
                }`}
                onClick={() => switchSession(session)}
              >
                <div className="truncate">
                  {session.sessionTitle || `Chat ${session.id}`}
                </div>
                <div className="text-xs text-gray-500">
                  {new Date(session.updatedAt).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header - minimal, centered */}
        <div className="bg-[#23272f] border-b border-[#23272f] p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-gray-400 hover:text-white"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <h1 className="text-2xl font-bold text-white tracking-tight">Chatbot</h1>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="max-w-2xl mx-auto px-4 py-16">
              {!currentSession ? (
                <div className="flex flex-col items-center justify-center h-[60vh]">
                  <h2 className="text-3xl font-bold text-white mb-6">Where should we begin?</h2>
                  <div className="w-full max-w-xl">
                    <div className="rounded-2xl bg-[#23272f] border border-[#23272f] shadow-lg px-6 py-8 flex flex-col items-center">
                      <Input
                        ref={inputRef}
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Ask anything..."
                        disabled={isLoading}
                        className="flex-1 bg-[#343541] text-white placeholder-gray-400 border-none focus:ring-0 focus:outline-none text-lg pl-4 rounded-xl"
                      />
                      <Button 
                        onClick={sendMessage} 
                        disabled={!inputMessage.trim() || isLoading}
                        size="lg"
                        className="mt-6 w-full bg-[#343541] hover:bg-[#23272f] text-white rounded-xl px-4 py-3 font-semibold text-lg"
                      >
                        {isLoading ? (
                          <Loader2 className="h-5 w-5 animate-spin" />
                        ) : (
                          <Send className="h-5 w-5" />
                        )}
                        <span className="ml-2">Send</span>
                      </Button>
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
                      <div className={`flex items-end gap-3 max-w-[80%] ${message.messageType === 'user' ? 'flex-row-reverse' : ''}`}>
                        {/* Avatar */}
                        <div className="flex-shrink-0">
                          {message.messageType === 'user' ? (
                            <div className="w-8 h-8 bg-[#6e56cf] rounded-full flex items-center justify-center">
                              <User className="h-4 w-4 text-white" />
                            </div>
                          ) : (
                            <div className="w-8 h-8 bg-gradient-to-br from-green-400 to-blue-500 rounded-full flex items-center justify-center">
                              <Bot className="h-4 w-4 text-white" />
                            </div>
                          )}
                        </div>
                        {/* Bubble */}
                        <div className={`rounded-2xl px-5 py-4 text-base ${message.messageType === 'user' ? 'bg-[#343541] text-white' : 'bg-[#18181c] text-gray-100'} shadow-md`}>
                          {message.messageContent}
                          <div className="text-xs text-gray-500 mt-2 text-right">
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
                      <div className="rounded-2xl px-5 py-4 bg-[#18181c] text-gray-100 shadow-md flex items-center gap-3">
                        <Bot className="h-4 w-4 text-white" />
                        <span className="text-sm text-gray-400">Thinking...</span>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Input Area - only show if session is active */}
        {currentSession && (
          <div className="bg-[#23272f] border-t border-[#23272f] p-6">
            <div className="max-w-2xl mx-auto">
              {error && (
                <div className="mb-3 p-3 bg-red-900/50 border border-red-800 rounded-lg">
                  <p className="text-sm text-red-200">{error}</p>
                </div>
              )}
              <div className="flex gap-3">
                <Input
                  ref={inputRef}
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask anything..."
                  disabled={isLoading}
                  className="flex-1 bg-[#343541] text-white placeholder-gray-400 border-none focus:ring-0 focus:outline-none text-lg pl-4 rounded-xl"
                />
                <Button 
                  onClick={sendMessage} 
                  disabled={!inputMessage.trim() || isLoading}
                  size="lg"
                  className="bg-[#343541] hover:bg-[#23272f] text-white rounded-xl px-4 py-3 font-semibold text-lg"
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Send className="h-5 w-5" />
                  )}
                  <span className="ml-2">Send</span>
                </Button>
              </div>
              <p className="text-xs text-gray-500 mt-2 text-center">
                Press Enter to send - Let your tutor take it from here!.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
