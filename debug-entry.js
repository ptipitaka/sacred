// Test getEntry functionality
import { getEntry } from 'astro:content';

async function testGetEntry() {
  try {
    console.log('Testing getEntry for romn/tipitaka/vi/paci/index...');
    const entry = await getEntry('docs', 'romn/tipitaka/vi/paci/index');
    console.log('Entry found:', entry ? 'YES' : 'NO');
    if (entry) {
      console.log('Entry data:', entry.data);
    }
  } catch (error) {
    console.log('Error:', error);
  }
}

testGetEntry();