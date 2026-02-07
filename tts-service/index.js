/**
 * TTS Microservice - Express API for server-side text-to-speech
 * Serves checkpoint insights as audio for NeetNinja PWA
 */

import express from 'express';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { v4 as uuidv4 } from 'uuid';
import path from 'path';
import { fileURLToPath } from 'url';
import { generateAudio } from './services/tts.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3001;

// Security middleware
app.use(helmet({
  crossOriginResourcePolicy: { policy: "cross-origin" } // Allow audio files to be loaded cross-origin
}));

// Parse JSON request bodies
app.use(express.json({ limit: '10kb' })); // Limit body size to prevent abuse

// Rate limiting - 10 requests per minute per IP
const limiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 10, // 10 requests per window
  message: { error: 'Too many requests. Please try again later.' },
  standardHeaders: true,
  legacyHeaders: false,
});

// Apply rate limiting to API endpoint only
app.use('/api', limiter);

// Serve static audio files
app.use('/audio', express.static(path.join(__dirname, 'public', 'audio'), {
  maxAge: '1h', // Cache for 1 hour
  setHeaders: (res, filePath) => {
    res.set('Access-Control-Allow-Origin', '*');
    res.set('Access-Control-Allow-Methods', 'GET');
  }
}));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    service: 'tts-service',
    timestamp: new Date().toISOString()
  });
});

/**
 * POST /api/generate-insight-audio
 * Generate TTS audio for checkpoint insights
 * 
 * Request body:
 * {
 *   "text": "Insight text to convert to speech",
 *   "testId": "123",  // Optional: for filename tagging
 *   "institution": "neet bro institute"  // Optional: for gating
 * }
 * 
 * Response:
 * {
 *   "audioUrl": "/audio/<uuid>.mp3"
 * }
 */
app.post('/api/generate-insight-audio', async (req, res) => {
  const startTime = Date.now();
  
  try {
    const { text, testId, institution } = req.body;

    // Validate text parameter
    if (!text || typeof text !== 'string') {
      return res.status(400).json({ 
        error: 'Invalid request: text is required and must be a string' 
      });
    }

    // Enforce text length limit (800 characters ~ 2 minutes of speech)
    if (text.length > 800) {
      return res.status(400).json({ 
        error: 'Text too long. Maximum 800 characters allowed.' 
      });
    }

    // Optional: institution gating (if needed server-side)
    // Note: Client-side gating is primary, this is defense in depth
    // if (institution && institution.toLowerCase() !== 'neet bro institute') {
    //   return res.status(403).json({ 
    //     error: 'TTS service is only available for authorized institutions' 
    //   });
    // }

    // Generate unique filename (UUID or testId-based)
    const filename = testId ? `insight-${testId}-${Date.now()}` : `insight-${uuidv4()}`;

    console.log(`📨 TTS request received:`, {
      testId: testId || 'N/A',
      institution: institution || 'N/A',
      textLength: text.length,
      filename
    });

    // Generate audio file
    const audioUrl = await generateAudio(text, filename);

    const duration = Date.now() - startTime;
    console.log(`✅ TTS generation completed in ${duration}ms`);

    // Return audio URL
    res.json({ 
      audioUrl,
      filename,
      generationTime: duration
    });

  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`❌ TTS generation failed after ${duration}ms:`, error);
    
    res.status(500).json({ 
      error: 'Failed to generate audio. Please try again.',
      details: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ 
    error: 'Internal server error',
    details: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`🎙️ TTS Service running on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
  console.log(`🔊 Audio endpoint: http://localhost:${PORT}/api/generate-insight-audio`);
  console.log(`🎵 Static audio: http://localhost:${PORT}/audio/`);
});
