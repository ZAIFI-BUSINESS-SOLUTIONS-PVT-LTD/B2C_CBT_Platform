import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// Initialize Sentry synchronously at app startup so it captures initialization errors
try {
    // Only initialize if DSN provided in env
    const SENTRY_DSN = (import.meta as any).env?.VITE_SENTRY_DSN;
    if (SENTRY_DSN) {
        // import synchronously to ensure immediate initialization
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const Sentry = require('@sentry/react');
        Sentry.init({
            dsn: SENTRY_DSN,
            sendDefaultPii: true,
            environment: (import.meta as any).env?.MODE || 'production',
        });
        // mark global so errorReporting's dynamic init knows Sentry is already initialized
        try { (window as any).__SENTRY_INITIALIZED = true; } catch (e) { /* ignore */ }
    }
} catch (e) {
    // eslint-disable-next-line no-console
    console.warn('Sentry init failed at bootstrap:', e);
}

createRoot(document.getElementById("root")!).render(<App />);

// ============================================================================
// PWA Service Worker Registration (Workbox-powered vite-plugin-pwa)
// ============================================================================
import { registerSW } from 'virtual:pwa-register';

// Register service worker with update prompt
const updateSW = registerSW({
  onNeedRefresh() {
    // New version available - show update notification
    console.log('[PWA] New version available!');
    
    // Dispatch custom event for UI to handle
    window.dispatchEvent(new CustomEvent('pwa-update-available', {
      detail: { updateSW }
    }));
    
    // Auto-confirm for now (you can add UI prompt later)
    if (confirm('New version available! Click OK to update.')) {
      updateSW(true);
    }
  },
  onOfflineReady() {
    console.log('[PWA] App ready to work offline');
    window.dispatchEvent(new CustomEvent('pwa-offline-ready'));
  },
  onRegistered(registration) {
    console.log('[PWA] Service Worker registered');
    
    // Check for updates every hour
    if (registration) {
      setInterval(() => {
        registration.update();
      }, 60 * 60 * 1000);
    }
  },
  onRegisterError(error) {
    console.error('[PWA] Service Worker registration failed:', error);
  }
});

// Export update function globally for manual triggers
(window as any).updatePWA = () => {
  if (updateSW) {
    updateSW(true);
  }
};

// ============================================================================
// PWA Install Prompt Handler
// ============================================================================
let deferredPrompt: any = null;

window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent the mini-infobar from appearing on mobile
  e.preventDefault();
  // Stash the event so it can be triggered later
  deferredPrompt = e;
  console.log('[PWA] Install prompt available');
  
  // Optionally, show a custom install button in your UI
  // You can dispatch a custom event here to notify your app
  window.dispatchEvent(new CustomEvent('pwa-install-available'));
});

// Export function to trigger install prompt manually
(window as any).showPWAInstallPrompt = async () => {
  if (!deferredPrompt) {
    console.log('[PWA] Install prompt not available');
    return false;
  }
  
  // Show the install prompt
  deferredPrompt.prompt();
  
  // Wait for the user to respond to the prompt
  const { outcome } = await deferredPrompt.userChoice;
  console.log(`[PWA] User response to install prompt: ${outcome}`);
  
  // Clear the deferred prompt
  deferredPrompt = null;
  
  return outcome === 'accepted';
};

window.addEventListener('appinstalled', () => {
  console.log('[PWA] App installed successfully');
  deferredPrompt = null;
});
