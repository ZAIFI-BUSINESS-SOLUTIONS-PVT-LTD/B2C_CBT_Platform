#!/usr/bin/env node

/**
 * PWA Pre-Build Verification Script
 * 
 * Run this before building to ensure all PWA requirements are met.
 * Usage: node pwa-verify.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('\n🔍 InzightEd PWA Verification\n');
console.log('='.repeat(50));

let errors = 0;
let warnings = 0;

// Check critical files
const criticalFiles = [
  'client/public/manifest.json',
  'client/public/service-worker.js',
  'client/index.html',
  'client/src/main.tsx'
];

console.log('\n📁 Checking critical files...\n');
criticalFiles.forEach(file => {
  try {
    fs.accessSync(file);
    console.log(`✅ ${file}`);
  } catch {
    console.log(`❌ ${file} - MISSING`);
    errors++;
  }
});

// Check icon files
const requiredIcons = [72, 96, 128, 144, 152, 192, 384, 512];
console.log('\n🎨 Checking app icons...\n');

requiredIcons.forEach(size => {
  const iconPath = `client/public/icons/icon-${size}.png`;
  try {
    fs.accessSync(iconPath);
    console.log(`✅ icon-${size}.png`);
  } catch {
    console.log(`❌ icon-${size}.png - MISSING`);
    warnings++;
  }
});

// Check manifest.json content
console.log('\n📋 Checking manifest.json...\n');
try {
  const manifest = JSON.parse(fs.readFileSync('client/public/manifest.json', 'utf8'));
  
  // Required fields
  const requiredFields = ['name', 'short_name', 'start_url', 'display', 'icons'];
  requiredFields.forEach(field => {
    if (manifest[field]) {
      console.log(`✅ ${field}: ${typeof manifest[field] === 'object' ? '✓' : manifest[field]}`);
    } else {
      console.log(`❌ ${field} - MISSING`);
      errors++;
    }
  });
  
  // Check icons array
  if (manifest.icons && manifest.icons.length >= 2) {
    console.log(`✅ icons array: ${manifest.icons.length} icons defined`);
  } else {
    console.log(`⚠️  icons array: only ${manifest.icons?.length || 0} icons`);
    warnings++;
  }
  
  // Check display mode
  if (manifest.display === 'standalone' || manifest.display === 'fullscreen') {
    console.log(`✅ display mode: ${manifest.display}`);
  } else {
    console.log(`⚠️  display mode: ${manifest.display} (recommended: standalone)`);
    warnings++;
  }
  
} catch (error) {
  console.log(`❌ Error reading manifest.json: ${error.message}`);
  errors++;
}

// Check index.html for PWA tags
console.log('\n🌐 Checking index.html PWA tags...\n');
try {
  const html = fs.readFileSync('client/index.html', 'utf8');
  
  const checks = [
    { tag: '<link rel="manifest"', name: 'manifest link' },
    { tag: 'name="theme-color"', name: 'theme-color meta' },
    { tag: 'name="viewport"', name: 'viewport meta' },
    { tag: 'name="apple-mobile-web-app-capable"', name: 'iOS PWA support' }
  ];
  
  checks.forEach(check => {
    if (html.includes(check.tag)) {
      console.log(`✅ ${check.name}`);
    } else {
      console.log(`⚠️  ${check.name} - MISSING`);
      warnings++;
    }
  });
  
} catch (error) {
  console.log(`❌ Error reading index.html: ${error.message}`);
  errors++;
}

// Check main.tsx for service worker registration
console.log('\n⚙️  Checking service worker registration...\n');
try {
  const mainTsx = fs.readFileSync('client/src/main.tsx', 'utf8');
  
  if (mainTsx.includes('serviceWorker') && mainTsx.includes('register')) {
    console.log('✅ Service worker registration found');
  } else {
    console.log('❌ Service worker registration NOT found');
    errors++;
  }
  
  if (mainTsx.includes('beforeinstallprompt')) {
    console.log('✅ Install prompt handler found');
  } else {
    console.log('⚠️  Install prompt handler not found (optional)');
  }
  
} catch (error) {
  console.log(`❌ Error reading main.tsx: ${error.message}`);
  errors++;
}

// Final summary
console.log('\n' + '='.repeat(50));
console.log('\n📊 Summary:\n');

if (errors === 0 && warnings === 0) {
  console.log('🎉 Perfect! All PWA requirements met.');
  console.log('\n✅ Next steps:');
  console.log('   1. npm run build');
  console.log('   2. Deploy dist/public/ to HTTPS server');
  console.log('   3. Test on Android Chrome\n');
  process.exit(0);
} else if (errors === 0) {
  console.log(`⚠️  ${warnings} warning(s) found.`);
  
  if (warnings > 0 && requiredIcons.some(size => {
    try {
      fs.accessSync(`client/public/icons/icon-${size}.png`);
      return false;
    } catch {
      return true;
    }
  })) {
    console.log('\n⚠️  ICONS MISSING:');
    console.log('   Generate icons before building:');
    console.log('   1. Open client/public/icons/generate-icons.html');
    console.log('   2. Or run: cd client/public/icons && npm run generate-icons');
  }
  
  console.log('\n✅ You can still build, but fix warnings for best results.\n');
  process.exit(0);
} else {
  console.log(`❌ ${errors} error(s) found.`);
  console.log(`⚠️  ${warnings} warning(s) found.`);
  console.log('\n❌ Please fix errors before building.\n');
  console.log('💡 See PWA_SUMMARY.md for guidance.\n');
  process.exit(1);
}
