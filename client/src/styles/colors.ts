/**
 * InzightEd-inspired Color Theme Configuration
 * Consistent color palette based on the provided design system
 */

export const COLORS = {
  // Primary Colors
  primary: {
    500: '#4F83FF',  // Main blue
    600: '#3B82F6',  // Darker blue for hover states
    700: '#2563EB',  // Even darker for active states
    50: '#E8F0FF',   // Very light blue background
    100: '#DBEAFE', // Light blue
  },
  
  // Secondary Colors
  secondary: {
    50: '#F8FAFC',   // Very light gray
    100: '#F1F5F9',  // Light gray background
    200: '#E2E8F0',  // Border gray
    300: '#CBD5E1',  // Muted gray
    400: '#94A3B8',  // Medium gray
    500: '#64748B',  // Text gray
    600: '#475569',  // Dark text gray
    700: '#334155',  // Darker gray
    800: '#1E293B',  // Very dark gray
    900: '#0F172A',  // Almost black
  },
  
  // Success/Green
  success: {
    50: '#ECFDF5',
    100: '#D1FAE5',
    500: '#10B981',
    600: '#059669',
    700: '#047857',
  },
  
  // Warning/Orange
  warning: {
    50: '#FFFBEB',
    100: '#FEF3C7',
    500: '#F59E0B',
    600: '#D97706',
    700: '#B45309',
  },
  
  // Error/Red
  error: {
    50: '#FEF2F2',
    100: '#FEE2E2',
    500: '#EF4444',
    600: '#DC2626',
    700: '#B91C1C',
  },
  
  // Purple accent (for special features)
  purple: {
    50: '#F5F3FF',
    100: '#EDE9FE',
    500: '#8B5CF6',
    600: '#7C3AED',
    700: '#6D28D9',
  },
  
  // Background gradients
  background: {
    primary: 'from-blue-50 via-indigo-50 to-purple-50',
    secondary: 'from-gray-50 to-blue-50',
    card: '#FFFFFF',
    overlay: 'rgba(15, 23, 42, 0.5)', // Dark overlay for modals
  }
} as const;

// CSS Custom Properties for easy integration with Tailwind
export const CSS_VARIABLES = `
  :root {
    --color-primary: ${COLORS.primary[500]};
    --color-primary-hover: ${COLORS.primary[600]};
    --color-primary-active: ${COLORS.primary[700]};
    --color-primary-light: ${COLORS.primary[50]};
    --color-secondary: ${COLORS.secondary[500]};
    --color-success: ${COLORS.success[500]};
    --color-warning: ${COLORS.warning[500]};
    --color-error: ${COLORS.error[500]};
    --color-purple: ${COLORS.purple[500]};
  }
`;
