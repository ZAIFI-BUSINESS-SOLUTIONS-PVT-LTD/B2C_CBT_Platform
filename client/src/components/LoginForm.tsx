import { useState } from "react";
import { Link } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { RegisterForm } from "@/components/RegisterForm";
import GoogleSignIn from "@/components/google-signin";
import MobileOtpLogin from "@/components/MobileOtpLogin";
import Logo from "@/assets/images/logo.svg";

import { AlertCircle, Eye, EyeOff, Smartphone } from "lucide-react";

export function LoginForm() {
  const { login, loading, error } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  // register modal removed; standalone /register page now
  const [showPassword, setShowPassword] = useState(false);
  const [showOtpLogin, setShowOtpLogin] = useState(false);

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
      {/* Login Form */}
      <div className="w-full flex flex-col items-center justify-center md:max-w-md">
        <form
          onSubmit={handleSubmit}
          className="space-y-4 w-full p-6 pb-6 pt-8 bg-white rounded-t-2xl shadow-lg md:rounded-2xl md:mx-4 md:px-6 md:py-8"
        >
          <div className="space-y-1 items-center text-center text-sm text-gray-600">
            <img src={Logo} alt="Logo" className="h-6 mx-auto mb-2" />
            Login
          </div>
          <div className="space-y-1">
            <Input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className={`transition-all duration-200 text-base h-12 rounded-xl ${
                hasAuthError
                  ? "border-red-500 focus:border-red-500 focus:ring-red-500 bg-red-50"
                  : "focus:border-blue-500 focus:ring-blue-500"
              }`}
              aria-invalid={hasAuthError ? "true" : "false"}
              aria-describedby={hasAuthError ? "login-error" : undefined}
            />
          </div>
          {/* Password Input */}
          <div className="space-y-1 relative">
            <Input
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className={`transition-all duration-200 pr-10 text-base h-12 rounded-xl ${
                hasAuthError
                  ? "border-red-500 focus:border-red-500 focus:ring-red-500 bg-red-50"
                  : "focus:border-blue-500 focus:ring-blue-500"
              }`}
              aria-invalid={hasAuthError ? "true" : "false"}
              aria-describedby={hasAuthError ? "login-error" : undefined}
            />
            {/* Password Toggle Button */}
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
          {/* Error Message - Positioned between password and login button */}
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

          {/* Forgot password link shown for authentication errors */}
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

          {/* Login Button and link to Register page */}
          <div className="flex flex-col w-full gap-3">
            <Button variant="default" type="submit" disabled={loading} size={"lg"} className="w-full rounded-xl h-12">
              {loading ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Logging in...</span>
                </div>
              ) : (
                "Login"
              )}
            </Button>
            {/* Google Sign-In Button */}
            <GoogleSignIn
              onSuccess={(data) => {
                console.log("Google sign-in successful:", data);
              }}
              onError={(error) => {
                console.error("Google sign-in error:", error);
                setFormError(error);
              }}
              disabled={loading}
            />
            {/* Mobile OTP Login Button */}
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={() => setShowOtpLogin(true)}
              disabled={loading}
              className="w-full text-lg py-3 border-green-300 hover:bg-green-50 hover:border-green-400 text-green-700 hover:text-green-800"
            >
              <Smartphone className="h-5 w-5 mr-2" />
              Login with Mobile OTP
            </Button>

          </div>

          {/* OR Divider */}
          <div className="relative flex items-center justify-center my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative bg-white px-4 text-sm text-gray-500 font-medium">OR</div>
          </div>
          <Button asChild type="button" size={"lg"} variant="outline" className="w-full rounded-xl h-12">
            <Link href="/register" className="w-full text-center">
              Create Profile
            </Link>
          </Button>
        </form>
        {/* Mobile OTP Login Dialog */}
        <Dialog open={showOtpLogin} onOpenChange={setShowOtpLogin}>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>
                <span className="block text-center text-green-700 text-2xl font-bold">Mobile OTP Login</span>
              </DialogTitle>
            </DialogHeader>
            <MobileOtpLogin
              onSuccess={() => {
                console.log("Mobile OTP login successful");
                setTimeout(() => setShowOtpLogin(false), 100);
              }}
              onError={(error) => {
                console.error("Mobile OTP login error:", error);
                // Don't close dialog on error, let user retry
              }}
              onBack={() => setShowOtpLogin(false)}
            />
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
