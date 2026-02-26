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
                // Landing page after login should be Topics
                navigate("/topics");
            }
        }
    }, [loading, isAuthenticated, student, navigate]);

    return (
        <>
            {/* Mobile / small screens: use public logo-bg.jpg as background */}
            <div className="min-h-screen w-full flex items-end justify-center relative overflow-hidden md:hidden" style={{ backgroundImage: "url('/login-bg.jpg')", backgroundSize: 'cover', backgroundPosition: 'center' }}>
                {/* Penguin mascot positioned near top-center of viewport */}
                <img src="/penguin_welcome.png" alt="Login mascot" className="absolute top-14 left-1/2 w-28 sm:w-32 pointer-events-none mt-32" style={{ transform: 'translateX(-50%) scale(2.0)' }} />

                {/* Headline + subtext under penguin */}
                <div className="absolute left-1/2 transform -translate-x-1/2 text-center w-11/12 max-w-2xl" style={{ top: '50%' }}>
                    <h1 className="text-xl sm:text-2xl md:text-3xl font-semibold leading-tight" style={{ color: '#233a56' }}>
                        <span className="block">Get ready for NEET</span>
                        <span className="block">with NEET Bro!</span>
                    </h1>
                    <p className="mt-2 text-xs sm:text-sm" style={{ color: '#7ea5c3' }}>Enter your mobile number to get started.</p>
                </div>

                <div className="w-full max-w-md mx-auto">
                    <LoginForm />
                </div>
            </div>

            {/* Desktop: full background image with centered form */}
            <div className="hidden md:flex min-h-screen w-full items-center justify-center relative" style={{ backgroundImage: `url(${Login})`, backgroundSize: 'cover', backgroundPosition: 'center' }}>
                {/* Optional penguin on desktop too (adjust top for desktop) */}
                <img src="/login-penguin.png" alt="Login mascot" className="absolute top-20 left-1/2 w-36 pointer-events-none opacity-95" style={{ transform: 'translateX(-50%) scale(1.5)' }} />

                {/* Desktop headline + subtext */}
                <div className="absolute left-1/2 transform -translate-x-1/2 text-center w-3/4 max-w-3xl hidden md:block" style={{ top: '42%' }}>
                    <h1 className="text-3xl lg:text-4xl font-semibold leading-tight" style={{ color: '#233a56' }}>
                        <span className="block">Get ready for NEET</span>
                        <span className="block">with NEET Bro!</span>
                    </h1>
                    <p className="mt-2 text-sm" style={{ color: '#7ea5c3' }}>Enter your mobile number to get started.</p>
                </div>

                <div className="w-full max-w-md px-4">
                    <LoginForm />
                </div>
            </div>
        </>
    );
}