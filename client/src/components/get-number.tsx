import { useState } from "react";
import { useLocation } from "wouter";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { apiRequest } from "@/lib/queryClient";
import { useAuth } from "@/hooks/use-auth";
import Logo from "@/assets/images/logo.svg";
import Login from "@/assets/images/login.png";

export function GetNumber() {
    const [phoneNumber, setPhoneNumber] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [, navigate] = useLocation();
    const { setStudent } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validate phone number
        if (!phoneNumber.trim()) {
            setError("Phone number is required");
            return;
        }

        // Basic phone number validation (adjust regex as needed)
        const phoneRegex = /^[0-9]{10}$/;
        if (!phoneRegex.test(phoneNumber.replace(/\s|-/g, ""))) {
            setError("Please enter a valid 10-digit phone number");
            return;
        }

        setLoading(true);
        try {
            // Call API to update phone number
            const updatedStudent = await apiRequest("/api/student-profile/update-phone/", "POST", { phone_number: phoneNumber });

            // Update the student data in auth context
            setStudent(updatedStudent);

            console.log("Phone number submitted:", phoneNumber);

            // Navigate to dashboard after successful submission
            navigate("/dashboard");
        } catch (err: any) {
            setError(err.message || "Failed to save phone number");
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            {/* Mobile / small screens */}
            <div className="min-h-screen w-full flex items-end justify-center relative overflow-hidden md:hidden" style={{ backgroundImage: `url(${Login})`, backgroundSize: 'cover', backgroundPosition: 'center' }}>
                <div className="w-full max-w-md mx-auto">
                    <form onSubmit={handleSubmit} className="space-y-4 w-full p-6 pb-6 pt-8 bg-white rounded-t-2xl shadow-lg">
                        <div className="space-y-1 items-center text-center text-sm text-gray-600">
                            <img src={Logo} alt="Logo" className="h-6 mx-auto mb-2" />
                            <h2 className="text-xl font-semibold text-gray-800">Enter Your Mobile Number</h2>
                            <p className="text-xs text-gray-500">We'll use this to keep you updated</p>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <Label htmlFor="phoneNumber">Mobile Number *</Label>
                                <Input
                                    id="phoneNumber"
                                    name="phoneNumber"
                                    type="tel"
                                    placeholder="Enter your 10-digit mobile number"
                                    value={phoneNumber}
                                    onChange={(e) => setPhoneNumber(e.target.value)}
                                    required
                                    className="h-12 rounded-xl"
                                    maxLength={10}
                                />
                            </div>

                            {error && (
                                <div className="text-red-600 text-sm mt-2 p-2 bg-red-50 rounded">
                                    {error}
                                </div>
                            )}
                        </div>

                        <div className="pt-4">
                            <Button
                                type="submit"
                                disabled={loading}
                                className="w-full h-12 rounded-xl text-sm"
                            >
                                {loading ? "Saving..." : "Continue"}
                            </Button>
                        </div>
                    </form>
                </div>
            </div>

            {/* Desktop: full background image with centered form */}
            <div className="hidden md:flex min-h-screen w-full items-center justify-center relative" style={{ backgroundImage: `url(${Login})`, backgroundSize: 'cover', backgroundPosition: 'center' }}>
                <div className="w-full max-w-md px-4">
                    <form onSubmit={handleSubmit} className="space-y-4 w-full p-6 pb-6 pt-8 bg-white rounded-2xl shadow-lg">
                        <div className="space-y-1 items-center text-center text-sm text-gray-600">
                            <img src={Logo} alt="Logo" className="h-6 mx-auto mb-2" />
                            <h2 className="text-xl font-semibold text-gray-800">Enter Your Mobile Number</h2>
                            <p className="text-xs text-gray-500">We'll use this to keep you updated</p>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <Label htmlFor="phoneNumber">Mobile Number *</Label>
                                <Input
                                    id="phoneNumber"
                                    name="phoneNumber"
                                    type="tel"
                                    placeholder="Enter your 10-digit mobile number"
                                    value={phoneNumber}
                                    onChange={(e) => setPhoneNumber(e.target.value)}
                                    required
                                    className="h-12 rounded-xl"
                                    maxLength={10}
                                />
                            </div>

                            {error && (
                                <div className="text-red-600 text-sm mt-2 p-2 bg-red-50 rounded">
                                    {error}
                                </div>
                            )}
                        </div>

                        <div className="pt-4">
                            <Button
                                type="submit"
                                disabled={loading}
                                className="w-full h-12 rounded-xl text-lg"
                            >
                                {loading ? "Saving..." : "Continue"}
                            </Button>
                        </div>
                    </form>
                </div>
            </div>
        </>
    );
}
