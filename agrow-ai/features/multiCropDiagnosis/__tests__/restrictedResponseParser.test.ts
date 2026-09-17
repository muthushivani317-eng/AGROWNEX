import { parseRestrictedCropDiagnosisResponse } from '../responseParser';

const base = {
  crop_id: 'redgram',
  restricted_runtime: true,
  field_validated: false,
  recommendation_available: false,
  official_accuracy_claim: false,
  runtime_id: 'redgram_mobilenetv3_small_v1_restricted',
  confidence: 0.82,
  margin: 0.21,
  test_mode: {
    active: true,
    code: 'RESTRICTED_CROP_CONTROLLED_TEST',
    display_required: true,
    banner_text: 'TEST MODE — NOT AUTHORIZED FOR GENERAL RELEASE — RESULT NOT VALIDATED',
  },
};

test('accepted Redgram response preserves an approved exact label', () => {
  expect(parseRestrictedCropDiagnosisResponse(
    { ...base, status: 'accepted', predicted_label: 'redgram__sterility_mosaic' },
    'redgram',
    ['redgram__healthy', 'redgram__leaf_spot', 'redgram__sterility_mosaic'],
  )).toMatchObject({
    outcome: 'accepted',
    class_id: 'redgram__sterility_mosaic',
    accepted: true,
    calibrated_confidence: 0.82,
    margin: 0.21,
    test_mode: base.test_mode,
  });
});

test('Redgram leaf-spot abstention never renders a diagnosis', () => {
  expect(parseRestrictedCropDiagnosisResponse(
    { ...base, status: 'abstained', predicted_label: 'redgram__leaf_spot' },
    'redgram',
    ['redgram__healthy', 'redgram__leaf_spot', 'redgram__sterility_mosaic'],
  )).toMatchObject({ outcome: 'uncertain', class_id: null, accepted: false });
});

test('unknown Chilli label fails closed', () => {
  expect(parseRestrictedCropDiagnosisResponse(
    {
      ...base,
      crop_id: 'chilli',
      runtime_id: 'chilli_mobilenetv3_small_v1_restricted',
      status: 'accepted',
      predicted_label: 'chilli__cercospora',
    },
    'chilli',
    [
      'chilli__bacterial_spot',
      'chilli__cercospora_leaf_spot',
      'chilli__healthy',
      'chilli__leaf_curl_virus',
    ],
  )).toMatchObject({ outcome: 'blocked', status: 'malformed_response' });
});

test.each(['runtime_error', 'abstained'])('%s remains non-diagnostic', (status) => {
  expect(parseRestrictedCropDiagnosisResponse(
    { ...base, status, predicted_label: null },
    'redgram',
    ['redgram__healthy', 'redgram__leaf_spot', 'redgram__sterility_mosaic'],
  ).outcome).not.toBe('accepted');
});

test('runtime_error with null confidence and margin maps to model unavailable', () => {
  expect(parseRestrictedCropDiagnosisResponse(
    {
      ...base,
      status: 'runtime_error',
      predicted_label: null,
      confidence: null,
      margin: null,
      abstention_code: 'MODEL_INTEGRITY_OR_RUNTIME_FAILURE',
    },
    'redgram',
    ['redgram__healthy', 'redgram__leaf_spot', 'redgram__sterility_mosaic'],
  )).toMatchObject({
    outcome: 'blocked',
    status: 'model_load_failed',
    message: 'The restricted diagnosis runtime is unavailable.',
  });
});
