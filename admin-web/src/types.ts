export type Permission =
  | 'view_dashboard' | 'view_analytics' | 'manage_farmers'
  | 'view_crop_intelligence'
  | 'manage_procurement' | 'view_ai' | 'view_audit'
  | 'manage_admins' | 'reveal_buyer_contact' | 'view_revenue' | 'view_ai_costs';

export interface AdminMe {
  id: string;
  user_id: string;
  role: string;
  full_name: string | null;
  permissions: Permission[];
  status: 'active' | 'suspended';
}

export interface Envelope<T> { success: boolean; data: T; message?: string }
export interface Page<T> { items: T[]; page: number; page_size: number; total: number; total_pages: number }
export interface MetricCard { key: string; value: number | null }
export interface Farmer {
  user_id: string; farmer_ref?: string; full_name: string | null; phone_number: string | null;
  district: string | null; village: string | null; primary_crop: string | null;
  farm_count: number; created_at: string | null;
}
export interface Procurement {
  offer_id: string; listing_ref?: string; farmer_ref?: string; crop: string | null;
  product_category?: string | null;
  availability_type?: 'available_now' | 'upcoming_harvest' | null;
  quantity: number; unit: string; harvest_date: string | null; village: string | null;
  district: string | null; farmer_name: string | null; admin_status: string;
  buyer_name: string | null; buyer_contact: string | null; buyer_contact_masked: boolean;
  buyer_offer_price: number | null; follow_up_at: string | null;
  variety?: string | null; expected_grade?: string | null; asking_price?: number | null;
  price_unit?: string | null; negotiable?: boolean; packaging?: string | null;
  pickup_location?: string | null; pickup_available?: boolean;
}
export interface AuditRow {
  id: string; role: string | null; action: string; target: string | null;
  target_id: string | null; created_at: string;
}

export type JsonRecord = Record<string, unknown>;
