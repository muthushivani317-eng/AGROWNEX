export type InputCategory = "seed" | "fertilizer" | "pesticide";
export type InputOrderStatus =
  "placed" | "confirmed" | "out_for_delivery" | "delivered";

export interface CatalogItem {
  id: string;
  name: string;
  name_ta: string | null;
  category: InputCategory;
  unit: string;
  unit_price: string;
  stock_quantity: number;
  stock_version: number;
  crop_tags: string[];
  description: string | null;
}

export interface InputOrder {
  id: string;
  order_ref: string;
  status: InputOrderStatus;
  total_amount: string;
  currency: "INR";
  delivery_address: string;
  delivery_eta: string | null;
  cash_collected_at: string | null;
  created_at: string;
  items: Array<{
    product_name: string;
    unit: string;
    unit_price: string;
    quantity: number;
    line_total: string;
  }>;
}
