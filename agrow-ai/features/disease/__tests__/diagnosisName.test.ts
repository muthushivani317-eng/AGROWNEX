import { formatDiagnosisName } from '../utils/diagnosisName';

describe('saved diagnosis display names', () => {
  it('removes the model crop prefix and formats the disease identifier', () => {
    expect(formatDiagnosisName('banana__sigatoka_leaf_spot')).toBe('Sigatoka Leaf Spot');
  });
  it('preserves readable and Tamil names', () => {
    expect(formatDiagnosisName('Leaf spot')).toBe('Leaf spot');
    expect(formatDiagnosisName('இலைப்புள்ளி')).toBe('இலைப்புள்ளி');
  });
  it('does not invent names for missing results', () => {
    expect(formatDiagnosisName(null)).toBeNull();
    expect(formatDiagnosisName('')).toBeNull();
    expect(formatDiagnosisName('banana__')).toBeNull();
  });
});
