import { useState } from "react";
import { useLocation } from "wouter";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { AlertCircle, ArrowLeft, Eye, EyeOff, Building2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface InstitutionRegisterFormProps {
  onSuccess?: () => void;
  onBack?: () => void;
  onSwitchToLogin?: () => void;
}

export function InstitutionRegisterForm({ onSuccess, onBack, onSwitchToLogin }: InstitutionRegisterFormProps) {
  const [, navigate] = useLocation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [showPassword, setShowPassword] = useState(false);

  // Form fields
  const [institutionName, setInstitutionName] = useState("");
  const [adminUsername, setAdminUsername] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [institutionCode, setInstitutionCode] = useState("");
  const [examTypes, setExamTypes] = useState<string[]>(["neet"]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setFieldErrors({});
    setLoading(true);

    // Client-side validation
    const errors: Record<string, string> = {};
    
    if (!institutionName.trim()) {
      errors.institution_name = "Institution name is required";
    }
    if (!adminUsername.trim()) {
      errors.admin_username = "Username is required";
    }
    if (!adminPassword) {
      errors.admin_password = "Password is required";
    } else if (adminPassword.length < 6) {
      errors.admin_password = "Password must be at least 6 characters";
    }
    if (examTypes.length === 0) {
      errors.exam_types = "Please select at least one exam type";
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setLoading(false);
      return;
    }

    try {
      const response = await fetch("/api/institution-admin/register/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          institution_name: institutionName.trim(),
          admin_username: adminUsername.trim(),
          admin_password: adminPassword,
          institution_code: institutionCode.trim() || undefined,
          exam_types: examTypes,
        }),
      });

      // Defensive parsing: read text first and parse JSON only when present.
      const respText = await response.text();
      let data: any = {};
      try {
        data = respText ? JSON.parse(respText) : {};
      } catch (e) {
        // If response wasn't JSON, keep the raw text as message
        data = { message: respText };
      }

      if (!response.ok) {
        if (data.errors) {
          setFieldErrors(data.errors);
        }
        setError(data.message || "Registration failed");
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
      console.error("Registration error:", err);
      setError("Failed to connect to server. Please try again.");
      setLoading(false);
    }
  };

  const toggleExamType = (type: string) => {
    setExamTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
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
            <h2 className="text-xl font-bold">Institution Registration</h2>
          </div>
          <p className="text-sm text-gray-600">Create your institution profile</p>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Institution Name */}
        <div className="space-y-1">
          <Label htmlFor="institutionName">
            Institution Name <span className="text-red-500">*</span>
          </Label>
          <Input
            id="institutionName"
            type="text"
            placeholder="e.g., Acme Coaching Center"
            value={institutionName}
            onChange={(e) => setInstitutionName(e.target.value)}
            disabled={loading}
            className={fieldErrors.institution_name ? "border-red-500" : ""}
          />
          {fieldErrors.institution_name && (
            <p className="text-xs text-red-500">{fieldErrors.institution_name}</p>
          )}
        </div>

        {/* Institution Code (Optional) */}
        <div className="space-y-1">
          <Label htmlFor="institutionCode">
            Institution Code (Optional)
          </Label>
          <Input
            id="institutionCode"
            type="text"
            placeholder="Auto-generated if not provided"
            value={institutionCode}
            onChange={(e) => setInstitutionCode(e.target.value.toUpperCase())}
            disabled={loading}
            className={fieldErrors.institution_code ? "border-red-500" : ""}
            maxLength={20}
          />
          <p className="text-xs text-gray-500">
            Students will use this code to access your tests
          </p>
          {fieldErrors.institution_code && (
            <p className="text-xs text-red-500">{fieldErrors.institution_code}</p>
          )}
        </div>

        {/* Admin Username */}
        <div className="space-y-1">
          <Label htmlFor="adminUsername">
            Admin Username <span className="text-red-500">*</span>
          </Label>
          <Input
            id="adminUsername"
            type="text"
            placeholder="Your admin username"
            value={adminUsername}
            onChange={(e) => setAdminUsername(e.target.value)}
            disabled={loading}
            className={fieldErrors.admin_username ? "border-red-500" : ""}
          />
          {fieldErrors.admin_username && (
            <p className="text-xs text-red-500">{fieldErrors.admin_username}</p>
          )}
        </div>

        {/* Admin Password */}
        <div className="space-y-1">
          <Label htmlFor="adminPassword">
            Password <span className="text-red-500">*</span>
          </Label>
          <div className="relative">
            <Input
              id="adminPassword"
              type={showPassword ? "text" : "password"}
              placeholder="Minimum 6 characters"
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
              disabled={loading}
              className={fieldErrors.admin_password ? "border-red-500" : ""}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {fieldErrors.admin_password && (
            <p className="text-xs text-red-500">{fieldErrors.admin_password}</p>
          )}
        </div>

        {/* Exam Types */}
        <div className="space-y-2">
          <Label>
            Exam Types <span className="text-red-500">*</span>
          </Label>
          <div className="flex flex-col space-y-2">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="neet"
                checked={examTypes.includes("neet")}
                onCheckedChange={() => toggleExamType("neet")}
                disabled={loading}
              />
              <label htmlFor="neet" className="text-sm font-medium cursor-pointer">
                NEET (Medical)
              </label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="jee"
                checked={examTypes.includes("jee")}
                onCheckedChange={() => toggleExamType("jee")}
                disabled={loading}
              />
              <label htmlFor="jee" className="text-sm font-medium cursor-pointer">
                JEE (Engineering)
              </label>
            </div>
          </div>
          {fieldErrors.exam_types && (
            <p className="text-xs text-red-500">{fieldErrors.exam_types}</p>
          )}
        </div>

        {/* Submit Button */}
        <Button
          type="submit"
          disabled={loading}
          size="lg"
          className="w-full rounded-xl h-12"
        >
          {loading ? (
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>Creating Profile...</span>
            </div>
          ) : (
            "Create Institution Profile"
          )}
        </Button>

        {/* Admin Login Link */}
        <div className="text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{" "}
            <button
              type="button"
              onClick={() => onSwitchToLogin?.()}
              className="text-blue-600 hover:text-blue-700 font-medium underline"
              disabled={loading}
            >
              Admin Login
            </button>
          </p>
        </div>

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
