import fs from 'node:fs';
import path from 'node:path';

const screen = fs.readFileSync(path.resolve(__dirname, '..', 'PlantIdentifierScreen.tsx'), 'utf8');
const api = fs.readFileSync(path.resolve(__dirname, '..', 'plantIdentifierApi.ts'), 'utf8');

describe('Plant Identifier redesign contract', () => {
  it('uses the existing photo and identification flows with the active language', () => {
    expect(screen).toContain("captureFromCamera({ base64: false })");
    expect(screen).toContain("pickFromGallery({ base64: false })");
    expect(screen).toContain('identifyPlant({ ...picked, preferredLanguage:');
    expect(screen).toContain("onPress={() => void pick('camera')}");
  });

  it('renders only real result fields and never fabricates confidence', () => {
    expect(screen).toContain('result.common_name');
    expect(screen).toContain('result.scientific_name');
    expect(screen).toContain('result.family');
    expect(screen).toContain('result.description');
    expect(screen).toContain('result.visible_characteristics');
    expect(screen).toContain('Number.isFinite(result.confidence)');
  });

  it('keeps uncertainty and disease-routing safety invariants', () => {
    expect(screen).toContain("result?.status === 'uncertain'");
    expect(screen).toContain("result?.status === 'non_plant'");
    expect(api).toContain('used_for_disease_routing !== false');
    expect(api).toContain('disease_inference_available !== false');
    expect(screen).not.toContain('Continue to Disease Detection');
  });

  it('retains the real journal and localized safety disclaimer', () => {
    expect(screen).toContain("router.push('/plant-identifier/journal'");
    expect(screen).toContain('plantJournalStorage.add');
    expect(screen).toContain("t('plantIdentifier.disclaimer')");
  });

  it('guards image selection and exposes retry plus reset recovery', () => {
    expect(screen).toContain('pickLock.current');
    expect(screen).toContain("setStatus('capture_error')");
    expect(screen).toContain("plantIdentifier.photoAccessFailed");
    expect(screen).toContain("plantIdentifier.startOver");
    expect(screen).toContain("plantIdentifier.journalSaveFailed");
  });
});
