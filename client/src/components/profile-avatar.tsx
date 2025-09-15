import { useMemo } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

/**
 * Lightweight StudentProfile avatar used in headers.
 * Clicking the avatar navigates to the full /profile page.
 */
export function StudentProfile() {
  const { student } = useAuth();
  const [, navigate] = useLocation();

  const initials = useMemo(() => {
    const name = (student && (student.fullName || student.email)) || "";
    if (!name) return "ST";
    return name
      .split(" ")
      .map((w: string) => w.charAt(0))
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }, [student]);

  return (
    <Button
      variant="ghost"
      className="p-1 rounded-full hover:bg-gray-100 touch-none"
      onClick={() => navigate('/dashboard')}
    >
      <Avatar className="h-10 w-10">
        <AvatarFallback className="bg-blue-600 text-white">{initials}</AvatarFallback>
      </Avatar>
    </Button>
  );
}
