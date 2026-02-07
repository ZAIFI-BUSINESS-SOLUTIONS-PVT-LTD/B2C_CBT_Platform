/**
 * TTS Service - Server-side speech generation using edge-tts (Python)
 * Generates MP3 audio files for insight dictation
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';

const execAsync = promisify(exec);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Voice configuration (Indian English female voice)
const VOICE = 'en-IN-NeerjaNeural';

// Audio output directory (relative to project root)
const AUDIO_DIR = path.join(__dirname, '..', 'public', 'audio');

/**
 * Generate audio file from text using edge-tts Python CLI
 * @param {string} text - Text to convert to speech
 * @param {string} filename - Output filename (without extension)
 * @returns {Promise<string>} - Public URL path to the generated audio file
 */
export async function generateAudio(text, filename) {
  try {
    // Ensure audio directory exists
    await fs.ensureDir(AUDIO_DIR);

    // Full path to output file
    const outputPath = path.join(AUDIO_DIR, `${filename}.mp3`);

    console.log(`🎙️ Generating TTS audio: ${filename}.mp3`);
    console.log(`📝 Text length: ${text.length} characters`);
    console.log(`🎤 Voice: ${VOICE}`);

    // Escape text for shell (replace quotes and special chars)
    const escapedText = text.replace(/"/g, '\\"').replace(/\$/g, '\\$').replace(/`/g, '\\`');

    // Use edge-tts Python CLI via child process
    // Command: edge-tts -v "en-IN-NeerjaNeural" -t "text" --write-media output.mp3
    const command = `edge-tts --voice "${VOICE}" --text "${escapedText}" --write-media "${outputPath}"`;

    console.log(`🔧 Executing: edge-tts --voice "${VOICE}" --text "[text]" --write-media "${outputPath}"`);

    // Execute edge-tts command with 30 second timeout
    await execAsync(command, {
      timeout: 30000,
      maxBuffer: 10 * 1024 * 1024 // 10MB buffer
    });

    // Verify file was created
    const exists = await fs.pathExists(outputPath);
    if (!exists) {
      throw new Error('Audio file was not created');
    }

    console.log(`✅ Audio generated successfully: ${outputPath}`);

    // Return public URL path
    return `/audio/${filename}.mp3`;
  } catch (error) {
    console.error(`❌ TTS generation failed:`, error);
    
    // Provide helpful error message
    if (error.message.includes('edge-tts')) {
      throw new Error('edge-tts not installed. Run: pip install edge-tts');
    }
    
    throw new Error(`Failed to generate audio: ${error.message}`);
  }
}

/**
 * Get audio file stats (for monitoring/cleanup)
 * @param {string} filename - Audio filename (without extension)
 * @returns {Promise<Object>} - File stats or null if not found
 */
export async function getAudioStats(filename) {
  try {
    const filePath = path.join(AUDIO_DIR, `${filename}.mp3`);
    const exists = await fs.pathExists(filePath);
    
    if (!exists) {
      return null;
    }

    const stats = await fs.stat(filePath);
    return {
      size: stats.size,
      created: stats.birthtime,
      modified: stats.mtime
    };
  } catch (error) {
    console.error(`Error getting audio stats:`, error);
    return null;
  }
}

/**
 * Delete audio file
 * @param {string} filename - Audio filename (without extension)
 * @returns {Promise<boolean>} - True if deleted successfully
 */
export async function deleteAudio(filename) {
  try {
    const filePath = path.join(AUDIO_DIR, `${filename}.mp3`);
    await fs.remove(filePath);
    console.log(`🗑️ Deleted audio file: ${filename}.mp3`);
    return true;
  } catch (error) {
    console.error(`Error deleting audio file:`, error);
    return false;
  }
}
