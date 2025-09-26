// Breadcrumb Builder Utility for Astro Starlight
// Dynamic breadcrumb generation based on file path and content structure

import { getEntry } from 'astro:content';

/**
 * Clean title by removing quotes and extra formatting
 * @param {string} title - Raw title from frontmatter
 * @returns {string} Cleaned title
 */
export function cleanTitle(title) {
  if (typeof title !== 'string') return title;
  
  // Remove surrounding quotes and return cleaned title
  return title.replace(/^["']|["']$/g, '');
}

/**
 * Get title from file's frontmatter or fallback to sectionName
 * @param {string} sectionPath - Path to the file/folder
 * @param {string} sectionName - Default name from path
 * @param {string} collection - Content collection
 * @returns {Promise<string>} Title to use in breadcrumb
 */
async function getTitleFromFrontmatter(sectionPath, sectionName, collection) {
  try {
    // Try to get entry from content collection
    const entry = await getEntry(collection, sectionPath);
    if (entry && entry.data && entry.data.title) {
      // Remove quotes and clean the title
      const title = cleanTitle(entry.data.title);
      // console.log(`Found frontmatter title for ${sectionPath}: "${title}"`);
      return title;
    }
  } catch (error) {
    // Entry not found or error occurred, fall back to sectionName
    // console.log(`No frontmatter title found for ${sectionPath}, using section name`);
  }
  
  // Fallback to original section name
  return sectionName;
}

/**
 * Check if file should skip breadcrumb generation
 * @param {string} path - File path
 * @returns {boolean}
 */
function shouldSkipBreadcrumb(path) {
  const fileName = path.split('/').pop();
  return fileName === 'index' || fileName === '0' || !path.includes('tipitaka');
}

/**
 * Find the deepest level that contains index.mdx file
 * This will be the root level for breadcrumb
 * @param {Array} pathParts - Array of path components
 * @param {string} collection - Content collection
 * @returns {Promise<number>} Index of the root level
 */
async function findRootLevel(pathParts, collection) {
  // For now, use simple rule-based approach since getEntry() seems unreliable
  // Check common patterns where index.mdx typically exists
  
  const fullPath = pathParts.join('/');
  // console.log(`Finding root level for path: ${fullPath}`);
  
  // Known patterns that have index.mdx:
  // 1. Book subsections: su/dn/sila, su/mn/mula, ab/yk/yk1, etc.
  // 2. Direct books: vi/para, ab/dhs, etc.
  // 3. Complex books: ab/pt/anu/tikatika, ab/pt/pac/tika, etc.
  
  if (pathParts.length >= 7) { // e.g., romn/tipitaka/ab/pt/anu/tikatika/1
    const basket = pathParts[2];  // ab
    const book = pathParts[3];    // pt
    const section = pathParts[4]; // anu, pac, anupac, pacanu
    const subsection = pathParts[5]; // tikatika, tikaduka, tika, duka
    
    // Special case for Paṭṭhāna (ab/pt) - has deeper structure
    if (basket === 'ab' && book === 'pt') {
      // console.log(`Using subsection level (index 5) for ${basket}/${book}/${section}/${subsection}`);
      return 5; // Return subsection level (tikatika, tikaduka, etc.)
    }
  }
  
  if (pathParts.length >= 5) { // e.g., romn/tipitaka/su/dn/sila/1
    const basket = pathParts[2];  // su, ab, vi
    const book = pathParts[3];    // dn, yk, para
    const section = pathParts[4]; // sila, yk1, etc.
    
    // Check if this looks like a book subsection pattern
    if (basket === 'su' && ['dn', 'mn', 'sn', 'an'].includes(book)) {
      // For Suttanta books, subsections like 'sila', 'maha', 'pati' have index.mdx
      // console.log(`Using subsection level (index 4) for ${basket}/${book}/${section}`);
      return 4; // Return section level (sila, maha, etc.)
    }
    
    if (basket === 'ab' && ['yk'].includes(book)) {
      // For Abhidhamma books like Yamaka, subsections like 'yk1', 'yk2' have index.mdx
      // console.log(`Using subsection level (index 4) for ${basket}/${book}/${section}`);
      return 4; // Return section level (yk1, yk2, etc.)
    }
  }
  
  if (pathParts.length >= 4) { // e.g., romn/tipitaka/vi/para/1
    // For books that don't have subsections, use book level
    // console.log(`Using book level (index 3) for direct book`);
    return 3; // Return book level (para, dhs, etc.)
  }
  
  // Default: return basket level
  // console.log('Using basket level (index 2) as fallback');
  return 2;
}

/**
 * Build breadcrumb chain dynamically from current page path
 * @param {string} currentPath - Current page path (e.g., "romn/tipitaka/vi/para/1/1-1")
 * @param {string} collection - Content collection name (usually "docs")
 * @returns {Promise<Array>} Array of breadcrumb items with title and link
 */
export async function buildBreadcrumb(currentPath, collection = 'docs') {
  const breadcrumb = [];
  
  // Skip breadcrumb for certain files
  if (shouldSkipBreadcrumb(currentPath)) {
    return breadcrumb;
  }
  
  // Parse path components
  const pathParts = currentPath.split('/');
  const locale = pathParts[0]; // e.g., "romn"
  
  // Skip if not a tipitaka path
  if (pathParts.length < 4 || pathParts[1] !== 'tipitaka') {
    return breadcrumb;
  }
  
  // Find the root level where index.mdx exists (deepest level that has index.mdx)
  const rootLevel = await findRootLevel(pathParts, collection);
  
  // Create breadcrumb starting from root level
  for (let i = rootLevel; i < pathParts.length; i++) {
    const sectionPath = pathParts.slice(0, i + 1).join('/');
    const sectionName = pathParts[i];
    
    // For root level (has index.mdx), add trailing slash
    const isRootLevel = (i === rootLevel);
    const link = isRootLevel ? `/${sectionPath}/` : `/${sectionPath}`;
    
    // Try to get title from frontmatter, fallback to section name
    const title = await getTitleFromFrontmatter(sectionPath, sectionName, collection);
    
    breadcrumb.push({
      title: title,
      link: link
    });
  }
  
  return breadcrumb;
}

/**
 * Get relative path between two paths
 * @param {string} from - Source path
 * @param {string} to - Target path
 * @returns {string} Relative path
 */
export function getRelativePath(from, to) {
  const fromParts = from.split('/').filter(Boolean);
  const toParts = to.split('/').filter(Boolean);
  
  // Find common prefix
  let commonLength = 0;
  while (commonLength < fromParts.length && 
         commonLength < toParts.length && 
         fromParts[commonLength] === toParts[commonLength]) {
    commonLength++;
  }
  
  // Calculate relative path
  const upLevels = fromParts.length - commonLength - 1;
  const upPath = '../'.repeat(Math.max(0, upLevels));
  const downPath = toParts.slice(commonLength).join('/');
  
  return upPath + downPath;
}