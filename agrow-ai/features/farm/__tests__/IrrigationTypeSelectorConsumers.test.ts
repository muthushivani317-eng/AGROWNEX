import fs from 'node:fs';
import path from 'node:path';

const farmForm = fs.readFileSync(
  path.resolve(__dirname, '../screens/FarmFormScreen.tsx'),
  'utf8',
);

describe('irrigation selector consumers', () => {
  it('uses the shared selector in the common Add/Edit Farm form', () => {
    expect(farmForm).toContain('AgIrrigationTypeDropdown');
    expect(farmForm).toContain('export function FarmFormScreen({ farmId }');
    expect(farmForm).toContain('const isEdit = Boolean(farmId)');
  });

  it('derives options only from canonical IRRIGATION_TYPES', () => {
    expect(farmForm).toContain('const irrigationOptions = IRRIGATION_TYPES.map');
    expect(farmForm).toContain('options={irrigationOptions}');
    expect(farmForm).not.toMatch(/const\s+IRRIGATION_TYPES\s*=/);
  });
});
