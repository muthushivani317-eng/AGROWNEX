import { evaluateImageQuality } from '../qualityGate';

test('decode failure is rejected without diagnostic inference', () => {
  expect(evaluateImageQuality({ decoded: false, width: 0, height: 0 })).toEqual(['decode_failed']);
});

test('checks dimensions, blur, exposure, and nearly blank signals', () => {
  expect(evaluateImageQuality({
    decoded: true, width: 100, height: 100,
    luminanceMean: 2, luminanceVariance: 2, uniformPixelRatio: 0.99,
  })).toEqual([
    'dimensions_too_small', 'extreme_blur', 'extreme_exposure', 'nearly_blank',
  ]);
});

test('quality checks do not return a crop identity', () => {
  const result = evaluateImageQuality({
    decoded: true, width: 1024, height: 1024,
    luminanceMean: 120, luminanceVariance: 30, uniformPixelRatio: 0.1,
  });
  expect(result).toEqual([]);
  expect(JSON.stringify(result)).not.toMatch(/banana|rice|cotton|groundnut|chilli|redgram/);
});
