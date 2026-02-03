/**
 * PWA Install Button Component (OPTIONAL)
 * 
 * Add this component to your UI to provide a custom "Install App" button.
 * 
 * Usage:
 * import { PWAInstallButton } from '@/components/PWAInstallButton';
 * 
 * Then in your component:
 * <PWAInstallButton />
 */

import { useState, useEffect } from 'react';

export function PWAInstallButton() {
  const [showInstall, setShowInstall] = useState(false);
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    // Listen for PWA install availability
    const handleInstallAvailable = () => {
      setShowInstall(true);
    };

    window.addEventListener('pwa-install-available', handleInstallAvailable);

    // Check if already installed (standalone mode)
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    if (isStandalone) {
      setShowInstall(false);
    }

    return () => {
      window.removeEventListener('pwa-install-available', handleInstallAvailable);
    };
  }, []);

  const handleInstall = async () => {
    setInstalling(true);
    
    try {
      const installed = await (window as any).showPWAInstallPrompt();
      
      if (installed) {
        console.log('App installed successfully!');
        setShowInstall(false);
      } else {
        console.log('User dismissed install prompt');
      }
    } catch (error) {
      console.error('Install failed:', error);
    } finally {
      setInstalling(false);
    }
  };

  // Don't show button if install is not available
  if (!showInstall) {
    return null;
  }

  return (
    <button
      onClick={handleInstall}
      disabled={installing}
      className="fixed bottom-4 right-4 z-50 flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-3 rounded-lg shadow-lg transition-all duration-200 disabled:opacity-50"
    >
      <svg 
        className="w-5 h-5" 
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24"
      >
        <path 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          strokeWidth={2} 
          d="M12 4v16m0 0l-4-4m4 4l4-4" 
        />
      </svg>
      <span>{installing ? 'Installing...' : 'Install App'}</span>
    </button>
  );
}

/**
 * Alternative: Banner Style (shows at top)
 */
export function PWAInstallBanner() {
  const [showBanner, setShowBanner] = useState(false);
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    const handleInstallAvailable = () => {
      setShowBanner(true);
    };

    window.addEventListener('pwa-install-available', handleInstallAvailable);

    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    if (isStandalone) {
      setShowBanner(false);
    }

    return () => {
      window.removeEventListener('pwa-install-available', handleInstallAvailable);
    };
  }, []);

  const handleInstall = async () => {
    setInstalling(true);
    
    try {
      const installed = await (window as any).showPWAInstallPrompt();
      if (installed) {
        setShowBanner(false);
      }
    } catch (error) {
      console.error('Install failed:', error);
    } finally {
      setInstalling(false);
    }
  };

  if (!showBanner) {
    return null;
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-indigo-600 text-white py-3 px-4 shadow-lg">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <svg 
            className="w-6 h-6" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" 
            />
          </svg>
          <span className="font-medium">
            Install InzightEd app for the best experience!
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleInstall}
            disabled={installing}
            className="bg-white text-indigo-600 px-4 py-2 rounded-md font-medium hover:bg-indigo-50 transition-colors disabled:opacity-50"
          >
            {installing ? 'Installing...' : 'Install'}
          </button>
          <button
            onClick={() => setShowBanner(false)}
            className="text-white hover:text-indigo-200 p-2"
          >
            <svg 
              className="w-5 h-5" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M6 18L18 6M6 6l12 12" 
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook: Use PWA install in any component
 */
export function usePWAInstall() {
  const [canInstall, setCanInstall] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    const handleInstallAvailable = () => {
      setCanInstall(true);
    };

    window.addEventListener('pwa-install-available', handleInstallAvailable);

    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    setIsInstalled(isStandalone);

    return () => {
      window.removeEventListener('pwa-install-available', handleInstallAvailable);
    };
  }, []);

  const install = async () => {
    setInstalling(true);
    
    try {
      const installed = await (window as any).showPWAInstallPrompt();
      
      if (installed) {
        setCanInstall(false);
        setIsInstalled(true);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Install failed:', error);
      return false;
    } finally {
      setInstalling(false);
    }
  };

  return {
    canInstall,
    installing,
    isInstalled,
    install
  };
}
