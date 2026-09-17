import { completeProfileSchema, otpSchema, phoneSchema, profileSchema } from '../schemas';

describe('phoneSchema', () => {
  it('accepts and normalises a valid 10-digit mobile', () => {
    const result = phoneSchema.safeParse({ phone: '+91 98765 43210' });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.phone).toBe('9876543210');
  });

  it('rejects numbers that do not start 6-9', () => {
    expect(phoneSchema.safeParse({ phone: '1234567890' }).success).toBe(false);
  });

  it('rejects short numbers', () => {
    expect(phoneSchema.safeParse({ phone: '98765' }).success).toBe(false);
  });
});

describe('otpSchema', () => {
  it('accepts a 6-digit code', () => {
    expect(otpSchema.safeParse({ code: '123456' }).success).toBe(true);
  });

  it('rejects non-numeric or wrong-length codes', () => {
    expect(otpSchema.safeParse({ code: '12a456' }).success).toBe(false);
    expect(otpSchema.safeParse({ code: '12345' }).success).toBe(false);
  });
});

describe('profileSchema', () => {
  it('requires a name and district', () => {
    expect(profileSchema.safeParse({ name: 'A', district: '' }).success).toBe(false);
  });

  it('coerces empty numeric profile fields to null and passes with valid data', () => {
    const result = profileSchema.safeParse({
      name: 'Muthu Kumar',
      district: 'madurai',
      experienceYears: '',
      preferredCrops: ['paddy'],
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.experienceYears).toBeNull();
      expect(result.data.gender).toBeNull();
      expect(result.data.education).toBeNull();
      expect(result.data.preferredCrops).toEqual(['paddy']);
    }
  });

  it('rejects an out-of-range experience value', () => {
    const result = profileSchema.safeParse({
      name: 'Muthu',
      district: 'madurai',
      experienceYears: '120',
    });
    expect(result.success).toBe(false);
  });

  it('accepts an optional gender and education', () => {
    const result = profileSchema.safeParse({
      name: 'Muthu',
      district: 'madurai',
      gender: 'female',
      education: 'graduate',
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.gender).toBe('female');
      expect(result.data.education).toBe('graduate');
    }
  });
});

describe('completeProfileSchema', () => {
  it('coerces an empty land holding to null', () => {
    const result = completeProfileSchema.safeParse({
      name: 'Muthu Kumar',
      district: 'madurai',
      landHoldingAcres: '',
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.landHoldingAcres).toBeNull();
  });

  it('rejects an out-of-range land holding', () => {
    expect(completeProfileSchema.safeParse({
      name: 'Muthu',
      district: 'madurai',
      landHoldingAcres: '1000001',
    }).success).toBe(false);
  });
});
