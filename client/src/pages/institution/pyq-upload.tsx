/**
 * PYQ Upload Page for Institution Admins
 * Allows institutions to upload Previous Year Question Papers in Excel format
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import { AlertCircle, CheckCircle, Upload, FileText } from 'lucide-react';

interface UploadResponse {
  success: boolean;
  message: string;
  pyq_id: number;
  pyq_name: string;
  questions_created: number;
  topics_used: string[];
  exam_type: string;
}

interface UploadError {
  error: string;
}

export default function PYQUploadPage() {
  const [name, setName] = useState('');
  const [examType, setExamType] = useState('neet');
  const [notes, setNotes] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { toast } = useToast();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!name.trim()) {
      setError('PYQ name is required');
      return;
    }
    
    if (!file) {
      setError('Please select an Excel file');
      return;
    }

    // Validate file extension
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      setError('Only Excel files (.xlsx, .xls) are supported');
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    try {
      // Get institution admin token
      const token = localStorage.getItem("institutionAdminToken");
      
      if (!token) {
        throw new Error('Not authenticated as institution admin');
      }

      // Prepare form data
      const formData = new FormData();
      formData.append('name', name.trim());
      formData.append('exam_type', examType);
      formData.append('file', file);
      if (notes.trim()) {
        formData.append('notes', notes.trim());
      }

      // Upload
      const response = await fetch('/api/institution/pyqs/', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        let errorMessage = 'Upload failed';
        try {
          const errorData = await response.json();
          errorMessage = errorData.error || errorData.message || errorData.detail || `Server error (status ${response.status})`;
        } catch (jsonErr) {
          // Response is not JSON, try to get text
          try {
            const errorText = await response.text();
            errorMessage = errorText || `Server error (status ${response.status})`;
          } catch {
            errorMessage = `Server error (status ${response.status})`;
          }
        }
        throw new Error(errorMessage);
      }

      const data: UploadResponse = await response.json();
      setResult(data);
      
      // Show success toast
      toast({
        title: 'Upload Successful',
        description: `${data.questions_created} questions uploaded successfully`,
      });

      // Reset form
      setName('');
      setExamType('neet');
      setNotes('');
      setFile(null);
      
      // Reset file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement;
      if (fileInput) fileInput.value = '';

    } catch (err: any) {
      console.error('Upload error:', err);
      const errorMessage = typeof err.message === 'string' ? err.message : 'Failed to upload PYQ. Please try again.';
      setError(errorMessage);
      
      toast({
        title: 'Upload Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-3xl mx-auto">
        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-6 w-6 text-blue-600" />
              Upload Previous Year Question Paper
            </CardTitle>
            <p className="text-sm text-gray-600 mt-2">
              Upload past exam questions for students to practice. Supports Excel format (.xlsx, .xls).
            </p>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* PYQ Name */}
              <div>
                <Label htmlFor="name">
                  PYQ Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., NEET 2023 Official Paper"
                  className="mt-1"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  Give a descriptive name that students will see
                </p>
              </div>

              {/* Exam Type */}
              <div>
                <Label htmlFor="exam-type">Exam Type</Label>
                <select
                  id="exam-type"
                  value={examType}
                  onChange={(e) => setExamType(e.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="neet">NEET</option>
                  <option value="jee">JEE</option>
                  <option value="other">Other</option>
                </select>
              </div>

              {/* Notes */}
              <div>
                <Label htmlFor="notes">Notes (Optional)</Label>
                <Textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add any additional information about this paper..."
                  className="mt-1"
                  rows={3}
                />
              </div>

              {/* File Upload */}
              <div>
                <Label htmlFor="file-input">
                  Excel File <span className="text-red-500">*</span>
                </Label>
                <div className="mt-1">
                  <Input
                    id="file-input"
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handleFileChange}
                    className="cursor-pointer"
                    required
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Required: topic_name, subject, question_text, option_a/b/c/d, correct_answer, explanation<br />
                  Optional: question_image, option_a/b/c/d_image, explanation_image (base64 format)
                </p>
                {file && (
                  <div className="mt-2 flex items-center gap-2 text-sm text-green-600">
                    <FileText className="h-4 w-4" />
                    <span>{file.name}</span>
                  </div>
                )}
              </div>

              {/* Error Alert */}
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Success Alert */}
              {result && (
                <Alert className="border-green-500 bg-green-50">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <AlertDescription className="text-green-800">
                    <strong>{result.message}</strong>
                    <div className="mt-2 space-y-1 text-sm">
                      <p>• Questions uploaded: {result.questions_created}</p>
                      <p>• Topics covered: {result.topics_used.length}</p>
                      <p>• Exam type: {result.exam_type.toUpperCase()}</p>
                    </div>
                  </AlertDescription>
                </Alert>
              )}

              {/* Submit Button */}
              <div className="flex gap-3">
                <Button
                  type="submit"
                  disabled={uploading}
                  className="flex-1 bg-blue-600 hover:bg-blue-700"
                >
                  {uploading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4 mr-2" />
                      Upload PYQ
                    </>
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => window.history.back()}
                >
                  Cancel
                </Button>
              </div>
            </form>

            {/* Help Section + Exact Column Order */}
            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  File Format Requirements
                </h3>
                  <div className="text-sm text-blue-800 space-y-3">
                  <div>
                    <p className="font-medium mb-1">Required Columns (must be present):</p>
                    <ul className="ml-4 space-y-1">
                      <li>• <strong>topic_name</strong> - Topic/chapter name</li>
                      <li>• <strong>subject</strong> - Subject (Physics, Chemistry, Botany, Zoology, Math)</li>
                      <li>• <strong>question_text</strong> - Question text</li>
                      <li>• <strong>option_a</strong>, <strong>option_b</strong>, <strong>option_c</strong>, <strong>option_d</strong> - Answer options</li>
                      <li>• <strong>correct_answer</strong> - Correct answer (A, B, C, D, or numeric/text for NVT)</li>
                      <li>• <strong>explanation</strong> - Solution explanation</li>
                    </ul>
                  </div>
                  <div>
                    <p className="font-medium mb-1">Optional Columns:</p>
                    <ul className="ml-4 space-y-1">
                      <li>• <strong>chapter</strong> - Optional chapter identifier (e.g., "Chapter 1" or "Mechanics")</li>
                      <li>• <strong>question_image</strong> - Image for the question (base64 or data URI)</li>
                      <li>• <strong>option_a_image</strong>, <strong>option_b_image</strong>, <strong>option_c_image</strong>, <strong>option_d_image</strong> - Images for options</li>
                      <li>• <strong>explanation_image</strong> - Image for explanation</li>
                      <li className="text-xs italic mt-1">Optional columns may be omitted; when provided they should follow the column order shown in the exact header row.</li>
                    </ul>
                  </div>
                  <div>
                    <p className="font-medium mb-1">Additional Info:</p>
                    <ul className="ml-4 space-y-1">
                      <li>• Excel file (.xlsx or .xls format)</li>
                      <li>• First row must contain column headers</li>
                      <li>• Maximum 5000 questions per upload</li>
                      <li>• Topics will be auto-mapped based on <strong>topic_name</strong> and <strong>subject</strong></li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="p-4 bg-white rounded-lg border border-gray-200">
                <h3 className="font-semibold text-gray-900 mb-2">Exact Excel Column Order (header row)</h3>
                <p className="text-sm text-gray-600 mb-2">Include columns in this order. Optional image columns may be omitted but if present should appear after the required columns in the order below.</p>
                <div className="overflow-auto">
                  <pre className="bg-gray-100 p-3 rounded text-sm">{`topic_name,subject,chapter,question_text,option_a,option_b,option_c,option_d,correct_answer,explanation,question_image,option_a_image,option_b_image,option_c_image,option_d_image,explanation_image`}</pre>
                  <table className="w-full mt-3 text-sm">
                    <thead>
                      <tr className="text-left text-xs text-gray-500">
                        <th className="py-1">Column</th>
                        <th className="py-1">Required</th>
                        <th className="py-1">Notes / Example</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        ['topic_name', 'Yes', 'e.g., Mechanics'],
                        ['subject', 'Yes', 'Physics'],
                        ['chapter', 'No', 'Optional chapter or section'],
                        ['question_text', 'Yes', 'Question stem text'],
                        ['option_a', 'Yes', 'First option text'],
                        ['option_b', 'Yes', 'Second option text'],
                        ['option_c', 'Yes', 'Third option text'],
                        ['option_d', 'Yes', 'Fourth option text'],
                        ['correct_answer', 'Yes', 'A / B / C / D or numeric/text'],
                        ['explanation', 'Yes', 'Detailed solution'],
                        ['question_image', 'No', 'Base64 payload or data URI (optional)'],
                        ['option_a_image', 'No', 'Base64 payload (optional)'],
                        ['option_b_image', 'No', 'Base64 payload (optional)'],
                        ['option_c_image', 'No', 'Base64 payload (optional)'],
                        ['option_d_image', 'No', 'Base64 payload (optional)'],
                        ['explanation_image', 'No', 'Base64 payload (optional)'],
                      ].map((row) => (
                        <tr key={row[0]} className="border-t">
                          <td className="py-1 text-gray-800">{row[0]}</td>
                          <td className="py-1 text-gray-600">{row[1]}</td>
                          <td className="py-1 text-gray-600">{row[2]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
