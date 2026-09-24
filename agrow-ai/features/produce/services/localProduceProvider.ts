import { uuid } from '@/utils/id';

import { DEFAULT_CURRENCY, DEFAULT_PAGE_SIZE } from '../constants';
import type {
  ProduceImageInput,
  ProduceInput,
  ProduceListParams,
  ProduceListResult,
  ProduceOffer,
  ProduceOfferDetail,
  ProduceStatus,
} from '../types';
import { computeInsight } from './produceEngine';
import { ProduceError, type ProduceProvider } from './produceProvider';
import { produceStorage } from './produceStorage';

/**
 * Local, offline produce provider. Runs the same deterministic procurement
 * engine as the backend over MMKV-stored offers, so the module is fully usable
 * in dev / without a backend. It never fabricates a market price (no verified
 * source offline → snapshot stays null) or a buyer (docs/PRODUCT_RULES.md).
 */
const UPCOMING: ProduceStatus[] = ['submitted', 'planned'];
const CONCLUDED: ProduceStatus[] = ['harvested', 'fulfilled', 'withdrawn', 'expired'];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Recompute the (time-sensitive) insight from the stored facts on every read. */
function withInsight(offer: ProduceOfferDetail): ProduceOfferDetail {
  if (!offer.expectedHarvestDate) return { ...offer, insight: null };
  return {
    ...offer,
    insight: computeInsight(
      {
        quantity: offer.quantity,
        unit: offer.unit,
        expectedHarvestDate: offer.expectedHarvestDate,
        askingPrice: offer.askingPrice,
      },
      offer.insight?.priceReference ?? null,
    ),
  };
}

function toSummary(offer: ProduceOfferDetail): ProduceOffer {
  const { images, statusHistory, ...summary } = withInsight(offer);
  void images;
  void statusHistory;
  return summary;
}

function paginate(items: ProduceOffer[], page: number, pageSize: number): ProduceListResult {
  const start = (page - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    page,
    pageSize,
    total: items.length,
    totalPages: Math.max(1, Math.ceil(items.length / pageSize)),
  };
}

function matches(offer: ProduceOfferDetail, params: ProduceListParams): boolean {
  if (params.status && offer.status !== params.status) return false;
  if (params.farmId && offer.farmId !== params.farmId) return false;
  if (params.availabilityType && offer.availabilityType !== params.availabilityType) return false;
  if (params.category && offer.category !== params.category) return false;
  if (params.crop && !offer.cropName.toLowerCase().includes(params.crop.toLowerCase()))
    return false;
  if (
    params.search &&
    !`${offer.productName} ${offer.cropName} ${offer.variety ?? ''} ${offer.category}`
      .toLowerCase()
      .includes(params.search.toLowerCase())
  )
    return false;
  if (params.organicOnly && !offer.organicCertificationVerified) return false;
  return true;
}

export const localProduceProvider: ProduceProvider = {
  async list(params: ProduceListParams): Promise<ProduceListResult> {
    const rows = produceStorage
      .localOffers()
      .filter((o) => matches(o, params))
      .map(toSummary);
    return paginate(rows, params.page ?? 1, params.pageSize ?? DEFAULT_PAGE_SIZE);
  },

  async upcoming(page = 1, pageSize = DEFAULT_PAGE_SIZE): Promise<ProduceListResult> {
    const now = today();
    const rows = produceStorage
      .localOffers()
      .filter((o) => o.availabilityType === 'upcoming_harvest' && UPCOMING.includes(o.status) && Boolean(o.expectedHarvestDate && o.expectedHarvestDate >= now))
      .sort((a, b) => (a.expectedHarvestDate ?? '').localeCompare(b.expectedHarvestDate ?? ''))
      .map(toSummary);
    return paginate(rows, page, pageSize);
  },

  async history(page = 1, pageSize = DEFAULT_PAGE_SIZE): Promise<ProduceListResult> {
    const rows = produceStorage
      .localOffers()
      .filter((o) => CONCLUDED.includes(o.status))
      .map(toSummary);
    return paginate(rows, page, pageSize);
  },

  async get(id: string): Promise<ProduceOfferDetail> {
    const offer = produceStorage.getLocal(id);
    if (!offer) throw new ProduceError('produce_offer_not_found', 'Offer not found.');
    return withInsight(offer);
  },

  async create(input: ProduceInput): Promise<ProduceOfferDetail> {
    const now = new Date().toISOString();
    const id = uuid();
    const status = input.category === 'other_produce' ? 'draft' : input.status ?? 'submitted';
    const submitted = status === 'submitted';
    const images = (input.images ?? []).map((img, index) => ({
      id: uuid(),
      imageUrl: img.imageUrl,
      thumbnailUrl: img.thumbnailUrl ?? null,
      mimeType: img.mimeType ?? null,
      caption: img.caption ?? null,
      displayOrder: index,
      createdAt: now,
    }));
    const offer: ProduceOfferDetail = {
      id,
      farmId: input.farmId,
      cropName: input.cropName,
      availabilityType: input.availabilityType ?? 'upcoming_harvest',
      category: input.category ?? 'other_produce',
      productName: input.productName ?? input.cropName,
      customProductName: input.customProductName ?? null,
      variety: input.variety ?? null,
      quantity: input.quantity,
      unit: input.unit,
      cultivatedAreaHectares:
        input.cultivatedAreaAcres == null ? null : input.cultivatedAreaAcres * 0.40468564224,
      expectedTotalQuantity: input.expectedTotalQuantity ?? null,
      availableQuantity: input.availableQuantity ?? null,
      quantityProvenance: 'farmer_reported',
      qualityNotes: input.qualityNotes ?? null,
      expectedHarvestDate: input.expectedHarvestDate ?? null,
      expectedGrade: input.expectedGrade ?? null,
      askingPrice: input.askingPrice ?? null,
      priceUnit: input.priceUnit ?? input.unit,
      negotiable: input.negotiable ?? false,
      packaging: input.packaging ?? null,
      currency: input.currency ?? DEFAULT_CURRENCY,
      currentMarketPriceSnapshot: null, // no verified source offline — never fabricated
      district: input.district ?? null,
      status,
      thumbnailUrl: images[0]?.thumbnailUrl ?? images[0]?.imageUrl ?? null,
      imageCount: images.length,
      insight: null,
      // No offline source of truth for organic certification (admin-verified
      // only) -- never fabricate a status while offline.
      organicCertificationStatus: null,
      organicCertificationVerified: false,
      createdAt: now,
      updatedAt: now,
      syncStatus: 'synced',
      block: input.block ?? null,
      village: input.village ?? null,
      latitude: input.latitude ?? null,
      longitude: input.longitude ?? null,
      availableFrom: input.availableFrom ?? null,
      availableUntil: input.availableUntil ?? null,
      marketPriceSource: null,
      marketPriceDate: null,
      procurementChannel: submitted ? 'mock' : null,
      procurementReference: submitted ? `MOCK-${uuid().slice(0, 8).toUpperCase()}` : null,
      notes: input.notes ?? null,
      pickupLocation: input.pickupLocation ?? null,
      images,
      statusHistory: [
        {
          id: uuid(),
          oldStatus: null,
          newStatus: status,
          note: 'Offer created',
          createdAt: now,
        },
      ],
    };
    produceStorage.upsertLocal(offer);
    return withInsight(offer);
  },

  async update(id: string, input: ProduceInput): Promise<ProduceOfferDetail> {
    const existing = produceStorage.getLocal(id);
    if (!existing) throw new ProduceError('produce_offer_not_found', 'Offer not found.');
    const now = new Date().toISOString();
    const statusChanged = input.status && input.status !== existing.status;
    const next: ProduceOfferDetail = {
      ...existing,
      cropName: input.cropName ?? existing.cropName,
      availabilityType: input.availabilityType ?? existing.availabilityType,
      category: input.category ?? existing.category,
      productName: input.productName ?? existing.productName,
      customProductName: input.customProductName ?? existing.customProductName,
      variety: input.variety ?? existing.variety,
      quantity: input.quantity ?? existing.quantity,
      unit: input.unit ?? existing.unit,
      expectedHarvestDate: input.expectedHarvestDate ?? existing.expectedHarvestDate,
      expectedGrade: input.expectedGrade ?? existing.expectedGrade,
      askingPrice: input.askingPrice ?? existing.askingPrice,
      priceUnit: input.priceUnit ?? existing.priceUnit,
      negotiable: input.negotiable ?? existing.negotiable,
      packaging: input.packaging ?? existing.packaging,
      district: input.district ?? existing.district,
      block: input.block ?? existing.block,
      village: input.village ?? existing.village,
      notes: input.notes ?? existing.notes,
      pickupLocation: input.pickupLocation ?? existing.pickupLocation,
      availableFrom: input.availableFrom ?? existing.availableFrom,
      availableUntil: input.availableUntil ?? existing.availableUntil,
      status: input.status ?? existing.status,
      updatedAt: now,
      statusHistory: statusChanged
        ? [
            ...existing.statusHistory,
            {
              id: uuid(),
              oldStatus: existing.status,
              newStatus: input.status as ProduceStatus,
              note: null,
              createdAt: now,
            },
          ]
        : existing.statusHistory,
    };
    produceStorage.upsertLocal(next);
    return withInsight(next);
  },

  async remove(id: string): Promise<void> {
    produceStorage.removeLocal(id);
  },

  async addImage(id: string, image: ProduceImageInput): Promise<ProduceOfferDetail> {
    const existing = produceStorage.getLocal(id);
    if (!existing) throw new ProduceError('produce_offer_not_found', 'Offer not found.');
    const now = new Date().toISOString();
    const images = [
      ...existing.images,
      {
        id: uuid(),
        imageUrl: image.imageUrl,
        thumbnailUrl: image.thumbnailUrl ?? null,
        mimeType: image.mimeType ?? null,
        caption: image.caption ?? null,
        displayOrder: existing.images.length,
        createdAt: now,
      },
    ];
    const next: ProduceOfferDetail = {
      ...existing,
      images,
      imageCount: images.length,
      thumbnailUrl: existing.thumbnailUrl ?? images[0].thumbnailUrl ?? images[0].imageUrl,
      updatedAt: now,
    };
    produceStorage.upsertLocal(next);
    return withInsight(next);
  },

  async buyerOffer() {
    throw new ProduceError(
      'procurement_unavailable',
      'A verified buyer offer requires the backend.',
    );
  },

  async decideBuyerOffer() {
    throw new ProduceError(
      'procurement_unavailable',
      'A verified buyer offer requires the backend.',
    );
  },
};
