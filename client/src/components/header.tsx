import { GraduationCap, User, LogOut, MessageCircle, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { useLocation } from "wouter";
import { getPostTestHidden } from '@/lib/postTestHidden';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function Header() {
  const { isAuthenticated, student, logout } = useAuth();
  const [, navigate] = useLocation();
  const postHidden = getPostTestHidden();
  const [showComingSoon, setShowComingSoon] = React.useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      // Redirect to home page immediately after logout
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <header className="bg-white shadow-sm border-b border-neet-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          <div className="flex items-center space-x-4">
            <div className="bg-neet-blue text-white p-2.5 rounded-xl shadow-sm">
              <GraduationCap className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-neet-gray-900 tracking-tight">
                NEET Practice Platform
              </h1>
              <p className="text-sm text-neet-gray-500">
                Smart Test Preparation
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {isAuthenticated && student ? (
              <>
                <span className="text-sm text-neet-gray-600 font-medium">
                  Welcome, {student.fullName || student.email}
                </span>
                <Button 
                  variant="outline" 
                  className={`shadow-sm ${postHidden ? 'filter blur-sm opacity-60 cursor-not-allowed' : ''}`}
                  onClick={() => {
                    if (postHidden) return;
                    setShowComingSoon(true);
                    setTimeout(() => { setShowComingSoon(false); navigate('/dashboard'); }, 1400);
                  }}
                  disabled={postHidden}
                >
                  <MessageCircle className="h-4 w-4 mr-2" />
                  AI Tutor
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button className="btn-primary shadow-sm">
                      <User className="h-4 w-4 mr-2" />
                      Profile
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="w-56">
                    <DropdownMenuLabel>My Account</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem>
                      <User className="mr-2 h-4 w-4" />
                      <span>Profile Settings</span>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem 
                      onClick={handleLogout}
                      className="text-red-600 focus:text-red-600"
                    >
                      <LogOut className="mr-2 h-4 w-4" />
                      <span>Logout</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <span className="text-sm text-neet-gray-600 font-medium">Not authenticated</span>
            )}
          </div>
        </div>
      </div>
    </header>
    {showComingSoon && (
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowComingSoon(false)} />
        <div className="relative bg-white rounded-2xl shadow-xl border border-gray-200 p-6 w-[90%] max-w-sm z-60">
          <div className="flex flex-col items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center border border-blue-100">
              <Lock className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold">Coming soon</h3>
            <p className="text-sm text-gray-600 text-center">The Chatbot is being rolled out soon. It will be available for students shortly.</p>
            <div className="pt-2">
              <Button onClick={() => setShowComingSoon(false)}>Got it</Button>
            </div>
          </div>
        </div>
      </div>
    )}
  );
}
