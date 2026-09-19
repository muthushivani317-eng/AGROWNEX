import { describe, expect, it, vi } from 'vitest';
import {
  applySecurityHeaders,
  mergeSecurityHeaders,
  securityHeaders,
} from './security-headers.mjs';

describe('Admin Web security headers', () => {
  it('sets HSTS and a restrictive Firebase-compatible CSP', () => {
    const headers = securityHeaders(new URL('https://api.example.test'));

    expect(headers['Strict-Transport-Security']).toBe(
      'max-age=31536000; includeSubDomains',
    );
    expect(headers['Content-Security-Policy']).toContain("default-src 'self'");
    expect(headers['Content-Security-Policy']).toContain("object-src 'none'");
    expect(headers['Content-Security-Policy']).toContain("frame-ancestors 'none'");
    expect(headers['Content-Security-Policy']).toContain('https://*.firebaseapp.com');
    expect(headers['Content-Security-Policy']).toContain('https://api.example.test');
    expect(headers['Content-Security-Policy']).not.toContain("script-src 'unsafe-inline'");
  });

  it('applies headers to static and local error responses', () => {
    const response = { setHeader: vi.fn() };

    applySecurityHeaders(response);

    expect(response.setHeader).toHaveBeenCalledWith(
      'Strict-Transport-Security',
      'max-age=31536000; includeSubDomains',
    );
    expect(response.setHeader).toHaveBeenCalledWith(
      'Content-Security-Policy',
      expect.stringContaining("default-src 'self'"),
    );
  });

  it('does not let proxied upstream responses weaken security headers', () => {
    const headers = mergeSecurityHeaders({
      'Content-Security-Policy': "default-src *",
      'Strict-Transport-Security': 'max-age=0',
      'content-type': 'application/json',
    });

    expect(headers['Content-Security-Policy']).toContain("default-src 'self'");
    expect(headers['Strict-Transport-Security']).toBe(
      'max-age=31536000; includeSubDomains',
    );
    expect(headers['content-type']).toBe('application/json');
  });
});
