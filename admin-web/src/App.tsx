import { Leaf, LogOut, Menu, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { api, ApiError, getCsrfToken } from './api';
import { signOutAdmin } from './auth';
import { ErrorPanel, Loading } from './components';
import { InputsMarketplacePage } from './InputsMarketplace';
import { Login } from './Login';
import { OrganicInputsAdminPage } from './OrganicInputsAdmin';
import { hasPermission, navigation } from './navigation';
import { OrganicPilotPage } from './OrganicPilot';
import { OrganicContentPage } from './OrganicContent';
import { OrganicReferenceReviewPage } from './OrganicReferenceReview';
import { OrganicCertificationPage } from './OrganicCertification';
import { PartnerOrganizationsPage } from './PartnerOrganizations';
import { FpoCropBoardPage } from './FpoCropBoard';
import { AiPage, AuditPage, CropIntelligencePage, DashboardPage, FarmersPage, FarmsPage, ProducePage, SupportPage, TeamPage } from './pages';
import type { AdminMe, Permission } from './types';
import { useResource } from './useResource';
import { useMarketplaceAttention } from './marketplaceAttention';
import { msUntilSignOut, REAUTH_EVENT } from './sessionTimeout';

function Guard({ permission, me, children }: { permission: Permission | readonly Permission[]; me: AdminMe; children: React.ReactNode }) {
  if (hasPermission(me.permissions, permission)) return <>{children}</>;
  // Send the admin to the first page they may open (avoids a redirect loop on
  // "/" for roles without the dashboard, e.g. FPO partners).
  const first = navigation.find(item => hasPermission(me.permissions, item.permission));
  return first ? <Navigate to={first.to} replace /> : <div className="panel-message">You do not have access to any page yet.</div>;
}

function Portal({ me, onLogout }: { me: AdminMe; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const allowed = navigation.filter(item => hasPermission(me.permissions, item.permission));
  const attention = useMarketplaceAttention(me.permissions);
  return <div className="portal"><aside className={open ? 'open' : ''}><div className="sidebar-brand"><div className="brand-mark small"><Leaf size={32}/></div><div><strong>AgrowAI</strong><span>ADMIN</span></div><button className="icon-button close" onClick={() => setOpen(false)} aria-label="Close navigation"><X/></button></div><nav>{allowed.map(({to,label,icon:Icon}) => <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)}><Icon size={19}/><span>{label}</span>{to === '/produce' && <small className="nav-new">NEW</small>}{to === '/organic-inputs' && (attention?.total ?? 0) > 0 && <small className="nav-new" title="Needs your attention">{attention!.total}</small>}</NavLink>)}</nav><div className="admin-profile"><div className="profile-name"><span className="dashboard-avatar">{(me.full_name ?? 'A').charAt(0).toUpperCase()}</span><span>{me.full_name ?? 'AgrowAI team member'}</span></div><small>{me.role.replaceAll('_',' ')}</small><button onClick={onLogout}>Sign out <LogOut size={16}/></button></div></aside>{open && <button className="scrim" aria-label="Close navigation" onClick={() => setOpen(false)} />}<main className="content"><div className="mobile-bar"><button className="icon-button" onClick={() => setOpen(true)} aria-label="Open navigation"><Menu/></button><strong>AgrowAI Admin</strong><span className="secure-dot">Secure</span></div><Routes><Route path="/" element={<Guard permission="view_dashboard" me={me}><DashboardPage me={me}/></Guard>} /><Route path="/farmers" element={<Guard permission="manage_farmers" me={me}><FarmersPage canDelete={me.role === 'owner' || me.role === 'super_admin'}/></Guard>} /><Route path="/farms" element={<Guard permission="view_analytics" me={me}><FarmsPage/></Guard>} /><Route path="/produce" element={<Guard permission="manage_procurement" me={me}><ProducePage canReveal={me.permissions.includes('reveal_buyer_contact')}/></Guard>} /><Route path="/buyers" element={<Guard permission="manage_procurement" me={me}><ProducePage mode="buyers" canReveal={me.permissions.includes('reveal_buyer_contact')}/></Guard>} /><Route path="/ledgers" element={<Guard permission="manage_procurement" me={me}><ProducePage mode="ledgers" canReveal={me.permissions.includes('reveal_buyer_contact')}/></Guard>} /><Route path="/inputs" element={<Guard permission="manage_procurement" me={me}><InputsMarketplacePage/></Guard>} /><Route path="/organic-inputs" element={<Guard permission={['manage_marketplace_catalog', 'manage_marketplace_suppliers', 'manage_marketplace_qc', 'manage_marketplace_procurement']} me={me}><OrganicInputsAdminPage permissions={me.permissions}/></Guard>} /><Route path="/fpo-crop-board" element={<Guard permission="view_fpo_board" me={me}><FpoCropBoardPage/></Guard>} /><Route path="/crop-intelligence" element={<Guard permission="view_crop_intelligence" me={me}><CropIntelligencePage/></Guard>} /><Route path="/organic-pilot" element={<Guard permission="view_dashboard" me={me}><OrganicPilotPage/></Guard>} /><Route path="/organic-content" element={<Guard permission="manage_content" me={me}><OrganicContentPage/></Guard>} /><Route path="/organic-library-review" element={<Guard permission="manage_content" me={me}><OrganicReferenceReviewPage/></Guard>} /><Route path="/organic-certification" element={<Guard permission="manage_farmers" me={me}><OrganicCertificationPage/></Guard>} /><Route path="/support" element={<Guard permission="manage_support" me={me}><SupportPage/></Guard>} /><Route path="/ai" element={<Guard permission="view_ai" me={me}><AiPage canViewCosts={me.permissions.includes('view_ai_costs')}/></Guard>} /><Route path="/audit" element={<Guard permission="view_audit" me={me}><AuditPage/></Guard>} /><Route path="/partner-organizations" element={<Guard permission="manage_admins" me={me}><PartnerOrganizationsPage/></Guard>} /><Route path="/team" element={<Guard permission="manage_admins" me={me}><TeamPage/></Guard>} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></main></div>;
}

export default function App() {
  const [epoch, setEpoch] = useState(0);
  const state = useResource(async () => {
    try { return await api<AdminMe>('/admin/me'); }
    catch (error) { if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null; throw error; }
  }, [epoch]);
  if (state.loading) return <Loading />;
  if (state.error) return <ErrorPanel message={state.error} retry={() => void state.reload()} />;
  if (!state.data) return <Login onSuccess={() => setEpoch(x => x + 1)} />;
  return <SignedIn me={state.data} onSignedOut={() => setEpoch(x => x + 1)} />;
}

// Auto sign-out 15 minutes after sign-in (and immediately if the API reports
// the sign-in is too old), so admins see the login page instead of a 403.
function SignedIn({ me, onSignedOut }: { me: AdminMe; onSignedOut: () => void }) {
  const logout = () => void signOutAdmin(getCsrfToken()).then(onSignedOut).catch((error: Error) => window.alert(error.message));
  useEffect(() => {
    const timer = window.setTimeout(logout, msUntilSignOut());
    window.addEventListener(REAUTH_EVENT, logout);
    return () => { window.clearTimeout(timer); window.removeEventListener(REAUTH_EVENT, logout); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return <Portal me={me} onLogout={logout} />;
}
