import { describe, expect, it } from 'vitest';
import { navigation } from './navigation';

describe('admin navigation permission contract', () => {
  it('requires an explicit backend permission for every section', () => {
    expect(navigation.every(item => Boolean(item.permission))).toBe(true);
  });

  it('keeps owner team management behind manage_admins', () => {
    expect(navigation.find(item => item.to === '/team')?.permission).toBe('manage_admins');
  });

  it('does not expose any farmer-facing route', () => {
    expect(navigation.some(item => item.to.includes('farmer-app'))).toBe(false);
  });
});
