import React from "react";
import { Home, NotepadText, FileChartPie, MessageSquareMore, School, Lock } from "lucide-react";
import { useLocation } from "wouter";
import { getPostTestHidden } from '@/lib/postTestHidden';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Mobile dock shown on small screens with navigation shortcuts
 * Items: Home, Test, Dashboard, Chatbot
 * Role-based visibility:
 * - Institution tab: hidden for normal students (without institution)
 * - Test/Chatbot tabs: blurred/locked for institution students
 */
export default function MobileDock() {
    const [location, navigate] = useLocation();
    const { student } = useAuth();

    const isActive = (path: string) => {
        try {
            if (!location) return false;
            // treat root specially
            if (path === "/") return location === "/";
            return location.startsWith(path);
        } catch {
            return false;
        }
    };

    const postHidden = getPostTestHidden();

    // Check if user is institution student
    const isInstitutionStudent = student?.isInstitutionStudent === true;
    const hasInstitution = !!student?.institution;

    const allItems = [
        { key: "home", href: "/", label: "Home", icon: <Home className="h-5 w-5" /> },
        { key: "test", href: "/topics", label: "Test", icon: <NotepadText className="h-5 w-5" />, lockedForInstitution: true },
        { key: "institution", href: "/institution-tests", label: "Institution", icon: <School className="h-4 w-4" />, hideForNormal: true },
        { key: "analysis", href: "/dashboard", label: "Analysis", icon: <FileChartPie className="h-5 w-5" /> },
        { key: "chatbot", href: "/chatbot", label: "Chatbot", icon: <MessageSquareMore className="h-5 w-5" />, lockedForInstitution: true },
    ];

    // Filter items based on user type
    const items = allItems.filter(item => {
        // Hide Institution tab for normal students
        if (item.hideForNormal && !hasInstitution && !isInstitutionStudent) {
            return false;
        }
        return true;
    });

    return (
        <nav
            aria-label="Mobile navigation"
            className="fixed bottom-0 left-0 right-0 md:hidden bg-white border border-gray-200 shadow-lg rounded-t-2xl z-50 pointer-events-auto"
            style={{
                WebkitTapHighlightColor: 'transparent',
                // ensure dock sits above safe-area (iPhone notch / home indicator)
                paddingBottom: 'env(safe-area-inset-bottom, 0px)',
                touchAction: 'manipulation'
            }}
        >
            <div className="max-w-4xl mx-auto pt-2">
                <ul className="flex justify-between items-center h-16">
                    {items.map((it) => {
                        const active = isActive(it.href);
                        const disabled = postHidden && ['Test', 'Analysis', 'Chatbot'].includes(it.label);
                        const lockedForInstitution = isInstitutionStudent && it.lockedForInstitution;
                        const isDisabled = disabled || lockedForInstitution;
                        
                        return (
                            <li key={it.key} className="flex-1 relative">
                                <button
                                    onClick={() => { if (!isDisabled) navigate(it.href); }}
                                    aria-current={active ? "page" : undefined}
                                    aria-label={it.label}
                                    aria-disabled={isDisabled}
                                    disabled={isDisabled}
                                    className={`w-full h-full flex flex-col items-center justify-center gap-0 transition-colors duration-200 focus:outline-none ${isDisabled ? 'filter blur-sm opacity-60 cursor-not-allowed' : ''}`}
                                >
                                    <div
                                        className={`mb-1 p-2 rounded-full transition-transform duration-200 ease-in-out ${active
                                            ? 'bg-gradient-to-br from-blue-50/60 to-indigo-50/40 text-blue-600 scale-105 ring-1 ring-blue-200'
                                            : 'text-gray-600 hover:text-gray-800'
                                            }`}
                                    >
                                        {it.icon}
                                    </div>
                                    <span
                                        className={`text-[11px] leading-3 tracking-wide transition-colors duration-200 ${active ? 'text-blue-700 font-semibold' : 'text-gray-500'
                                            }`}
                                    >
                                        {it.label}
                                    </span>
                                </button>
                                {lockedForInstitution && (
                                    <div className="absolute top-2 right-2 bg-gray-800/80 rounded-full p-1">
                                        <Lock className="h-3 w-3 text-white" />
                                    </div>
                                )}
                            </li>
                        );
                    })}
                </ul>
            </div>
        </nav>
    );
}
