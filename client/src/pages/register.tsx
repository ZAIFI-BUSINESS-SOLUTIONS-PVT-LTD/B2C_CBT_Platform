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
            navigate("/");
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

            {/* Desktop: two-column split with image on the left and white panel on the right. The form overlaps the dividing line. */}
            <div className="hidden md:flex min-h-screen w-full relative">
                {/* Left image column (taller/longer visual) */}
                <div
                    className="w-3/5 min-h-screen h-screen flex-shrink-0 bg-cover bg-center bg-no-repeat"
                    style={{ backgroundImage: `url(${Login})`, backgroundSize: 'cover', backgroundPosition: 'center', backgroundRepeat: 'no-repeat' }}
                />

                {/* Right white column where the card sits; the card is shifted left to overlap the image */}
                <div className="w-2/5 h-full bg-white" />

                {/* Absolutely positioned card placed at the seam of the two columns */}
                <div className="absolute left-[60%] top-1/2 transform -translate-x-1/2 -translate-y-1/2 z-30 w-full max-w-md px-4">
                    <div className="mx-auto">
                        <RegisterForm onSuccess={() => { /* RegisterForm already navigates */ }} />
                    </div>
                </div>
            </div>
        </>
    );
}
