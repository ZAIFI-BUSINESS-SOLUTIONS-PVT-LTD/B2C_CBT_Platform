import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  AlertCircle, 
  Upload, 
  FileSpreadsheet, 
  LogOut, 
  Building2, 
  CheckCircle, 
  Download, 
  ArrowLeft,
  FileText,
  Check
} from "lucide-react";
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
  test_name: string;
  total_questions: number;
  updated_answers: number;
  recalculated_test_answers: number;
  updated_sessions: number;
  backup_data: Array<{
    id: number;
    old_answer: string;
    new_answer: string;
  }>;
}

export default function AnswerKeyUpload() {
  const [, navigate] = useLocation();
  const [adminData, setAdminData] = useState<InstitutionAdminData | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  // Form state
  const [testName, setTestName] = useState("");
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
    // Create a sample template programmatically
    const csvContent = "question,answer\n1,A\n2,B\n3,45.6\n4,C\n5,D\n";
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "answer_key_template.csv";
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

    setLoading(true);

    try {
      const token = localStorage.getItem("institutionAdminToken");
      
      const formData = new FormData();
      formData.append("file", file);
      formData.append("test_name", testName.trim());

      const response = await fetch("/api/institution-admin/upload-answer-key/", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || "Upload failed");
      }

      // Success
      setUploadResult(data);
      setFile(null);
      setTestName("");
      
      // Reset file input
      const fileInput = document.getElementById("file-upload") as HTMLInputElement;
      if (fileInput) {
        fileInput.value = "";
      }

    } catch (err: any) {
      setError(err.message || "Failed to upload answer key");
    } finally {
      setLoading(false);
    }
  };

  const handleBackToDashboard = () => {
    navigate("/institution-admin-dashboard");
  };

  if (!adminData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50">
      {/* Header */}
      <div className="bg-white border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleBackToDashboard}
                className="flex items-center"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Dashboard
              </Button>
              <div className="h-6 w-px bg-gray-300"></div>
              <div className="flex items-center space-x-2">
                <Building2 className="h-5 w-5 text-blue-600" />
                <span className="font-semibold text-gray-900">{adminData.institution.name}</span>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Answer Key</h1>
          <p className="text-gray-600">
            Update correct answers and recalculate scores for a test
          </p>
        </div>

        {/* Instructions Card */}
        <Card className="mb-6 border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle className="flex items-center text-blue-900">
              <FileText className="mr-2 h-5 w-5" />
              Instructions
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-blue-800 space-y-2">
            <p><strong>Excel Format Requirements:</strong></p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>File must be in <code className="bg-blue-100 px-1 py-0.5 rounded">.xlsx</code> format</li>
              <li>Must have two columns: <code className="bg-blue-100 px-1 py-0.5 rounded">question</code> and <code className="bg-blue-100 px-1 py-0.5 rounded">answer</code></li>
              <li>Question numbers must start from 1 and be sequential (1, 2, 3, ...)</li>
              <li>Answers can be single letters (A, B, C, D) or numeric values (45.6, 12, etc.)</li>
              <li>Total questions in Excel must match the test's question count</li>
            </ul>
            <p className="mt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadTemplate}
                className="text-blue-700 border-blue-300 hover:bg-blue-100"
              >
                <Download className="mr-2 h-4 w-4" />
                Download Sample Template
              </Button>
            </p>
          </CardContent>
        </Card>

        {/* Upload Form */}
        <Card>
          <CardHeader>
            <CardTitle>Answer Key Details</CardTitle>
            <CardDescription>
              Upload an Excel file with correct answers for your test
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Test Name */}
              <div className="space-y-2">
                <Label htmlFor="test-name">
                  Test Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="test-name"
                  type="text"
                  placeholder="Enter exact test name"
                  value={testName}
                  onChange={(e) => setTestName(e.target.value)}
                  disabled={loading}
                  required
                />
                <p className="text-sm text-gray-500">
                  Must match the exact test name used when uploading questions
                </p>
              </div>

              {/* File Upload */}
              <div className="space-y-2">
                <Label htmlFor="file-upload">
                  Answer Key File <span className="text-red-500">*</span>
                </Label>
                <div className="flex items-center space-x-4">
                  <Input
                    id="file-upload"
                    type="file"
                    accept=".xlsx"
                    onChange={handleFileChange}
                    disabled={loading}
                    required
                  />
                  {file && (
                    <Badge variant="secondary" className="flex items-center space-x-1">
                      <FileSpreadsheet className="h-4 w-4" />
                      <span>{file.name}</span>
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-gray-500">
                  Only .xlsx files are accepted (max 10MB)
                </p>
              </div>

              {/* Error Alert */}
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Processing...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Upload Answer Key
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Success Result */}
        {uploadResult && (
          <Card className="mt-6 border-green-200 bg-green-50">
            <CardHeader>
              <CardTitle className="flex items-center text-green-900">
                <CheckCircle className="mr-2 h-5 w-5" />
                Answer Key Uploaded Successfully
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <p className="text-sm text-gray-600">Test Name</p>
                  <p className="text-lg font-semibold text-gray-900">{uploadResult.test_name}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <p className="text-sm text-gray-600">Total Questions</p>
                  <p className="text-lg font-semibold text-gray-900">{uploadResult.total_questions}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <p className="text-sm text-gray-600">Answers Updated</p>
                  <p className="text-lg font-semibold text-blue-600">{uploadResult.updated_answers}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <p className="text-sm text-gray-600">Test Answers Recalculated</p>
                  <p className="text-lg font-semibold text-purple-600">{uploadResult.recalculated_test_answers}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <p className="text-sm text-gray-600">Sessions Updated</p>
                  <p className="text-lg font-semibold text-orange-600">{uploadResult.updated_sessions}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-green-200 flex items-center justify-center">
                  <Check className="h-12 w-12 text-green-600" />
                </div>
              </div>

              {uploadResult.backup_data && uploadResult.backup_data.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-semibold text-gray-700 mb-2">
                    Changes Summary (First 5):
                  </p>
                  <div className="bg-white rounded-lg p-3 border border-green-200 max-h-40 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-1 px-2">Question ID</th>
                          <th className="text-left py-1 px-2">Old Answer</th>
                          <th className="text-left py-1 px-2">New Answer</th>
                        </tr>
                      </thead>
                      <tbody>
                        {uploadResult.backup_data.slice(0, 5).map((item, idx) => (
                          <tr key={idx} className="border-b last:border-0">
                            <td className="py-1 px-2">{item.id}</td>
                            <td className="py-1 px-2 text-red-600">{item.old_answer || '(empty)'}</td>
                            <td className="py-1 px-2 text-green-600 font-semibold">{item.new_answer}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {uploadResult.backup_data.length > 5 && (
                      <p className="text-xs text-gray-500 mt-2 text-center">
                        ... and {uploadResult.backup_data.length - 5} more changes
                      </p>
                    )}
                  </div>
                </div>
              )}

              <div className="flex space-x-4 mt-6">
                <Button
                  onClick={() => setUploadResult(null)}
                  variant="outline"
                  className="flex-1"
                >
                  Upload Another
                </Button>
                <Button
                  onClick={handleBackToDashboard}
                  className="flex-1"
                >
                  Back to Dashboard
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
