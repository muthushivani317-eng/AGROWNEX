import { Linking } from 'react-native';

import { isSafeExternalUrl, openExternalUrl } from '../safeLinks';

describe('safeLinks', () => {
  it('allows only plain https links', () => {
    expect(isSafeExternalUrl('https://agritech.tnau.ac.in/x')).toBe(true);
    expect(isSafeExternalUrl('HTTPS://www.agrowai.in/privacy?lang=ta')).toBe(true);
    expect(isSafeExternalUrl('https://example.org/a?t=1:2&b=x@y')).toBe(true);
    expect(isSafeExternalUrl('https://api.example.org:8443')).toBe(true);
    for (const bad of [
      'http://example.com',
      'javascript:alert(1)',
      'intent://scan/#Intent;scheme=zxing;end',
      'file:///data/data/com.agrowai.app/files/x',
      'agrowai://admin',
      'https://user:pass@evil.example',
      'https://good.example@evil.example/',
      'https://exa mple.org',
      'https://example.org/\nx',
      '',
      null,
      undefined,
    ]) {
      expect(isSafeExternalUrl(bad)).toBe(false);
    }
  });

  it('never hands an unsafe link to the OS', async () => {
    const open = jest.spyOn(Linking, 'openURL').mockResolvedValue(true);
    await expect(openExternalUrl('intent://x#Intent;end')).resolves.toBe(false);
    expect(open).not.toHaveBeenCalled();
    await expect(openExternalUrl('https://www.agrowai.in/privacy')).resolves.toBe(true);
    expect(open).toHaveBeenCalledWith('https://www.agrowai.in/privacy');
  });
});
