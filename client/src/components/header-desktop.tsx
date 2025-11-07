import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useLocation } from "wouter";
import { StudentProfile } from "@/components/profile-avatar";
import Logo from "@/assets/images/logo.svg";
import { Crown, Home, NotepadText, FileChartPie, MessageSquareMore, ChevronDown, ChevronRight, School } from "lucide-react";
import { getAccessToken } from '@/lib/auth';
import { getPostTestHidden } from '@/lib/postTestHidden';
import { API_CONFIG } from '@/config/api';
import { useAuth } from '@/contexts/AuthContext';
import { ScrollArea } from '@/components/ui/scroll-area';

/**
 * Header component extracted from the desktop home page.
 * Renders the brand logo on the left and a payment button + student profile on the right.
 */

// Small helper for rendering a sidebar item
interface NavItem {
    to: string;
    text: string;
    icon: React.ReactNode;
    activePattern?: RegExp;
    onClick?: () => void;
    expandable?: boolean;
    expanded?: boolean;
    disabled?: boolean;
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

function SidebarItem({ item, currentPath, navigate }: { item: NavItem; currentPath: string; navigate: (to: string) => void; }) {
    const isActive = item.activePattern ? item.activePattern.test(currentPath) : currentPath === item.to;
    const disabled = !!item.disabled;
    return (
        <li role="none">
            <button
                onClick={() => { if (disabled) return; item.onClick ? item.onClick() : navigate(item.to); }}
                role="menuitem"
                aria-label={item.text}
                aria-disabled={disabled}
                disabled={disabled}
                className={`group w-full flex items-center rounded-lg transition-all duration-200 focus:outline-none px-4 py-3 text-left ${isActive ? 'bg-gradient-to-r from-blue-50 to-blue-100 text-blue-600 font-medium shadow-sm' : 'text-gray-700 hover:bg-blue-50'} ${disabled ? 'filter blur-sm opacity-60 cursor-not-allowed' : ''}`}
            >
                <div className={`flex items-center justify-center transition-colors duration-200 group-hover:text-blue-600 mr-3 ${isActive ? 'text-blue-600' : 'text-gray-600'} ${disabled ? 'text-gray-400' : ''}`}>
                    {item.icon}
                </div>
                <span className="text-base whitespace-nowrap overflow-hidden flex-1">
                    {item.text}
                </span>
                {item.expandable && (
                    <div className={`transition-colors duration-200 ${isActive ? 'text-blue-600' : 'text-gray-500'}`}>
                        {item.expanded ? (
                            <ChevronDown className="h-4 w-4" />
                        ) : (
                            <ChevronRight className="h-4 w-4" />
                        )}
                    </div>
                )}
            </button>
        </li>
    );
}

export default function HeaderDesktop() {
    const [, navigate] = useLocation();

    const { student } = useAuth();
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

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
            } else {
                console.error('Failed to load sessions:', response.status);
            }
        } catch (error) {
            console.error('Failed to load chat sessions:', error);
        }
    };

    useEffect(() => {
        loadChatSessions();
    }, []);

    // compute left spacing class for header when used in a layout with sidebar
    const leftClass = 'md:left-64';

    // Navigation items configuration
    const postHidden = getPostTestHidden();

    const navItems: NavItem[] = [
        { to: '/', text: 'Home', icon: <Home className="h-5 w-5" />, activePattern: /^\/$/ },
        { to: '/topics', text: 'Test', icon: <NotepadText className="h-5 w-5" />, activePattern: /^\/topics/ },
        { to: '/institution-tests', text: 'Institution Tests', icon: <School className="h-5 w-5" />, activePattern: /^\/institution-tests/ },
        { to: '/dashboard', text: 'Analysis', icon: <FileChartPie className="h-5 w-5" />, activePattern: /^\/dashboard/ },
        {
            to: '/chatbot', text: 'Chatbot', icon: <MessageSquareMore className="h-5 w-5" />, activePattern: /^\/chatbot/, onClick: () => {
                // If already on chatbot page, just toggle expansion
                if (path.startsWith('/chatbot')) {
                    setExpandedItems(prev => {
                        const newSet = new Set(prev);
                        if (newSet.has('chatbot')) {
                            newSet.delete('chatbot');
                        } else {
                            newSet.add('chatbot');
                        }
                        return newSet;
                    });
                } else {
                    // Navigate to chatbot page and expand
                    navigate('/chatbot');
                    setExpandedItems(prev => new Set([...prev, 'chatbot']));
                }
            }, expandable: true, expanded: expandedItems.has('chatbot')
        },
    ];

    // Wouter current path (hack: useLocation gives [path, set])
    const [path] = useLocation();

    // Auto-expand chatbot section when on chatbot page (only expand, don't collapse)
    useEffect(() => {
        if (path.startsWith('/chatbot')) {
            setExpandedItems(prev => new Set([...prev, 'chatbot']));
        }
    }, [path]);

    return (
        <>
            <header className={`flex items-center justify-end fixed top-0 ${leftClass} right-0 z-50 h-20 bg-white border-b transition-all duration-300`} role="banner">
                <div className="flex items-center justify-end pr-3 space-x-3">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => navigate('/payment')}
                        className="aspect-square bg-orange-100 rounded-full h-12 w-12"
                        aria-label="Go to Payment"
                    >
                        <Crown className="h-5 w-5 text-amber-600" />
                    </Button>
                    <StudentProfile />
                </div>
            </header>

            {/* Desktop-style static sidebar */}
            <aside
                className={`fixed top-0 left-0 h-full bg-white z-40 shadow-md overflow-hidden flex flex-col`}
                style={{
                    width: '256px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                }}
                aria-label="Main sidebar navigation"
            >
                <div className="flex items-center h-20 mb-2 border-b justify-start px-6">
                    <div className="flex items-center justify-center">
                        <img src={Logo} alt="InzightEd Logo" className="h-9 pt-1" />
                    </div>
                </div>

                <nav className="flex-1 flex flex-col justify-between overflow-y-auto py-4">
                    <div className="px-3">
                        <div className="px-3 mb-4">
                            <span className="text-sm font-medium text-gray-500 uppercase tracking-wider">Main Menu</span>
                        </div>

                        <ul className="space-y-2" role="menu">
                            {navItems.map(item => {
                                // compute disabled state for certain menu items when post-test flag is set
                                const isDisabled = postHidden && ['Test', 'Analysis', 'Chatbot'].includes(item.text);
                                const itemWithDisabled = { ...item, disabled: isDisabled } as NavItem;
                                return <SidebarItem key={item.to} item={itemWithDisabled} currentPath={path} navigate={navigate} />
                            })}
                        </ul>
                        {expandedItems.has('chatbot') && (
                            <div className="mt-2">
                                <ScrollArea className="max-h-40">
                                    <div className="space-y-1">
                                        {sessions.map((session) => (
                                            <button
                                                key={session.chatSessionId}
                                                onClick={() => navigate(`/chatbot?session=${session.chatSessionId}`)}
                                                className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg truncate"
                                            >
                                                {session.sessionTitle || `Chat ${session.id}`}
                                            </button>
                                        ))}
                                    </div>
                                </ScrollArea>
                            </div>
                        )}
                    </div>

                    {/* User profile + logout */}
                    <div className="mt-auto px-3">
                        <div className="flex items-center p-3 bg-blue-50 rounded-xl">
                            <div className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-medium text-sm">U</div>
                            <div className="ml-3">
                                <div className="text-sm font-medium text-gray-700">User Name</div>
                                <div className="text-sm text-gray-500">Role/Institution</div>
                            </div>
                        </div>
                    </div>
                </nav>

            </aside>
        </>
    );
}
