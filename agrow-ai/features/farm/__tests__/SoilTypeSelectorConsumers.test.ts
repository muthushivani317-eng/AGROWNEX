import fs from 'node:fs';
import path from 'node:path';

const farmForm = fs.readFileSync(
  path.resolve(__dirname, '../screens/FarmFormScreen.tsx'),
  'utf8',
);

describe('soil selector consumers', () => {
  it('reuses the shared selector for the common Add/Edit Farm form', () => {
    expect(farmForm).toContain('AgSoilTypeDropdown');
    expect(farmForm).toContain('export function FarmFormScreen({ farmId }');
    expect(farmForm).toContain('const isEdit = Boolean(farmId)');
  });

  it('derives selector options from the canonical SOIL_TYPES dataset', () => {
    expect(farmForm).toContain('const soilOptions = SOIL_TYPES.map');
    expect(farmForm).toContain('options={soilOptions}');
    expect(farmForm).not.toMatch(/const\s+SOIL_TYPES\s*=/);
  });
});
