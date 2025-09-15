// Lightweight error reporting helper
// Generates a stable, reportable error code and returns it along with a timestamp.
// In production you can replace the body of `reportError` to call Sentry/LogRocket/etc.
export interface ReportResult {
  errorCode: string;
  timestamp: string;
}

// Optional Sentry DSN read from Vite env. Set VITE_SENTRY_DSN in your .env for production.
const SENTRY_DSN = (import.meta as any).env?.VITE_SENTRY_DSN || (import.meta as any).env?.SENTRY_DSN || null;

let _sentryInitialized = false;

async function initSentryOnce() {
  if (!SENTRY_DSN || _sentryInitialized) return null;
  // If main.tsx already initialized Sentry, skip dynamic init
  try {
    if ((window as any).__SENTRY_INITIALIZED) {
      _sentryInitialized = true;
      return (window as any).Sentry || null;
    }
  } catch (e) {
    // ignore
  }
  try {
    const Sentry = await import('@sentry/react');
    // initialize with minimal config; projects can extend this
    Sentry.init({
      dsn: SENTRY_DSN,
      environment: (import.meta as any).env?.MODE || 'production',
      tracesSampleRate: 0.0,
    });
    _sentryInitialized = true;
    return Sentry;
  } catch (e) {
    // If package isn't installed or import fails, log and continue silently.
    // eslint-disable-next-line no-console
    console.warn('[reportError] Sentry init failed or not installed:', e);
    return null;
  }
}

export function reportError(err: unknown, info?: unknown): ReportResult {
  // Generate a UUID-like token when possible, otherwise fallback to timestamp+random
  const errorCode = (typeof crypto !== 'undefined' && (crypto as any).randomUUID)
    ? (crypto as any).randomUUID()
    : `ERR-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

  const timestamp = new Date().toISOString();

  // Prepare payload for reporting
  const payload = {
    errorCode,
    timestamp,
    message: (err && typeof err === 'object' && (err as any).message) ? (err as any).message : String(err),
    details: info,
  };

  // TODO: integrate with Sentry / LogRocket / backend logging endpoint here in production
  // Example (commented):
  // if (process.env.NODE_ENV === 'production') {
  //   Sentry.captureException(err, { extra: info, tags: { errorCode } });
  // }

  // For now, write to console so support/devs can see the payload in logs
  // This makes local testing simple and avoids network calls in the helper.
  // eslint-disable-next-line no-console
  console.error('[reportError] ', payload);

  // If Sentry is configured, send the error there tagged with the generated errorCode.
  if (SENTRY_DSN) {
    // Initialize once and capture without blocking (fire-and-forget)
    initSentryOnce().then((SentryModule: any) => {
      try {
        if (SentryModule && SentryModule.captureException) {
          SentryModule.captureException(err, { extra: info, tags: { errorCode } });
        }
      } catch (e) {
        // eslint-disable-next-line no-console
        console.warn('[reportError] Sentry capture failed', e);
      }
    }).catch((e) => {
      // eslint-disable-next-line no-console
      console.warn('[reportError] Sentry init failed', e);
    });
  }

  return { errorCode, timestamp };
}

export default reportError;
