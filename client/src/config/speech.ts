// Speech-to-Text Configuration for Chatbot

export const SPEECH_CONFIG = {
  // Default language for speech recognition
  DEFAULT_LANGUAGE: 'en-US',
  
  // Available languages for speech recognition
  SUPPORTED_LANGUAGES: [
    { code: 'en-US', name: 'English (US)' },
    { code: 'en-GB', name: 'English (UK)' },
    { code: 'en-IN', name: 'English (India)' },
    { code: 'hi-IN', name: 'Hindi (India)' },
    { code: 'ta-IN', name: 'Tamil (India)' },
    { code: 'te-IN', name: 'Telugu (India)' },
    { code: 'kn-IN', name: 'Kannada (India)' },
    { code: 'ml-IN', name: 'Malayalam (India)' },
    { code: 'gu-IN', name: 'Gujarati (India)' },
    { code: 'bn-IN', name: 'Bengali (India)' },
    { code: 'mr-IN', name: 'Marathi (India)' },
    { code: 'pa-IN', name: 'Punjabi (India)' },
    { code: 'ur-IN', name: 'Urdu (India)' },
  ],
  
  // Speech recognition settings
  RECOGNITION_SETTINGS: {
    // Whether to capture interim (partial) results
    interimResults: true,
    
    // Whether to continue listening after getting a result
    continuous: true,
    
    // Maximum number of alternative transcriptions
    maxAlternatives: 1,
  },
  
  // UI settings
  UI_SETTINGS: {
    // Animation duration for mic button state changes (ms)
    animationDuration: 200,
    
    // Auto-stop recording after this many seconds of silence (0 = disabled)
    autoStopDelay: 5000,
    
    // Show language selector in UI
    showLanguageSelector: true,
  },
};

// Helper function to get language name by code
export const getLanguageName = (code: string): string => {
  const language = SPEECH_CONFIG.SUPPORTED_LANGUAGES.find(lang => lang.code === code);
  return language?.name || code;
};

// Helper function to check if a language is supported
export const isLanguageSupported = (code: string): boolean => {
  return SPEECH_CONFIG.SUPPORTED_LANGUAGES.some(lang => lang.code === code);
};
