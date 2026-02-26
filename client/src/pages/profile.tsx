import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
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
    Trash2,
    Bookmark,
    ChevronRight,
    MoreVertical,
} from "lucide-react";

// Helper: safely get initials from a name (handles undefined/null)
const getInitials = (name?: string) => {
    if (!name) return "";
    return name
        .split(/\s+/)
        .filter(Boolean)
        .map(word => word.charAt(0))
        .join("")
        .toUpperCase()
        .slice(0, 2);
};

const getDisplayName = (p?: { fullName?: string; email?: string; phoneNumber?: string } | null) => {
    if (!p) return "";
    return p.fullName || p.email || p.phoneNumber || "";
};

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
 * Restructured with glassmorphic menu-based design
 * - Background: testpage-bg.png
 * - Glassmorphic containers
 * - Menu items: Profile, Bookmarks, Logout
 * - Profile modal for editing user details
 */
export function StudentProfile() {
    const [showProfileDialog, setShowProfileDialog] = useState(false);
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);
    const [deleteConfirmation, setDeleteConfirmation] = useState("");
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const { isAuthenticated, student, logout } = useAuth();
    const [, navigate] = useLocation();

    // Fetch student profile
    const { data: profile, isLoading } = useQuery<StudentProfile>({
        queryKey: ['/api/students/me/'],
        retry: false,
        enabled: isAuthenticated && !!student,
    });

    // Update profile mutation
    const profileMutation = useMutation({
        mutationFn: async (data: ProfileFormData) => {
            if (profile) {
                return await apiRequest(`/api/student-profile/update/${profile.studentId}/`, "PUT", data);
            } else {
                return await apiRequest("/api/student-profile", "POST", data);
            }
        },
        onSuccess: () => {
            setShowProfileDialog(false);
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

    // Delete account mutation
    const deleteAccountMutation = useMutation({
        mutationFn: async () => {
            return await apiRequest("/api/student-profile/delete-account/", "POST", {
                confirmation: "DELETE"
            });
        },
        onSuccess: async () => {
            toast({
                title: "Account deleted",
                description: "Your account and all associated data have been permanently deleted.",
            });
            try {
                await logout();
            } catch (e) {
                console.warn('Logout after deletion failed:', e);
            }
            try {
                queryClient.clear();
            } catch (e) {
                console.warn('Failed to clear query client:', e);
            }

            try {
                navigate('/login');
                setTimeout(() => {
                    if (window.location.pathname !== '/login') {
                        window.location.href = '/login';
                    }
                }, 300);
            } catch (e) {
                window.location.href = '/login';
            }
        },
        onError: (error: any) => {
            toast({
                title: "Deletion failed",
                description: error.message || "Failed to delete account. Please try again.",
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

    // Handle delete account
    const handleDeleteAccount = () => {
        if (deleteConfirmation === "DELETE") {
            deleteAccountMutation.mutate();
            setShowDeleteDialog(false);
        }
    };

    const handleLogout = async () => {
        await logout();
        navigate('/topics');
    };

    // Show loading state
    if (isLoading) {
        return (
            <div className="min-h-screen w-full bg-gradient-to-br from-purple-100 via-blue-100 to-indigo-100 flex items-center justify-center">
                <div className="w-12 h-12 bg-white/30 rounded-full animate-pulse backdrop-blur-sm"></div>
            </div>
        );
    }

    // If no profile, show create profile form in glassmorphic style
    if (!profile) {
        return (
            <div 
                className="min-h-screen w-full bg-cover bg-center bg-no-repeat relative"
                style={{ backgroundImage: "url('/testpage-bg.png')" }}
            >
                {/* overlay removed to restore background vibrancy */}
                
                {/* Content */}
                <div className="relative z-10 min-h-screen flex flex-col">
                    {/* Header */}
                    <header className="p-4">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => navigate('/topics')}
                            className="bg-white/10 backdrop-blur-md border border-white/20 text-gray-900 hover:bg-white/20 h-10 w-10"
                        >
                            <ChevronLeft className="h-5 w-5 text-gray-700" />
                        </Button>
                    </header>

                    {/* Create Profile Card */}
                    <div className="flex-1 flex items-center justify-center p-4">
                        <Card className="w-full max-w-md bg-white/10 backdrop-blur-md border border-white/20 shadow-2xl rounded-3xl">
                            <CardContent className="p-6 text-gray-900">
                                <div className="flex flex-col items-center text-center space-y-3 mb-6">
                                    <Avatar className="h-20 w-20 bg-gradient-to-br from-blue-400 to-blue-600">
                                        <AvatarFallback className="bg-transparent text-white text-2xl">
                                            <Plus className="h-8 w-8" />
                                        </AvatarFallback>
                                    </Avatar>
                                    <h2 className="text-xl font-bold text-gray-900">Create Your Profile</h2>
                                    <p className="text-sm text-gray-700">Add basic details to personalize your experience</p>
                                </div>

                                <ProfileForm
                                    form={form}
                                    onSubmit={onSubmit}
                                    isLoading={profileMutation.isPending}
                                    glassmorphic={true}
                                />
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        );
    }

    // Main profile page with glassmorphic menu design
    return (
        <div 
            className="min-h-screen w-full bg-cover bg-center bg-no-repeat relative"
            style={{ backgroundImage: "url('/testpage-bg.png')" }}
        >
        {/* overlay removed to restore background vibrancy */}
            
            {/* Content */}
            <div className="relative z-10 min-h-screen flex flex-col">
                {/* Header */}
                <header className="p-4 flex items-center justify-between">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => navigate('/topics')}
                        className="bg-white/10 backdrop-blur-md border border-white/20 text-gray-900 hover:bg-white/20 h-10 w-10"
                    >
                        <ChevronLeft className="h-5 w-5 text-gray-700" />
                    </Button>
                    <h1 className="text-xl font-bold text-gray-900">Profile</h1>
                    <div className="w-10"></div> {/* Spacer for symmetry */}
                </header>

                {/* Profile Content */}
                    <div className="flex-1 flex flex-col items-center px-4 pt-8 pb-20">
                    <div className="w-full max-w-md bg-white/10 backdrop-blur-md rounded-3xl p-6 shadow-2xl border border-white/20 text-gray-900">
                        {/* Avatar and User Info */}
                        <div className="flex flex-col items-center text-center mb-8">
                            <Avatar className="h-32 w-32 mb-4 bg-gradient-to-br from-blue-400 to-blue-600 ring-4 ring-white/30">
                                <AvatarFallback className="bg-transparent text-white text-[3.12rem] font-bold leading-none">
                                    {getInitials(getDisplayName(profile))}
                                </AvatarFallback>
                            </Avatar>
                            <h2 className="text-2xl font-bold text-gray-900 mb-1">
                                {getDisplayName(profile) || 'User'}
                            </h2>
                            <p className="text-gray-700 text-sm">
                                @{profile.studentId}
                            </p>
                        </div>

                        {/* Menu Items */}
                        <div className="w-full space-y-3">
                            {/* Profile Menu Item */}
                            <button
                                onClick={() => setShowProfileDialog(true)}
                                className="w-full bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-4 flex items-center justify-between hover:bg-white/15 transition-all duration-200 shadow-lg"
                            >
                                <div className="flex items-center gap-3">
                                    <div className="bg-white/20 p-2 rounded-xl">
                                        <User className="h-5 w-5 text-gray-700" />
                                    </div>
                                    <span className="text-gray-900 font-medium">Profile</span>
                                </div>
                                <ChevronRight className="h-5 w-5 text-gray-700/60" />
                            </button>

                            {/* Bookmarks Menu Item */}
                            <button
                                onClick={() => navigate('/bookmarked-questions')}
                                className="w-full bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-4 flex items-center justify-between hover:bg-white/15 transition-all duration-200 shadow-lg"
                            >
                                <div className="flex items-center gap-3">
                                    <div className="bg-white/20 p-2 rounded-xl">
                                        <Bookmark className="h-5 w-5 text-gray-700" />
                                    </div>
                                    <span className="text-gray-900 font-medium">Bookmarks</span>
                                </div>
                                <ChevronRight className="h-5 w-5 text-gray-700/60" />
                            </button>

                            {/* Logout Menu Item */}
                            <button
                                onClick={handleLogout}
                                className="w-full bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-4 flex items-center justify-between hover:bg-white/15 transition-all duration-200 shadow-lg"
                            >
                                <div className="flex items-center gap-3">
                                    <div className="bg-red-50 p-2 rounded-xl">
                                        <LogOut className="h-5 w-5 text-red-400" />
                                    </div>
                                    <span className="text-red-400 font-medium">Logout</span>
                                </div>
                                <ChevronRight className="h-5 w-5 text-red-300/60" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Profile Edit Dialog */}
            <Dialog open={showProfileDialog} onOpenChange={setShowProfileDialog}>
                <DialogContent className="w-[calc(100%-3rem)] max-w-md rounded-2xl bg-white/90 backdrop-blur-sm border border-gray-200 shadow-xl overflow-hidden p-0">
                    <div className="max-h-[85vh] overflow-y-auto">
                        <div className="p-6">
                            <DialogHeader className="mb-4">
                                <DialogTitle className="text-xl font-bold text-gray-900">Edit Profile</DialogTitle>
                            </DialogHeader>
                            
                            <ProfileForm
                                form={form}
                                onSubmit={onSubmit}
                                isLoading={profileMutation.isPending}
                                onCancel={() => setShowProfileDialog(false)}
                                glassmorphic={true}
                            />
                            
                            {/* Delete Account Button */}
                            <div className="mt-6 pt-4 border-t border-gray-200">
                                <button
                                    onClick={() => {
                                        setShowProfileDialog(false);
                                        setDeleteConfirmation("");
                                        setShowDeleteDialog(true);
                                    }}
                                    className="w-full flex items-center justify-center gap-2 text-red-600 border border-red-200 bg-red-50 hover:bg-red-100 rounded-lg py-3 transition-colors"
                                >
                                    <Trash2 className="h-4 w-4" />
                                    <span className="font-medium">Delete Account</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Delete Account Confirmation Dialog */}
            <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
                <AlertDialogContent className="w-[calc(100%-3rem)] max-w-md rounded-2xl bg-white/95 backdrop-blur-sm border border-gray-200 shadow-xl overflow-hidden p-0">
                    <div className="max-h-[70vh] overflow-y-auto p-6">
                        <AlertDialogHeader>
                            <AlertDialogTitle className="text-gray-900">Delete Account</AlertDialogTitle>
                            <AlertDialogDescription className="space-y-4 text-gray-600">
                                <p>
                                    This action cannot be undone. This will permanently delete your account
                                    and remove all your data from our servers, including:
                                </p>
                                <ul className="list-disc list-inside space-y-1 text-sm">
                                    <li>All test sessions and answers</li>
                                    <li>Performance insights and analytics</li>
                                    <li>Chat history and conversations</li>
                                    <li>Subscription and payment records</li>
                                    <li>Profile information</li>
                                </ul>
                                <div className="pt-2">
                                    <Label htmlFor="delete-confirmation" className="text-sm font-medium text-gray-700">
                                        Type <span className="font-bold">DELETE</span> to confirm:
                                    </Label>
                                    <Input
                                        id="delete-confirmation"
                                        value={deleteConfirmation}
                                        onChange={(e) => setDeleteConfirmation(e.target.value)}
                                        placeholder="DELETE"
                                        className="mt-2"
                                    />
                                </div>
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter className="mt-6">
                            <AlertDialogCancel onClick={() => setDeleteConfirmation("")}>
                                Cancel
                            </AlertDialogCancel>
                            <AlertDialogAction
                                onClick={handleDeleteAccount}
                                disabled={deleteConfirmation !== "DELETE" || deleteAccountMutation.isPending}
                                className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
                            >
                                {deleteAccountMutation.isPending ? "Deleting..." : "Delete Account"}
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </div>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}

/**
 * Profile Form Component
 * Handles creating/editing profile information
 * Supports glassmorphic design for overlay backgrounds
 */
interface ProfileFormProps {
    form: any;
    onSubmit: (data: ProfileFormData) => void;
    isLoading: boolean;
    onCancel?: () => void;
    glassmorphic?: boolean;
}

function ProfileForm({ form, onSubmit, isLoading, onCancel, glassmorphic = false }: ProfileFormProps) {
    const inputClasses = glassmorphic
        ? "bg-white/50 border border-gray-200 text-gray-900 placeholder:text-gray-500 rounded-md px-3 py-2 shadow-sm focus:ring-2 focus:ring-blue-200"
        : "";
    const labelClasses = glassmorphic ? "text-gray-700 font-medium" : "";
    const buttonClasses = glassmorphic ? "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 rounded-md px-4 py-2" : "";

    return (
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-4">
                <div>
                    <Label htmlFor="fullName" className={labelClasses}>Full Name *</Label>
                    <Input
                        id="fullName"
                        {...form.register("fullName")}
                        placeholder="Enter your full name"
                        className={inputClasses}
                    />
                    {form.formState.errors.fullName && (
                        <p className="text-sm text-red-400 mt-1">
                            {form.formState.errors.fullName.message}
                        </p>
                    )}
                </div>

                <div>
                    <Label htmlFor="email" className={labelClasses}>Email Address *</Label>
                    <Input
                        id="email"
                        type="email"
                        {...form.register("email")}
                        placeholder="Enter your email address"
                        className={inputClasses}
                    />
                    {form.formState.errors.email && (
                        <p className="text-sm text-red-400 mt-1">
                            {form.formState.errors.email.message}
                        </p>
                    )}
                </div>

                <div>
                    <Label htmlFor="phoneNumber" className={labelClasses}>Phone Number</Label>
                    <Input
                        id="phoneNumber"
                        {...form.register("phoneNumber")}
                        placeholder="Enter your phone number"
                        className={inputClasses}
                    />
                </div>

                <div>
                    <Label htmlFor="dateOfBirth" className={labelClasses}>Date of Birth</Label>
                    <Input
                        id="dateOfBirth"
                        type="date"
                        {...form.register("dateOfBirth")}
                        className={inputClasses}
                    />
                </div>

                <div>
                    <Label htmlFor="schoolName" className={labelClasses}>School/College Name</Label>
                    <Input
                        id="schoolName"
                        {...form.register("schoolName")}
                        placeholder="Enter your school or college name"
                        className={inputClasses}
                    />
                </div>

                <div>
                    <Label htmlFor="targetExamYear" className={labelClasses}>Target Exam Year</Label>
                    <Input
                        id="targetExamYear"
                        type="number"
                        {...form.register("targetExamYear", { valueAsNumber: true })}
                        placeholder="2025"
                        min="2024"
                        max="2030"
                        className={inputClasses}
                    />
                </div>
            </div>

            <div className="pt-4 flex flex-col-reverse sm:flex-row sm:justify-end sm:items-center gap-3">
                {onCancel && (
                    <Button 
                        type="button" 
                        variant="outline" 
                        onClick={onCancel} 
                        className={`w-full sm:w-auto ${buttonClasses}`}
                    >
                        Cancel
                    </Button>
                )}
                <Button
                    type="submit"
                    disabled={isLoading}
                    className={`w-full sm:w-auto ${glassmorphic ? 'bg-blue-600 text-white hover:bg-blue-700 rounded-md px-4 py-2' : ''}`}
                >
                    {isLoading ? "Saving..." : "Save Profile"}
                </Button>
            </div>
        </form>
    );
}