/**
 * PWA Icon Generator Script
 * 
 * This script generates all required PWA icons from a source image.
 * 
 * USAGE:
 * 1. Place your logo/icon as "source-icon.png" in this folder
 *    (Recommended: 1024x1024 or larger, square, PNG with transparency)
 * 
 * 2. Install dependencies:
 *    npm install
 * 
 * 3. Run the script:
 *    npm run generate-icons
 * 
 * OR use the HTML generator (no dependencies):
 *    Open generate-icons.html in browser
 */

import sharp from 'sharp';
import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Icon sizes required for PWA
const SIZES = [72, 96, 128, 144, 152, 192, 384, 512];

// Source image file (should be 1024x1024 or larger)
const SOURCE_IMAGE = path.join(__dirname, 'source-icon.png');

async function generateIcons() {
  console.log('🎨 PWA Icon Generator Starting...\n');

  // Check if source image exists
  try {
    await fs.access(SOURCE_IMAGE);
  } catch (error) {
    console.error('❌ Error: source-icon.png not found!');
    console.log('\n📋 Instructions:');
    console.log('1. Place your app icon as "source-icon.png" in this folder');
    console.log('2. Image should be square (1024x1024 recommended)');
    console.log('3. PNG format with transparency preferred');
    console.log('4. Run this script again\n');
    console.log('OR use generate-icons.html in browser (no setup needed)');
    process.exit(1);
  }

  console.log(`✅ Found source image: ${SOURCE_IMAGE}\n`);

  // Generate each icon size
  for (const size of SIZES) {
    const outputPath = path.join(__dirname, `icon-${size}.png`);
    
    try {
      await sharp(SOURCE_IMAGE)
        .resize(size, size, {
          fit: 'contain',
          background: { r: 0, g: 0, b: 0, alpha: 0 }
        })
        .png()
        .toFile(outputPath);
      
      console.log(`✅ Generated icon-${size}.png (${size}x${size})`);
    } catch (error) {
      console.error(`❌ Failed to generate icon-${size}.png:`, error.message);
    }
  }

  console.log('\n🎉 All icons generated successfully!');
  console.log('\n📁 Generated files:');
  SIZES.forEach(size => {
    console.log(`   - icon-${size}.png`);
  });
  
  console.log('\n✅ Next steps:');
  console.log('1. Check the generated icons');
  console.log('2. Run: npm run build');
  console.log('3. Deploy to HTTPS server');
  console.log('4. Test PWA installation on Android Chrome\n');
}

generateIcons().catch(error => {
  console.error('❌ Fatal error:', error);
  process.exit(1);
});
