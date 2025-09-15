import React from "react";
import { Home, NotepadText, FileChartPie, MessageSquareMore } from "lucide-react";
import { useLocation } from "wouter";

/**
 * Mobile dock shown on small screens with navigation shortcuts
 * Items: Home, Test, Dashboard, Chatbot
 */
export default function MobileDock() {
    const [location, navigate] = useLocation();

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

    const items = [
        { key: "home", href: "/", label: "Home", icon: <Home className="h-5 w-5" /> },
        { key: "test", href: "/topics", label: "Test", icon: <NotepadText className="h-5 w-5" /> },
        { key: "chatbot", href: "/chatbot", label: "Chatbot", icon: <MessageSquareMore className="h-5 w-5" /> },
    ];

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
                        return (
                            <li key={it.key} className="flex-1">
                                <button
                                    onClick={() => navigate(it.href)}
                                    aria-current={active ? "page" : undefined}
                                    aria-label={it.label}
                                    className="w-full h-full flex flex-col items-center justify-center gap-0 transition-colors duration-200 focus:outline-none"
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
                            </li>
                        );
                    })}
                </ul>
            </div>
        </nav>
    );
}
