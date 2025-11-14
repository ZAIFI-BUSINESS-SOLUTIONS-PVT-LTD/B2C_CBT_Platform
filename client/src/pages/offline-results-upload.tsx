import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Upload, FileSpreadsheet, LogOut, Building2, CheckCircle, Download, ArrowLeft, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";

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

interface UploadResult {
  success: boolean;
  processed_rows: number;
  created_sessions: number;
  created_students: number;
  questions_created: number;
  errors_count: number;
  test_name: string;
  test_code: string;
  errors_file?: string;
}

export default function OfflineResultsUpload() {
  const [, navigate] = useLocation();
  const [adminData, setAdminData] = useState<InstitutionAdminData | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  // Form state
  const [testName, setTestName] = useState("");
  const [examType, setExamType] = useState("");
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
      const validExtensions = [".xlsx"];
      const fileExtension = selectedFile.name.substring(selectedFile.name.lastIndexOf(".")).toLowerCase();
      
      if (!validExtensions.includes(fileExtension)) {
        setError("Please select an Excel file (.xlsx)");
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

  const handleDownloadTemplate = () => {
    // Create a link to download the sample template
    const link = document.createElement("a");
    link.href = "/sample_offline_test_template.xlsx";
    link.download = "offline_test_template.xlsx";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setUploadResult(null);

    if (!file) {
      setError("Please select an Excel file to upload");
      return;
    }

    if (!testName.trim()) {
      setError("Please enter a test name");
      return;
    }

    if (!examType) {
      setError("Please select an exam type");
      return;
    }

    setLoading(true);

    try {
      const token = localStorage.getItem("institutionAdminToken");
      
      const formData = new FormData();
      formData.append("file", file);
      formData.append("test_name", testName.trim());
      formData.append("exam_type", examType);

      const response = await fetch("/api/institution-admin/upload-results/", {
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
      setUploadResult(data);
      
      // Reset form
      setTestName("");
      setFile(null);
      
      // Reset file input
      const fileInput = document.getElementById("file-upload") as HTMLInputElement;
      if (fileInput) {
        fileInput.value = "";
      }

      setLoading(false);
    } catch (err: any) {
      console.error("Upload error:", err);
      setError("Failed to upload offline results. Please try again.");
      setLoading(false);
    }
  };

  const handleDownloadErrors = () => {
    if (uploadResult?.errors_file) {
      const link = document.createElement("a");
      link.href = uploadResult.errors_file;
      link.download = "upload_errors.csv";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
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
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => navigate("/institution-admin/dashboard")}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <Button variant="outline" onClick={handleLogout}>
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Upload Result */}
        {uploadResult && (
          <Card className="bg-green-50 border-green-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-green-800">
                <CheckCircle className="h-5 w-5" />
                Upload Successful!
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="bg-white p-3 rounded-lg shadow-sm">
                  <p className="text-sm text-gray-600">Test Name</p>
                  <p className="text-lg font-semibold text-gray-900">{uploadResult.test_name}</p>
                </div>
                <div className="bg-white p-3 rounded-lg shadow-sm">
                  <p className="text-sm text-gray-600">Test Code</p>
                  <p className="text-lg font-semibold text-gray-900">{uploadResult.test_code}</p>
                </div>
                <div className="bg-white p-3 rounded-lg shadow-sm">
                  <p className="text-sm text-gray-600">Rows Processed</p>
                  <p className="text-lg font-semibold text-blue-600">{uploadResult.processed_rows}</p>
                </div>
                <div className="bg-white p-3 rounded-lg shadow-sm">
                  <p className="text-sm text-gray-600">Sessions Created</p>
                  <p className="text-lg font-semibold text-green-600">{uploadResult.created_sessions}</p>
                </div>
                <div className="bg-white p-3 rounded-lg shadow-sm">
                  <p className="text-sm text-gray-600">Students</p>
                  <p className="text-lg font-semibold text-purple-600">{uploadResult.created_students}</p>
                </div>
                <div className="bg-white p-3 rounded-lg shadow-sm">
                  <p className="text-sm text-gray-600">Questions</p>
                  <p className="text-lg font-semibold text-indigo-600">{uploadResult.questions_created}</p>
                </div>
              </div>

              {uploadResult.errors_count > 0 && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {uploadResult.errors_count} rows had errors and were skipped.
                    {uploadResult.errors_file && (
                      <Button
                        variant="link"
                        className="ml-2 p-0 h-auto text-red-700"
                        onClick={handleDownloadErrors}
                      >
                        Download error report
                      </Button>
                    )}
                  </AlertDescription>
                </Alert>
              )}

              <Button
                onClick={() => setUploadResult(null)}
                variant="outline"
                className="w-full"
              >
                Upload Another File
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Upload Form */}
        {!uploadResult && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Upload Offline Test Results
              </CardTitle>
              <CardDescription>
                Upload an Excel file containing student responses from paper-based tests
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Test Name */}
                <div className="space-y-2">
                  <Label htmlFor="testName">
                    Test Name <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="testName"
                    type="text"
                    placeholder="e.g., NEET Mock Test 1"
                    value={testName}
                    onChange={(e) => setTestName(e.target.value)}
                    disabled={loading}
                  />
                  <p className="text-xs text-gray-600">
                    This name will be used for the test. All rows in the Excel must belong to this test.
                  </p>
                </div>

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

                {/* File Upload */}
                <div className="space-y-2">
                  <Label htmlFor="file-upload">
                    Excel File <span className="text-red-500">*</span>
                  </Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="file-upload"
                      type="file"
                      accept=".xlsx"
                      onChange={handleFileChange}
                      disabled={loading}
                      className="cursor-pointer"
                    />
                    {file && <FileSpreadsheet className="h-5 w-5 text-green-600" />}
                  </div>
                  <p className="text-xs text-gray-600">
                    Upload an Excel file (.xlsx) with student responses. Max size: 10MB, Max rows: 5000
                  </p>
                </div>

                {/* Submit Button */}
                <Button type="submit" disabled={loading} size="lg" className="w-full">
                  {loading ? (
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Processing...</span>
                    </div>
                  ) : (
                    <>
                      <Upload className="h-4 w-4 mr-2" />
                      Upload Results
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Template Download Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Excel Template
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-3 p-4 bg-blue-50 rounded-lg">
              <Download className="h-5 w-5 text-blue-600 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium text-gray-900 mb-1">Download Template</p>
                <p className="text-sm text-gray-600 mb-3">
                  Use this template to ensure your Excel file has the correct format with sample data.
                </p>
                <Button onClick={handleDownloadTemplate} variant="outline" size="sm">
                  <Download className="h-4 w-4 mr-2" />
                  Download Template
                </Button>
              </div>
            </div>

            <div className="space-y-3">
              <p className="font-medium text-gray-900">Required Columns:</p>
              <div className="grid grid-cols-2 gap-2">
                <Badge variant="secondary">student_name</Badge>
                <Badge variant="secondary">phone_number</Badge>
                <Badge variant="secondary">test_name</Badge>
                <Badge variant="secondary">subject</Badge>
                <Badge variant="secondary">topic_name</Badge>
                <Badge variant="secondary">question_text</Badge>
                <Badge variant="secondary">option_a</Badge>
                <Badge variant="secondary">option_b</Badge>
                <Badge variant="secondary">option_c</Badge>
                <Badge variant="secondary">option_d</Badge>
                <Badge variant="secondary">explanation</Badge>
                <Badge variant="secondary">correct_answer</Badge>
                <Badge variant="secondary">opted_answer</Badge>
              </div>

              <p className="font-medium text-gray-900 mt-4">Optional Columns:</p>
              <div className="grid grid-cols-2 gap-2">
                <Badge variant="outline">email</Badge>
                <Badge variant="outline">exam_type</Badge>
                <Badge variant="outline">question_type</Badge>
                <Badge variant="outline">time_taken_seconds</Badge>
                <Badge variant="outline">answered_at</Badge>
                <Badge variant="outline">attempt_status</Badge>
              </div>
            </div>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm">
                <strong>Important:</strong>
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>Each row represents one student's answer to one question</li>
                  <li>Students are matched by phone number (primary) or name</li>
                  <li>New students will be auto-created if not found</li>
                  <li>Questions and topics will be created automatically</li>
                  <li>Answers are auto-evaluated based on correct_answer vs opted_answer</li>
                </ul>
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
