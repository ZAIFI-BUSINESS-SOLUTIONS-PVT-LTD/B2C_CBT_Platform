import { useState } from "react";
import { Link, useLocation } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import MobileOtpLogin from "@/components/MobileOtpLogin";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { AlertCircle, Eye, EyeOff, Smartphone } from "lucide-react";
import GoogleSignIn from "@/components/google-signin";

export function LoginForm() {
  const { login, loading, error } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  // register modal removed; standalone /register page now
  const [showPassword, setShowPassword] = useState(false);
  const [showOtpLogin, setShowOtpLogin] = useState(false);
  const [, navigate] = useLocation();

  // Check if there's any authentication error
  const hasAuthError = formError || error;

  // Clean error message - hide technical details
  const getCleanErrorMessage = () => {
    if (formError) {
      // Handle validation errors
      if (formError.includes("required")) {
        return formError; // Keep validation messages as they are user-friendly
      }
    }

    if (error) {
      // If backend returned the duplicate-name validation, surface a clear instruction
      try {
        const msg = String(error).toLowerCase();
        if (msg.includes("multiple accounts") || msg.includes("multiple accounts found")) {
          return "Multiple accounts were found with this name. Please login using your Student ID or email.";
        }
      } catch (e) {
        // ignore
      }

      // Handle authentication errors - convert all to user-friendly message
      if (
        error.includes("invalid") ||
        error.includes("credentials") ||
        error.includes("non_field_errors") ||
        error.includes("401") ||
        error.includes("unauthorized")
      ) {
        return "Incorrect email or password. Please try again.";
      }
      // For any other server errors
      return "Unable to log in at this time. Please try again later.";
    }

    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    console.log("Login form submitted with:", { username, password });

    // Add validation to prevent empty submissions
    if (!username || !password) {
      console.log("Login attempted with empty credentials, blocking submission");
      setFormError("Username and password are required");
      return;
    }

    try {
      console.log("Calling login function...");
      const result = await login({ email: username, password }); // Pass username as email parameter
      console.log("Login successful:", result);
    } catch (err: any) {
      console.error("Login error:", err);
      setFormError(err.message || "Login failed");
    }
  };

  // Show forgot link only for server/auth errors (not form validation)
  const showForgotLink =
    !!error &&
    (error.includes("invalid") ||
      error.includes("credentials") ||
      error.includes("non_field_errors") ||
      error.includes("401") ||
      error.includes("unauthorized"));

  return (
    // Page wrappers (e.g. `pages/login.tsx` / `pages/register.tsx`) are now responsible for background
    <div>
      {/*
      <div className="w-full flex flex-col items-center justify-center md:max-w-md">
        <form
          onSubmit={handleSubmit}
          className="space-y-4 w-full p-6 pb-6 pt-8 bg-white/8 backdrop-blur-md border border-white/10 rounded-2xl shadow-lg md:mx-4 md:px-6 md:py-8"
        >
          <div className="space-y-1">
            <Input
              type="text"
              placeholder="Email id"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className={`transition-all duration-200 text-base h-12 rounded-xl bg-white/10 placeholder-white/70 text-white border border-white/20 focus:bg-white/20 focus:border-blue-300 ${hasAuthError
                ? "ring-1 ring-red-400"
                : ""
                }`}
              aria-invalid={hasAuthError ? "true" : "false"}
              aria-describedby={hasAuthError ? "login-error" : undefined}
            />
          </div>
          {/* Password Input 
          <div className="space-y-1 relative">
            <Input
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className={`transition-all duration-200 pr-10 text-base h-12 rounded-xl bg-white/10 placeholder-white/70 text-white border border-white/20 focus:bg-white/20 focus:border-blue-300 ${hasAuthError
                ? "ring-1 ring-red-400"
                : ""
                }`}
              aria-invalid={hasAuthError ? "true" : "false"}
              aria-describedby={hasAuthError ? "login-error" : undefined}
            />
            {/* Password Toggle Button
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700 focus:outline-none focus:text-gray-700 transition-colors duration-200"
              aria-label={showPassword ? "Hide password" : "Show password"}
              tabIndex={0}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {/* Error Message - Positioned between password and login button
          {getCleanErrorMessage() && (
            <div
              id="login-error"
              role="alert"
              className="flex items-center space-x-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-md p-3 animate-in slide-in-from-top-2 duration-300"
            >
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{getCleanErrorMessage()}</span>
            </div>
          )}

          {/* Forgot password link shown for authentication errors
          {showForgotLink && (
            <div className="w-full text-left mt-2">
              <Link
                href="/forgot-password"
                className="text-blue-600 underline p-0 h-auto min-h-0 hover:text-blue-700 transition-colors duration-200 text-sm"
              >
                Forgotten your password?
              </Link>
            </div>
          )}

          {/* Login Button
          <div className="flex flex-col w-full gap-3">
            <Button
              variant="default"
              type="submit"
              disabled={loading}
              size={"lg"}
              className="w-full rounded-xl h-12 bg-gradient-to-r from-blue-500/95 to-blue-400/95 text-white shadow-lg hover:from-blue-500/100 hover:to-blue-400/100 transition-all duration-200"
            >
              {loading ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Logging in...</span>
                </div>
              ) : (
                "Login"
              )}
            </Button>
          </div>
          {/* Google Sign-In Button
          <div className="flex flex-col w-full gap-3">
            <GoogleSignIn
              onSuccess={(data) => console.log('Google sign-in success', data)}
              onError={(err) => setFormError(String(err))}
              disabled={loading}
              className="w-full rounded-xl h-12 bg-white/10 text-white border border-white/20"
            />
          </div>

          {/* Create Profile
          <div className="flex flex-col w-full gap-3">
            <Button asChild type="button" size={"lg"} variant="outline" className="w-full rounded-xl h-12 bg-white/6 text-white/90 border border-white/10">
              <Link href="/register" className="w-full text-center">
                Create Profile
              </Link>
            </Button>
          </div>
            {/* (OTP button moved outside form)

        </form>
        */}
        {/* Inline Mobile OTP UI (show phone input + Get OTP directly) */}
        <div className="w-full max-w-md -mt-28">
          <div className="bg-white/6 p-4 rounded-2xl shadow-sm">
            <MobileOtpLogin
              onSuccess={() => {
                setShowOtpLogin(false);
                navigate('/dashboard');
              }}
            />
          </div>
        </div>
      </div>
  );
}