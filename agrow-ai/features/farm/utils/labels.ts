import { COMMON_CROPS } from '@/constants/crops';
import { TAMIL_NADU_DISTRICTS } from '@/constants/locations';

/** Resolve a crop id to its localized label (falls back to the raw id). */
export function cropLabel(id: string | null, tamil: boolean): string | null {
  if (!id) return null;
  const crop = COMMON_CROPS.find((c) => c.id === id);
  return crop ? (tamil ? crop.ta : crop.en) : id;
}

/** Resolve a district id to its localized label. */
export function districtLabel(id: string | null, tamil: boolean): string | null {
  if (!id) return null;
  const district = TAMIL_NADU_DISTRICTS.find((d) => d.id === id);
  return district ? (tamil ? district.ta : district.en) : id;
}
