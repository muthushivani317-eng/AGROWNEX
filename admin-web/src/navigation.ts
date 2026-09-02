import { Activity, BrainCircuit, Building2, CircleHelp, ClipboardList, LayoutDashboard, Leaf, Scale, ScrollText, Shield, Users } from 'lucide-react';
import type { Permission } from './types';

export const navigation = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, permission: 'view_dashboard' },
  { to: '/farmers', label: 'Farmers', icon: Users, permission: 'manage_farmers' },
  { to: '/farms', label: 'Farms', icon: Building2, permission: 'view_analytics' },
  { to: '/produce', label: 'Sell My Produce', icon: Leaf, permission: 'manage_procurement' },
  { to: '/buyers', label: 'Buyer CRM', icon: ClipboardList, permission: 'manage_procurement' },
  { to: '/ledgers', label: 'Ledgers', icon: Scale, permission: 'manage_procurement' },
  { to: '/crop-intelligence', label: 'Crop Intelligence', icon: Activity, permission: 'view_crop_intelligence' },
  { to: '/support', label: 'Farmer Support', icon: CircleHelp, permission: 'manage_support' },
  { to: '/ai', label: 'AI monitoring', icon: BrainCircuit, permission: 'view_ai' },
  { to: '/audit', label: 'Audit records', icon: ScrollText, permission: 'view_audit' },
  { to: '/team', label: 'Team & permissions', icon: Shield, permission: 'manage_admins' }
] as const satisfies ReadonlyArray<{ to: string; label: string; icon: typeof Activity; permission: Permission }>;
