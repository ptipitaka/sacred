/**
 * Hypothes.is Configuration for TPTK Project
 * Centralized config management for annotation system
 */

// Environment-based configuration
export interface HypothesisConfig {
  // Basic settings
  openSidebar?: boolean;
  showHighlights?: boolean;
  
  // Group settings
  group?: string; // Group ID for private groups
  
  // UI customization
  theme?: 'light' | 'dark';
  branding?: {
    appBackgroundColor?: string;
    ctaBackgroundColor?: string;
    ctaTextColor?: string;
    selectionFontFamily?: string;
  };
  
  // Advanced settings
  enableExperimentalNewNoteButton?: boolean;
  usernameUrl?: string;
  services?: Array<{
    apiUrl?: string;
    authority?: string;
    groups?: string[];
  }>;
}

// Default configuration for TPTK
export const DEFAULT_HYPOTHESIS_CONFIG: HypothesisConfig = {
  openSidebar: false,
  showHighlights: true,
  theme: 'light',
  branding: {
    // TPTK brand colors
    appBackgroundColor: '#f8fafc',
    ctaBackgroundColor: '#4f46e5', // Purple theme
    ctaTextColor: '#ffffff',
    selectionFontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif'
  },
  enableExperimentalNewNoteButton: true
};

// Environment-specific configurations
export const HYPOTHESIS_CONFIGS = {
  development: {
    ...DEFAULT_HYPOTHESIS_CONFIG,
    // Development-specific settings
    group: undefined, // Public annotations for dev
  },
  
  production: {
    ...DEFAULT_HYPOTHESIS_CONFIG,
    // Production will use private groups
    group: '', // Will be set when we create the group
  },
  
  // Private group for TPTK team review
  tptk_review: {
    ...DEFAULT_HYPOTHESIS_CONFIG,
    group: '', // Will be populated with actual group ID
    branding: {
      ...DEFAULT_HYPOTHESIS_CONFIG.branding,
      appBackgroundColor: '#fef3c7', // Yellow tint for review mode
      ctaBackgroundColor: '#d97706', // Orange for review actions
    }
  }
} as const;

// Helper function to get config based on environment and context
export function getHypothesisConfig(
  environment: keyof typeof HYPOTHESIS_CONFIGS = 'development',
  overrides: Partial<HypothesisConfig> = {}
): HypothesisConfig {
  const baseConfig = HYPOTHESIS_CONFIGS[environment];
  return {
    ...baseConfig,
    ...overrides,
    branding: {
      ...baseConfig.branding,
      ...overrides.branding
    }
  };
}

// Type for component props
export interface HypothesisAnnotationProps {
  frontmatter?: any;
  enabled?: boolean;
  environment?: keyof typeof HYPOTHESIS_CONFIGS;
  configOverrides?: Partial<HypothesisConfig>;
}