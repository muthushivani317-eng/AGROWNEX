import { describe, expect, it } from 'vitest';
import { parseConfig } from './config';

const valid = {
  VITE_API_BASE_URL: 'https://api.agrowai.in/api/v1',
  VITE_FIREBASE_API_KEY: 'public-browser-key',
  VITE_FIREBASE_AUTH_DOMAIN: 'agrow-ai-8ba58.firebaseapp.com',
  VITE_FIREBASE_PROJECT_ID: 'agrow-ai-8ba58',
  VITE_FIREBASE_APP_ID: '1:261385790274:web:0123456789abcdef',
};

describe('production deployment configuration', () => {
  it('accepts a Firebase Web app id', () => {
    expect(parseConfig(valid, true).firebase.appId).toBe(valid.VITE_FIREBASE_APP_ID);
  });

  it('rejects an Android Firebase app id', () => {
    expect(() => parseConfig({
      ...valid,
      VITE_FIREBASE_APP_ID: '1:261385790274:android:2ba1c924e37cf32e269edb',
    }, true)).toThrow(/Firebase Web App ID/);
  });
});
