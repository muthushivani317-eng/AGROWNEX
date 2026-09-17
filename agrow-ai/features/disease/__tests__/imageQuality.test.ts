import { MIN_IMAGE_BYTES } from '../constants';
import { checkImageQuality } from '../utils/imageQuality';

const good = {
  width: 800,
  height: 800,
  fileSize: MIN_IMAGE_BYTES + 5000,
  mimeType: 'image/jpeg',
};

describe('checkImageQuality', () => {
  it('accepts a good image', () => {
    expect(checkImageQuality(good)).toEqual({ ok: true, issues: [] });
  });

  it('flags low resolution', () => {
    const r = checkImageQuality({ ...good, width: 100, height: 800 });
    expect(r.ok).toBe(false);
    expect(r.issues).toContain('too_small');
  });

  it('flags file size bounds', () => {
    expect(checkImageQuality({ ...good, fileSize: 500 }).issues).toContain('too_small');
    expect(
      checkImageQuality({ ...good, fileSize: 50 * 1024 * 1024 }).issues,
    ).toContain('too_large');
  });

  it('flags unsupported formats', () => {
    expect(checkImageQuality({ ...good, mimeType: 'image/gif' }).issues).toContain(
      'unsupported_type',
    );
  });

  it('de-duplicates issues', () => {
    // tiny fileSize AND tiny dimensions both map to too_small ⇒ once.
    const r = checkImageQuality({ width: 10, height: 10, fileSize: 5, mimeType: 'image/jpeg' });
    expect(r.issues.filter((i) => i === 'too_small')).toHaveLength(1);
  });
});
