import fs from 'node:fs';
import path from 'node:path';

import { farmFormSchema, type FarmFormInput } from '../schemas';

const source = fs.readFileSync(
  path.resolve(__dirname, '../screens/FarmFormScreen.tsx'),
  'utf8',
);

describe('FarmFormScreen required-fields message', () => {
  it('uses current values and the real schema instead of partial formState errors', () => {
    expect(source).toContain('getValues, setValue');
    expect(source).toContain('const currentValues = getValues()');
    expect(source).toContain('farmFormSchema.safeParse(currentValues)');
    expect(source).not.toContain('formState.errors.name ?');
  });

  it('reports sowing date when name and crop are filled but sowing date is untouched', () => {
    const values: FarmFormInput = {
      name: 'North Field',
      crop: 'paddy',
      cropVariety: '',
      sowingDate: '',
      soilType: '',
      irrigationType: '',
      waterSource: '',
      district: '',
      block: '',
      village: '',
      status: 'active',
      notes: '',
      areaSource: 'auto',
      areaManual: '',
    };

    const result = farmFormSchema.safeParse(values);
    expect(result.success).toBe(false);
    if (result.success) return;

    const invalidRequiredFields = [
      ...new Set(
        result.error.issues
          .map((issue) => String(issue.path[0]))
          .filter((field) => ['name', 'crop', 'sowingDate'].includes(field)),
      ),
    ];

    expect(invalidRequiredFields).toEqual(['sowingDate']);
  });
});

describe('FarmFormScreen location autofill', () => {
  it('reverse geocodes GPS coordinates and fills district, block, and village', () => {
    expect(source).toContain('autofillAddressFromCoordinates(loc.latitude, loc.longitude)');
    expect(source).toContain("setValue('district', address.district");
    expect(source).toContain("setValue('block', address.block");
    expect(source).toContain("setValue('village', address.village");
  });

  it('keeps partial results and explains how to complete missing fields', () => {
    expect(source).toContain('const hasCompleteAddress = Boolean(address.district && address.block && address.village)');
    expect(source).toContain("'farm.locationAddressPartial'");
    expect(source).toContain("'farm.locationAddressUnavailable'");
  });
});

describe('FarmFormScreen current visual system', () => {
  it('uses the light field-journal palette instead of the legacy dark surface', () => {
    expect(source).toContain("const SCREEN_BG = '#F7F3E8'");
    expect(source).toContain("const SURFACE = '#FFFFFF'");
    expect(source).toContain('backgroundColor={SCREEN_BG}');
    expect(source).not.toContain("const SCREEN_BG = '#0B0E0C'");
  });

  it('pins labels and helper text to accessible colors on the fixed light background', () => {
    expect(source).toContain('labelStyle: styles.fieldLabelText');
    expect(source).toContain('hintStyle: styles.helperText');
    expect(source).toContain("fieldLabelText: { color: '#344A3D' }");
    expect(source).toContain("validationText: { color: '#C53D36' }");
    expect(source.match(/labelStyle={styles\.fieldLabelText}/g)?.length).toBeGreaterThanOrEqual(6);
  });
});

describe('FarmFormScreen async safety', () => {
  it('guards duplicate crop capture and catches camera errors', () => {
    const detection = source.slice(source.indexOf('const detectCrop ='), source.indexOf('const toOptions'));
    expect(detection).toContain('if (cropLock.current || saveLock.current) return');
    expect(detection.indexOf('try {')).toBeLessThan(detection.indexOf('await captureFromCamera'));
    expect(detection).toContain('cropLock.current = false');
  });
  it('guards save and preserves edit drafts on query refresh', () => {
    expect(source).toContain('if (saveLock.current || cropLock.current || gpsLock.current');
    expect(source).toContain('const onSettled = () => { saveLock.current = false; }');
    expect(source).toContain('seededFarm.current === farm.id');
  });
  it('bounds address lookup and keeps its loading state until completion', () => {
    expect(source).toContain('ADDRESS_TIMEOUT');
    expect(source).toContain('clearTimeout(addressTimeout)');
    expect(source).toContain('loading={locating || addressLoading}');
  });
});
