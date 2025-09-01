/**
 * Google OAuth Configuration
 * 
 * Centralized configuration for Google authentication.
 * Handles environment variables and provides fallbacks.
 */

// Google Client ID from environment variables
export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// API Base URL
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Google OAuth configuration
export const GOOGLE_CONFIG = {
  clientId: GOOGLE_CLIENT_ID,
  scope: 'openid email profile',
  responseType: 'id_token',
  cookiePolicy: 'single_host_origin',
  autoSelect: false,
  cancelOnTapOutside: true,
};

// Validation
export const isGoogleConfigured = (): boolean => {
  return Boolean(GOOGLE_CLIENT_ID);
};

// Error messages
export const GOOGLE_ERRORS = {
  NOT_CONFIGURED: 'Google authentication not configured',
  FAILED_TO_LOAD: 'Failed to load Google authentication',
  FAILED_TO_INITIALIZE: 'Failed to initialize Google authentication',
  NO_CREDENTIAL: 'No credential received from Google',
  SIGN_IN_FAILED: 'Google sign-in failed',
  NETWORK_ERROR: 'Network error during Google authentication',
  POPUP_BLOCKED: 'Popup was blocked. Please allow popups for this site.',
} as const;

export default {
  GOOGLE_CLIENT_ID,
  API_BASE_URL,
  GOOGLE_CONFIG,
  isGoogleConfigured,
  GOOGLE_ERRORS,
};
