import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Bell, BrainCircuit, CalendarDays, ChevronRight, CircleHelp, Cpu, FileCheck2, IndianRupee, Leaf, Mail, RefreshCw, Satellite, Search, ShieldCheck, ShoppingBasket, Sprout, Tractor, UserCheck, UserPlus, Users, type LucideIcon } from 'lucide-react';
import { api } from './api';
import { Card, DataTable, ErrorPanel, Loading } from './components';
import { navigation } from './navigation';
import type { AdminMe, JsonRecord, MetricCard, Page, Procurement } from './types';
import { useResource } from './useResource';

type Overview = { cards: MetricCard[]; procurement_status_counts: Record<string, number>; generated_at: string };
type Growth = { label: string; count: number };
export function formatDashboardValue(value: unknown, money = false): string {
  if (value == null || value === '' || !['number', 'string'].includes(typeof value) || !Number.isFinite(Number(value))) return '—';
  return new Intl.NumberFormat('en-IN', money ? { style: 'currency', currency: 'INR', maximumFractionDigits: 2 } : {}).format(Number(value));
}
function Stat({ icon: Icon, label, value, note }: { icon: LucideIcon; label: string; value: string; note: string }) {
  return <article className="dashboard-stat"><div className="stat-main"><span className="dashboard-icon"><Icon size={23}/></span><div><h2>{label}</h2><strong>{value}</strong></div></div><small>{note}</small></article>;
}
function GrowthChart({ points }: { points: Growth[] }) {
  if (!points.length) return <div className="dashboard-placeholder"><Sprout/><strong>No registration history available</strong><p>Monthly registrations will appear when the analytics service returns data.</p></div>;
  const max = Math.max(1, ...points.map(p => p.count));
  const coords = points.map((p, i) => [46 + i * 550 / Math.max(1, points.length - 1), 196 - p.count / max * 160]);
  const line = coords.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join(' ');
  return <><div className="chart-legend"><span/>New farmer registrations <small>Monthly · completed months</small></div><svg className="growth-chart" viewBox="0 0 630 230" role="img" aria-label={`Monthly farmer registrations: ${points.map(p => `${p.label}: ${p.count}`).join(', ')}`}>
    <defs><linearGradient id="growth-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#198845" stopOpacity=".18"/><stop offset="100%" stopColor="#198845" stopOpacity=".01"/></linearGradient></defs>
    {[0, 1, 2, 3, 4].map(i => <g key={i}><line x1="46" x2="596" y1={196-i*40} y2={196-i*40} stroke="#dfe5df" strokeDasharray="3 4"/><text x="32" y={200-i*40} textAnchor="end">{Number((max*i/4).toFixed(1))}</text></g>)}
    <path d={`${line} L${coords.at(-1)![0]},196 L46,196 Z`} fill="url(#growth-fill)"/><path d={line} fill="none" stroke="#16823e" strokeWidth="2.5"/>
    {points.map((p,i) => <g key={p.label}><circle cx={coords[i][0]} cy={coords[i][1]} r="4" fill="#16823e"><title>{p.label}: {p.count} registrations</title></circle><text x={coords[i][0]} y="220" textAnchor="middle">{p.label}</text></g>)}
  </svg></>;
}
function MonthlyGrowth() {
  const [months, setMonths] = useState(6);
  const state = useResource(() => api<{ farmer_growth: Growth[] }>('/admin/analytics'));
  return <Card className="growth-panel"><div className="section-head"><h2>Farmer Growth</h2><div className="chart-tabs" aria-label="Chart period">{[3,6].map(n => <button key={n} aria-pressed={months===n} onClick={() => setMonths(n)}>{n}M</button>)}</div></div>{state.loading ? <p className="panel-message" role="status">Loading registration history…</p> : state.error ? <ErrorPanel message={state.error} retry={() => void state.reload()}/> : <GrowthChart points={(state.data?.farmer_growth ?? []).slice(-months)}/>}</Card>;
}
function RecentListings() {
  const state = useResource(async () => (await api<{ page: Page<Procurement> }>('/admin/procurement?page=1&page_size=5')).page);
  return <Card className="recent-panel"><div className="section-head"><h2>Recent Produce Listings</h2><Link to="/produce" aria-label="Open produce listings"><ArrowUpRight size={19}/></Link></div>{state.loading ? <p className="panel-message" role="status">Loading listings…</p> : state.error ? <ErrorPanel message={state.error} retry={() => void state.reload()}/> : state.data?.items.length ? <DataTable columns={['Farmer','Crop','District','Quantity','Status']} rows={state.data.items.map(x => [<span>{x.farmer_name ?? 'Unnamed farmer'}<small className="table-detail">{x.farmer_ref ?? '—'}</small></span>, x.crop ?? '—', x.district ?? '—', `${x.quantity ?? '—'} ${x.unit ?? ''}`, <span className={`listing-status ${x.admin_status === 'new' ? 'pending' : ''}`}>{x.admin_status.replaceAll('_',' ')}</span>])}/> : <div className="dashboard-placeholder"><ShoppingBasket/><strong>No produce listings yet</strong><p>Farmer submissions will appear here.</p></div>}<Link className="dashboard-card-footer" to="/produce">View all listings <ChevronRight size={15}/></Link></Card>;
}
function AttentionRow({ icon: Icon, label, note, value, to, tone = '' }: { icon: LucideIcon; label: string; note: string; value: string; to: string; tone?: string }) {
  return <Link className={`attention-row ${tone}`} to={to}><span className="dashboard-icon"><Icon size={23}/></span><div><strong>{label}</strong><small>{note}</small></div><b>{value}</b><ChevronRight size={18}/></Link>;
}
function RevenueStats() {
  const state = useResource(() => api<JsonRecord>('/admin/business-dashboard'));
  if (state.error) return <div className="revenue-error" role="alert">Revenue metrics unavailable. <button onClick={() => void state.reload()}>Retry</button></div>;
  return <>{[['New Today','new_farmers_today',UserPlus,'Registered today',false],['Active Farmers','active_farmers_30d',UserCheck,'Last 30 days',false],['GMV','gmv',IndianRupee,'All-time transactions',true],['Pending Payments','payment_outstanding',FileCheck2,'Outstanding amount',true]].map(([label,key,icon,note,money]) => <Stat key={String(key)} label={String(label)} icon={icon as LucideIcon} note={state.loading ? 'Loading…' : String(note)} value={formatDashboardValue(state.data?.[String(key)], Boolean(money))}/>)}</>;
}
export function DashboardPage({ me }: { me: AdminMe }) {
  const [search, setSearch] = useState('');
  const [epoch, setEpoch] = useState(0);
  const state = useResource(() => api<Overview>('/admin/dashboard'), [epoch]);
  const can = (permission: AdminMe['permissions'][number]) => me.permissions.includes(permission);
  const counts = Object.fromEntries((state.data?.cards ?? []).map(card => [card.key,card.value]));
  const value = (key: string) => formatDashboardValue(counts[key]);
  const matches = navigation.filter(item => can(item.permission) && item.label.toLowerCase().includes(search.toLowerCase()));
  return <div className="dashboard"><header className="dashboard-header"><div><h1>Command Centre</h1><p>A live, permission-controlled view of AgrowAI operations.</p></div><div className="dashboard-tools"><div className="dashboard-search"><Search size={18}/><input aria-label="Find an admin section" placeholder="Find a section…" value={search} onChange={e => setSearch(e.target.value)}/>{search && <div className="search-results">{matches.length ? matches.map(item => <Link key={item.to} to={item.to} onClick={() => setSearch('')}>{item.label}<ChevronRight size={16}/></Link>) : <p>No matching sections</p>}</div>}</div><button className="dashboard-refresh" aria-label="Refresh dashboard" disabled={state.loading} onClick={() => setEpoch(n=>n+1)}><RefreshCw size={19}/></button><span className="dashboard-date"><CalendarDays size={18}/>Live overview</span><span className="dashboard-avatar" title={`${me.full_name ?? 'Administrator'} · ${me.role}`}>{(me.full_name ?? 'A').charAt(0).toUpperCase()}</span></div></header>
    {state.loading ? <Loading/> : state.error ? <ErrorPanel message={state.error} retry={() => void state.reload()}/> : <div key={epoch}>
      <div className="dashboard-stats"><Stat icon={Users} label="Total Farmers" value={value('total_farmers')} note="Registered profiles"/><Stat icon={ShoppingBasket} label="Produce Listings" value={value('produce_listings')} note="All-time listings"/>{can('view_revenue') && <RevenueStats/>}</div>
      <div className="dashboard-grid">{can('view_analytics') ? <MonthlyGrowth/> : <Card className="growth-panel"><h2>Farmer Growth</h2><div className="dashboard-placeholder"><ShieldCheck/><strong>Analytics access required</strong><p>Your current role does not include registration history.</p></div></Card>}
      <Card className="attention-panel"><div className="section-head"><h2>Operations Attention</h2><span>Work queues</span></div><div className="dashboard-rows">{can('manage_procurement') && <AttentionRow icon={ShoppingBasket} label="New Produce Listings" note="New in procurement pipeline" value={formatDashboardValue(state.data?.procurement_status_counts.new)} to="/produce"/>}{can('view_ai') && <AttentionRow icon={Leaf} label="Disease Reports" note="Total reports · not a review queue" value={value('disease_reports')} to="/ai" tone="amber"/>}{can('manage_support') && <AttentionRow icon={CircleHelp} label="Farmer Support" note="Review issues raised by farmers" value="" to="/support"/>}{!can('manage_procurement') && !can('view_ai') && !can('manage_support') && <p className="panel-message">No work queues are available for your role.</p>}</div></Card>
      {can('manage_procurement') && <RecentListings/>}
      <Card className="health-panel"><div className="section-head"><h2>Platform Health</h2><ShieldCheck size={18}/></div><div className="dashboard-rows">{[[Cpu,'AI Service Status','Service health is not instrumented'],[Mail,'Notification Delivery','Delivery health is not instrumented'],[FileCheck2,'Report Processing','Processing health is not instrumented']].map(([icon,label,note]) => { const Icon = icon as LucideIcon; return <div className="health-row" key={String(label)}><span className="dashboard-icon"><Icon size={21}/></span><div><strong>{String(label)}</strong><small>{String(note)}</small></div><span className="health-status">Not monitored</span></div>; })}</div></Card></div>
      <div className="dashboard-bottom">{[[Tractor,'Total Farms','total_farms'],[ShieldCheck,'Disease Reports','disease_reports'],[Satellite,'Satellite Reports','satellite_reports'],[BrainCircuit,'Intelligence Reports','intelligence_reports'],[Bell,'Notifications Sent','notifications_sent']].map(([icon,label,key]) => { const Icon=icon as LucideIcon; return <div key={String(key)}><span className="dashboard-icon"><Icon size={26}/></span><div><span>{String(label)}</span><strong>{value(String(key))}</strong></div></div>; })}</div>
      <p className="dashboard-updated">Snapshot updated {state.data?.generated_at ? new Date(state.data.generated_at).toLocaleString('en-IN') : 'just now'} · Each metric shows its own reporting period.</p>
    </div>}
  </div>;
}
