import { z } from 'zod';

/**
 * Validation for the Add/Edit farm form (docs: VALIDATION → crop, area, required
 * fields). Boundary and GPS location are validated separately in the editor.
 */
export const farmFormSchema = z.object({
  name: z.string().trim().min(2, { message: 'farm.errorNameRequired' }),
  crop: z.string().trim().min(1, { message: 'farm.errorCropRequired' }),
  cropVariety: z.string().trim().optional().default(''),
  sowingDate: z
    .string()
    .trim()
    .min(1, { message: 'farm.errorSowingDateRequired' })
    .refine((v) => /^\d{4}-\d{2}-\d{2}$/.test(v), {
      message: 'farm.errorDateInvalid',
    }),
  soilType: z.string().optional().default(''),
  irrigationType: z.string().optional().default(''),
  waterSource: z.string().optional().default(''),
  district: z.string().optional().default(''),
  block: z.string().trim().optional().default(''),
  village: z.string().trim().optional().default(''),
  status: z.enum(['draft', 'active', 'harvested', 'archived']).default('active'),
  notes: z.string().trim().max(2000).optional().default(''),
  areaSource: z.enum(['auto', 'manual']).default('auto'),
  areaManual: z
    .string()
    .trim()
    .optional()
    .default('')
    .transform((v) => (v === '' ? null : Number(v)))
    .refine((v) => v === null || (!Number.isNaN(v) && v > 0 && v <= 100_000), {
      message: 'farm.errorAreaInvalid',
    }),
});

export type FarmFormInput = z.input<typeof farmFormSchema>;
export type FarmFormData = z.output<typeof farmFormSchema>;
