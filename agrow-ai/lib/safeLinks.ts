import { Linking } from 'react-native';

/**
 * Open a link that came from the server or curated data.
 *
 * Only plain `https:` links are opened. `intent:`, `javascript:`, `file:`,
 * custom app schemes and links with embedded credentials are refused, so a
 * tampered record cannot launch another app or a local file.
 */
// Parsed with a regex, not `new URL()`: React Native's URL polyfill is not
// WHATWG-compliant and mis-reads some valid links.
//   https://  host[:port]  then end, "/", "?" or "#"; no userinfo ("@") in the
//   authority; no whitespace or control characters anywhere.
const SAFE_HTTPS = /^https:\/\/[a-z0-9.-]+(:\d{1,5})?([/?#]|$)/i;
// eslint-disable-next-line no-control-regex
const UNSAFE_CHARS = /[\s\u0000-\u001f\u007f]/;

export function isSafeExternalUrl(url: string | null | undefined): url is string {
  if (!url) return false;
  const value = url.trim();
  return SAFE_HTTPS.test(value) && !UNSAFE_CHARS.test(value);
}

export async function openExternalUrl(url: string | null | undefined): Promise<boolean> {
  if (!isSafeExternalUrl(url)) return false;
  try {
    await Linking.openURL(url.trim());
    return true;
  } catch {
    return false;
  }
}
