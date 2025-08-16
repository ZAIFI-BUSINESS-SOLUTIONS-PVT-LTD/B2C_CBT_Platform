import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { RegisterForm } from "@/components/RegisterForm";

import { AlertCircle, Eye, EyeOff } from "lucide-react";
import loginImg from "@/assets/images/login.png";

export function LoginForm() {
  const { login, loading, error } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [showRegister, setShowRegister] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

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
      if (error.includes("invalid") || 
          error.includes("credentials") || 
          error.includes("non_field_errors") ||
          error.includes("401") ||
          error.includes("unauthorized")) {
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


  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 relative overflow-hidden font-sans">
      <div className="flex flex-col md:flex-row items-center justify-center w-full max-w-4xl min-h-[600px] bg-white/60 rounded-2xl shadow-2xl p-0 md:p-8 relative z-10">
        {/* Left: Illustration */}
        <div className="hidden md:flex flex-col items-center justify-center w-1/2 h-full p-8">
          <img
            src={loginImg}
            alt="Login Illustration"
            className="w-[420px] h-[420px] object-contain"
            style={{ minHeight: 380 }}
          />
        </div>
        {/* Right: Login Form */}
        <div className="w-full md:w-1/2 flex flex-col items-center justify-center p-6 md:p-10">
          <form onSubmit={handleSubmit} className="space-y-6 w-full max-w-md mx-auto p-8 bg-white rounded-xl shadow-lg">
            <h2 className="text-3xl font-bold mb-2 text-blue-700 text-center">Welcome!</h2>
            <p className="text-lg text-gray-500 mb-6 text-center">Sign in to your account</p>
            {/* Email/Username Input */}
            <div className="space-y-1">
              <Input
                type="text"
                placeholder="Username, Email, or Student ID"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                className={`transition-all duration-200 text-base py-3 ${
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
                onChange={e => setPassword(e.target.value)}
                required
                className={`transition-all duration-200 pr-10 text-base py-3 ${
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
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
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
            {/* Login Button */}
            <Button 
              type="submit" 
              disabled={loading} 
              className="w-full transition-all duration-200 bg-blue-600 hover:bg-blue-700 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-lg py-3"
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
            {/* Create Profile Link */}
            <div className="text-center mt-4">
              <Dialog open={showRegister} onOpenChange={setShowRegister}>
                <DialogTrigger asChild>
                  <Button 
                    type="button" 
                    variant="link" 
                    className="text-blue-600 underline p-0 h-auto min-h-0 hover:text-blue-700 transition-colors duration-200 text-base"
                  >
                    Create Profile
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[425px]">
                  <DialogHeader>
                    <DialogTitle>
                      <span className="block text-center text-blue-700 text-2xl font-bold">Create Student Profile</span>
                    </DialogTitle>
                  </DialogHeader>
                  <RegisterForm onSuccess={(profile) => {
                    console.log("Profile created successfully:", profile);
                    setTimeout(() => setShowRegister(false), 100);
                  }} />
                </DialogContent>
              </Dialog>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
