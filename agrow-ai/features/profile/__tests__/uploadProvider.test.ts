import { uploadService } from '../services/uploadProvider';

// With no EXPO_PUBLIC_S3_UPLOAD_ENDPOINT configured (the default in tests), the
// service uses the local mock, which keeps the on-device URI as the stored ref.
describe('uploadService (mock provider)', () => {
  it('returns the local uri when S3 is not configured', async () => {
    const uri = 'file:///data/user/0/agrowai/cache/photo-123.jpg';
    const url = await uploadService.uploadImage(uri);
    expect(url).toBe(uri);
  });

  it('accepts a folder argument without changing the mock result', async () => {
    const uri = 'file:///tmp/leaf.png';
    const url = await uploadService.uploadImage(uri, 'profiles');
    expect(url).toBe(uri);
  });
});
