import fs from 'node:fs';
import path from 'node:path';

const source = fs.readFileSync(
  path.resolve(__dirname, '../AgDatePicker.tsx'),
  'utf8',
);

describe('AgDatePicker device-safe theme contract', () => {
  it('gives the Modal an explicit theme background and full-screen presentation', () => {
    expect(source).toContain('style={[styles.modal, { backgroundColor: colors.bg }]}');
    expect(source).toContain('presentationStyle="fullScreen"');
  });

  it('uses native static styles throughout instead of Modal className styling', () => {
    expect(source).toContain('const styles = StyleSheet.create');
    expect(source).not.toContain('className=');
    expect(source).not.toContain('<AgPressable');
  });

  it('uses explicit selected and today background colors', () => {
    expect(source).toContain('? colors.primary');
    expect(source).toContain('? `${colors.primary}1A`');
  });
});
