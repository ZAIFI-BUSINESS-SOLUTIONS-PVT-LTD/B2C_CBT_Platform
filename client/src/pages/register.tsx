import { useEffect } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import { RegisterForm } from "@/components/RegisterForm";
import Login from "@/assets/images/login.png";

/**
 * Standalone Register Page
 * Redirects to home if already authenticated
 */
export default function RegisterPage() {
    const { isAuthenticated, loading } = useAuth();
    const [, navigate] = useLocation();

    useEffect(() => {
        if (!loading && isAuthenticated) {
            navigate("/dashboard");
        }
    }, [loading, isAuthenticated, navigate]);

    return (
        <>
            {/* Mobile / small screens: keep full-background behavior */}
            <div className="min-h-screen w-full flex items-end justify-center relative overflow-hidden md:hidden" style={{ backgroundImage: `url(${Login})`, backgroundSize: 'cover', backgroundPosition: 'center' }}>
                <div className="w-full flex flex-col items-center justify-center md:max-w-md">
                    <RegisterForm onSuccess={() => { /* RegisterForm already navigates */ }} />
                </div>
            </div>

            {/* Desktop: full background image with centered form */}
            <div className="hidden md:flex min-h-screen w-full items-center justify-center relative" style={{ backgroundImage: `url(${Login})`, backgroundSize: 'cover', backgroundPosition: 'center' }}>
                <div className="w-full max-w-md px-4">
                    <RegisterForm onSuccess={() => { /* RegisterForm already navigates */ }} />
                </div>
            </div>
        </>
    );
}
