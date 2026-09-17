import fs from 'node:fs';
import path from 'node:path';

import { en } from '@/localization/locales/en';
import { ta } from '@/localization/locales/ta';

const source = fs.readFileSync(
  path.resolve(__dirname, '../screens/DiseaseScreen.tsx'),
  'utf8',
);

describe('DiseaseScreen localization contract', () => {
  it('contains no hardcoded user-facing English JSX or string props', () => {
    expect(source.match(/>\s*[A-Za-z][^<{\r\n]*</g) ?? []).toEqual([]);
    expect(
      source.match(/\b(?:title|accessibilityLabel|explanation)="[A-Za-z][^"]*"/g) ?? [],
    ).toEqual([]);
  });

  it('does not retain manual English/Tamil UI branches', () => {
    const forbiddenEnglish = [
      'Select a crop before analysis.',
      'Sign in again before analysis.',
      'Confirm that the photo belongs to the selected crop.',
      'This crop dataset has been expert-reviewed, but its diagnosis model is not yet deployed.',
      'Disease analysis is not available for this crop yet.',
      'Analysis is already running.',
      'Verify against official source.',
      'Crop identity could not be verified.',
      'Disease analysis was safely blocked.',
      'A separate nutrient assessment may help.',
      'This is not a confirmed nutrient diagnosis.',
      'Open Nutrient Deficiency Check',
      'Continue Disease Check',
    ];
    for (const text of forbiddenEnglish) expect(source).not.toContain(text);
  });

  it('localizes every new entry-screen instruction in English and Tamil', () => {
    const keys = [
      'titleDisease', 'titleDetection', 'photoFirstTitle', 'photoFirstMessage',
      'takePhotoSubtitle', 'chooseGallerySubtitle', 'photoTipTitle', 'photoTipMessage',
    ] as const;
    for (const key of keys) {
      expect(en.disease[key]).toBeTruthy();
      expect(ta.disease[key]).toBeTruthy();
      expect(ta.disease[key]).not.toBe(en.disease[key]);
    }
  });

  it('keeps capability, fresh-photo, and typed-error keys in English/Tamil parity', () => {
    for (const key of [
      'capabilitiesLoading', 'capabilitiesUnavailable', 'retryCapabilities',
      'noCropsAvailable', 'testerRoleRequired', 'releaseNotAuthorized', 'startFreshPhoto',
    ] as const) {
      expect(en.disease[key]).toBeTruthy();
      expect(ta.disease[key]).toBeTruthy();
    }
    expect(Object.keys(ta.disease.errors).sort()).toEqual(Object.keys(en.disease.errors).sort());
    expect(en.banana.ui.startFreshPhoto).toBeTruthy();
    expect(ta.banana.ui.startFreshPhoto).toBeTruthy();
  });
});
