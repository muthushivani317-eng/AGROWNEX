import { describe, expect, it } from 'vitest';
import { resolveRequestPath } from './server.mjs';

describe('Admin Web static server', () => {
  it('rejects malformed URL escapes instead of crashing', () => {
    expect(resolveRequestPath('/%E0%A4%A')).toBeNull();
    expect(resolveRequestPath('/assets/app.js')).toBe('/assets/app.js');
  });
});
