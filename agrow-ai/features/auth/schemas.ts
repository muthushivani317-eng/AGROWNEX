import { z } from 'zod';

/** 10-digit Indian mobile (optionally with +91 / leading 0, stripped). */
export const phoneSchema = z.object({
  phone: z
    .string()
    .trim()
    .transform((v) => v.replace(/\D/g, '').slice(-10))
    .refine((v) => /^[6-9]\d{9}$/.test(v), { message: 'auth.invalidPhone' }),
});
export type PhoneForm = z.infer<typeof phoneSchema>;

export const otpSchema = z.object({
  code: z
    .string()
    .trim()
    .regex(/^\d{6}$/, { message: 'auth.invalidOtp' }),
});
export type OtpForm = z.infer<typeof otpSchema>;

/**
 * Gender and education are optional, low-sensitivity demographic fields the
 * backend has supported for a while (app.modules.auth.profile_models.FarmerProfile
 * -- see FarmerMeUpdate/FarmerMeOut) but which were never exposed in this
 * form. They replace the old `annualIncome` field: that field was collected
 * here but silently dropped by the backend (`FarmerMeUpdate` never declared
 * it), so it never actually saved anything -- removing it loses no data.
 * Financial means-testing for a specific scheme still happens, purposefully
 * and separately, in the Schemes eligibility flow (features/schemes), not as
 * a permanent profile field.
 */
export const GENDER_OPTIONS = ['male', 'female', 'other'] as const;
export const EDUCATION_OPTIONS = [
  'none',
  'primary',
  'secondary',
  'higher_secondary',
  'graduate',
] as const;

export const profileSchema = z.object({
  name: z.string().trim().min(2, { message: 'profile.nameRequired' }),
  language: z.enum(['ta', 'en']).default('ta'),
  district: z.string().trim().min(1, { message: 'profile.districtRequired' }),
  block: z.string().trim().optional().default(''),
  village: z.string().trim().optional().default(''),
  experienceYears: z
    .string()
    .trim()
    .optional()
    .default('')
    .transform((v) => (v === '' ? null : Number(v)))
    .refine((v) => v === null || (!Number.isNaN(v) && v >= 0 && v <= 80), {
      message: 'profile.experienceInvalid',
    }),
  // Plain nullable strings, not z.enum: the backend column
  // (FarmerProfile.gender/.education) is an unconstrained VARCHAR, and
  // FarmerProfile/AuthUser type these as `string | null` throughout, so a
  // strict literal-union type here would just fight the rest of the client
  // model for no validation benefit. GENDER_OPTIONS/EDUCATION_OPTIONS still
  // define the values the chip UI offers.
  gender: z.string().nullable().default(null),
  education: z.string().nullable().default(null),
  preferredCrops: z.array(z.string()).default([]),
  photoUrl: z.string().nullable().default(null),
});
export type ProfileForm = z.input<typeof profileSchema>;
export type ProfileData = z.output<typeof profileSchema>;

/** Onboarding stays short: no gender/education/income there; land holding is
 * display-only for now. */
export const completeProfileSchema = profileSchema
  .omit({ gender: true, education: true })
  .extend({
    landHoldingAcres: z
      .string()
      .trim()
      .optional()
      .default('')
      .transform((v) => (v === '' ? null : Number(v)))
      .refine((v) => v === null || (!Number.isNaN(v) && v >= 0 && v <= 1_000_000), {
        message: 'profile.landHoldingInvalid',
      }),
  });
export type CompleteProfileForm = z.input<typeof completeProfileSchema>;
export type CompleteProfileData = z.output<typeof completeProfileSchema>;
