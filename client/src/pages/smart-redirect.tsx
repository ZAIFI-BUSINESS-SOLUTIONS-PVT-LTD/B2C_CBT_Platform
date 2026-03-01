import { useEffect } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";

/**
 * Smart Redirect Component
 * 
 * Centralizes authentication-based routing decisions at the root path.
 * This prevents UI flashes by handling navigation before rendering any content.
 * 
 * Routing Logic:
 * - Loading: Shows nothing (prevents flash)
 * - Authenticated + has phone: → /topics (main test selection page)
 * - Authenticated + no phone: → /get-number (onboarding flow)
 * - Not authenticated: → /login (authentication required)
 */
export default function SmartRedirect() {
  const { isAuthenticated, loading, student } = useAuth();
  const [, navigate] = useLocation();

  useEffect(() => {
    // Wait until auth state is determined
    if (loading) return;

    if (isAuthenticated) {
      // User is logged in - check if they have a phone number
      if (!student?.phoneNumber) {
        // Need to complete onboarding
        navigate("/get-number", { replace: true });
      } else {
        // Fully authenticated - go to main app (topics page)
        navigate("/topics", { replace: true });
      }
    } else {
      // Not authenticated - show login page
      navigate("/login", { replace: true });
    }
  }, [loading, isAuthenticated, student, navigate]);

  // Show nothing while determining where to redirect
  // This prevents any UI flash during the redirect decision
  return null;
}
