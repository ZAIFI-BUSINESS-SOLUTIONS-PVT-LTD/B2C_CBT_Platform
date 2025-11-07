import React, { useState } from 'react';
import { getAccessToken, authenticatedFetch } from '@/lib/auth';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface InstitutionCodeModalProps {
  open: boolean;
  onClose: () => void;
  onVerified: (institution: Institution) => void;
}

interface Institution {
  id: number;
  name: string;
  code: string;
  exam_types: string[];
}

export function InstitutionCodeModal({ open, onClose, onVerified }: InstitutionCodeModalProps) {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleVerify = async () => {
    if (!code.trim()) {
      setError('Please enter an institution code');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Get student JWT token using auth helper
      const token = getAccessToken();
      if (!token) {
        throw new Error('Please login to verify institution code');
      }

      // Use authenticatedFetch which will attempt token refresh on 401
      const response = await authenticatedFetch('/api/institutions/verify-code/', {
        method: 'POST',
        body: JSON.stringify({ code: code.trim() }),
      } as RequestInit);

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || (data.error && data.error.message) || 'Failed to verify institution code');
      }

      if (data.success && data.institution) {
        setSuccess(true);
        setTimeout(() => {
          onVerified(data.institution);
          handleClose();
        }, 1000);
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred while verifying the code');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setCode('');
    setError(null);
    setSuccess(false);
    onClose();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      handleVerify();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Enter Institution Code</DialogTitle>
          <DialogDescription>
            Enter the code provided by your institution to access their tests.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="institution-code">Institution Code</Label>
            <Input
              id="institution-code"
              placeholder="e.g., INST_CODE_123"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading || success}
              className="uppercase"
            />
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert className="border-green-500 bg-green-50 text-green-900">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription>
                Institution code verified successfully! Loading tests...
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="sm:justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={loading || success}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleVerify}
            disabled={loading || success || !code.trim()}
          >
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {success ? 'Verified!' : 'Verify Code'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
