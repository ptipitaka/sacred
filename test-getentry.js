// Test getEntry function
import { getEntry } from 'astro:content';

async function testGetEntry() {
  console.log('Testing getEntry...');
  
  try {
    // Test 1: Direct path
    const result1 = await getEntry('docs', 'romn/tipitaka/vi/para/index');
    console.log('Result 1 (index):', !!result1);
  } catch (e) {
    console.log('Error 1:', e.message);
  }
  
  try {
    // Test 2: Without extension
    const result2 = await getEntry('docs', 'romn/tipitaka/vi/para/index');
    console.log('Result 2 (index):', !!result2);
  } catch (e) {
    console.log('Error 2:', e.message);
  }
}

testGetEntry();