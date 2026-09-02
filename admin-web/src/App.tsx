import { useState } from 'react';
import { Leaf, LogOut, Menu, X } from 'lucide-react';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { api, ApiError, getCsrfToken } from './api';
import { signOutAdmin } from './auth';
import { Login } from './Login';
import { ErrorPanel, Loading } from './components';
import { navigation } from './navigation';
import { AiPage, AuditPage, CropIntelligencePage, DashboardPage, FarmersPage, FarmsPage, ProducePage, SupportPage, TeamPage } from './pages';
import type { AdminMe, Permission } from './types';
import { useResource } from './useResource';

function Guard({ permission, me, children }: { permission: Permission; me: AdminMe; children: React.ReactNode }) {
  return me.permissions.includes(permission) ? <>{children}</> : <Navigate to="/" replace />;
}

function Portal({ me, onLogout }: { me: AdminMe; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const allowed = navigation.filter(item => me.permissions.includes(item.permission));
  return <div className="portal"><aside className={open ? 'open' : ''}><div className="sidebar-brand"><div className="brand-mark small"><Leaf size={32}/></div><div><strong>AgrowAI</strong><span>ADMIN</span></div><button className="icon-button close" onClick={() => setOpen(false)} aria-label="Close navigation"><X/></button></div><nav>{allowed.map(({to,label,icon:Icon}) => <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)}><Icon size={19}/><span>{label}</span>{to === '/produce' && <small className="nav-new">NEW</small>}</NavLink>)}</nav><div className="admin-profile"><div className="profile-name"><span className="dashboard-avatar">{(me.full_name ?? 'A').charAt(0).toUpperCase()}</span><span>{me.full_name ?? 'AgrowAI team member'}</span></div><small>{me.role.replaceAll('_',' ')}</small><button onClick={onLogout}>Sign out <LogOut size={16}/></button></div></aside>{open && <button className="scrim" aria-label="Close navigation" onClick={() => setOpen(false)} />}<main className="content"><div className="mobile-bar"><button className="icon-button" onClick={() => setOpen(true)} aria-label="Open navigation"><Menu/></button><strong>AgrowAI Admin</strong><span className="secure-dot">Secure</span></div><Routes><Route path="/" element={<Guard permission="view_dashboard" me={me}><DashboardPage me={me}/></Guard>} /><Route path="/farmers" element={<Guard permission="manage_farmers" me={me}><FarmersPage/></Guard>} /><Route path="/farms" element={<Guard permission="view_analytics" me={me}><FarmsPage/></Guard>} /><Route path="/produce" element={<Guard permission="manage_procurement" me={me}><ProducePage canReveal={me.permissions.includes("reveal_buyer_contact")}/></Guard>} /><Route path="/buyers" element={<Guard permission="manage_procurement" me={me}><ProducePage mode="buyers" canReveal={me.permissions.includes("reveal_buyer_contact")}/></Guard>} /><Route path="/ledgers" element={<Guard permission="manage_procurement" me={me}><ProducePage mode="ledgers" canReveal={me.permissions.includes("reveal_buyer_contact")}/></Guard>} /><Route path="/crop-intelligence" element={<Guard permission="view_crop_intelligence" me={me}><CropIntelligencePage/></Guard>} /><Route path="/support" element={<Guard permission="manage_support" me={me}><SupportPage/></Guard>} /><Route path="/ai" element={<Guard permission="view_ai" me={me}><AiPage canViewCosts={me.permissions.includes("view_ai_costs")}/></Guard>} /><Route path="/audit" element={<Guard permission="view_audit" me={me}><AuditPage/></Guard>} /><Route path="/team" element={<Guard permission="manage_admins" me={me}><TeamPage/></Guard>} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></main></div>;
}

export default function App() {
  const [epoch, setEpoch] = useState(0);
  const state = useResource(async () => {
    try { return await api<AdminMe>('/admin/me'); }
    catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null;
      throw error;
    }
  }, [epoch]);
  if (state.loading) return <Loading />;
  if (state.error) return <ErrorPanel message={state.error} retry={() => void state.reload()} />;
  if (!state.data) return <Login onSuccess={() => setEpoch(x => x + 1)} />;
  return <Portal me={state.data} onLogout={() => void signOutAdmin(getCsrfToken()).then(() => setEpoch(x => x + 1)).catch((error: Error) => window.alert(error.message))} />;
}
