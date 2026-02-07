/**
 * TTS Helper - Audio playback for checkpoint insights
 * Handles audio generation request and playback via HTMLAudioElement
 */

import { API_CONFIG } from '@/config/api';
import { authenticatedFetch } from '@/lib/auth';

export interface TTSResponse {
  audioUrl: string;
  filename?: string;
  generationTime?: number;
}

/**
 * Play checkpoint insights audio
 * @param text - Text to convert to speech
 * @param testId - Optional test ID for filename tagging
 * @param institution - Optional institution name
 * @returns Promise<boolean> - True if playback succeeded, false otherwise
 */
export async function playInsightAudio(
  text: string,
  testId?: number | string,
  institution?: string
): Promise<boolean> {
  try {
    console.log('🎙️ Generating TTS audio...', { textLength: text.length, testId, institution });

    // Request audio generation from TTS service
    const response = await authenticatedFetch(
      `${API_CONFIG.BASE_URL}/api/generate-insight-audio`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text,
          testId: testId?.toString(),
          institution,
        }),
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Failed to generate audio' }));
      console.error('❌ TTS generation failed:', error);
      return false;
    }

    const data: TTSResponse = await response.json();
    const audioUrl = data.audioUrl;

    if (!audioUrl) {
      console.error('❌ No audio URL in response');
      return false;
    }

    console.log('✅ Audio generated:', audioUrl);

    // Construct full URL (audioUrl is relative path like "/audio/insight-123.mp3")
    const fullAudioUrl = `${API_CONFIG.BASE_URL}${audioUrl}`;

    // Play audio using HTMLAudioElement
    const audio = new Audio(fullAudioUrl);
    
    await audio.play();
    console.log('🔊 Audio playback started');

    return true;
  } catch (error) {
    console.error('❌ Audio playback failed:', error);
    return false;
  }
}

/**
 * Preload audio to unlock playback in user gesture
 * Call this in a click handler to satisfy autoplay policy
 * @returns Audio element (keep reference to set src later)
 */
export function unlockAudio(): HTMLAudioElement {
  try {
    // Create audio element and play silent audio to unlock
    const audio = new Audio();
    audio.volume = 0.01;
    
    // Create tiny silent data URL (prevents network request)
    const silentMp3 = 'data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAADhAC7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7//////////////////////////////////////////////////////////////////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAAAAAAAAAAAA4S/AAAA//sQZAAP8AAAaQAAAAgAAA0gAAABAAABpAAAACAAADSAAAAETEFNRTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//sQZDwP8AAAaQAAAAgAAA0gAAABAAABpAAAACAAADSAAAAEVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV';
    
    audio.src = silentMp3;
    audio.play().catch(() => {
      // Ignore errors during unlock
      console.log('Audio unlock attempt made');
    });
    
    return audio;
  } catch (error) {
    console.warn('Audio unlock failed:', error);
    return new Audio(); // Return empty audio element as fallback
  }
}

/**
 * Play audio with custom Audio element (after unlock)
 * @param audio - Unlocked Audio element
 * @param audioUrl - Full URL to audio file
 * @returns Promise<boolean> - True if playback succeeded
 */
export async function playAudioWithElement(
  audio: HTMLAudioElement,
  audioUrl: string
): Promise<boolean> {
  try {
    console.log('🔊 Playing audio:', audioUrl);
    
    // Reset audio element
    audio.pause();
    audio.currentTime = 0;
    audio.volume = 1.0;
    audio.src = audioUrl;
    
    await audio.play();
    console.log('✅ Audio playback started');
    
    return true;
  } catch (error) {
    console.error('❌ Audio playback failed:', error);
    return false;
  }
}
