const required = [
  'VITE_API_BASE_URL', 'VITE_FIREBASE_API_KEY', 'VITE_FIREBASE_AUTH_DOMAIN',
  'VITE_FIREBASE_PROJECT_ID', 'VITE_FIREBASE_APP_ID'
] as const;

export function getConfig() {
  const env = import.meta.env as Record<string, string | undefined>;
  const missing = required.filter((key) => !env[key]?.trim());
  if (missing.length) throw new Error(`Missing deployment configuration: ${missing.join(', ')}`);
  const apiBaseUrl = env.VITE_API_BASE_URL!.replace(/\/$/, '');
  if (import.meta.env.PROD && !apiBaseUrl.startsWith('https://')) {
    throw new Error('Production API URL must use HTTPS.');
  }
  return {
    apiBaseUrl,
    firebase: {
      apiKey: env.VITE_FIREBASE_API_KEY!, authDomain: env.VITE_FIREBASE_AUTH_DOMAIN!,
      projectId: env.VITE_FIREBASE_PROJECT_ID!, appId: env.VITE_FIREBASE_APP_ID!
    }
  };
}
