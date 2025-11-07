import { useState } from "react";
import { useLocation } from "wouter";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { AlertCircle, ArrowLeft, Eye, EyeOff, Building2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface InstitutionAdminLoginFormProps {
  onSuccess?: () => void;
  onBack?: () => void;
  onSwitchToRegister?: () => void;
}

export function InstitutionAdminLoginForm({ 
  onSuccess, 
  onBack,
  onSwitchToRegister 
}: InstitutionAdminLoginFormProps) {
  const [, navigate] = useLocation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  // Form fields
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    // Client-side validation
    if (!username.trim()) {
      setError("Username is required");
      setLoading(false);
      return;
    }
    if (!password) {
      setError("Password is required");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch("/api/institution-admin/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username.trim(),
          password: password,
        }),
      });

      const respText = await response.text();
      let data: any = {};
      try {
        data = respText ? JSON.parse(respText) : {};
      } catch (e) {
        data = { message: respText };
      }

      if (!response.ok) {
        setError(data.message || "Invalid username or password");
        setLoading(false);
        return;
      }

      // Store tokens
      localStorage.setItem("institutionAdminToken", data.access);
      localStorage.setItem("institutionAdminRefresh", data.refresh);
      localStorage.setItem("institutionAdmin", JSON.stringify({
        id: data.admin.id,
        username: data.admin.username,
        institution: data.institution,
      }));

      // Navigate to institution admin dashboard
      if (onSuccess) {
        onSuccess();
      } else {
        navigate("/institution-admin/dashboard");
      }
    } catch (err: any) {
      console.error("Login error:", err);
      setError("Failed to connect to server. Please try again.");
      setLoading(false);
    }
  };

  return (
    <div className="w-full flex flex-col items-center justify-center md:max-w-md">
      <form
        onSubmit={handleSubmit}
        className="space-y-4 w-full p-6 pb-6 pt-8 bg-white rounded-t-2xl shadow-lg md:rounded-2xl md:mx-4 md:px-6 md:py-8"
      >
        {/* Header */}
        <div className="space-y-2 text-center">
          <div className="flex items-center justify-center gap-2 text-blue-600">
            <Building2 className="h-6 w-6" />
            <h2 className="text-xl font-bold">Institution Admin Login</h2>
          </div>
          <p className="text-sm text-gray-600">Access your institution dashboard</p>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Username */}
        <div className="space-y-1">
          <Label htmlFor="username">
            Admin Username <span className="text-red-500">*</span>
          </Label>
          <Input
            id="username"
            type="text"
            placeholder="Your admin username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading}
            autoComplete="username"
          />
        </div>

        {/* Password */}
        <div className="space-y-1">
          <Label htmlFor="password">
            Password <span className="text-red-500">*</span>
          </Label>
          <div className="relative">
            <Input
              id="password"
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              autoComplete="current-password"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Login Button */}
        <Button
          type="submit"
          disabled={loading}
          size="lg"
          className="w-full rounded-xl h-12"
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

        {/* Switch to Register */}
        {onSwitchToRegister && (
          <div className="text-center">
            <p className="text-sm text-gray-600">
              Don't have an institution account?{" "}
              <button
                type="button"
                onClick={onSwitchToRegister}
                className="text-blue-600 hover:text-blue-700 font-medium underline"
                disabled={loading}
              >
                Register here
              </button>
            </p>
          </div>
        )}

        {/* Back Button */}
        {onBack && (
          <Button
            type="button"
            variant="ghost"
            onClick={onBack}
            disabled={loading}
            className="w-full"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Login
          </Button>
        )}
      </form>
    </div>
  );
}
