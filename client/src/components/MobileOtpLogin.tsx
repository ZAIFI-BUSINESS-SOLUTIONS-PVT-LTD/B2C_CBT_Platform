import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { AlertCircle, Smartphone, ArrowLeft } from "lucide-react";
import { sendOtp, verifyOtp } from "@/lib/otp-auth";

interface MobileOtpLoginProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
  onBack?: () => void;
  disabled?: boolean;
}

export default function MobileOtpLogin({ 
  onSuccess, 
  onError, 
  onBack,
  disabled = false 
}: MobileOtpLoginProps) {
  const { setAuthFromTokens } = useAuth();
  const [step, setStep] = useState<'mobile' | 'otp'>('mobile');
  const [mobileNumber, setMobileNumber] = useState("");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(0);
  const [canResend, setCanResend] = useState(true);
  const [otpDigits, setOtpDigits] = useState<string[]>(Array(6).fill(''));
  const inputsRef = useRef<(HTMLInputElement | null)[]>([]);

  // Countdown timer for OTP expiry (5 minutes)
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (countdown > 0) {
      timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [countdown]);

  // Format countdown display
  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Normalize mobile number to E.164 format for India
  const normalizeMobileNumber = (mobile: string) => {
    const cleaned = mobile.replace(/\D/g, '');
    if (cleaned.length === 10) {
      return `+91${cleaned}`;
    } else if (cleaned.length === 12 && cleaned.startsWith('91')) {
      return `+${cleaned}`;
    } else if (cleaned.length === 13 && cleaned.startsWith('+91')) {
      return cleaned;
    }
    return mobile; // Return as-is if format not recognized
  };

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    // Validate mobile number
    if (!mobileNumber.trim()) {
      setError("Mobile number is required");
      setLoading(false);
      return;
    }

    const normalizedMobile = normalizeMobileNumber(mobileNumber);
    
    // Basic validation for Indian mobile numbers
    if (!normalizedMobile.match(/^\+91[6-9]\d{9}$/)) {
      setError("Please enter a valid Indian mobile number");
      setLoading(false);
      return;
    }

    try {
      const response = await sendOtp(normalizedMobile);
      console.log("OTP sent successfully:", response);
      
      setStep('otp');
      setCountdown(300); // 5 minutes
      setCanResend(false);
      
      // Enable resend after cooldown period
      setTimeout(() => setCanResend(true), 30000); // 30 seconds cooldown
      
    } catch (err: any) {
      console.error("Send OTP error:", err);
      
      if (err.message?.includes('429')) {
        setError("Too many attempts. Please try again later.");
      } else if (err.message?.includes('rate limit')) {
        setError("Rate limit exceeded. Please wait before requesting another OTP.");
      } else {
        setError(err.message || "Failed to send OTP. Please try again.");
      }
      
      if (onError) {
        onError(err.message || "Failed to send OTP");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const enteredOtp = otpDigits.join('');
    if (!enteredOtp) {
      setError("OTP is required");
      setLoading(false);
      return;
    }

    if (enteredOtp.length !== 6) {
      setError("Please enter a valid 6-digit OTP");
      setLoading(false);
      return;
    }

    try {
      const normalizedMobile = normalizeMobileNumber(mobileNumber);
      const response = await verifyOtp(normalizedMobile, enteredOtp);
      console.log("OTP verified successfully:", response);

      // Set authentication using the same method as other login flows
      setAuthFromTokens({ access: response.access, refresh: response.refresh }, response.student);

      if (onSuccess) {
        onSuccess();
      }
      
    } catch (err: any) {
      console.error("Verify OTP error:", err);
      
      if (err.message?.includes('invalid') || err.message?.includes('expired')) {
        setError("Invalid or expired OTP. Please try again.");
      } else {
        setError(err.message || "Failed to verify OTP. Please try again.");
      }
      
      if (onError) {
        onError(err.message || "Failed to verify OTP");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (!canResend || loading) return;
    
    setError(null);
    setOtpDigits(Array(6).fill(''));
    
    try {
      setLoading(true);
      const normalizedMobile = normalizeMobileNumber(mobileNumber);
      await sendOtp(normalizedMobile);
      
      setCountdown(300); // Reset countdown
      setCanResend(false);
      setTimeout(() => setCanResend(true), 30000); // 30 seconds cooldown
      
    } catch (err: any) {
      console.error("Resend OTP error:", err);
      setError(err.message || "Failed to resend OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    if (step === 'otp') {
      setStep('mobile');
      setOtpDigits(Array(6).fill(''));
      setError(null);
      setCountdown(0);
    } else if (onBack) {
      onBack();
    }
  };

  useEffect(() => {
    if (step === 'otp') {
      // focus first input when entering otp step
      setTimeout(() => inputsRef.current[0]?.focus(), 50);
    }
  }, [step]);

  const handleOtpInputChange = (index: number, value: string) => {
    // accept only digits
    const digits = value.replace(/\D/g, '');
    setOtpDigits(prev => {
      const next = [...prev];
      if (digits.length === 1) {
        next[index] = digits;
      } else if (digits.length > 1) {
        // pasted multiple digits - fill from index
        for (let i = 0; i < digits.length && index + i < next.length; i++) {
          next[index + i] = digits.charAt(i);
        }
      } else {
        next[index] = '';
      }
      return next;
    });

    // move focus
    if (digits.length === 1) {
      const nextInput = inputsRef.current[index + 1];
      if (nextInput) nextInput.focus();
    } else if (digits.length > 1) {
      const pos = Math.min(6, index + digits.length);
      const nextInput = inputsRef.current[pos];
      if (nextInput) nextInput.focus();
    }
  };

  const handleOtpKeyDown = (e: React.KeyboardEvent, index: number) => {
    const key = e.key;
    if (key === 'Backspace') {
      if (otpDigits[index]) {
        setOtpDigits(prev => {
          const next = [...prev];
          next[index] = '';
          return next;
        });
      } else {
        const prevInput = inputsRef.current[index - 1];
        if (prevInput) prevInput.focus();
      }
    }
    if (key === 'ArrowLeft') {
      const prevInput = inputsRef.current[index - 1];
      if (prevInput) prevInput.focus();
    }
    if (key === 'ArrowRight') {
      const nextInput = inputsRef.current[index + 1];
      if (nextInput) nextInput.focus();
    }
  };

  if (step === 'mobile') {
    return (
      <div className="w-full flex flex-col items-center">
        {onBack && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-800 mb-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to login options
          </Button>
        )}

        <div className="w-full max-w-xs bg-white/6 p-4 rounded-2xl shadow-inner border border-white/10">
          <p className="text-sm text-gray-600">
            Enter your mobile number
          </p>

          <form onSubmit={handleSendOtp} className="space-y-3">
            <div className="flex items-center bg-white/90 rounded-xl overflow-hidden border border-white/20 shadow-sm">
              <span className="px-3 text-sm text-gray-700 bg-transparent">+91</span>
              <Input
                type="tel"
                placeholder="98765 43210"
                value={mobileNumber}
                onChange={(e) => setMobileNumber(e.target.value.replace(/[^0-9\s]/g, ''))}
                required
                disabled={loading || disabled}
                className="flex-1 text-base h-12 rounded-none px-2"
                maxLength={13}
              />
            </div>

            {error && (
              <div className="flex items-center space-x-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-md p-3">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <Button
              type="submit"
              disabled={loading || disabled}
              className="w-full h-12 rounded-full bg-gradient-to-r from-blue-500 to-blue-400 text-white shadow-lg"
              size="lg"
            >
              {loading ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Sending OTP...</span>
                </div>
              ) : (
                "Get OTP"
              )}
            </Button>

            <p className="text-center text-xs text-gray-500">OTP will be sent for verification.</p>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={handleBack}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-800"
      >
        <ArrowLeft className="h-4 w-4" />
        Change mobile number
      </Button>

      <div className="text-center">
        <p className="text-sm text-gray-600">
          We've sent a 6-digit code to
        </p>
        <p className="text-sm font-medium text-gray-900">
          {normalizeMobileNumber(mobileNumber)}
        </p>
      </div>

      <form onSubmit={handleVerifyOtp} className="space-y-4">
        <div>
          <div className="flex items-center justify-center gap-2">
            {otpDigits.map((digit, idx) => (
              <input
                key={idx}
                ref={(el) => (inputsRef.current[idx] = el)}
                value={digit}
                onChange={(e) => handleOtpInputChange(idx, e.target.value)}
                onKeyDown={(e) => handleOtpKeyDown(e as any, idx)}
                inputMode="numeric"
                pattern="\d*"
                maxLength={1}
                className="w-12 h-12 md:w-14 md:h-14 bg-white/90 border border-blue-300 rounded-md text-center text-xl font-mono focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            ))}
          </div>

          {countdown > 0 && (
            <p className="text-xs text-gray-500 mt-2 text-center">
              OTP expires in {formatCountdown(countdown)}
            </p>
          )}
        </div>

        {error && (
          <div className="flex items-center space-x-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-md p-3">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <Button
          type="submit"
          disabled={loading || disabled || otpDigits.join('').length !== 6}
          className="w-full text-base py-3 rounded-full bg-gradient-to-r from-blue-500 to-blue-400 text-white"
          size="lg"
        >
          {loading ? (
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>Verifying...</span>
            </div>
          ) : (
            "Verify OTP"
          )}
        </Button>

        <div className="text-center">
          <Button
            type="button"
            variant="link"
            onClick={handleResendOtp}
            disabled={!canResend || loading}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {!canResend ? "Resend OTP (wait 30s)" : "Resend OTP"}
          </Button>
        </div>
      </form>
    </div>
  );
}