import { useEffect } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import { InstitutionStudentRegisterForm } from "@/components/InstitutionStudentRegisterForm";
import Login from "@/assets/images/login.png";

/**
 * Institution Student Register Page
 * Allows institution students to create accounts with an institution code
 */
export default function InstitutionStudentRegisterPage() {
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
                <div className="w-full max-w-md mx-auto">
                    <InstitutionStudentRegisterForm onBack={() => navigate("/login")} />
                </div>
            </div>

            {/* Desktop: two-column split with image on the left and white panel on the right */}
            <div className="hidden md:flex min-h-screen w-full relative">
                {/* Left image column */}
                <div
                    className="w-3/5 min-h-screen h-screen flex-shrink-0 bg-cover bg-center bg-no-repeat"
                    style={{
                        backgroundImage: `url(${Login})`,
                        backgroundSize: 'cover',
                        backgroundPosition: 'center',
                        backgroundRepeat: 'no-repeat'
                    }}
                />

                {/* Right white column */}
                <div className="w-2/5 h-full bg-white" />

                {/* Absolutely positioned card at the seam of the two columns */}
                <div className="absolute left-[60%] top-1/2 transform -translate-x-1/2 -translate-y-1/2 z-30 w-full max-w-md px-4">
                    <div className="mx-auto">
                        <InstitutionStudentRegisterForm onBack={() => navigate("/login")} />
                    </div>
                </div>
            </div>
        </>
    );
}
