import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';
import { uuid } from '@/utils/id';

import { DEFAULT_CURRENCY, produceKeys } from '../constants';
import { computeInsight } from '../services/produceEngine';
import { getProduceProvider } from '../services/produceProvider';
import { listCacheKey } from '../services/produceStorage';
import { isOfflineError, produceOutbox } from '../services/produceSync';
import type {
  ProduceImageInput,
  ProduceInput,
  ProduceListParams,
  ProduceOfferDetail,
} from '../types';

export interface ProduceMutationResult {
  offer: ProduceOfferDetail;
  offline: boolean;
}

const LIST_STALE = 5 * 60 * 1000;

export function useProduceList(params: ProduceListParams, enabled = true) {
  return useQuery({
    queryKey: produceKeys.list(listCacheKey(params, 'all')),
    enabled,
    queryFn: () => getProduceProvider().list(params),
    staleTime: LIST_STALE,
  });
}

export function useUpcomingProduce(enabled = true) {
  return useQuery({
    queryKey: produceKeys.upcoming('1'),
    enabled,
    queryFn: () => getProduceProvider().upcoming(),
    staleTime: LIST_STALE,
  });
}

export function useProduceHistory(enabled = true) {
  return useQuery({
    queryKey: produceKeys.history('1'),
    enabled,
    queryFn: () => getProduceProvider().history(),
    staleTime: LIST_STALE,
  });
}

export function useProduceDetail(id: string | undefined) {
  return useQuery({
    queryKey: produceKeys.detail(id ?? ''),
    enabled: Boolean(id),
    queryFn: () => getProduceProvider().get(id as string),
  });
}

export function useBuyerOffer(id: string | undefined) {
  return useQuery({
    queryKey: ['produce', 'buyer-offer', id],
    enabled: Boolean(id),
    queryFn: () => getProduceProvider().buyerOffer(id as string),
    retry: false,
  });
}

export function useDecideBuyerOffer(id: string) {
  return useMutation({
    mutationFn: (decision: 'accepted' | 'rejected') =>
      getProduceProvider().decideBuyerOffer(id, decision, uuid()),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['produce', 'buyer-offer', id] });
      void queryClient.invalidateQueries({ queryKey: produceKeys.detail(id) });
    },
  });
}

/** Build an optimistic offer so an offline create still renders + syncs later. */
function optimisticOffer(input: ProduceInput): ProduceOfferDetail {
  const now = new Date().toISOString();
  return {
    id: uuid(),
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
    currentMarketPriceSnapshot: null,
    district: input.district ?? null,
    status: input.category === 'other_produce' ? 'draft' : input.status ?? 'submitted',
    thumbnailUrl: input.images?.[0]?.imageUrl ?? null,
    imageCount: input.images?.length ?? 0,
    insight: input.expectedHarvestDate ? computeInsight({
      quantity: input.quantity,
      unit: input.unit,
      expectedHarvestDate: input.expectedHarvestDate,
      askingPrice: input.askingPrice,
    }, null) : null,
    organicCertificationStatus: null,
    organicCertificationVerified: false,
    createdAt: now,
    updatedAt: now,
    syncStatus: 'pending',
    block: input.block ?? null,
    village: input.village ?? null,
    latitude: input.latitude ?? null,
    longitude: input.longitude ?? null,
    availableFrom: input.availableFrom ?? null,
    availableUntil: input.availableUntil ?? null,
    marketPriceSource: null,
    marketPriceDate: null,
    procurementChannel: null,
    procurementReference: null,
    notes: input.notes ?? null,
    pickupLocation: input.pickupLocation ?? null,
    images: [],
    statusHistory: [],
  };
}

function invalidateAll(): void {
  void queryClient.invalidateQueries({ queryKey: produceKeys.all });
}

export function useCreateProduce() {
  return useMutation<ProduceMutationResult, unknown, ProduceInput>({
    mutationFn: async (input) => {
      try {
        const offer = await getProduceProvider().create(input);
        return { offer, offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          const offer = optimisticOffer(input);
          produceOutbox.enqueue({ op: 'create', offerId: offer.id, input });
          return { offer, offline: true };
        }
        throw error;
      }
    },
    onSuccess: invalidateAll,
  });
}

export function useUpdateProduce(id: string) {
  return useMutation<ProduceMutationResult, unknown, ProduceInput>({
    mutationFn: async (input) => {
      try {
        const offer = await getProduceProvider().update(id, input);
        return { offer, offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          produceOutbox.enqueue({ op: 'update', offerId: id, input });
          return { offer: optimisticOffer({ ...input }), offline: true };
        }
        throw error;
      }
    },
    onSuccess: () => {
      invalidateAll();
      void queryClient.invalidateQueries({ queryKey: produceKeys.detail(id) });
    },
  });
}

export function useDeleteProduce() {
  return useMutation<{ offline: boolean }, unknown, string>({
    mutationFn: async (id) => {
      try {
        await getProduceProvider().remove(id);
        return { offline: false };
      } catch (error) {
        if (isOfflineError(error)) {
          produceOutbox.enqueue({ op: 'delete', offerId: id });
          return { offline: true };
        }
        throw error;
      }
    },
    onSuccess: invalidateAll,
  });
}

export function useAddProduceImage(id: string) {
  return useMutation<ProduceOfferDetail, unknown, ProduceImageInput>({
    mutationFn: (image) => getProduceProvider().addImage(id, image),
    onSuccess: () => {
      invalidateAll();
      void queryClient.invalidateQueries({ queryKey: produceKeys.detail(id) });
    },
  });
}
