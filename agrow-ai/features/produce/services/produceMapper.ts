import type { Paginated } from '@/types';

import type {
  ApiPriceReference,
  ApiProcurementInsight,
  ApiProduceDetail,
  ApiProduceImage,
  ApiProduceSummary,
  ApiStatusHistory,
  PriceReference,
  ProcurementInsight,
  ProduceImage,
  ProduceImageInput,
  ProduceInput,
  ProduceListResult,
  ProduceOffer,
  ProduceOfferDetail,
  StatusHistory,
} from '../types';

const HECTARES_PER_ACRE = 0.40468564224;

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

export function apiToPriceReference(
  dto: ApiPriceReference | null,
): PriceReference | null {
  if (!dto) return null;
  return {
    modalPrice: dto.modal_price,
    minimumPrice: dto.minimum_price,
    maximumPrice: dto.maximum_price,
    unit: dto.unit,
    source: dto.source,
    priceDate: dto.price_date,
    market: dto.market,
    district: dto.district,
  };
}

export function apiToInsight(
  dto: ApiProcurementInsight | null,
): ProcurementInsight | null {
  if (!dto) return null;
  return {
    daysToHarvest: dto.days_to_harvest,
    harvestWindow: dto.harvest_window,
    quantityKg: dto.quantity_kg,
    estimatedMarketValue: dto.estimated_market_value,
    estimatedAskingValue: dto.estimated_asking_value,
    priceReference: apiToPriceReference(dto.price_reference),
  };
}

export function apiToImage(dto: ApiProduceImage): ProduceImage {
  return {
    id: dto.id,
    imageUrl: dto.image_url,
    thumbnailUrl: dto.thumbnail_url,
    mimeType: dto.mime_type,
    caption: dto.caption,
    displayOrder: dto.display_order,
    createdAt: dto.created_at,
  };
}

export function apiToStatusHistory(dto: ApiStatusHistory): StatusHistory {
  return {
    id: dto.id,
    oldStatus: dto.old_status,
    newStatus: dto.new_status,
    note: dto.note,
    createdAt: dto.created_at,
  };
}

export function apiToOffer(dto: ApiProduceSummary): ProduceOffer {
  return {
    id: dto.id,
    listingRef: dto.listing_ref,
    farmId: dto.farm_id,
    cropName: dto.crop_name,
    availabilityType: dto.availability_type ?? 'upcoming_harvest',
    category: dto.category ?? 'other_produce',
    productName: dto.product_name ?? dto.crop_name,
    customProductName: dto.category === 'other_produce' ? dto.product_name ?? dto.crop_name : null,
    variety: dto.variety,
    quantity: dto.quantity,
    unit: dto.unit,
    cultivatedAreaHectares: dto.cultivated_area_hectares,
    expectedTotalQuantity: dto.expected_total_quantity,
    availableQuantity: dto.available_quantity,
    quantityProvenance: dto.quantity_provenance,
    qualityNotes: dto.quality_notes,
    expectedHarvestDate: dto.expected_harvest_date,
    expectedGrade: dto.expected_grade,
    askingPrice: dto.asking_price,
    priceUnit: dto.price_unit ?? dto.unit,
    negotiable: dto.negotiable ?? false,
    packaging: dto.packaging ?? null,
    currency: dto.currency,
    currentMarketPriceSnapshot: dto.current_market_price_snapshot,
    district: dto.district,
    status: dto.status,
    thumbnailUrl: dto.thumbnail_url,
    imageCount: dto.image_count,
    insight: apiToInsight(dto.insight),
    organicCertificationStatus: dto.organic_certification_status,
    organicCertificationVerified: dto.organic_certification_verified ?? false,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    syncStatus: 'synced',
  };
}

export function apiToDetail(dto: ApiProduceDetail): ProduceOfferDetail {
  return {
    ...apiToOffer(dto),
    block: dto.block,
    village: dto.village,
    latitude: dto.latitude,
    longitude: dto.longitude,
    availableFrom: dto.available_from,
    availableUntil: dto.available_until,
    marketPriceSource: dto.market_price_source,
    marketPriceDate: dto.market_price_date,
    procurementChannel: dto.procurement_channel,
    procurementReference: dto.procurement_reference,
    notes: dto.notes,
    pickupLocation: dto.pickup_location ?? null,
    images: (dto.images ?? []).map(apiToImage),
    statusHistory: (dto.status_history ?? []).map(apiToStatusHistory),
  };
}

export function apiToListResult(dto: Paginated<ApiProduceSummary>): ProduceListResult {
  return {
    items: dto.items.map(apiToOffer),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
  };
}

/** Domain input → backend request body (camelCase → snake_case). */
export function inputToApi(input: ProduceInput): Record<string, unknown> {
  return {
    farm_id: input.farmId,
    crop_name: input.cropName,
    availability_type: input.availabilityType ?? 'upcoming_harvest',
    category: input.category ?? 'other_produce',
    product_name: input.productName ?? input.cropName,
    variety: input.variety ?? null,
    quantity: input.quantity,
    unit: input.unit,
    cultivated_area_hectares:
      input.cultivatedAreaAcres == null
        ? null
        : input.cultivatedAreaAcres * HECTARES_PER_ACRE,
    expected_total_quantity: input.expectedTotalQuantity ?? null,
    available_quantity: input.availableQuantity ?? null,
    quantity_provenance: 'farmer_reported',
    quality_notes: input.qualityNotes ?? null,
    expected_harvest_date: input.expectedHarvestDate,
    expected_grade: input.expectedGrade ?? null,
    asking_price: input.askingPrice ?? null,
    price_unit: input.priceUnit ?? input.unit,
    negotiable: input.negotiable ?? false,
    packaging: input.packaging ?? null,
    currency: input.currency ?? 'INR',
    available_from: input.availableFrom ?? null,
    available_until: input.availableUntil ?? null,
    district: input.district ?? null,
    block: input.block ?? null,
    village: input.village ?? null,
    latitude: input.latitude ?? null,
    longitude: input.longitude ?? null,
    notes: input.notes ?? null,
    pickup_location: input.pickupLocation ?? null,
    status: input.category === 'other_produce' ? 'draft' : input.status ?? 'submitted',
    images: (input.images ?? []).map(imageInputToApi),
  };
}

/** Update body — omit status/images so partial edits don't reset them. */
export function updateInputToApi(input: ProduceInput): Record<string, unknown> {
  const body = inputToApi(input);
  delete body.images;
  return body;
}

export function imageInputToApi(image: ProduceImageInput): Record<string, unknown> {
  return {
    image_url: image.imageUrl,
    thumbnail_url: image.thumbnailUrl ?? null,
    mime_type: image.mimeType ?? null,
    file_size: image.fileSize ?? null,
    caption: image.caption ?? null,
  };
}
