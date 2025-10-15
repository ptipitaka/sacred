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

// Collaborative team-based groups for TPTK project
export const TPTK_GROUPS = {
  // Main collaborative review team - all experts work together
  REVIEW_TEAM: {
    name: 'TPTK Review Team',
    description: 'Collaborative team of all experts: manuscript verifiers, translators, editors, and scholars working together through discussion and consensus',
    type: 'private' as const,
    purpose: 'Collaborative review, discussion, and consensus-based validation for all Tipitaka content',
    roles: ['admin', 'master_verifier', 'translator', 'editor', 'scholar', 'manuscript_expert']
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

// Simplified group selection - let users choose their own group
export function selectGroupForContent(
  frontmatter: any,
  userRole?: string
): keyof typeof TPTK_GROUPS | null {
  
  if (!frontmatter.type || frontmatter.type !== 'tipitaka') {
    return null; // No annotation for non-tipitaka content
  }
  
  // Default to REVIEW_TEAM for tipitaka content
  // Users can manually switch groups in Hypothesis sidebar if needed
  return 'REVIEW_TEAM';
}

// Helper to get group ID for selection
export function getGroupIdForSelection(
  groupSelection: keyof typeof TPTK_GROUPS | null
): string | undefined {
  
  if (!groupSelection) return undefined;
  
  // Simplified configuration - direct mapping
  const GROUP_IDS: Record<keyof typeof TPTK_GROUPS, string> = {
    REVIEW_TEAM: 'RGMZekaj', // TPTK Review Team - Private collaborative team
    COMMUNITY: ''            // Public group (no ID needed)
  };
  
  return GROUP_IDS[groupSelection];
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