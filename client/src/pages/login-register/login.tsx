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
    const { isAuthenticated, loading, student } = useAuth();
    const [, navigate] = useLocation();

    useEffect(() => {
        if (!loading && isAuthenticated) {
            // If already authenticated, check where to redirect
            if (!student?.phoneNumber) {
                navigate("/get-number");
            } else {
                navigate("/dashboard");
            }
        }
    }, [loading, isAuthenticated, student, navigate]);

    return (
        <>
            {/* Mobile / small screens: keep full-background behavior */}
            <div className="min-h-screen w-full flex items-end justify-center relative overflow-hidden md:hidden" style={{ backgroundImage: `url(${Login})`, backgroundSize: 'cover', backgroundPosition: 'center' }}>
                <div className="w-full max-w-md mx-auto">
                    <LoginForm />
                </div>
            </div>

            {/* Desktop: full background image with centered form */}
            <div className="hidden md:flex min-h-screen w-full items-center justify-center relative" style={{ backgroundImage: `url(${Login})`, backgroundSize: 'cover', backgroundPosition: 'center' }}>
                <div className="w-full max-w-md px-4">
                    <LoginForm />
                </div>
            </div>
        </>
    );
}