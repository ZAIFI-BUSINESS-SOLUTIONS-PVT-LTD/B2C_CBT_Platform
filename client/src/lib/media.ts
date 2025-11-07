/**
 * Helper to normalize various image representations into a usable <img> src.
 * Accepts:
 * - full data URIs (e.g. data:image/png;base64,AAAA)
 * - raw base64 payload (AAAA...)
 * - http(s) URLs
 * Returns undefined when input is empty or invalid.
 */
export default function normalizeImageSrc(value?: string | null, fallbackMime: string = 'image/png'): string | undefined {
  if (value === null || value === undefined) return undefined;
  try {
  let s = String(value).trim();
  if (!s) return undefined;

  // Debug logging (can be removed in production)
  console.log('[normalizeImageSrc] Input length:', s.length, 'First 50 chars:', s.substring(0, 50));

    // If already a data URI, return as-is
    if (/^data:/i.test(s)) {
      console.log('[normalizeImageSrc] Already a data URI, returning as-is');
      return s;
    }

    // If it's an absolute URL, return as-is
    if (/^https?:\/\//i.test(s)) {
      console.log('[normalizeImageSrc] HTTP(S) URL detected, returning as-is');
      return s;
    }

    // If the string looks like it already contains a data: prefix followed by comma,
    // return as-is (defensive parsing)
    const commaIndex = s.indexOf(',');
    if (commaIndex > 0 && s.slice(0, commaIndex).includes('data:')) {
      console.log('[normalizeImageSrc] Data URI with comma found, returning as-is');
      return s;
    }

    // If it's likely raw base64 (not a data: URI or URL), sanitize it by
    // removing internal whitespace/newlines and any surrounding quotes which
    // may have been introduced during transport (Excel/CSV exports can do this).
    let payload = s;
    // strip surrounding single or double quotes
    payload = payload.replace(/^"|"$/g, '').replace(/^'|'$/g, '');
    // remove all whitespace/newlines inside the payload
    payload = payload.replace(/\s+/g, '');

    // Heuristics on base64 prefixes to guess mime type for common formats
    const prefix = payload.slice(0, 12);
    let mime = fallbackMime;
    if (prefix.startsWith('/9j') || prefix.startsWith('/9j/')) {
      mime = 'image/jpeg';
    } else if (prefix.startsWith('iVBORw0KG')) {
      mime = 'image/png';
    } else if (prefix.startsWith('R0lGOD')) {
      mime = 'image/gif';
    } else if (/^(PHN2|PD94)/.test(prefix) || s.startsWith('<svg')) {
      mime = 'image/svg+xml';
    }

    // Basic validation: ensure payload contains only base64 characters (+ / =).
    const base64Regex = /^[A-Za-z0-9+/]+={0,2}$/;
    if (!base64Regex.test(payload)) {
      // Still attempt to return a data URI, but log a warning to help debug
      console.warn('[normalizeImageSrc] Warning: payload did not match base64 regex. Proceeding anyway.');
      console.log('[normalizeImageSrc] Payload sample (first 40):', payload.substring(0, 40));
    }

    const result = `data:${mime};base64,${payload}`;
    console.log('[normalizeImageSrc] Wrapped as data URI:', mime, 'Result length:', result.length, 'Sanitized payload length:', payload.length);
    return result;
  } catch (e) {
    console.error('[normalizeImageSrc] Error:', e);
    return undefined;
  }
}
