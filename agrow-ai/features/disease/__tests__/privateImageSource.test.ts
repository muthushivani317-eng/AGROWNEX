import { buildDiseaseImageSource } from '../components/DiseaseReportImage';

describe('private disease image source', () => {
  it('uses the ownership-checked endpoint with a bearer token', () => {
    const source = buildDiseaseImageSource({
      reportId: 'report/id',
      privateImageAvailable: true,
      legacyUrl: 'https://public.example/legacy.jpg',
      token: 'test-id-token',
    });
    expect(source).toEqual({
      uri: expect.stringMatching(/\/disease\/report%2Fid\/image$/),
      headers: { Authorization: 'Bearer test-id-token' },
    });
  });

  it('uses the legacy URL only while a private copy or token is unavailable', () => {
    expect(
      buildDiseaseImageSource({
        reportId: 'report-1',
        privateImageAvailable: false,
        legacyUrl: 'https://public.example/legacy.jpg',
        token: 'test-id-token',
      }),
    ).toEqual({ uri: 'https://public.example/legacy.jpg' });
  });

  it('renders nothing rather than making an unauthenticated private request', () => {
    expect(
      buildDiseaseImageSource({
        reportId: 'report-1',
        privateImageAvailable: true,
        legacyUrl: null,
        token: null,
      }),
    ).toBeNull();
  });
});
