import {
  canUseFrozenDiseaseModel,
  cropCapability,
  CROP_CAPABILITIES,
  normalizeCropId,
} from '../cropCapabilities';

test('banana remains available with its evidence-backed provider', () => {
  expect(cropCapability('banana')).toMatchObject({
    datasetVerificationStatus: 'EXPERT_VERIFIED',
    diseaseModelStatus: 'DEPLOYED_RESEARCH_ONLY',
    diseaseModelAvailable: false,
    diagnosisStatus: 'AVAILABLE_FIELD_VALIDATION_IN_PROGRESS',
    requiresUserCropConfirmation: true,
    hasTrainedCropConfirmationGate: false,
  });
});

test('static metadata never authorizes a runtime', () => {
  for (const crop of ['banana', 'rice', 'cotton', 'groundnut', 'chilli', 'redgram']) {
    expect(canUseFrozenDiseaseModel(crop)).toBe(false);
  }
});

test.each([
  ['paddy', 'rice'],
  ['Paddy', 'rice'],
  ['Rice', 'rice'],
  [' paddy_rice ', 'rice'],
  ['Paddy (Rice)', 'rice'],
  ['நெல்', 'rice'],
  ['Cotton', 'cotton'],
  ['Groundnut', 'groundnut'],
])('normalizes crop alias %s to canonical id %s', (input, expected) => {
  expect(normalizeCropId(input)).toBe(expected);
});

test.each(['blackgram', 'maize'])(
  'crop %s cannot use a model without complete release evidence',
  (crop) => expect(canUseFrozenDiseaseModel(crop)).toBe(false),
);

test.each([
  ['blackgram', 'DATASET_UNRESOLVED'],
  ['coconut', 'MODEL_NOT_COMPLETED'],
])('status for %s cannot be promoted by a dropdown entry', (crop, status) => {
  expect(cropCapability(crop)?.diagnosisStatus).toBe(status);
  expect(cropCapability(crop)?.diseaseModelAvailable).toBe(false);
});

test.each(['chilli', 'redgram'])(
  '%s exposes only a restricted internal-testing runtime',
  (crop) => {
    expect(canUseFrozenDiseaseModel(crop)).toBe(false);
    expect(cropCapability(crop)).toMatchObject({
      diagnosisStatus: 'RESTRICTED_INTERNAL_TESTING_ONLY',
      diseaseModelStatus: 'DEPLOYED_RESEARCH_ONLY',
      diseaseModelAvailable: false,
      productionApproved: false,
    });
  },
);

test.each(['rice', 'cotton', 'groundnut'])(
  '%s remains audit-blocked in static metadata',
  (crop) => {
    expect(cropCapability(crop)).toMatchObject({
      diagnosisStatus: 'LEGACY_JOINT_MODEL_AUDIT_REQUIRED',
      diseaseModelStatus: 'DEPLOYED_RESEARCH_ONLY',
      diseaseModelAvailable: false,
      fieldValidationStatus: 'IN_PROGRESS',
      productionApproved: false,
    });
  },
);

test('production approval remains independent and false', () => {
  expect(Object.values(CROP_CAPABILITIES).every((item) => !item.productionApproved)).toBe(true);
});
