const fixedConnectSources = [
  "'self'",
  'https://api.agrowai.in',
  'https://*.googleapis.com',
  'https://*.firebaseio.com',
  'https://www.google.com',
  'https://www.recaptcha.net',
  'wss://*.firebaseio.com',
];

export function securityHeaders(apiUpstream = null) {
  const connectSources = [...fixedConnectSources];
  if (apiUpstream?.origin && !connectSources.includes(apiUpstream.origin)) {
    connectSources.push(apiUpstream.origin);
  }

  const contentSecurityPolicy = [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "script-src 'self' https://www.gstatic.com https://www.google.com https://www.recaptcha.net",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    `connect-src ${connectSources.join(' ')}`,
    "frame-src https://www.google.com https://recaptcha.google.com https://www.recaptcha.net https://*.firebaseapp.com",
    "worker-src 'self' blob:",
    "manifest-src 'self'",
    'upgrade-insecure-requests',
  ].join('; ');

  return {
    'Content-Security-Policy': contentSecurityPolicy,
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'no-referrer',
  };
}

export function applySecurityHeaders(response, apiUpstream = null) {
  for (const [name, value] of Object.entries(securityHeaders(apiUpstream))) {
    response.setHeader(name, value);
  }
}

export function mergeSecurityHeaders(headers, apiUpstream = null) {
  return { ...headers, ...securityHeaders(apiUpstream) };
}
