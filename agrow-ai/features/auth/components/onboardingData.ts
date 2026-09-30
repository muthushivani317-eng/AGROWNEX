export interface LocalizedCatalogLabel {
  code: string;
  en: string;
  ta: string;
}

export interface OnboardingProductOption extends LocalizedCatalogLabel {
  category: string;
  default_unit: 'kg' | 'quintal' | 'tonne' | 'bag' | 'litre' | 'nos' | 'head';
}

export interface FarmCatalog {
  version: number;
  categories: LocalizedCatalogLabel[];
  items: OnboardingProductOption[];
  other_code: string;
  units: LocalizedCatalogLabel[];
  farmer_types: LocalizedCatalogLabel[];
  needs: LocalizedCatalogLabel[];
  months: string[];
}

export function productLabel(
  items: OnboardingProductOption[],
  id: string,
  language: 'ta' | 'en',
): string {
  return items.find((product) => product.code === id)?.[language] ?? id;
}

export function toFormUnit(unit: OnboardingProductOption['default_unit']) {
  return unit === 'nos' || unit === 'head' ? 'count' as const : unit;
}
