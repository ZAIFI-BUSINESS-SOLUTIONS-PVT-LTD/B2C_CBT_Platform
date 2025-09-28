// Mobile OTP Authentication utilities
import { StudentProfile } from "@/types/api";
import { API_BASE_URL } from "@/config/google-auth";
import { APIError } from "@/lib/queryClient";

// Use the same base URL logic as other auth functions
console.log('🔗 OTP API Base URL:', API_BASE_URL);

export interface SendOtpRequest {
  mobile_number: string;
}

export interface SendOtpResponse {
  message: string;
  cooldown_seconds?: number;
}

export interface VerifyOtpRequest {
  mobile_number: string;
  otp_code: string;
}

export interface VerifyOtpResponse {
  access: string;
  refresh: string;
  student: StudentProfile;
}

/**
 * Send OTP to mobile number
 * @param mobileNumber Mobile number in E.164 format (e.g., +919876543210)
 * @returns SendOtpResponse with success message and optional cooldown
 */
export const sendOtp = async (mobileNumber: string): Promise<SendOtpResponse> => {
  console.log('📱 Sending OTP to:', mobileNumber);
  
  const response = await fetch(`${API_BASE_URL}/auth/send-otp/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ mobile_number: mobileNumber }),
  });

  console.log('📡 Send OTP response status:', response.status, response.statusText);

  if (!response.ok) {
    // Handle different error cases
    let parsed: any = null;
    try {
      parsed = await response.json();
    } catch (e) {
      throw new Error(`Failed to send OTP (status ${response.status})`);
    }

    // Handle standardized error format
    if (parsed && parsed.error && parsed.error.code && parsed.error.message) {
      throw new APIError(
        parsed.error.code, 
        parsed.error.message, 
        response.status, 
        parsed.error.timestamp, 
        parsed.error.details
      );
    }

    // Handle legacy detail field
    if (parsed && parsed.detail) {
      throw new Error(parsed.detail);
    }

    // Handle rate limiting specifically
    if (response.status === 429) {
      const message = parsed.message || 'Too many requests. Please try again later.';
      throw new Error(message);
    }

    throw new Error(parsed.message || 'Failed to send OTP');
  }

  const data = await response.json();
  console.log('✅ OTP sent successfully:', data);
  return data;
};

/**
 * Verify OTP and login
 * @param mobileNumber Mobile number in E.164 format
 * @param otpCode 6-digit OTP code
 * @returns VerifyOtpResponse with JWT tokens and student profile
 */
export const verifyOtp = async (mobileNumber: string, otpCode: string): Promise<VerifyOtpResponse> => {
  console.log('🔐 Verifying OTP for:', mobileNumber);
  
  const response = await fetch(`${API_BASE_URL}/auth/verify-otp/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ 
      mobile_number: mobileNumber, 
      otp_code: otpCode 
    }),
  });

  console.log('📡 Verify OTP response status:', response.status, response.statusText);

  if (!response.ok) {
    // Handle different error cases
    let parsed: any = null;
    try {
      parsed = await response.json();
    } catch (e) {
      throw new Error(`Failed to verify OTP (status ${response.status})`);
    }

    // Handle standardized error format
    if (parsed && parsed.error && parsed.error.code && parsed.error.message) {
      throw new APIError(
        parsed.error.code, 
        parsed.error.message, 
        response.status, 
        parsed.error.timestamp, 
        parsed.error.details
      );
    }

    // Handle legacy detail field
    if (parsed && parsed.detail) {
      throw new Error(parsed.detail);
    }

    // Common error messages for OTP verification
    if (response.status === 400) {
      const message = parsed.message || 'Invalid or expired OTP';
      throw new Error(message);
    }

    if (response.status === 404) {
      const message = parsed.message || 'Mobile number not registered';
      throw new Error(message);
    }

    throw new Error(parsed.message || 'Failed to verify OTP');
  }

  const data = await response.json();
  console.log('✅ OTP verified successfully, student profile:', data.student);
  return data;
};