/**
 * Hypothes.is Group Management Utilities for TPTK
 * Simplified group structure with MASTER verification approach
 */

export interface HypothesisGroup {
  id: string;
  name: string;
  description?: string;
  type: 'private' | 'restricted' | 'open';
  authority: string;
  created: string;
  updated: string;
  members: {
    admins: string[];
    moderators: string[];
    members: string[];
  };
}

// Simplified groups for TPTK project
export const TPTK_GROUPS = {
  // Main review team for editorial oversight
  REVIEW_TEAM: {
    name: 'TPTK Review Team',
    description: 'Main review team for Tipitaka content - editors, validators, and quality assurance',
    type: 'private' as const,
    purpose: 'Primary content review and validation',
    roles: ['editor', 'validator', 'qa_lead']
  },
  
  // Master verification experts for all Tipitaka content
  MASTER: {
    name: 'TPTK Master Verifiers',
    description: 'Master experts for verifying accuracy against original manuscripts and identifying potential source errors',
    type: 'restricted' as const,
    purpose: 'Manuscript verification and source error identification',
    roles: ['master_verifier', 'manuscript_expert', 'academic', 'scholar']
  },
  
  // Translation teams for different languages
  TRANSLATORS: {
    name: 'TPTK Translation Team',
    description: 'Translators and language experts for multilingual content',
    type: 'restricted' as const,
    purpose: 'Translation review and language consistency',
    roles: ['translator', 'language_expert']
  },
  
  // Public group for community feedback
  COMMUNITY: {
    name: 'TPTK Community',
    description: 'Open community for public feedback and discussion',
    type: 'open' as const,
    purpose: 'Community engagement and public feedback',
    roles: ['community_member', 'student', 'practitioner']
  }
} as const;

// Group selection logic based on content and user context
export function selectGroupForContent(
  frontmatter: any,
  userRole?: string
): keyof typeof TPTK_GROUPS | null {
  
  if (!frontmatter.type || frontmatter.type !== 'tipitaka') {
    return null;
  }

  const reviewStatus = frontmatter.review?.current;
  
  // For review/revision status, use MASTER group for manuscript verification
  if (['review', 'revision'].includes(reviewStatus)) {
    return 'MASTER'; // Single expert group for all Tipitaka content verification
  }
  
  // For approved/published content, allow community input
  if (['approved', 'published'].includes(reviewStatus)) {
    return 'COMMUNITY';
  }
  
  // Default to main review team
  return 'REVIEW_TEAM';
}

// Helper to get group ID from environment configuration
export function getGroupIdForSelection(
  groupSelection: keyof typeof TPTK_GROUPS | null,
  environment: string
): string | undefined {
  
  if (!groupSelection) return undefined;
  
  // This will be populated when we create actual groups
  const GROUP_IDS: Record<string, Record<keyof typeof TPTK_GROUPS, string>> = {
    development: {
      REVIEW_TEAM: '',
      MASTER: '',
      TRANSLATORS: '',
      COMMUNITY: '' // Empty means public in development
    },
    production: {
      REVIEW_TEAM: '', // Will be filled with actual IDs
      MASTER: '',
      TRANSLATORS: '',
      COMMUNITY: ''
    },
    tptk_review: {
      REVIEW_TEAM: '', // Same as production but with review-specific config
      MASTER: '',
      TRANSLATORS: '',
      COMMUNITY: ''
    }
  };
  
  return GROUP_IDS[environment]?.[groupSelection];
}

// Generate group creation payload for Hypothes.is API
export function generateGroupCreationPayload(
  groupKey: keyof typeof TPTK_GROUPS
): Omit<HypothesisGroup, 'id' | 'created' | 'updated' | 'authority'> {
  const groupConfig = TPTK_GROUPS[groupKey];
  
  return {
    name: groupConfig.name,
    description: groupConfig.description,
    type: groupConfig.type,
    members: {
      admins: [], // Will be populated during setup
      moderators: [],
      members: []
    }
  };
}

// Batch create all TPTK groups
export function getAllGroupCreationPayloads(): Array<{
  key: keyof typeof TPTK_GROUPS;
  payload: Omit<HypothesisGroup, 'id' | 'created' | 'updated' | 'authority'>;
}> {
  return Object.keys(TPTK_GROUPS).map(key => ({
    key: key as keyof typeof TPTK_GROUPS,
    payload: generateGroupCreationPayload(key as keyof typeof TPTK_GROUPS)
  }));
}