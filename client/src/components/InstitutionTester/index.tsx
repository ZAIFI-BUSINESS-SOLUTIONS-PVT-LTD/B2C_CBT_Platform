import React, { useState } from 'react';
import { getAccessToken, authenticatedFetch } from '@/lib/auth';
import { School } from 'lucide-react';
import { InstitutionCodeModal } from './InstitutionCodeModal';
import { InstitutionTestsList } from './InstitutionTestsList';

interface Institution {
  id: number;
  name: string;
  code: string;
  exam_types: string[];
}

export function InstitutionTester() {
  const [showModal, setShowModal] = useState(true); // Show modal by default when user visits the page
  const [verifiedInstitution, setVerifiedInstitution] = useState<Institution | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  const handleVerified = (institution: Institution) => {
    setVerifiedInstitution(institution);
    // Store in localStorage for this session
    localStorage.setItem('verified_institution', JSON.stringify(institution));
  };

  const handleBack = () => {
    setVerifiedInstitution(null);
    localStorage.removeItem('verified_institution');
    setShowModal(true); // Show modal again when going back
  };

  // Check if student is already linked to an institution on the backend
  React.useEffect(() => {
    const checkInstitutionLink = async () => {
      try {
        const token = getAccessToken();
        if (!token) {
          setIsCheckingAuth(false);
          return;
        }

        // Try to get student profile to check if institution is linked (authenticatedFetch will try refresh)
        const response = await authenticatedFetch('/api/students/me/');

        if (response.ok) {
          const data = await response.json();
          // If student has an institution linked, use it
          if (data.institution) {
            setVerifiedInstitution(data.institution);
            localStorage.setItem('verified_institution', JSON.stringify(data.institution));
            setShowModal(false);
          } else {
            // No institution linked, clear localStorage and show modal
            localStorage.removeItem('verified_institution');
          }
        }
      } catch (error) {
        console.error('Error checking institution link:', error);
        localStorage.removeItem('verified_institution');
      } finally {
        setIsCheckingAuth(false);
      }
    };

    checkInstitutionLink();
  }, []);

  if (isCheckingAuth) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          <p className="text-muted-foreground">Checking institution link...</p>
        </div>
      </div>
    );
  }

  if (verifiedInstitution) {
    return (
      <div className="container mx-auto py-6">
        <InstitutionTestsList 
          institution={verifiedInstitution} 
          onBack={handleBack} 
        />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6">
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6">
        <div className="rounded-full bg-primary/10 p-6">
          <School className="h-16 w-16 text-primary" />
        </div>
        
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold">Institution Tests</h1>
          <p className="text-muted-foreground max-w-md">
            Access tests created by your institution. Enter your institution code to get started.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
        >
          Enter Institution Code
        </button>
      </div>

      <InstitutionCodeModal
        open={showModal}
        onClose={() => setShowModal(false)}
        onVerified={handleVerified}
      />
    </div>
  );
}
