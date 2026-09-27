import { httpClient } from '@/services/apiClient';

/**
 * Farmer -> Agrownex selling (we buy after quality checks, then resell).
 * /organic-inputs/* returns plain JSON (no {success,data} envelope), so this
 * uses httpClient directly -- same convention as organicPgsApi.ts.
 */
export type SupplierStatus =
  | 'draft' | 'submitted' | 'under_review' | 'clarification_required'
  | 'inspection_scheduled' | 'inspection_completed' | 'approved'
  | 'rejected' | 'suspended' | 'expired';

export interface SupplierProfile {
  id: string;
  status: SupplierStatus;
  production_location: string | null;
  district: string | null;
  village: string | null;
  contact_name: string | null;
  contact_phone: string | null;
}

export interface SupplierApplyInput {
  contact_name: string;
  contact_phone: string;
  village?: string | null;
  district?: string | null;
  production_location?: string | null;
  production_capacity_note?: string | null;
}

export interface ProductType { id: string; name: string; name_ta: string | null }

export interface SellBatch {
  id: string;
  batch_code: string;
  product_type_id: string;
  status: string;
  batch_quantity: string;
  unit: string;
  expected_procurement_price: string | null;
  latest_review_note: string | null;
  created_at: string;
}

export interface BatchCreateInput {
  product_type_id: string;
  batch_quantity: string;
  unit: string;
  expected_procurement_price?: string | null;
  production_location?: string | null;
  production_completion_date?: string | null;
}

export interface ProcurementOffer {
  id: string;
  offered_quantity: string;
  unit: string;
  offered_unit_price: string;
  status: string;
}

const base = '/organic-inputs';

export const sellApi = {
  /** null when the farmer has not applied yet (404). */
  async getProfile(): Promise<SupplierProfile | null> {
    try {
      return (await httpClient.get<SupplierProfile>(`${base}/supplier-profile`)).data;
    } catch (error) {
      if ((error as { status?: number }).status === 404) return null;
      throw error;
    }
  },
  async applyAndSubmit(input: SupplierApplyInput): Promise<void> {
    await httpClient.post(`${base}/supplier-profile`, input);
    await httpClient.post(`${base}/supplier-profile/submit`);
  },
  async productTypes(): Promise<ProductType[]> {
    return (await httpClient.get<ProductType[]>(`${base}/product-types`)).data;
  },
  async myBatches(): Promise<SellBatch[]> {
    return (await httpClient.get<SellBatch[]>(`${base}/batches`)).data;
  },
  async createAndSubmitBatch(input: BatchCreateInput): Promise<void> {
    const batch = (await httpClient.post<SellBatch>(`${base}/batches`, input)).data;
    await httpClient.post(`${base}/batches/${batch.id}/submit`);
  },
  async offer(batchId: string): Promise<ProcurementOffer> {
    return (await httpClient.get<ProcurementOffer>(`${base}/batches/${batchId}/procurement-offer`)).data;
  },
  async decideOffer(batchId: string, accept: boolean): Promise<void> {
    await httpClient.post(`${base}/batches/${batchId}/procurement-offer/decision`, {
      accept,
      rejection_reason: accept ? null : 'Declined by farmer in app',
    });
  },
};
