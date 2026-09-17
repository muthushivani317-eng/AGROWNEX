import fs from 'fs';
import path from 'path';

const farmFormPath = path.resolve(__dirname, '../../../features/farm/screens/FarmFormScreen.tsx');

describe('shared crop selector consumers', () => {
  const source = fs.readFileSync(farmFormPath, 'utf8');

  it('uses one shared selector for the combined Add/Edit Farm form', () => {
    expect(source).toContain('AgCropDropdown');
    expect(source).toContain('const isEdit = Boolean(farmId)');
    expect(source).toMatch(/crop:\s*farm\.crop\s*\?\?\s*['\"]{2}/);
  });

  it('preserves photo detection matching and confirmation into the same canonical field', () => {
    expect(source).toContain('matchCropId(result.common_name)');
    expect(source).toContain('COMMON_CROPS.find');
    expect(source).toMatch(/setValue\(['\"]crop['\"],\s*cropSuggestion\.matchedId/);
  });
});
