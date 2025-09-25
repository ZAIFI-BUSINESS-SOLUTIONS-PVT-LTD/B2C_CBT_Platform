import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { getAccessToken } from "@/lib/auth";
import { API_CONFIG } from "@/config/api";
import { SPEECH_CONFIG } from "@/config/speech";
import { useLocation } from "wouter";
import { MessageSquareMore, Mic, MicOff, Send, Loader2 } from "lucide-react";
import { ShineBorder } from "@/components/shine-border";

interface MiniChatbotProps {
    className?: string;
}

export default function MiniChatbot({ className = "" }: MiniChatbotProps) {
    const [, navigate] = useLocation();

    const quickPrompts = [
        'How can I improve my algebra?', 'Create a 2-week study plan', 'Time management tips for exams'
    ];

    // Chat functionality states
    const [inputMessage, setInputMessage] = useState('');
    const [isChatLoading, setIsChatLoading] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [speechSupported, setSpeechSupported] = useState(false);
    const [recognitionLanguage, setRecognitionLanguage] = useState(SPEECH_CONFIG.DEFAULT_LANGUAGE);
    const recognitionRef = useRef<any>(null);

    // Initialize speech recognition
    useEffect(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (SpeechRecognition) {
            setSpeechSupported(true);
            const recognition = new SpeechRecognition();

            recognition.continuous = SPEECH_CONFIG.RECOGNITION_SETTINGS.continuous;
            recognition.interimResults = SPEECH_CONFIG.RECOGNITION_SETTINGS.interimResults;
            recognition.lang = recognitionLanguage;
            recognition.maxAlternatives = SPEECH_CONFIG.RECOGNITION_SETTINGS.maxAlternatives;

            recognition.onresult = (event: any) => {
                let transcript = '';
                for (let i = 0; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                }
                setInputMessage(transcript);

                // Manually adjust textarea height after setting transcribed text
                setTimeout(() => {
                    const textarea = document.querySelector('textarea[placeholder="Ask anything..."]') as HTMLTextAreaElement;
                    if (textarea) {
                        textarea.style.height = 'auto';
                        textarea.style.height = textarea.scrollHeight + 'px';
                    }
                }, 0);
            };

            recognition.onstart = () => setIsRecording(true);
            recognition.onend = () => setIsRecording(false);
            recognition.onerror = () => setIsRecording(false);

            recognitionRef.current = recognition;
        } else {
            setSpeechSupported(false);
        }

        return () => {
            if (recognitionRef.current) {
                recognitionRef.current.abort();
            }
        };
    }, [recognitionLanguage]);

    // Chat functions
    const getAuthHeaders = () => {
        const token = getAccessToken();
        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        };
    };

    const generateSessionTitleFromMessage = (message: string): string => {
        if (!message) return 'New Chat';
        let trimmed = message.trim();
        if (trimmed.length > 40) {
            trimmed = trimmed.slice(0, 40).trim() + '...';
        }
        return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
    };

    const createNewSessionAndRedirect = async (messageToSend: string) => {
        try {
            setIsChatLoading(true);
            const url = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_SESSIONS}`;

            const sessionTitle = generateSessionTitleFromMessage(messageToSend);

            const response = await fetch(url, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ sessionTitle }),
            });

            if (response.ok) {
                const newSession = await response.json();
                // Redirect to chatbot page with the new session and message
                navigate(`/chatbot?sessionId=${newSession.chatSessionId}&message=${encodeURIComponent(messageToSend)}`);
            } else {
                console.error('Failed to create session');
            }
        } catch (error) {
            console.error('Failed to create session:', error);
        } finally {
            setIsChatLoading(false);
        }
    };

    const handleChatSend = (message: string) => {
        if (!message.trim()) return;
        setInputMessage('');

        // Reset textarea height after clearing input
        setTimeout(() => {
            const textarea = document.querySelector('textarea[placeholder="Ask anything..."]') as HTMLTextAreaElement;
            if (textarea) {
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';
            }
        }, 0);

        createNewSessionAndRedirect(message);
    };

    const toggleSpeechRecognition = () => {
        if (!speechSupported) return;

        if (isRecording) {
            if (recognitionRef.current) {
                recognitionRef.current.stop();
            }
            setTimeout(() => {
                if (inputMessage.trim()) {
                    handleChatSend(inputMessage.trim());
                }
            }, 100);
        } else {
            if (recognitionRef.current) {
                try {
                    setInputMessage('');

                    // Reset textarea height after clearing input
                    setTimeout(() => {
                        const textarea = document.querySelector('textarea[placeholder="Ask anything..."]') as HTMLTextAreaElement;
                        if (textarea) {
                            textarea.style.height = 'auto';
                            textarea.style.height = textarea.scrollHeight + 'px';
                        }
                    }, 0);

                    recognitionRef.current.start();
                } catch (error) {
                    console.error('Failed to start speech recognition:', error);
                    setIsRecording(false);
                }
            }
        }
    };

    return (
        <div className={`w-full h-full ${className}`}>
            <Card className="bg-gradient-to-br from-white via-white to-slate-50/50 rounded-2xl shadow-xl backdrop-blur-sm h-full flex flex-col">
                <ShineBorder shineColor={["#a855f7", "#3b82f6", "#0ea5e9"]} />

                {/* Minimalistic subtle background pattern (diagonal lines + soft gradient) */}
                <div className="absolute inset-0 -z-10 pointer-events-none overflow-hidden rounded-2xl">
                    <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none" viewBox="0 0 800 600" aria-hidden>
                        <defs>
                            <pattern id="diagonalLines" patternUnits="userSpaceOnUse" width="120" height="120" patternTransform="rotate(22)">
                                <rect width="120" height="120" fill="transparent" />
                                <path d="M0 120 L120 0" stroke="rgba(15,23,42,0.04)" strokeWidth="1" />
                            </pattern>
                            <linearGradient id="softGradient" x1="0" x2="1" y1="0" y2="1">
                                <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
                                <stop offset="100%" stopColor="#eef2ff" stopOpacity="1" />
                            </linearGradient>
                        </defs>
                        <rect width="100%" height="100%" fill="url(#diagonalLines)" />
                        <rect width="100%" height="100%" fill="url(#softGradient)" opacity="0.06" />
                    </svg>
                </div>

                <CardContent className="p-4 flex flex-col h-full">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-4">
                            <div className="relative">
                                <div className="absolute inset-0 w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 blur-md opacity-30"></div>
                                <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 flex items-center justify-center shadow-xl ring-2 ring-white/40">
                                    <MessageSquareMore className="h-6 w-6 text-white drop-shadow-sm" />
                                </div>
                            </div>
                            <div className="flex-1">
                                <p className="text-md text-slate-600 mt-0.5 font-medium leading-relaxed">Your own personal AI study assistant</p>
                            </div>
                        </div>
                    </div>

                    {/* Main area - grows and can scroll if needed */}
                    <div className="flex-1 overflow-auto flex items-center justify-center px-3 py-2">
                        <div className="w-full h-full flex flex-col items-center justify-center space-y-4">
                            {speechSupported && isRecording ? (
                                <div className="flex items-center justify-center gap-3 py-3 px-4 bg-gradient-to-r from-emerald-50 via-green-50 to-emerald-50 rounded-2xl border border-green-200/60 shadow-sm backdrop-blur-sm">
                                    <div className="flex gap-1">
                                        <div className="w-2 h-2 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full animate-pulse shadow-sm" style={{ animationDelay: '0ms' }}></div>
                                        <div className="w-2 h-2 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full animate-pulse shadow-sm" style={{ animationDelay: '200ms' }}></div>
                                        <div className="w-2 h-2 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full animate-pulse shadow-sm" style={{ animationDelay: '400ms' }}></div>
                                    </div>
                                    <span className="text-sm text-green-700 font-semibold">Listening... Tap ✓ to send</span>
                                </div>
                            ) : !speechSupported ? (
                                <div className="text-xs text-slate-500 text-center py-3 px-4 bg-slate-50/50 rounded-xl border border-slate-200/50">
                                    Voice input not supported
                                </div>
                            ) : (
                                // Quick Prompts and Button to full Chatbot
                                <div className="w-full max-w-sm text-center">
                                    <div className="mt-3">
                                        <Button size="lg" variant="default" onClick={() => navigate('/chatbot')} className="rounded-xl px-4">Go to Chatbot</Button>
                                    </div>
                                    <div className="mt-3 flex flex-wrap justify-center gap-2">
                                        {quickPrompts.map((p) => (
                                            <Button
                                                key={p}
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => createNewSessionAndRedirect(p)}
                                                className="rounded-xl border px-3 py-2 text-sm min-w-[10rem] max-w-xs truncate"
                                            >
                                                {p}
                                            </Button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Input area pinned to bottom */}
                    <div className="mt-4">
                        <div className="flex items-center gap-3">
                            <div className="flex-1 relative group">
                                <Input
                                    value={inputMessage}
                                    onChange={(e) => setInputMessage(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            e.preventDefault();
                                            if (inputMessage.trim()) {
                                                handleChatSend(inputMessage.trim());
                                            }
                                        }
                                    }}
                                    placeholder="Ask anything..."
                                    disabled={isChatLoading}
                                    className="border-slate-200/80 rounded-full text-sm focus:border-blue-300 focus:ring-blue-100 focus:ring-1 shadow-sm transition-all duration-200 bg-white/80 backdrop-blur-sm group-hover:shadow-md pl-4 pr-20 h-12"
                                />
                                <div className="absolute right-1 top-1/2 -translate-y-1/2 flex items-center gap-2">{speechSupported && (
                                    <Button
                                        type="button"
                                        size="icon"
                                        variant="ghost"
                                        onClick={toggleSpeechRecognition}
                                        disabled={isChatLoading}
                                        className={`h-10 w-10 p-0 rounded-full transition-all duration-200 hover:scale-105 ${isRecording
                                            ? 'text-green-600 hover:text-green-700 bg-green-50 hover:bg-green-100'
                                            : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
                                            }`}
                                    >
                                        {isRecording ? <Mic className="h-6 w-6" /> : <MicOff className="h-6 w-6" />}
                                    </Button>
                                )}
                                    <Button
                                        type="button"
                                        size="icon"
                                        onClick={() => {
                                            if (inputMessage.trim()) {
                                                handleChatSend(inputMessage.trim());
                                            }
                                        }}
                                        disabled={!inputMessage.trim() || isChatLoading}
                                        className="h-10 w-10 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:hover:scale-100"
                                    >
                                        {isChatLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
