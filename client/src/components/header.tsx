import { GraduationCap, User } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Header() {
  return (
    <header className="bg-white shadow-sm border-b border-neet-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          <div className="flex items-center space-x-4">
            <div className="bg-neet-blue text-white p-2.5 rounded-xl shadow-sm">
              <GraduationCap className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-neet-gray-900 tracking-tight">
                NEET Practice Platform
              </h1>
              <p className="text-sm text-neet-gray-500">
                Smart Test Preparation
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-neet-gray-600 font-medium">Welcome, Student</span>
            <Button className="btn-primary shadow-sm">
              <User className="h-4 w-4 mr-2" />
              Profile
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
