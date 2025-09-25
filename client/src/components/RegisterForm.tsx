import { useState } from "react";
import { useLocation } from "wouter";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { apiRequest } from "@/lib/queryClient";
import { StudentProfile } from "@/types/api";
import { Eye, EyeOff, CheckCircle, XCircle } from "lucide-react";
import Logo from "@/assets/images/logo.svg";
import Login from "@/assets/images/login.png";

export function RegisterForm({ onSuccess }: { onSuccess?: (profile: StudentProfile) => void }) {
  const [form, setForm] = useState({
    fullName: "",
    email: "",
    phoneNumber: "",
    dateOfBirth: "",
    password: "",
    passwordConfirmation: "",
  });
  const [, navigate] = useLocation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirmation, setShowPasswordConfirmation] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState({ score: 0, label: "", errors: [] as string[] });
  const [usernameAvailable, setUsernameAvailable] = useState<boolean | null>(null);
  const [checkingUsername, setCheckingUsername] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });

    // Check password strength in real-time
    if (name === 'password') {
      checkPasswordStrength(value);
    }

    // Check username availability for full name
    if (name === 'fullName' && value.length >= 2) {
      checkUsernameAvailability(value);
    }
  };

  // Password strength checking function
  const checkPasswordStrength = (password: string) => {
    let score = 0;
    const errors: string[] = [];

    if (password.length < 8) {
      errors.push("Must be at least 8 characters");
    } else {
      score += 20;
    }

    if (password.length > 64) {
      errors.push("Must be no more than 64 characters");
      setPasswordStrength({ score: 0, label: "Invalid", errors });
      return;
    }

    if (!/[a-z]/.test(password)) {
      errors.push("Must contain lowercase letter");
    } else {
      score += 15;
    }

    if (!/[A-Z]/.test(password)) {
      errors.push("Must contain uppercase letter");
    } else {
      score += 15;
    }

    if (!/\d/.test(password)) {
      errors.push("Must contain a number");
    } else {
      score += 15;
    }

    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      errors.push("Must contain special character");
    } else {
      score += 15;
    }

    // Bonus for length
    if (password.length >= 12) score += 10;
    if (password.length >= 16) score += 10;

    let label = "Very Weak";
    if (score >= 85) label = "Strong";
    else if (score >= 70) label = "Good";
    else if (score >= 50) label = "Fair";
    else if (score >= 30) label = "Weak";

    setPasswordStrength({ score: Math.min(100, score), label, errors });
  };

  // Username availability checking
  const checkUsernameAvailability = async (fullName: string) => {
    if (fullName.length < 2) {
      setUsernameAvailable(null);
      return;
    }

    setCheckingUsername(true);
    try {
      // Make API call to check username availability
      const response = await fetch(`/api/student-profile/check-username/?full_name=${encodeURIComponent(fullName)}`);
      const data = await response.json();
      setUsernameAvailable(data.available);
    } catch (err) {
      console.error('Error checking username availability:', err);
      setUsernameAvailable(null);
    } finally {
      setCheckingUsername(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setError(null);
    setSuccess(null);

    // Validate form before submission
    if (!form.fullName.trim()) {
      setError("Full name is required");
      return;
    }

    if (!form.email.trim()) {
      setError("Email is required");
      return;
    }

    if (!form.phoneNumber.trim()) {
      setError("Phone number is required");
      return;
    }

    if (!form.password) {
      setError("Password is required");
      return;
    }

    if (form.password !== form.passwordConfirmation) {
      setError("Passwords do not match");
      return;
    }

    if (passwordStrength.score < 50) {
      setError("Password is too weak. Please choose a stronger password.");
      return;
    }

    if (usernameAvailable === false) {
      setError("Username is already taken. Please choose a different name.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        full_name: form.fullName,
        email: form.email,
        phone_number: form.phoneNumber,
        date_of_birth: form.dateOfBirth,
        password: form.password,
        password_confirmation: form.passwordConfirmation,
      };

      const profile = await apiRequest("/api/student-profile/register/", "POST", payload);

      setSuccess(`Registration successful! Welcome, ${profile.full_name}. Your Student ID is: ${profile.student_id}`);

      if (onSuccess) onSuccess(profile);
      // Redirect user to login page after short delay to let them read success and then sign in
      setTimeout(() => navigate("/login"), 2000);
    } catch (err: any) {
      let msg = err.message || "Registration failed";
      if (err.response) {
        try {
          const data = await err.response.json();
          if (typeof data === 'object' && data.non_field_errors) {
            msg = data.non_field_errors.join(', ');
          } else if (typeof data === 'object') {
            // Handle field-specific errors
            const fieldErrors = Object.entries(data)
              .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
              .join('; ');
            msg = fieldErrors || JSON.stringify(data);
          } else {
            msg = typeof data === 'string' ? data : JSON.stringify(data);
          }
        } catch {
          // If JSON parsing fails, use the original error message
        }
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 w-full p-6 pb-6 pt-8 bg-white rounded-t-2xl shadow-lg max-w-md mx-auto md:rounded-2xl md:mx-4 md:px-6 md:py-8">
      <div className="space-y-1 items-center text-center text-sm text-gray-600">
        <img src={Logo} alt="Logo" className="h-6 mx-auto mb-2" />
        Create Profile
      </div>
      <div className="space-y-4">
        {/* Full Name with Username Availability */}
        <div>
          <Label htmlFor="fullName">Full Name (Username) *</Label>
          <div className="relative">
            <Input
              id="fullName"
              name="fullName"
              placeholder="Enter your full name"
              value={form.fullName}
              onChange={handleChange}
              required
              className={`h-12 rounded-xl ${usernameAvailable === false ? "border-red-500" : usernameAvailable === true ? "border-green-500" : ""}`}
            />
            {checkingUsername && <div className="absolute right-3 top-3 text-sm text-gray-500">Checking...</div>}
            {usernameAvailable === true && <CheckCircle className="absolute right-3 top-3 h-4 w-4 text-green-500" />}
            {usernameAvailable === false && <XCircle className="absolute right-3 top-3 h-4 w-4 text-red-500" />}
          </div>
          {usernameAvailable === false && <p className="text-red-600 text-sm mt-1">This username is already taken</p>}
        </div>
        {/* Email */}
        <div>
          <Label htmlFor="email">Email Address *</Label>
          <Input
            id="email"
            name="email"
            type="email"
            placeholder="Enter your email"
            value={form.email}
            onChange={handleChange}
            required
            className="h-12 rounded-xl"
          />
        </div>
        {/* Password */}
        <div>
          <Label htmlFor="password">Password *</Label>
          <div className="relative">
            <Input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              value={form.password}
              onChange={handleChange}
              required
              minLength={8}
              maxLength={64}
              className="h-12 rounded-xl pr-10"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700 focus:outline-none focus:text-gray-700 transition-colors duration-200"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {/* Password Strength Indicator */}
          {form.password && (
            <div className="mt-2">
              <div className="flex justify-between text-sm">
                <span>Password Strength:</span>
                <span className={
                  passwordStrength.score >= 70 ? "text-green-600" :
                    passwordStrength.score >= 50 ? "text-yellow-600" : "text-red-600"
                }>
                  {passwordStrength.label}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                <div
                  className={`h-2 rounded-full transition-all ${passwordStrength.score >= 70 ? "bg-green-500" :
                    passwordStrength.score >= 50 ? "bg-yellow-500" : "bg-red-500"}
                  `}
                  style={{ width: `${passwordStrength.score}%` }}
                ></div>
              </div>
              {passwordStrength.errors.length > 0 && (
                <ul className="text-red-600 text-xs mt-1">
                  {passwordStrength.errors.map((error, index) => (
                    <li key={index}>• {error}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
        {/* Password Confirmation */}
        <div>
          <Label htmlFor="passwordConfirmation">Confirm Password *</Label>
          <div className="relative">
            <Input
              id="passwordConfirmation"
              name="passwordConfirmation"
              type={showPasswordConfirmation ? "text" : "password"}
              placeholder="Re-enter your password"
              value={form.passwordConfirmation}
              onChange={handleChange}
              required
              className={`h-12 rounded-xl pr-10 ${form.passwordConfirmation && form.password !== form.passwordConfirmation ? "border-red-500" : ""}`}
            />
            <button
              type="button"
              onClick={() => setShowPasswordConfirmation(!showPasswordConfirmation)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700 focus:outline-none focus:text-gray-700 transition-colors duration-200"
              aria-label={showPasswordConfirmation ? "Hide password" : "Show password"}
            >
              {showPasswordConfirmation ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {form.passwordConfirmation && form.password !== form.passwordConfirmation && (
            <p className="text-red-600 text-sm mt-1">Passwords do not match</p>
          )}
        </div>
        {/* Phone Number */}
        <div>
          <Label htmlFor="phoneNumber">Phone Number *</Label>
          <Input
            id="phoneNumber"
            name="phoneNumber"
            placeholder="Enter your phone number"
            value={form.phoneNumber}
            onChange={handleChange}
            required
            className="h-12 rounded-xl"
          />
        </div>
        {/* Date of Birth */}
        <div>
          <Label htmlFor="dateOfBirth">Date of Birth *</Label>
          <Input
            id="dateOfBirth"
            name="dateOfBirth"
            type="date"
            value={form.dateOfBirth}
            onChange={handleChange}
            required
            className="h-12 rounded-xl"
          />
        </div>
        {error && <div className="text-red-600 text-sm mt-2 p-2 bg-red-50 rounded">{error}</div>}
        {success && <div className="text-green-700 text-sm mt-2 p-2 bg-green-50 rounded">{success}</div>}
      </div>
      <div className="pt-4">
        <Button
          type="submit"
          disabled={loading || passwordStrength.score < 50 || usernameAvailable === false}
          className="w-full h-12 rounded-xl text-lg"
        >
          {loading ? "Creating Account..." : "Create Account"}
        </Button>
      </div>
    </form>
  );
}
