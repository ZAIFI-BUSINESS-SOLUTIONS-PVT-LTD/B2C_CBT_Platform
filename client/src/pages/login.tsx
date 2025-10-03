import { useEffect } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import { LoginForm } from "@/components/LoginForm";
import Login from "@/assets/images/login.png";

/**
 * Standalone Login Page
 * Redirects to home if already authenticated
 */
export default function LoginPage() {
    const { isAuthenticated, loading } = useAuth();
    const [, navigate] = useLocation();

    useEffect(() => {
        if (!loading && isAuthenticated) {
            navigate("/");
        }
    }, [loading, isAuthenticated, navigate]);

    return (
        <>
            {/* Mobile / small screens: keep full-background behavior */}
            <div className="min-h-screen w-full flex items-end justify-center relative overflow-hidden md:hidden" style={{ backgroundImage: `url(${Login})`, backgroundSize: 'cover', backgroundPosition: 'center' }}>
                <div className="w-full max-w-md mx-auto">
                    <LoginForm />
                </div>
            </div>

            {/* Desktop: two-row split with image on the top and white panel on the bottom equally split. */}
            <div className="hidden md:flex flex-col min-h-screen w-full relative">
                {/* Top image row - flex-1 fills top half */}
                <div
                    className="flex-1 w-full bg-cover bg-center bg-no-repeat"
                    style={{ backgroundImage: `url(${Login})`, backgroundSize: 'cover', backgroundPosition: 'center', backgroundRepeat: 'no-repeat' }}
                />

                {/* Bottom white row - flex-1 fills bottom half */}
                <div className="flex-1 w-full bg-white" />

                {/* Absolutely positioned card centered in the viewport (middle seam) */}
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-30 w-full max-w-md px-4">
                    <div className="mx-auto">
                        <LoginForm />
                    </div>
                </div>
            </div>
        </>
    );
}
