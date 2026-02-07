/**
 * Audio Cleanup Script
 * Removes audio files older than specified hours to prevent disk bloat
 * Run via cron or scheduled task: node scripts/cleanup-audio.js
 */

import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const AUDIO_DIR = path.join(__dirname, '..', 'public', 'audio');
const MAX_AGE_HOURS = process.env.MAX_AGE_HOURS || 24; // Default: 24 hours
const MAX_AGE_MS = MAX_AGE_HOURS * 60 * 60 * 1000;

/**
 * Clean up old audio files
 */
async function cleanupAudio() {
  try {
    console.log(`🧹 Starting audio cleanup...`);
    console.log(`📂 Directory: ${AUDIO_DIR}`);
    console.log(`⏰ Max age: ${MAX_AGE_HOURS} hours`);

    // Ensure directory exists
    const exists = await fs.pathExists(AUDIO_DIR);
    if (!exists) {
      console.log(`ℹ️ Audio directory does not exist yet. Nothing to clean.`);
      return;
    }

    // Get all MP3 files
    const files = await fs.readdir(AUDIO_DIR);
    const mp3Files = files.filter(f => f.endsWith('.mp3'));

    console.log(`📊 Found ${mp3Files.length} audio files`);

    let deletedCount = 0;
    let totalSizeDeleted = 0;
    const now = Date.now();

    // Check each file
    for (const file of mp3Files) {
      const filePath = path.join(AUDIO_DIR, file);
      
      try {
        const stats = await fs.stat(filePath);
        const ageMs = now - stats.mtimeMs;

        // Delete if older than max age
        if (ageMs > MAX_AGE_MS) {
          await fs.remove(filePath);
          deletedCount++;
          totalSizeDeleted += stats.size;
          
          const ageHours = Math.floor(ageMs / (60 * 60 * 1000));
          console.log(`🗑️ Deleted: ${file} (age: ${ageHours}h, size: ${formatBytes(stats.size)})`);
        }
      } catch (error) {
        console.error(`❌ Error processing ${file}:`, error.message);
      }
    }

    console.log(`\n✅ Cleanup complete!`);
    console.log(`📊 Deleted: ${deletedCount} files`);
    console.log(`💾 Space freed: ${formatBytes(totalSizeDeleted)}`);
    console.log(`📁 Remaining: ${mp3Files.length - deletedCount} files`);

  } catch (error) {
    console.error(`❌ Cleanup failed:`, error);
    process.exit(1);
  }
}

/**
 * Format bytes to human-readable size
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Run cleanup
cleanupAudio().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
