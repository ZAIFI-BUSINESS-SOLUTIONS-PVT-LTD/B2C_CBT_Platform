import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    LogOut,
    ChevronLeft,
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
    // page mode: editing or viewing handled by isEditing
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

    // If not loading and no profile, show the full-page create profile form
    if (!isLoading && !profile) {
        return (
            <main className="min-h-screen w-full flex flex-col items-center py-8 px-4 bg-gray-50">
                {/* Sticky header */}
                <header className="sticky top-0 z-10 w-full bg-transparent">
                    <div className="max-w-xl mx-auto flex items-center justify-between py-3 px-2">
                        <Button
                            variant="secondary"
                            onClick={() => navigate('/')}
                            aria-label="Go home"
                            className="p-1 h-8 w-8 flex items-center justify-center"
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <h1 className="text-lg font-semibold">Create Profile</h1>
                        <div className="w-8" />
                    </div>
                    <Separator />
                </header>

                <div className="w-full max-w-xl bg-white rounded-lg shadow-sm p-4 sm:p-6 mt-4">
                    <div className="flex flex-col items-center text-center space-y-3 mb-4">
                        <Avatar className="h-16 w-16">
                            <AvatarFallback className="bg-blue-600 text-white">
                                <Plus className="h-5 w-5" />
                            </AvatarFallback>
                        </Avatar>
                        <h2 className="text-lg font-semibold">Create Your Profile</h2>
                        <p className="text-sm text-gray-600">Add basic details so we can personalise your experience.</p>
                    </div>

                    <Separator />

                    <div className="mt-4">
                        <ProfileForm
                            form={form}
                            onSubmit={onSubmit}
                            isLoading={profileMutation.isPending}
                        />
                    </div>
                </div>
            </main>
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

    // Main profile display as a dedicated page with sticky header
    return (
        <main className="min-h-screen w-full flex flex-col items-center p-4 bg-gray-50">
            <header className="sticky top-0 z-10 w-full bg-transparent">
                <div className="max-w-xl mx-auto flex items-center justify-between">
                    <Button
                        variant="secondary"
                        onClick={() => navigate('/')}
                        aria-label="Go home"
                        className="p-1 h-8 w-8 flex items-center justify-center"
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <h1 className="text-lg md:text-xl font-semibold">Profile</h1>
                    <div className="w-8" />
                </div>
            </header>

            <div className="w-full max-w-xl bg-white rounded-lg shadow-sm p-4 sm:p-6 mt-4">
                {!isEditing ? (
                    <ProfileView
                        profile={profile!}
                        onEdit={() => setIsEditing(true)}
                        onLogout={async () => {
                            await logout();
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
            </div>
        </main>
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
        <div className="space-y-6 ">
            {/* Profile Header */}
            <div className="flex items-center space-x-4 ">
                <Avatar className="h-12 w-12 md:h-16 md:w-16">
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

                <div className="flex-1 min-w-0">
                    <h3 className="text-base md:text-lg font-semibold truncate">{profile.fullName}</h3>
                    <p className="text-sm md:text-sm text-gray-600 truncate">{profile.email}</p>
                    {profile.targetExamYear && (
                        <Badge variant="outline" className="mt-1">
                            NEET {profile.targetExamYear}
                        </Badge>
                    )}
                </div>
            </div>

            <Separator />

            {/* Profile Details */}
            <div className="grid grid-cols-1 gap-4 ">
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
            <div className="pt-4 space-y-2 sm:flex sm:space-y-0 sm:justify-between">
                <Button
                    variant="outline"
                    onClick={onLogout}
                    className="flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 w-full sm:w-auto justify-center"
                >
                    <LogOut className="h-4 w-4" />
                    Logout
                </Button>
                <Button onClick={onEdit} className="flex items-center gap-2 w-full sm:w-auto justify-center">
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

            <div className="pt-4 space-y-2 sm:flex sm:space-y-0 sm:justify-end">
                {onCancel && (
                    <Button type="button" variant="outline" onClick={onCancel} className="w-full sm:w-auto">
                        Cancel
                    </Button>
                )}
                <Button type="submit" disabled={isLoading} className="w-full sm:w-auto">
                    {isLoading ? "Saving..." : "Save Profile"}
                </Button>
            </div>
        </form>
    );
}