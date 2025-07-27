import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { RegisterForm } from "@/components/RegisterForm";

export function LoginForm() {
  const { login, loading, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [showRegister, setShowRegister] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    console.log("Login form submitted with:", { email, password });
    
    // Add validation to prevent empty submissions
    if (!email || !password) {
      console.log("Login attempted with empty credentials, blocking submission");
      setFormError("Email and password are required");
      return;
    }
    
    try {
      console.log("Calling login function...");
      const result = await login({ email, password });
      console.log("Login successful:", result);
    } catch (err: any) {
      console.error("Login error:", err);
      setFormError(err.message || "Login failed");
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="space-y-4 max-w-sm mx-auto p-6 bg-white rounded shadow">
        <h2 className="text-xl font-bold mb-2">Student Login</h2>
        <Input
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />
        <Input
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
        />
        <Button type="submit" disabled={loading} className="w-full">
          {loading ? "Logging in..." : "Login"}
        </Button>
        {(formError || error) && (
          <div className="text-red-600 text-sm mt-2">{formError || error}</div>
        )}
        <div className="text-center mt-4">
          <Dialog open={showRegister} onOpenChange={setShowRegister}>
            <DialogTrigger asChild>
              <Button type="button" variant="link" className="text-blue-600 underline p-0 h-auto min-h-0">
                Create Profile
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Create Student Profile</DialogTitle>
              </DialogHeader>
              <RegisterForm onSuccess={(profile) => {
                console.log("Profile created successfully:", profile);
                // Small delay to ensure registration completes before closing dialog
                setTimeout(() => setShowRegister(false), 100);
              }} />
            </DialogContent>
          </Dialog>
        </div>
      </form>
    </>
  );
}
