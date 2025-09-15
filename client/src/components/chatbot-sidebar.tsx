import React, { useState, useEffect } from 'react';
import { Plus, Check, X, Pencil, FilePen, MoreHorizontal, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { getAccessToken } from '@/lib/auth';
import { API_CONFIG } from '@/config/api';
import { StudentProfile } from '@/types/api';
import { useAuth } from '@/contexts/AuthContext';
import { useLocation } from 'wouter';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

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

interface ChatbotSidebarProps {
  sidebarOpen: boolean;
  currentSession: ChatSession | null;
  isLoading: boolean;
  onCloseSidebar: () => void;
  onCreateNewSession: (messageToSend?: string) => Promise<void>;
  onSwitchSession: (session: ChatSession) => void;
  onLoadSessionMessages: (sessionId: string) => Promise<void>;
  onSetCurrentSession: (session: ChatSession | null) => void;
  onSetSessions: (sessions: ChatSession[]) => void;
  onSetIsNewSession: (isNew: boolean) => void;
  onUpdateSessionTitle: (sessionId: string, title: string) => void;
}

export default function ChatbotSidebar({
  sidebarOpen,
  currentSession,
  isLoading,
  onCloseSidebar,
  onCreateNewSession,
  onSwitchSession,
  onLoadSessionMessages,
  onSetCurrentSession,
  onSetSessions,
  onSetIsNewSession,
  onUpdateSessionTitle,
}: ChatbotSidebarProps) {
  const { student } = useAuth();
  const [, navigate] = useLocation();

  const initials = React.useMemo(() => {
    const name = (student && (student.fullName || student.email)) || "";
    if (!name) return "ST";
    return name
      .split(" ")
      .map((w: string) => w.charAt(0))
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }, [student]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [newTitle, setNewTitle] = useState('');
  const [renaming, setRenaming] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [renamingSession, setRenamingSession] = useState<ChatSession | null>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownOpen && !(event.target as Element).closest('.dropdown-container')) {
        setDropdownOpen(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [dropdownOpen]);

  // Load chat sessions when sidebar opens
  useEffect(() => {
    if (sidebarOpen) {
      loadChatSessions();
    }
  }, [sidebarOpen]);

  const getAuthHeaders = () => {
    const token = getAccessToken();
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  const loadChatSessions = async () => {
    try {
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSIONS}`;
      const response = await fetch(url, { headers: getAuthHeaders() });

      if (response.ok) {
        const data = await response.json();
        const loadedSessions = data.results || [];
        setSessions(loadedSessions);
        onSetSessions(loadedSessions);

        if (loadedSessions.length > 0) {
          // Only set current session to most recent if no session is currently selected
          if (!currentSession) {
            const mostRecent = loadedSessions[0];
            onSetCurrentSession(mostRecent);
            if (mostRecent.chatSessionId) {
              onLoadSessionMessages(mostRecent.chatSessionId);
            } else {
              console.error('chatSessionId is missing from session data');
            }
          }
        } else {
          onSetCurrentSession(null);
          onSetIsNewSession(true);
        }
      } else {
        const errorText = await response.text();
        console.error('Failed to load sessions:', response.status, errorText);
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
    }
  };

  const createNewSession = async () => {
    try {
      await onCreateNewSession();
      onCloseSidebar();
      // Don't reload sessions here - session won't be created until first message is sent
      // Sessions will be reloaded when the first message creates the session
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const switchSession = (session: ChatSession) => {
    onSwitchSession(session);
    onCloseSidebar();
  };

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
        // Update session in local state
        setSessions(prev => prev.map(s => s.chatSessionId === session.chatSessionId ? { ...s, sessionTitle: title } : s));
        onUpdateSessionTitle(session.chatSessionId, title);
      } else {
        console.error('Failed to rename session title');
      }
    } catch (e) {
      console.error('Rename error', e);
    } finally {
      setRenaming(false);
    }
  };

  const deleteSession = async (session: ChatSession) => {
    const confirmDelete = window.confirm(`Are you sure you want to delete "${session.sessionTitle || `Chat ${session.id}`}"? This action cannot be undone.`);

    if (!confirmDelete) return;

    try {
      const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSION_DETAIL(session.chatSessionId)}`;
      const response = await fetch(url, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });

      if (response.ok) {
        // Remove session from local state
        setSessions(prev => prev.filter(s => s.chatSessionId !== session.chatSessionId));

        // If the deleted session was the current session, clear it
        if (currentSession?.chatSessionId === session.chatSessionId) {
          onSetCurrentSession(null);
          onSetIsNewSession(true);
        }
      } else {
        console.error('Failed to delete session');
        alert('Failed to delete session. Please try again.');
      }
    } catch (e) {
      console.error('Delete error', e);
      alert('Failed to delete session. Please try again.');
    }
  };

  if (!sidebarOpen) return null;

  return (
    <div className="fixed inset-0 z-40">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onCloseSidebar} />
      {/* Sidebar */}
      <div className="relative z-50">
        <div className="fixed left-0 top-0 h-full w-80 bg-white shadow-xl overflow-hidden transform transition-transform duration-300 ease-in-out flex flex-col" onClick={e => e.stopPropagation()}>
          <div className="flex items-center justify-between px-2 py-1 border-b border-[#E2E8F0] flex-shrink-0">
            <h3 className="text-lg font-semibold text-[#1F2937]">Chat Sessions</h3>
            <Button
              onClick={onCloseSidebar}
              variant="ghost"
              size="icon"
              className="aspect-square hover:bg-[#F8FAFC] rounded-full transition-colors"
            >
              <X className="h-5 w-5 text-[#6B7280]" />
            </Button>
          </div>
          <div className="p-2 border-b border-[#E2E8F0] flex-shrink-0">
            <Button
              onClick={createNewSession}
              disabled={isLoading}
              className="w-full bg-[#4F83FF] hover:bg-[#3B82F6] text-white rounded-lg py-3 flex items-center justify-center gap-2 font-semibold text-base shadow-md"
            >
              <FilePen className="h-4 w-4" />
              New chat
            </Button>
            <h1 className="mt-3 text-lg font-semibold text-[#1F2937]">History</h1>
          </div>
          <ScrollArea className="flex-1 min-h-0">
            <div className="p-2 space-y-1">
              {sessions.length === 0 ? (
                <div className="text-center py-8 text-[#6B7280] text-sm">
                  No chat sessions yet
                </div>
              ) : (
                sessions.map((session) => {
                  const isActive = currentSession?.chatSessionId === session.chatSessionId;
                  const isDropdownOpen = dropdownOpen === session.chatSessionId;
                  return (
                    <div key={session.chatSessionId} className="relative">
                      <div
                        className={`cursor-pointer rounded-lg pl-4 hover:bg-[#F8FAFC] transition-colors font-medium text-sm ${isActive ? 'bg-[#E8F0FF] text-[#1F2937]' : 'text-[#6B7280]'
                          } flex items-center justify-between gap-2`}
                        onClick={() => switchSession(session)}
                      >
                        <div className="flex-1 truncate">
                          <span className="flex items-center gap-1 w-full">
                            <span className="truncate max-w-[200px]">{session.sessionTitle || `Chat ${session.id}`}</span>
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="ml-1 flex-shrink-0 h-7 w-7 text-gray-300 hover:text-gray-500 hover:bg-[#F8FAFC]"
                            title="More options"
                            onClick={e => {
                              e.stopPropagation();
                              setDropdownOpen(isDropdownOpen ? null : session.chatSessionId);
                            }}
                          >
                            <MoreHorizontal className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>

                      {/* Dropdown Menu */}
                      {isDropdownOpen && (
                        <div className="dropdown-container absolute right-2 top-full mt-1 bg-white border border-[#E2E8F0] rounded-lg shadow-lg z-10 min-w-[120px]">
                          <button
                            className="w-full px-3 py-2 text-left text-sm text-[#6B7280] hover:bg-[#F8FAFC] hover:text-[#1F2937] flex items-center gap-2 border-b border-[#E2E8F0]"
                            onClick={e => {
                              e.stopPropagation();
                              setRenamingSession(session);
                              setNewTitle(session.sessionTitle || '');
                              setIsModalOpen(true);
                              setDropdownOpen(null);
                            }}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                            Rename
                          </button>
                          <button
                            className="w-full px-3 py-2 text-left text-sm text-[#DC2626] hover:bg-[#FEF2F2] hover:text-[#B91C1C] flex items-center gap-2"
                            onClick={e => {
                              e.stopPropagation();
                              deleteSession(session);
                              setDropdownOpen(null);
                            }}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </ScrollArea>

          {/* Sticky Footer with Profile */}
          <div className="flex-shrink-0 border-t border-[#E2E8F0] px-3 py-4 bg-white">
            <Button
              onClick={() => navigate('/dashboard')}
              className="w-full flex items-center gap-3 p-3"
              variant="ghost"
            >
              <Avatar className="h-10 w-10">
                <AvatarFallback className="bg-blue-600 text-white text-sm">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 text-left">
                <div className="font-medium text-sm truncate">
                  {student?.fullName || 'Student'}
                </div>
                <div className="text-xs text-[#6B7280] truncate">
                  {student?.email || ''}
                </div>
              </div>
            </Button>
          </div>
        </div>
      </div>

      {/* Rename Modal */}
      {isModalOpen && renamingSession && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setIsModalOpen(false)} />
          <div className="relative bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold text-[#1F2937] mb-4">Rename Chat Session</h3>
            <input
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              className="w-full px-3 py-2 border border-[#CBD5E1] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#4F83FF] focus:border-transparent"
              placeholder="Enter new title"
              maxLength={40}
              disabled={renaming}
            />
            <div className="flex justify-end gap-3 mt-6">
              <Button
                onClick={() => setIsModalOpen(false)}
                variant="outline"
                disabled={renaming}
              >
                Cancel
              </Button>
              <Button
                onClick={async () => {
                  if (newTitle.trim() && !renaming) {
                    await renameSessionTitle(renamingSession, newTitle.trim());
                    setIsModalOpen(false);
                    setRenamingSession(null);
                  }
                }}
                disabled={renaming || !newTitle.trim()}
                className="bg-[#4F83FF] hover:bg-[#3B82F6] text-white"
              >
                {renaming ? 'Renaming...' : 'Rename'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
