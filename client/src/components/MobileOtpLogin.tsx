import { useState, useEffect } from "react";
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

    if (!otp.trim()) {
      setError("OTP is required");
      setLoading(false);
      return;
    }

    if (otp.length !== 6) {
      setError("Please enter a valid 6-digit OTP");
      setLoading(false);
      return;
    }

    try {
      const normalizedMobile = normalizeMobileNumber(mobileNumber);
      const response = await verifyOtp(normalizedMobile, otp);
      console.log("OTP verified successfully:", response);

      // Set authentication using the same method as other login flows
      setAuthFromTokens(
        { access: response.access, refresh: response.refresh },
        response.student
      );

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
    setOtp("");
    
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
      setOtp("");
      setError(null);
      setCountdown(0);
    } else if (onBack) {
      onBack();
    }
  };

  if (step === 'mobile') {
    return (
      <div className="space-y-4">
        {onBack && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-800"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to login options
          </Button>
        )}
        
        <div className="text-center">
          <Smartphone className="h-8 w-8 mx-auto text-blue-600 mb-2" />
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            Login with Mobile OTP
          </h3>
          <p className="text-sm text-gray-600">
            Enter your mobile number to receive a verification code
          </p>
        </div>

        <form onSubmit={handleSendOtp} className="space-y-4">
          <div>
            <Input
              type="tel"
              placeholder="Enter mobile number (e.g., 9876543210)"
              value={mobileNumber}
              onChange={(e) => setMobileNumber(e.target.value)}
              required
              disabled={loading || disabled}
              className="text-base py-3"
              maxLength={13}
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter 10-digit Indian mobile number
            </p>
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
            className="w-full text-base py-3"
            size="lg"
          >
            {loading ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Sending OTP...</span>
              </div>
            ) : (
              "Send OTP"
            )}
          </Button>
        </form>
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
        <Smartphone className="h-8 w-8 mx-auto text-green-600 mb-2" />
        <h3 className="text-lg font-semibold text-gray-900 mb-1">
          Enter OTP
        </h3>
        <p className="text-sm text-gray-600">
          We've sent a 6-digit code to
        </p>
        <p className="text-sm font-medium text-gray-900">
          {mobileNumber}
        </p>
      </div>

      <form onSubmit={handleVerifyOtp} className="space-y-4">
        <div>
          <Input
            type="text"
            placeholder="Enter 6-digit OTP"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
            required
            disabled={loading || disabled}
            className="text-center text-xl font-mono py-3 tracking-widest"
            maxLength={6}
            autoComplete="one-time-code"
          />
          
          {countdown > 0 && (
            <p className="text-xs text-gray-500 mt-1 text-center">
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
          disabled={loading || disabled || otp.length !== 6}
          className="w-full text-base py-3"
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