import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-blue-50 via-blue-50/30 to-indigo-50">
      <Card className="w-full max-w-md mx-4 bg-white shadow-lg border border-[#E2E8F0]">
        <CardContent className="pt-6">
          <div className="flex mb-4 gap-2">
            <AlertCircle className="h-8 w-8 text-[#EF4444]" />
            <h1 className="text-2xl font-bold text-[#1F2937]">404 Page Not Found</h1>
          </div>

          <p className="mt-4 text-sm text-[#6B7280]">
            Did you forget to add the page to the router?
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
