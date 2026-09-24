/**
 * Sell My Produce — Procurement Intelligence domain types
 * (docs/API_CONTRACT.md → PRODUCE). This is NOT a marketplace: farmers do not
 * sell directly and no transactions happen here. The module collects verified
 * future-harvest information for procurement planning. Market prices come only
 * from verified sources and are never fabricated (docs/PRODUCT_RULES.md).
 *
 * Client-side camelCase mirror of the backend produce schemas.
 */

export type ProduceUnit = 'kg' | 'quintal' | 'tonne' | 'bag';
export type ProduceAvailabilityType = 'available_now' | 'upcoming_harvest';
export type ProduceCategory =
  | 'grains' | 'pulses' | 'vegetables' | 'fruits'
  | 'spices' | 'plantation_crops' | 'flowers' | 'other_produce';

export type ProduceGrade = 'a' | 'b' | 'c' | 'faq' | 'mixed' | 'ungraded';

export type ProduceStatus =
  | 'draft'
  | 'submitted'
  | 'planned'
  | 'harvested'
  | 'fulfilled'
  | 'withdrawn'
  | 'expired';

export type HarvestWindow = 'overdue' | 'this_week' | 'this_month' | 'later';

export type ProduceView = 'all' | 'available' | 'upcoming' | 'history';

export type SyncStatus = 'synced' | 'pending';

export interface PriceReference {
  modalPrice: number;
  minimumPrice: number;
  maximumPrice: number;
  unit: string;
  source: string;
  priceDate: string;
  market: string | null;
  district: string | null;
}

export interface ProcurementInsight {
  daysToHarvest: number;
  harvestWindow: HarvestWindow;
  quantityKg: number | null;
  estimatedMarketValue: number | null;
  estimatedAskingValue: number | null;
  priceReference: PriceReference | null;
}

export interface ProduceImage {
  id: string;
  imageUrl: string;
  thumbnailUrl: string | null;
  mimeType: string | null;
  caption: string | null;
  displayOrder: number;
  createdAt: string;
}

export interface StatusHistory {
  id: string;
  oldStatus: string | null;
  newStatus: string;
  note: string | null;
  createdAt: string;
}

export interface ProduceOffer {
  id: string;
  listingRef?: string;
  farmId: string;
  cropName: string;
  availabilityType: ProduceAvailabilityType;
  category: ProduceCategory;
  productName: string;
  customProductName: string | null;
  variety: string | null;
  quantity: number;
  unit: ProduceUnit;
  cultivatedAreaHectares: number | null;
  expectedTotalQuantity: number | null;
  availableQuantity: number | null;
  quantityProvenance: 'farmer_reported' | null;
  qualityNotes: string | null;
  expectedHarvestDate: string | null;
  expectedGrade: ProduceGrade | null;
  askingPrice: number | null;
  priceUnit: ProduceUnit | null;
  negotiable: boolean;
  packaging: string | null;
  currency: string;
  currentMarketPriceSnapshot: number | null;
  district: string | null;
  status: ProduceStatus;
  thumbnailUrl: string | null;
  imageCount: number;
  insight: ProcurementInsight | null;
  // Real, admin-verified organic certification status for this offer's farm
  // (never a farmer self-claim -- see backend OrganicFarmProfile.certification_status).
  // null when the farm has no organic profile at all.
  organicCertificationStatus: string | null;
  organicCertificationVerified: boolean;
  createdAt: string;
  updatedAt: string;
  // Client-only: 'pending' while a mutation is queued in the offline outbox.
  syncStatus?: SyncStatus;
}

export interface ProduceOfferDetail extends ProduceOffer {
  block: string | null;
  village: string | null;
  latitude: number | null;
  longitude: number | null;
  availableFrom: string | null;
  availableUntil: string | null;
  marketPriceSource: string | null;
  marketPriceDate: string | null;
  procurementChannel: string | null;
  procurementReference: string | null;
  notes: string | null;
  pickupLocation: string | null;
  images: ProduceImage[];
  statusHistory: StatusHistory[];
}

export interface ProduceImageInput {
  imageUrl: string;
  thumbnailUrl?: string | null;
  mimeType?: string | null;
  fileSize?: number | null;
  caption?: string | null;
}

export interface ProduceInput {
  farmId: string;
  cropName: string;
  availabilityType?: ProduceAvailabilityType;
  category?: ProduceCategory;
  productName?: string;
  customProductName?: string | null;
  variety?: string | null;
  quantity: number;
  unit: ProduceUnit;
  cultivatedAreaAcres?: number | null;
  expectedTotalQuantity?: number | null;
  availableQuantity?: number | null;
  qualityNotes?: string | null;
  expectedHarvestDate?: string | null;
  expectedGrade?: ProduceGrade | null;
  askingPrice?: number | null;
  priceUnit?: ProduceUnit | null;
  negotiable?: boolean;
  packaging?: string | null;
  pickupLocation?: string | null;
  currency?: string;
  availableFrom?: string | null;
  availableUntil?: string | null;
  district?: string | null;
  block?: string | null;
  village?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  notes?: string | null;
  status?: ProduceStatus;
  images?: ProduceImageInput[];
}

export interface ProduceListParams {
  status?: ProduceStatus | null;
  crop?: string | null;
  availabilityType?: ProduceAvailabilityType | null;
  category?: ProduceCategory | null;
  farmId?: string | null;
  search?: string | null;
  organicOnly?: boolean;
  page?: number;
  pageSize?: number;
}

export interface ProduceListResult {
  items: ProduceOffer[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  cached?: boolean;
}

export interface FrozenBuyerOffer {
  offerId: string;
  caseId: string;
  status: string;
  termsHash: string;
  frozenAt: string;
  terms: {
    buyer_name: string;
    quantity: string;
    unit_price: string;
    currency: string;
    price_unit: string;
    transport_cost: string;
    commission_rate: string;
  };
  decision: 'accepted' | 'rejected' | null;
  decidedAt: string | null;
}

export interface ApiFrozenBuyerOffer {
  offer_id: string;
  case_id: string;
  status: string;
  terms_hash: string;
  frozen_at: string;
  terms: FrozenBuyerOffer['terms'];
  decision: 'accepted' | 'rejected' | null;
  decided_at: string | null;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case).
// --------------------------------------------------------------------------- //
export interface ApiPriceReference {
  modal_price: number;
  minimum_price: number;
  maximum_price: number;
  unit: string;
  source: string;
  price_date: string;
  market: string | null;
  district: string | null;
}

export interface ApiProcurementInsight {
  days_to_harvest: number;
  harvest_window: HarvestWindow;
  quantity_kg: number | null;
  estimated_market_value: number | null;
  estimated_asking_value: number | null;
  price_reference: ApiPriceReference | null;
}

export interface ApiProduceImage {
  id: string;
  image_url: string;
  thumbnail_url: string | null;
  mime_type: string | null;
  caption: string | null;
  display_order: number;
  created_at: string;
}

export interface ApiStatusHistory {
  id: string;
  old_status: string | null;
  new_status: string;
  note: string | null;
  created_at: string;
}

export interface ApiProduceSummary {
  id: string;
  listing_ref?: string;
  farm_id: string;
  crop_name: string;
  availability_type?: ProduceAvailabilityType;
  category?: ProduceCategory;
  product_name?: string;
  variety: string | null;
  quantity: number;
  unit: ProduceUnit;
  cultivated_area_hectares: number | null;
  expected_total_quantity: number | null;
  available_quantity: number | null;
  quantity_provenance: 'farmer_reported' | null;
  quality_notes: string | null;
  expected_harvest_date: string | null;
  expected_grade: ProduceGrade | null;
  asking_price: number | null;
  price_unit?: ProduceUnit | null;
  negotiable?: boolean;
  packaging?: string | null;
  currency: string;
  current_market_price_snapshot: number | null;
  district: string | null;
  status: ProduceStatus;
  thumbnail_url: string | null;
  image_count: number;
  insight: ApiProcurementInsight | null;
  organic_certification_status: string | null;
  organic_certification_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface ApiProduceDetail extends ApiProduceSummary {
  block: string | null;
  village: string | null;
  latitude: number | null;
  longitude: number | null;
  available_from: string | null;
  available_until: string | null;
  market_price_source: string | null;
  market_price_date: string | null;
  procurement_channel: string | null;
  procurement_reference: string | null;
  notes: string | null;
  pickup_location?: string | null;
  images: ApiProduceImage[];
  status_history: ApiStatusHistory[];
}
