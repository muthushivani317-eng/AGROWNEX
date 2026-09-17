import { COMMON_CROPS } from '@/constants/crops';

const CROP_ALIASES: Record<string, string> = {
  rice: 'paddy',
  peanut: 'groundnut',
  'ground nut': 'groundnut',
  corn: 'maize',
  'chili pepper': 'chilli',
  chili: 'chilli',
  pepper: 'chilli',
  eggplant: 'brinjal',
  aubergine: 'brinjal',
};

function normalize(name: string): string {
  return name.trim().toLowerCase();
}

export function matchCropId(commonName: string | null): string | null {
  if (!commonName) return null;
  const normalized = normalize(commonName);
  const aliased = CROP_ALIASES[normalized];
  if (aliased) return aliased;
  const direct = COMMON_CROPS.find(
    (crop) => normalize(crop.en) === normalized || normalize(crop.id) === normalized,
  );
  if (direct) return direct.id;
  const partial = COMMON_CROPS.find(
    (crop) =>
      normalized.includes(normalize(crop.en)) || normalize(crop.en).includes(normalized),
  );
  return partial?.id ?? null;
}
