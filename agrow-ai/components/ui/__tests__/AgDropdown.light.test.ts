import fs from 'node:fs';
import path from 'node:path';

const source = fs.readFileSync(path.resolve(__dirname, '..', 'AgDropdown.tsx'), 'utf8');

describe('AgDropdown fixed-light presentation contract', () => {
  it('keeps fixed-light forms and modal choices readable in every app theme', () => {
    expect(source).toContain('light?: boolean');
    expect(source).toContain("bg: '#F8F5E9'");
    expect(source).toContain("surface: '#FFFDF8'");
    expect(source).toContain("text: '#173B2B'");
    expect(source).toContain('contentContainerStyle={styles.listContent}');
    expect(source).toContain('<TouchableOpacity');
    expect(source).toContain('accessibilityRole="radio"');
    expect(source).toContain('accessibilityState={{ checked: isSel }}');
    expect(source).toContain("accessibilityLabel={t('common.close')}");
    expect(source).toContain('accessibilityLabel={placeholder}');
    expect(source).toContain('minHeight: 64');
  });
});
