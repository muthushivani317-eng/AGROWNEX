import { Activity, BrainCircuit, Building2, CircleHelp, ClipboardList, LayoutDashboard, Leaf, Scale, ScrollText, Shield, ShoppingBasket, Sprout, UserCog, Users } from 'lucide-react';
import type { Permission } from './types';

export const navigation = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, permission: 'view_dashboard' },
  { to: '/farmers', label: 'Farmers', icon: Users, permission: 'manage_farmers' },
  { to: '/farms', label: 'Farms', icon: Building2, permission: 'view_analytics' },
  { to: '/produce', label: 'Sell My Produce', icon: Leaf, permission: 'manage_procurement' },
  { to: '/buyers', label: 'Buyer CRM', icon: ClipboardList, permission: 'manage_procurement' },
  { to: '/ledgers', label: 'Ledgers', icon: Scale, permission: 'manage_procurement' },
  { to: '/inputs', label: 'Inputs Catalog', icon: ShoppingBasket, permission: 'manage_procurement' },
  { to: '/organic-inputs', label: 'Organic Inputs (QC)', icon: Sprout, permission: ['manage_marketplace_catalog', 'manage_marketplace_suppliers', 'manage_marketplace_qc', 'manage_marketplace_procurement'] as const },
  { to: '/crop-intelligence', label: 'Crop Intelligence', icon: Activity, permission: 'view_crop_intelligence' },
  { to: '/organic-pilot', label: 'Organic pilot', icon: Leaf, permission: 'view_dashboard' },
  { to: '/organic-content', label: 'Organic content', icon: ClipboardList, permission: 'manage_content' },
  { to: '/organic-certification', label: 'PGS tracking', icon: Shield, permission: 'manage_farmers' },
  { to: '/support', label: 'Farmer Support', icon: CircleHelp, permission: 'manage_support' },
  { to: '/ai', label: 'AI monitoring', icon: BrainCircuit, permission: 'view_ai' },
  { to: '/audit', label: 'Audit records', icon: ScrollText, permission: 'view_audit' },
  { to: '/partner-organizations', label: 'Partner organizations', icon: UserCog, permission: 'manage_admins' },
  { to: '/team', label: 'Team & permissions', icon: Shield, permission: 'manage_admins' }
] as const satisfies ReadonlyArray<{ to: string; label: string; icon: typeof Activity; permission: Permission | readonly Permission[] }>;

export function hasPermission(granted: readonly Permission[], required: Permission | readonly Permission[]): boolean {
  return Array.isArray(required) ? required.some((p: Permission) => granted.includes(p)) : granted.includes(required as Permission);
}
