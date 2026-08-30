const required = [
  'VITE_API_BASE_URL', 'VITE_FIREBASE_API_KEY', 'VITE_FIREBASE_AUTH_DOMAIN',
  'VITE_FIREBASE_PROJECT_ID', 'VITE_FIREBASE_APP_ID'
] as const;

export function parseConfig(env: Record<string, string | undefined>, production: boolean) {
  const missing = required.filter((key) => !env[key]?.trim());
  if (missing.length) throw new Error(`Missing deployment configuration: ${missing.join(', ')}`);
  const apiBaseUrl = env.VITE_API_BASE_URL!.replace(/\/$/, '');
  if (production && !apiBaseUrl.startsWith('https://')) {
    throw new Error('Production API URL must use HTTPS.');
  }
  if (production && !/^1:\d+:web:[a-zA-Z0-9]+$/.test(env.VITE_FIREBASE_APP_ID!)) {
    throw new Error('VITE_FIREBASE_APP_ID must be a Firebase Web App ID.');
  }
  return {
    apiBaseUrl,
    firebase: {
      apiKey: env.VITE_FIREBASE_API_KEY!, authDomain: env.VITE_FIREBASE_AUTH_DOMAIN!,
      projectId: env.VITE_FIREBASE_PROJECT_ID!, appId: env.VITE_FIREBASE_APP_ID!
    }
  };
}

export function getConfig() {
  return parseConfig(import.meta.env as Record<string, string | undefined>, import.meta.env.PROD);
}
