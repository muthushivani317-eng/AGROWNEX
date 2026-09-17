import { farmFormSchema } from '../schemas';

describe('farmFormSchema', () => {
  it('accepts a minimal valid form and applies defaults', () => {
    const result = farmFormSchema.safeParse({
      name: 'North Field',
      crop: 'paddy',
      sowingDate: '2026-06-01',
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.status).toBe('active');
      expect(result.data.areaSource).toBe('auto');
      expect(result.data.areaManual).toBeNull();
    }
  });

  it('requires a name and a crop', () => {
    const noName = farmFormSchema.safeParse({ name: 'A', crop: 'paddy' });
    expect(noName.success).toBe(false);
    const noCrop = farmFormSchema.safeParse({ name: 'North', crop: '' });
    expect(noCrop.success).toBe(false);
  });

  it('parses a manual area to a number and rejects invalid ones', () => {
    const ok = farmFormSchema.safeParse({
      name: 'North',
      crop: 'paddy',
      sowingDate: '2026-06-01',
      areaSource: 'manual',
      areaManual: '3.5',
    });
    expect(ok.success).toBe(true);
    if (ok.success) expect(ok.data.areaManual).toBe(3.5);

    const bad = farmFormSchema.safeParse({
      name: 'North',
      crop: 'paddy',
      areaManual: '-2',
    });
    expect(bad.success).toBe(false);
  });

  it('validates the sowing date format', () => {
    expect(
      farmFormSchema.safeParse({ name: 'N', crop: 'paddy', sowingDate: 'June' })
        .success,
    ).toBe(false);
    expect(
      farmFormSchema.safeParse({
        name: 'North',
        crop: 'paddy',
        sowingDate: '2026-06-01',
      }).success,
    ).toBe(true);
  });
});
