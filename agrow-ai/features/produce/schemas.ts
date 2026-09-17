import dayjs from 'dayjs';
import { z } from 'zod';
import { resolveProduceProduct } from './constants';

/**
 * Validation for the Create/Edit produce form (docs: BUSINESS RULES →
 * quantity > 0, harvest date >= today, crop required, farm ownership). Mirrors
 * the backend validation so the offline path validates identically.
 */
export const produceFormSchema = z.object({
  farmId: z.string().min(1, { message: 'produce.errorFarmRequired' }),
  availabilityType: z.enum(['available_now', 'upcoming_harvest']),
  category: z.enum(['grains', 'pulses', 'vegetables', 'fruits', 'spices', 'plantation_crops', 'flowers', 'other_produce']),
  productName: z.string().trim().min(1, { message: 'produce.errorProductRequired' }),
  customProductName: z.string().trim().max(80).optional().default(''),
  cropName: z.string().trim().optional().default(''),
  variety: z.string().trim().optional().default(''),
  cultivatedAreaAcres: z
    .string()
    .trim()
    .transform((v) => v === '' ? null : Number(v))
    .refine((v) => v === null || (!Number.isNaN(v) && v > 0 && v <= 1_000_000), {
      message: 'produce.errorAreaInvalid',
    }),
  expectedTotalQuantity: z
    .string()
    .trim()
    .transform((v) => v === '' ? null : Number(v))
    .refine((v) => v === null || (!Number.isNaN(v) && v > 0 && v <= 1_000_000), {
      message: 'produce.errorQuantityInvalid',
    }),
  availableQuantity: z
    .string()
    .trim()
    .min(1, { message: 'produce.errorAvailableQuantityRequired' })
    .transform((v) => Number(v))
    .refine((v) => !Number.isNaN(v) && v > 0 && v <= 1_000_000, {
      message: 'produce.errorQuantityInvalid',
    }),
  unit: z.enum(['kg', 'quintal', 'tonne', 'bag']).default('quintal'),
  expectedHarvestDate: z.string().trim().default(''),
  availableFrom: z.string().trim().min(1, { message: 'produce.errorAvailableFromRequired' })
    .refine((v) => /^\d{4}-\d{2}-\d{2}$/.test(v), { message: 'produce.errorDateInvalid' }),
  availableUntil: z.string().trim().min(1, { message: 'produce.errorAvailableUntilRequired' })
    .refine((v) => /^\d{4}-\d{2}-\d{2}$/.test(v), { message: 'produce.errorDateInvalid' }),
  expectedGrade: z
    .enum(['a', 'b', 'c', 'faq', 'mixed', 'ungraded'])
    .optional(),
  askingPrice: z
    .string()
    .trim()
    .optional()
    .default('')
    .transform((v) => (v === '' ? null : Number(v)))
    .refine((v) => v === null || (!Number.isNaN(v) && v >= 0 && v <= 10_000_000), {
      message: 'produce.errorPriceInvalid',
    }),
  priceUnit: z.enum(['kg', 'quintal', 'tonne', 'bag']),
  negotiable: z.boolean().default(false),
  packaging: z.string().trim().max(120).optional().default(''),
  pickupLocation: z.string().trim().max(160).optional().default(''),
  notes: z.string().trim().max(2000).optional().default(''),
  qualityNotes: z.string().trim().max(2000).optional().default(''),
  status: z.enum(['draft', 'submitted', 'harvested', 'withdrawn']).default('submitted'),
}).superRefine((data, ctx) => {
  const product = resolveProduceProduct(data.category, data.productName, data.customProductName);
  if (!product) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, path: [data.category === 'other_produce' ? 'customProductName' : 'productName'], message: 'produce.errorProductInvalid' });
  }
  if (data.availabilityType === 'upcoming_harvest') {
    if (!data.expectedHarvestDate) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ['expectedHarvestDate'], message: 'produce.errorHarvestRequired' });
    } else if (!/^\d{4}-\d{2}-\d{2}$/.test(data.expectedHarvestDate)) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ['expectedHarvestDate'], message: 'produce.errorDateInvalid' });
    } else if (dayjs(data.expectedHarvestDate).isBefore(dayjs().startOf('day'))) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ['expectedHarvestDate'], message: 'produce.errorHarvestPast' });
    }
  }
  if (data.expectedTotalQuantity !== null && data.availableQuantity > data.expectedTotalQuantity) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, path: ['availableQuantity'], message: 'produce.errorAvailableExceedsExpected' });
  }
  if (dayjs(data.availableUntil).isBefore(dayjs(data.availableFrom))) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, path: ['availableUntil'], message: 'produce.errorAvailabilityOrder' });
  }
});

export type ProduceFormInput = z.input<typeof produceFormSchema>;
export type ProduceFormData = z.output<typeof produceFormSchema>;
