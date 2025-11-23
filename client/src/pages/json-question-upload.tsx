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
  FileCode, 
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
  total_records: number;
  success_count: number;
  skipped_count: number;
  offset_used: number;
  error_details: string[];
}

export default function JSONQuestionUpload() {
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
      const validExtensions = [".json"];
      const fileExtension = selectedFile.name.substring(selectedFile.name.lastIndexOf(".")).toLowerCase();
      
      if (!validExtensions.includes(fileExtension)) {
        setError("Please select a JSON file (.json)");
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
    // Create a sample JSON template
    const sampleData = [
      {
        "question_id": 1,
        "column_name": "question_image",
        "value": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
      },
      {
        "question_id": 2,
        "column_name": "option_a_image",
        "value": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
      },
      {
        "question_id": 3,
        "column_name": "explanation",
        "value": "Updated explanation text"
      }
    ];
    
    const jsonContent = JSON.stringify(sampleData, null, 2);
    const blob = new Blob([jsonContent], { type: 'application/json' });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "json_update_template.json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setUploadResult(null);

    if (!file) {
      setError("Please select a JSON file to upload");
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

      const response = await fetch("/api/institution-admin/upload-json-updates/", {
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
      setError(err.message || "Failed to upload JSON updates");
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
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload JSON Question Updates</h1>
          <p className="text-gray-600">
            Update question fields (images, text, etc.) using a JSON file
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
            <p><strong>JSON Format Requirements:</strong></p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>File must be in <code className="bg-blue-100 px-1 py-0.5 rounded">.json</code> format</li>
              <li>Must be an array of update records</li>
              <li>Each record must have: <code className="bg-blue-100 px-1 py-0.5 rounded">question_id</code>, <code className="bg-blue-100 px-1 py-0.5 rounded">column_name</code>, <code className="bg-blue-100 px-1 py-0.5 rounded">value</code></li>
              <li>
                <code className="bg-blue-100 px-1 py-0.5 rounded">question_id</code>: Question number (1, 2, 3, ...) in the test
              </li>
              <li>
                <code className="bg-blue-100 px-1 py-0.5 rounded">column_name</code>: Field to update (e.g., question_image, option_a, explanation)
              </li>
              <li>
                <code className="bg-blue-100 px-1 py-0.5 rounded">value</code>: New value (base64 for images, text for other fields)
              </li>
            </ul>
            <p className="mt-2">
              <strong>Allowed columns:</strong> question, option_a, option_b, option_c, option_d, correct_answer, explanation, difficulty, question_type, question_image, option_a_image, option_b_image, option_c_image, option_d_image, explanation_image
            </p>
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
            <CardTitle>JSON Update Details</CardTitle>
            <CardDescription>
              Upload a JSON file with question field updates
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
                  JSON File <span className="text-red-500">*</span>
                </Label>
                <div className="flex items-center space-x-4">
                  <Input
                    id="file-upload"
                    type="file"
                    accept=".json"
                    onChange={handleFileChange}
                    disabled={loading}
                    required
                  />
                  {file && (
                    <Badge variant="secondary" className="flex items-center space-x-1">
                      <FileCode className="h-4 w-4" />
                      <span>{file.name}</span>
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-gray-500">
                  Only .json files are accepted (max 10MB)
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
                    Upload JSON Updates
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
                JSON Updates Applied Successfully
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <p className="text-sm text-gray-600">Test Name</p>
                  <p className="text-lg font-semibold text-gray-900">{uploadResult.test_name}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <p className="text-sm text-gray-600">Total Records</p>
                  <p className="text-lg font-semibold text-gray-900">{uploadResult.total_records}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <p className="text-sm text-gray-600">Successfully Updated</p>
                  <p className="text-lg font-semibold text-green-600">{uploadResult.success_count}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <p className="text-sm text-gray-600">Skipped/Failed</p>
                  <p className="text-lg font-semibold text-orange-600">{uploadResult.skipped_count}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-green-200 col-span-2">
                  <p className="text-sm text-gray-600">Question ID Offset Used</p>
                  <p className="text-lg font-semibold text-blue-600">{uploadResult.offset_used}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    (Automatically calculated: first_question_id - 1)
                  </p>
                </div>
              </div>

              {uploadResult.error_details && uploadResult.error_details.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-semibold text-red-700 mb-2">
                    Errors/Warnings ({uploadResult.error_details.length}):
                  </p>
                  <div className="bg-white rounded-lg p-3 border border-red-200 max-h-40 overflow-y-auto">
                    <ul className="text-sm text-red-600 space-y-1">
                      {uploadResult.error_details.slice(0, 10).map((error, idx) => (
                        <li key={idx} className="border-b last:border-0 py-1">
                          {error}
                        </li>
                      ))}
                    </ul>
                    {uploadResult.error_details.length > 10 && (
                      <p className="text-xs text-gray-500 mt-2 text-center">
                        ... and {uploadResult.error_details.length - 10} more errors
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
