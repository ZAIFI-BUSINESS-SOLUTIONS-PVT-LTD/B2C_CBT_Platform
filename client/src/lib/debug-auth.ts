// Debugging utility to help identify frontend authentication issues
// Add this to your component temporarily to debug JWT issues

export const debugAuthentication = () => {
  const accessToken = localStorage.getItem('accessToken');
  const refreshToken = localStorage.getItem('refreshToken');
  
  console.group('🔍 Authentication Debug Info');
  console.log('Access Token exists:', !!accessToken);
  console.log('Access Token (first 50 chars):', accessToken?.substring(0, 50) + '...');
  console.log('Refresh Token exists:', !!refreshToken);
  console.log('Refresh Token (first 50 chars):', refreshToken?.substring(0, 50) + '...');
  
  // Decode JWT payload to check expiration
  if (accessToken) {
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const now = Math.floor(Date.now() / 1000);
      console.log('Token Payload:', {
        user_id: payload.user_id,
        student_id: payload.student_id,
        email: payload.email,
        exp: payload.exp,
        exp_readable: new Date(payload.exp * 1000).toLocaleString(),
        is_expired: payload.exp < now,
        expires_in_seconds: payload.exp - now,
        expires_in_minutes: Math.floor((payload.exp - now) / 60)
      });
    } catch (error) {
      console.error('Failed to decode token:', error);
    }
  }
  
  console.groupEnd();
};

// Helper to test an authenticated request
export const testAuthenticatedRequest = async (url: string) => {
  const accessToken = localStorage.getItem('accessToken');
  
  console.group(`🧪 Testing Request: ${url}`);
  console.log('Token being sent:', accessToken?.substring(0, 50) + '...');
  
  try {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });
    
    console.log('Response Status:', response.status);
    console.log('Response Headers:', Object.fromEntries(response.headers.entries()));
    
    if (response.status === 401) {
      const errorText = await response.text();
      console.error('401 Response Body:', errorText);
    } else if (response.ok) {
      console.log('✅ Request successful');
    }
    
    return response;
  } catch (error) {
    console.error('❌ Request failed:', error);
    throw error;
  } finally {
    console.groupEnd();
  }
};
