/**
 * Student Profile Component
 * 
 * DETAILED EXPLANATION:
 * This component displays student profile information in the top right corner
 * of the application. It provides a complete profile management interface with
 * both display and editing capabilities, backed by PostgreSQL database storage.
 * 
 * COMPONENT FEATURES:
 * - Student name and profile picture display
 * - Quick access to profile settings and actions
 * - Profile creation/editing functionality with form validation
 * - School and exam year information management
 * - Real-time profile updates with optimistic UI
 * 
 * BUSINESS LOGIC:
 * - Fetches profile data from PostgreSQL via API
 * - Handles profile creation for new students
 * - Supports profile editing with validation
 * - Manages profile state with React Query caching
 * - Implements error handling and loading states
 * 
 * USER EXPERIENCE:
 * - Positioned in top-right corner for easy access
 * - Modal dialog for profile editing to maintain context
 * - Form validation with clear error messages
 * - Optimistic updates for immediate feedback
 * - Responsive design for mobile and desktop
 * 
 * DATABASE INTEGRATION:
 * - Uses PostgreSQL student_profiles table
 * - Supports full CRUD operations for profile data
 * - Implements proper error handling for API failures
 * - Caches profile data for performance
 * 
 * TECHNICAL IMPLEMENTATION:
 * - React Query for data fetching and caching
 * - React Hook Form with Zod validation
 * - Shadcn/UI components for consistent design
 * - TypeScript for type safety
 * - Real-time updates with mutation invalidation
 */

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { 
  User, 
  Mail, 
  Phone, 
  Calendar,
  GraduationCap,
  Plus,
  Edit,
  LogOut
} from "lucide-react";

// Student profile form schema
const profileFormSchema = z.object({
  fullName: z.string().min(2, "Full name must be at least 2 characters"),
  email: z.string().email("Invalid email address"),
  phoneNumber: z.string().optional(),
  dateOfBirth: z.string().optional(),
  schoolName: z.string().optional(),
  targetExamYear: z.number().min(2024).max(2030).optional(),
});

type ProfileFormData = z.infer<typeof profileFormSchema>;

interface StudentProfile {
  studentId: string;
  fullName: string;
  email: string;
  phoneNumber?: string;
  dateOfBirth?: string;
  schoolName?: string;
  targetExamYear?: number;
}

/**
 * Main Student Profile Component
 * 
 * DETAILED FUNCTIONALITY:
 * This component serves as the primary interface for student profile display
 * and management. It handles the complete profile lifecycle from initial
 * creation to ongoing updates, with proper state management and error handling.
 * 
 * COMPONENT STATE:
 * - showProfileDialog: Controls modal dialog visibility
 * - isEditing: Toggles between view and edit modes
 * - currentProfile: Stores current profile data for editing
 * - toast: Handles user notifications
 * - queryClient: Manages React Query cache invalidation
 * 
 * AUTHENTICATION INTEGRATION:
 * - Uses demo email for development/testing
 * - Designed to integrate with full authentication system
 * - Supports dynamic user identification
 * 
 * REAL-TIME FEATURES:
 * - Optimistic updates for immediate user feedback
 * - Automatic cache invalidation on profile changes
 * - Loading states during API operations
 * - Error recovery with user-friendly messages
 * 
 * Displays profile info and handles profile management
 */
export function StudentProfile() {
  const [showProfileDialog, setShowProfileDialog] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [currentProfile, setCurrentProfile] = useState<StudentProfile | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { isAuthenticated, student, logout } = useAuth();
  const [, navigate] = useLocation();

  // Fetch student profile (only when authenticated)
  const { data: profile, isLoading } = useQuery<StudentProfile>({
    queryKey: ['/api/students/me/'],
    retry: false,
    enabled: isAuthenticated && !!student, // Only run this query when user is authenticated and student data exists
  });

  // Create/Update profile mutation
  const profileMutation = useMutation({
    mutationFn: async (data: ProfileFormData) => {
      if (currentProfile) {
        return await apiRequest(`/api/student-profile/update/${currentProfile.studentId}/`, "PUT", data);
      } else {
        return await apiRequest("/api/student-profile", "POST", data);
      }
    },
    onSuccess: (data) => {
      setCurrentProfile(data);
      setShowProfileDialog(false);
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['/api/students/me/'] });
      toast({
        title: "Profile saved successfully",
        description: "Your profile information has been updated.",
      });
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to save profile. Please try again.",
        variant: "destructive",
      });
    },
  });

  // Form setup
  const form = useForm<ProfileFormData>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: {
      fullName: "",
      email: student?.email || "",
      phoneNumber: "",
      dateOfBirth: "",
      schoolName: "",
      targetExamYear: 2025,
    },
  });

  // Update form when profile data is available
  useEffect(() => {
    if (profile) {
      setCurrentProfile(profile);
      form.reset({
        fullName: profile.fullName,
        email: profile.email,
        phoneNumber: profile.phoneNumber || "",
        dateOfBirth: profile.dateOfBirth || "",
        schoolName: profile.schoolName || "",
        targetExamYear: profile.targetExamYear || 2025,
      });
    }
  }, [profile, form]);

  // Handle form submission
  const onSubmit = (data: ProfileFormData) => {
    profileMutation.mutate(data);
  };

  // Get initials for avatar
  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map(word => word.charAt(0))
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  // Show create profile dialog if no profile exists
  if (!isLoading && !profile) {
    return (
      <div className="flex items-center space-x-2">
        <Dialog open={showProfileDialog} onOpenChange={setShowProfileDialog}>
          <DialogTrigger asChild>
            <Button variant="ghost" className="p-1 rounded-full hover:bg-gray-100">
              <Avatar className="h-10 w-10 cursor-pointer">
                <AvatarFallback className="bg-blue-600 text-white">
                  <Plus className="h-5 w-5" />
                </AvatarFallback>
              </Avatar>
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Create Your Profile</DialogTitle>
            </DialogHeader>
            <ProfileForm 
              form={form} 
              onSubmit={onSubmit} 
              isLoading={profileMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center space-x-2">
        <div className="w-10 h-10 bg-gray-200 rounded-full animate-pulse"></div>
      </div>
    );
  }

  // Main profile display
  return (
    <div className="flex items-center space-x-3">
      {/* Profile Menu - triggered by avatar click */}
      <Dialog open={showProfileDialog} onOpenChange={setShowProfileDialog}>
        <DialogTrigger asChild>
          <Button variant="ghost" className="p-1 rounded-full hover:bg-gray-100">
            <Avatar className="h-10 w-10 cursor-pointer">
              {/* AvatarImage removed: profilePicture field no longer exists */}
              <AvatarFallback className="bg-blue-600 text-white">
                {profile?.fullName ? getInitials(profile.fullName) : "ST"}
              </AvatarFallback>
            </Avatar>
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Student Profile</DialogTitle>
          </DialogHeader>
          
          {!isEditing ? (
            <ProfileView 
              profile={profile!} 
              onEdit={() => setIsEditing(true)}
              onLogout={async () => {
                await logout();
                setShowProfileDialog(false);
                navigate('/'); // Redirect to home page after logout
              }}
            />
          ) : (
            <ProfileForm 
              form={form} 
              onSubmit={onSubmit} 
              isLoading={profileMutation.isPending}
              onCancel={() => setIsEditing(false)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

/**
 * Profile View Component
 * Shows read-only profile information
 */
interface ProfileViewProps {
  profile: StudentProfile;
  onEdit: () => void;
  onLogout: () => void;
}

function ProfileView({ profile, onEdit, onLogout }: ProfileViewProps) {
  return (
    <div className="space-y-6">
      {/* Profile Header */}
      <div className="flex items-center space-x-4">
        <Avatar className="h-16 w-16">
          {/* AvatarImage removed: profilePicture field no longer exists */}
          <AvatarFallback className="bg-blue-600 text-white text-lg">
            {profile.fullName
              .split(" ")
              .map(word => word.charAt(0))
              .join("")
              .toUpperCase()
              .slice(0, 2)}
          </AvatarFallback>
        </Avatar>
        
        <div className="flex-1">
          <h3 className="text-lg font-semibold">{profile.fullName}</h3>
          <p className="text-sm text-gray-600">{profile.email}</p>
          {profile.targetExamYear && (
            <Badge variant="outline" className="mt-1">
              NEET {profile.targetExamYear}
            </Badge>
          )}
        </div>
      </div>

      <Separator />

      {/* Profile Details */}
      <div className="grid grid-cols-1 gap-4">
        {profile.phoneNumber && (
          <div className="flex items-center space-x-3">
            <Phone className="h-4 w-4 text-gray-500" />
            <div>
              <p className="text-sm font-medium">Phone Number</p>
              <p className="text-sm text-gray-600">{profile.phoneNumber}</p>
            </div>
          </div>
        )}

        {profile.dateOfBirth && (
          <div className="flex items-center space-x-3">
            <Calendar className="h-4 w-4 text-gray-500" />
            <div>
              <p className="text-sm font-medium">Date of Birth</p>
              <p className="text-sm text-gray-600">
                {new Date(profile.dateOfBirth).toLocaleDateString()}
              </p>
            </div>
          </div>
        )}

        {profile.schoolName && (
          <div className="flex items-center space-x-3">
            <GraduationCap className="h-4 w-4 text-gray-500" />
            <div>
              <p className="text-sm font-medium">School/College</p>
              <p className="text-sm text-gray-600">{profile.schoolName}</p>
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex justify-between pt-4">
        <Button 
          variant="outline" 
          onClick={onLogout} 
          className="flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </Button>
        <Button onClick={onEdit} className="flex items-center gap-2">
          <Edit className="h-4 w-4" />
          Edit Profile
        </Button>
      </div>
    </div>
  );
}

/**
 * Profile Form Component
 * Handles creating/editing profile information
 */
interface ProfileFormProps {
  form: any;
  onSubmit: (data: ProfileFormData) => void;
  isLoading: boolean;
  onCancel?: () => void;
}

function ProfileForm({ form, onSubmit, isLoading, onCancel }: ProfileFormProps) {
  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-1 gap-4">
        <div>
          <Label htmlFor="fullName">Full Name *</Label>
          <Input
            id="fullName"
            {...form.register("fullName")}
            placeholder="Enter your full name"
          />
          {form.formState.errors.fullName && (
            <p className="text-sm text-red-600 mt-1">
              {form.formState.errors.fullName.message}
            </p>
          )}
        </div>

        <div>
          <Label htmlFor="email">Email Address *</Label>
          <Input
            id="email"
            type="email"
            {...form.register("email")}
            placeholder="Enter your email address"
          />
          {form.formState.errors.email && (
            <p className="text-sm text-red-600 mt-1">
              {form.formState.errors.email.message}
            </p>
          )}
        </div>

        <div>
          <Label htmlFor="phoneNumber">Phone Number</Label>
          <Input
            id="phoneNumber"
            {...form.register("phoneNumber")}
            placeholder="Enter your phone number"
          />
        </div>

        <div>
          <Label htmlFor="dateOfBirth">Date of Birth</Label>
          <Input
            id="dateOfBirth"
            type="date"
            {...form.register("dateOfBirth")}
          />
        </div>

        <div>
          <Label htmlFor="schoolName">School/College Name</Label>
          <Input
            id="schoolName"
            {...form.register("schoolName")}
            placeholder="Enter your school or college name"
          />
        </div>

        <div>
          <Label htmlFor="targetExamYear">Target Exam Year</Label>
          <Input
            id="targetExamYear"
            type="number"
            {...form.register("targetExamYear", { valueAsNumber: true })}
            placeholder="2025"
            min="2024"
            max="2030"
          />
        </div>
      </div>

      <div className="flex justify-end space-x-2 pt-4">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={isLoading}>
          {isLoading ? "Saving..." : "Save Profile"}
        </Button>
      </div>
    </form>
  );
}