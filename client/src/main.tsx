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

