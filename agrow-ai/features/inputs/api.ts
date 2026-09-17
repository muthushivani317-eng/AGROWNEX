import type { AxiosRequestConfig } from "axios";

import { api } from "@/services/apiClient";
import { endpoints } from "@/services/endpoints";
import type { CatalogItem, InputCategory, InputOrder } from "./types";

export const getInputCatalog = (
  category?: InputCategory,
  crop?: string | null,
): Promise<CatalogItem[]> =>
  api.get(endpoints.inputs.catalog, {
    params: { ...(category ? { category } : {}), ...(crop ? { crop } : {}) },
  });
export const getInputOrders = (): Promise<InputOrder[]> =>
  api.get(endpoints.inputs.orders);
export function placeInputOrder(input: {
  cart: Array<{ item: CatalogItem; quantity: number }>;
  deliveryAddress: string;
  idempotencyKey: string;
}): Promise<InputOrder> {
  return api.post(
    endpoints.inputs.orders,
    {
      delivery_address: input.deliveryAddress,
      idempotency_key: input.idempotencyKey,
      items: input.cart.map(({ item, quantity }) => ({
        catalog_item_id: item.id,
        quantity,
        expected_unit_price: item.unit_price,
        expected_stock_version: item.stock_version,
      })),
    },
    { _skipRetry: true } as AxiosRequestConfig,
  );
}
