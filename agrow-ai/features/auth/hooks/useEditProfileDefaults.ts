import { useQuery } from '@tanstack/react-query';

import type { ApiFarmerMe } from '@/features/profile/types';
import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

import type { CompleteProfileForm } from '../schemas';

/** Raw farmer record for Edit profile (the mapped profile model drops the
 * onboarding fields: farm products, farmer type, GPS, FPO/KVK interest). */
export const EDIT_PROFILE_KEY = ['profile', 'me', 'raw'] as const;

const FARMER_TYPE_TO_FORM: Record<string, 'small' | 'tenant' | 'producer'> = {
  small: 'small',
  small_farmer: 'small',
  tenant: 'tenant',
  tenant_farmer: 'tenant',
  producer: 'producer',
  farm_producer: 'producer',
};

const UNITS = ['kg', 'quintal', 'tonne', 'bag', 'count', 'litre'] as const;
type Unit = (typeof UNITS)[number];

const toUnit = (unit: string | null | undefined): Unit =>
  (UNITS as readonly string[]).includes(unit ?? '') ? (unit as Unit) : unit === 'nos' || unit === 'head' ? 'count' : 'kg';

const numberText = (value: number | null | undefined) => (value == null ? '' : String(value));

/** Saved farmer record -> Complete-profile form values (edit mode pre-fill). */
export function farmerToProfileForm(me: ApiFarmerMe, fallbackLanguage: 'ta' | 'en'): CompleteProfileForm {
  return {
    name: me.full_name ?? '',
    language: me.language === 'en' || me.language === 'ta' ? me.language : fallbackLanguage,
    district: me.district ?? '',
    block: me.block ?? '',
    village: me.village ?? '',
    experienceYears: numberText(me.experience_years),
    landHoldingAcres: numberText(me.land_holding_acres),
    preferredCrops: me.preferred_crops ?? [],
    photoUrl: me.profile_photo ?? null,
    farmerType: me.farmer_type ? FARMER_TYPE_TO_FORM[me.farmer_type] ?? null : null,
    landmark: me.landmark ?? '',
    latitude: me.latitude ?? null,
    longitude: me.longitude ?? null,
    farmProducts: (me.farm_products ?? []).map((p) => ({
      productId: p.product_id,
      category: p.category === 'other_products' ? 'other' : p.category,
      expectedHarvestMonth: p.expected_harvest_month,
      approximateQuantity: p.approximate_quantity,
      unit: toUnit(p.unit),
      availableForSale: p.available_for_sale,
    })),
    wantsFpoSupport: Boolean(me.wants_fpo_support),
    wantsKvkSupport: Boolean(me.wants_kvk_support),
  };
}

export function useEditProfileDefaults(enabled: boolean) {
  return useQuery({
    queryKey: EDIT_PROFILE_KEY,
    enabled,
    queryFn: () => api.get<ApiFarmerMe>(endpoints.farmers.me),
    staleTime: 0,
  });
}
