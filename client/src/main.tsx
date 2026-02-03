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
// PWA Service Worker Registration
// ============================================================================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Register service worker only in production build
        const isProduction = import.meta.env.PROD;
        
        if (isProduction) {
            navigator.serviceWorker
                .register('/service-worker.js', { scope: '/' })
                .then((registration) => {
                    console.log('[PWA] Service Worker registered successfully:', registration.scope);
                    
                    // Check for updates every 60 seconds
                    setInterval(() => {
                        registration.update();
                    }, 60000);
                    
                    // Listen for new service worker waiting to activate
                    registration.addEventListener('updatefound', () => {
                        const newWorker = registration.installing;
                        if (newWorker) {
                            newWorker.addEventListener('statechange', () => {
                                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                    // New service worker available, show update notification
                                    console.log('[PWA] New version available! Refresh to update.');
                                    // Optionally, show a toast/notification to user
                                }
                            });
                        }
                    });
                })
                .catch((error) => {
                    console.error('[PWA] Service Worker registration failed:', error);
                });
        } else {
            console.log('[PWA] Service Worker registration skipped (development mode)');
        }
    });
}

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
