import type { Procurement } from './types';

export type ProcurementFilters = {
  search: string;
  category: string;
  availabilityType: string;
};

const categoryLabels: Record<string, string> = {
  grains: 'Grains',
  pulses: 'Pulses',
  vegetables: 'Vegetables',
  fruits: 'Fruits',
  spices: 'Spices',
  plantation_crops: 'Plantation crops',
  flowers: 'Flowers',
  other_produce: 'Other produce',
};

export const produceCategories = Object.entries(categoryLabels);

export function buildProcurementPath(filters: ProcurementFilters): string {
  const query = new URLSearchParams({ page: '1', page_size: '50' });
  const search = filters.search.trim();
  if (search) query.set('search', search);
  if (filters.category) query.set('category', filters.category);
  if (filters.availabilityType) query.set('availability_type', filters.availabilityType);
  return `/admin/procurement?${query.toString()}`;
}

const titleCase = (value: string) => value.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase());

export function marketplaceProductLabel(listing: Procurement): string {
  const product = listing.crop ?? 'Unnamed produce';
  const category = listing.product_category;
  return category ? `${product} · ${categoryLabels[category] ?? titleCase(category)}` : product;
}

export function marketplaceAvailabilityLabel(listing: Procurement): string {
  if (listing.availability_type === 'available_now') return 'Available now';
  if (listing.availability_type === 'upcoming_harvest') return 'Upcoming harvest';
  return listing.harvest_date ? 'Upcoming harvest' : 'Not specified';
}

export function marketplaceFarmerReference(listing: Procurement): string {
  return listing.farmer_ref ?? 'Reference unavailable';
}

export function marketplacePickupLabel(listing: Procurement): string {
  if (listing.pickup_available === false) return 'Not offered';
  if (listing.pickup_available || listing.pickup_location) return 'Available';
  return 'Not provided';
}

export function marketplacePriceLabel(listing: Procurement): string {
  const price = listing.asking_price == null
    ? 'Not provided'
    : `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(listing.asking_price)}${listing.price_unit ? ` / ${listing.price_unit}` : ''}`;
  return listing.negotiable ? `${price} · Negotiable` : price;
}
