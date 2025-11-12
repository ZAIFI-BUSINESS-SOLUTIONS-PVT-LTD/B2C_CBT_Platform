import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Upload, FileSpreadsheet, LogOut, Building2, CheckCircle } from "lucide-react";

interface InstitutionAdminData {
  id: number;
  username: string;
  institution: {
    id: number;
    name: string;
    code: string;
    exam_types: string[];
  };
}

export default function InstitutionAdminDashboard() {
  const [, navigate] = useLocation();
  const [adminData, setAdminData] = useState<InstitutionAdminData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [examType, setExamType] = useState("");
  const [testName, setTestName] = useState("");
  const [timeLimit, setTimeLimit] = useState("180");
  const [instructions, setInstructions] = useState("");
  const [scheduledDateTime, setScheduledDateTime] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    // Check if admin is logged in
    const adminDataStr = localStorage.getItem("institutionAdmin");
    const token = localStorage.getItem("institutionAdminToken");

    if (!adminDataStr || !token) {
      navigate("/login");
      return;
    }

    try {
      const data = JSON.parse(adminDataStr);
      setAdminData(data);
      // Set default exam type if available
      if (data.institution.exam_types && data.institution.exam_types.length > 0) {
        setExamType(data.institution.exam_types[0]);
      }
    } catch (err) {
      console.error("Failed to parse admin data:", err);
      navigate("/login");
    }
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem("institutionAdminToken");
    localStorage.removeItem("institutionAdminRefresh");
    localStorage.removeItem("institutionAdmin");
    navigate("/login");
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      // Validate file type
      const validExtensions = [".xlsx", ".xls"];
      const fileExtension = selectedFile.name.substring(selectedFile.name.lastIndexOf(".")).toLowerCase();
      
      if (!validExtensions.includes(fileExtension)) {
        setError("Please select an Excel file (.xlsx or .xls)");
        setFile(null);
        return;
      }

      // Validate file size (10MB limit)
      const maxSize = 10 * 1024 * 1024; // 10MB in bytes
      if (selectedFile.size > maxSize) {
        setError("File size must be less than 10MB");
        setFile(null);
        return;
      }

      setFile(selectedFile);
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!file) {
      setError("Please select an Excel file to upload");
      return;
    }

    if (!examType) {
      setError("Please select an exam type");
      return;
    }

    if (!testName.trim()) {
      setError("Please enter a test name");
      return;
    }

    setLoading(true);

    try {
      const token = localStorage.getItem("institutionAdminToken");
      
      const formData = new FormData();
      formData.append("file", file);
      formData.append("exam_type", examType);
      formData.append("test_name", testName.trim());
      formData.append("time_limit", timeLimit);
      if (instructions.trim()) {
        formData.append("instructions", instructions.trim());
      }
      if (scheduledDateTime) {
        try {
          // Convert local datetime-local value to ISO (UTC) so backend parses correctly
          const iso = new Date(scheduledDateTime).toISOString();
          formData.append("scheduled_date_time", iso);
        } catch (err) {
          console.warn("Failed to parse scheduledDateTime", err);
        }
      }

      const response = await fetch("/api/institution-admin/upload/", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.message || "Upload failed");
        setLoading(false);
        return;
      }

      // Success
      setSuccess(
        `Test created successfully! ${data.questions_created} questions uploaded. Test Code: ${data.test_code}` +
        (data.scheduled_date_time ? ` Scheduled for: ${new Date(data.scheduled_date_time).toLocaleString()}` : '')
      );
      
      // Reset form
      setTestName("");
      setTimeLimit("180");
      setInstructions("");
  setScheduledDateTime(null);
      setFile(null);
      
      // Reset file input
      const fileInput = document.getElementById("file-upload") as HTMLInputElement;
      if (fileInput) {
        fileInput.value = "";
      }

      setLoading(false);
    } catch (err: any) {
      console.error("Upload error:", err);
      setError("Failed to upload test. Please try again.");
      setLoading(false);
    }
  };

  if (!adminData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      {/* Header */}
      <div className="max-w-4xl mx-auto mb-6">
        <div className="flex items-center justify-between bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-3">
            <Building2 className="h-8 w-8 text-blue-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-900">{adminData.institution.name}</h1>
              <p className="text-sm text-gray-600">Code: {adminData.institution.code}</p>
            </div>
          </div>
          <Button variant="outline" onClick={handleLogout}>
            <LogOut className="h-4 w-4 mr-2" />
            Logout
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Success Alert */}
        {success && (
          <Alert className="bg-green-50 border-green-200">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">{success}</AlertDescription>
          </Alert>
        )}

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Upload Form */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Upload Test
            </CardTitle>
            <CardDescription>
              Upload an Excel file with questions to create a new test for your students
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Exam Type */}
              <div className="space-y-2">
                <Label htmlFor="examType">
                  Exam Type <span className="text-red-500">*</span>
                </Label>
                <Select value={examType} onValueChange={setExamType} disabled={loading}>
                  <SelectTrigger id="examType">
                    <SelectValue placeholder="Select exam type" />
                  </SelectTrigger>
                  <SelectContent>
                    {adminData.institution.exam_types.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type.toUpperCase()}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Test Name */}
              <div className="space-y-2">
                <Label htmlFor="testName">
                  Test Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="testName"
                  type="text"
                  placeholder="e.g., Physics Chapter 1 - Laws of Motion"
                  value={testName}
                  onChange={(e) => setTestName(e.target.value)}
                  disabled={loading}
                />
              </div>

              {/* Time Limit */}
              <div className="space-y-2">
                <Label htmlFor="timeLimit">Time Limit (minutes)</Label>
                <Input
                  id="timeLimit"
                  type="number"
                  min="1"
                  max="300"
                  value={timeLimit}
                  onChange={(e) => setTimeLimit(e.target.value)}
                  disabled={loading}
                />
              </div>

              {/* Instructions */}
              <div className="space-y-2">
                <Label htmlFor="instructions">Instructions (Optional)</Label>
                <Textarea
                  id="instructions"
                  placeholder="Add any special instructions for students..."
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  disabled={loading}
                  rows={3}
                />
              </div>

              {/* Scheduled Date & Time (Optional) */}
              <div className="space-y-2">
                <Label htmlFor="scheduledDateTime">Schedule Test (Optional)</Label>
                <Input
                  id="scheduledDateTime"
                  type="datetime-local"
                  value={scheduledDateTime ?? ""}
                  onChange={(e) => setScheduledDateTime(e.target.value || null)}
                  disabled={loading}
                />
                <p className="text-xs text-gray-600">Optional: set a future date & time when this test should become available. Leave empty to make the test available immediately after creation.</p>
              </div>

              {/* File Upload */}
              <div className="space-y-2">
                <Label htmlFor="file-upload">
                  Excel File <span className="text-red-500">*</span>
                </Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="file-upload"
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handleFileChange}
                    disabled={loading}
                    className="cursor-pointer"
                  />
                  {file && <FileSpreadsheet className="h-5 w-5 text-green-600" />}
                </div>
                <p className="text-xs text-gray-600">
                  Upload an Excel file (.xlsx) with questions. Max size: 10MB, Max questions: 5000
                </p>
              </div>

              {/* Submit Button */}
              <Button type="submit" disabled={loading} size="lg" className="w-full">
                {loading ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Uploading...</span>
                  </div>
                ) : (
                  <>
                    <Upload className="h-4 w-4 mr-2" />
                    Upload Test
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Info Card */}
        <Card>
          <CardHeader>
            <CardTitle>Excel File Format</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-gray-600">
            <p className="font-medium">Required Columns:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>question_text</li>
              <li>option_a, option_b, option_c, option_d</li>
              <li>correct_answer (A, B, C, or D)</li>
              <li>explanation</li>
            </ul>
            <p className="font-medium mt-4">Optional Columns:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>topic_name</li>
              <li>difficulty (Easy, Moderate, Hard)</li>
              <li>question_type</li>
            </ul>
            <p className="mt-4 text-xs text-gray-500">
              See documentation for detailed format and examples.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
