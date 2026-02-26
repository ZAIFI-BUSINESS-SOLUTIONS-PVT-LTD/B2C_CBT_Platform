import { useMemo } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { UserRound, Crown } from "lucide-react";

/**
 * Lightweight StudentProfile avatar used in headers.
 * Clicking the avatar navigates to the full /profile page.
 */
export function StudentProfile({ avatarClassName, showCrown }: { avatarClassName?: string; showCrown?: boolean } = {}) {
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
      className="p-1 rounded-full hover:bg-gray-100 touch-none relative"
      onClick={() => navigate('/profile')}
    >
      <Avatar className={avatarClassName ?? "h-10 w-10 sm:h-12 sm:w-12"}>
        {student?.googlePicture ? (
          <AvatarImage src={student.googlePicture} alt={student.fullName || 'Profile'} />
        ) : (
          <AvatarFallback className="bg-blue-600 flex items-center justify-center p-1 rounded-full">
            <div className="bg-blue-600 rounded-full p-1">
              <UserRound className="h-4 w-4 text-white" />
            </div>
          </AvatarFallback>
        )}

      {/* Optional crown badge positioned near the avatar */}
      {showCrown && (
        <span className="absolute -top-1 -right-1 h-6 w-6 rounded-full flex items-center justify-center bg-blue-100 border-2 border-blue-900 text-sky-400 shadow-sm">
          <Crown className="h-3 w-3" />
        </span>
      )}
      </Avatar>
    </Button>
  );
}
