import React from "react";
import { Button } from "@/components/ui/button";
import { useLocation } from "wouter";
import { StudentProfile } from "@/components/profile-avatar";
import Logo from "@/assets/images/logo.svg";
import { Crown, Home, NotepadText, FileChartPie, MessageSquareMore } from "lucide-react";

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
}

function SidebarItem({ item, currentPath, navigate }: { item: NavItem; currentPath: string; navigate: (to: string) => void; }) {
    const isActive = item.activePattern ? item.activePattern.test(currentPath) : currentPath === item.to;
    return (
        <li role="none">
            <button
                onClick={() => { item.onClick ? item.onClick() : navigate(item.to); }}
                role="menuitem"
                aria-label={item.text}
                className={`group w-full flex items-center rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 px-4 py-3 text-left ${isActive ? 'bg-gradient-to-r from-blue-50 to-blue-100 text-blue-600 font-medium shadow-sm' : 'text-gray-700 hover:bg-blue-50'}`}
            >
                <div className={`flex items-center justify-center transition-colors duration-200 group-hover:text-blue-600 mr-3 ${isActive ? 'text-blue-600' : 'text-gray-600'}`}>
                    {item.icon}
                </div>
                <span className="text-base whitespace-nowrap overflow-hidden">
                    {item.text}
                </span>
            </button>
        </li>
    );
}

export default function HeaderDesktop() {
    const [, navigate] = useLocation();

    // compute left spacing class for header when used in a layout with sidebar
    const leftClass = 'md:left-64';

    // Navigation items configuration
    const navItems: NavItem[] = [
        { to: '/', text: 'Home', icon: <Home className="h-5 w-5" />, activePattern: /^\/$/ },
        { to: '/topics', text: 'Test', icon: <NotepadText className="h-5 w-5" />, activePattern: /^\/topics/ },
        { to: '/dashboard', text: 'Analysis', icon: <FileChartPie className="h-5 w-5" />, activePattern: /^\/dashboard/ },
        { to: '/chatbot', text: 'Chatbot', icon: <MessageSquareMore className="h-5 w-5" />, activePattern: /^\/chatbot/ },
    ];

    // Wouter current path (hack: useLocation gives [path, set])
    const [path] = useLocation();

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
                            {navItems.map(item => (
                                <SidebarItem key={item.to} item={item} currentPath={path} navigate={navigate} />
                            ))}
                        </ul>
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
