import { useState } from 'react';
import { api } from './api';
import { Card, DataTable, Empty, ErrorPanel, Loading, Metric, PageTitle, formatDate } from './components';
import type { AuditRow, Farmer, JsonRecord, MetricCard, Page, Procurement } from './types';
import { useResource } from './useResource';

function Resource<T>({ state, children }: { state: ReturnType<typeof useResource<T>>; children: (data: T) => React.ReactNode }) {
  if (state.loading) return <Loading />;
  if (state.error) return <ErrorPanel message={state.error} retry={() => void state.reload()} />;
  return <>{state.data && children(state.data)}</>;
}

function BusinessMetrics() {
  const business = useResource(() => api<JsonRecord>('/admin/business-dashboard'));
  return <Resource state={business}>{data => <div className="metrics">{Object.entries(data).filter(([k]) => !['generated_at','currency','procurement_status_counts'].includes(k)).slice(0, 12).map(([key, value]) => <Metric key={key} label={key} value={typeof value === 'object' ? '—' : String(value ?? '—')} />)}</div>}</Resource>;
}

export function DashboardPage({ canViewRevenue }: { canViewRevenue: boolean }) {
  const dashboard = useResource(() => api<{ cards: MetricCard[]; procurement_status_counts: Record<string, number> }>('/admin/dashboard'));
  return <><PageTitle title="Command centre" subtitle="A live, permission-controlled view of AgrowAI operations." />
    {canViewRevenue && <BusinessMetrics />}
    <Resource state={dashboard}>{data => <Card><div className="section-head"><h2>Platform coverage</h2><span>Verified backend metrics</span></div><div className="metrics compact">{data.cards.map(card => <Metric key={card.key} label={card.key} value={card.value} />)}</div></Card>}</Resource>
  </>;
}

export function FarmersPage() {
  const state = useResource(() => api<Page<Farmer>>('/admin/farmers?page=1&page_size=50'));
  return <><PageTitle title="Farmers" subtitle="Registered farmer records available to your authorised scope." /><Resource state={state}>{data => data.items.length ? <Card><DataTable columns={['Reference','Farmer','Phone','Location','Crop','Farms','Joined']} rows={data.items.map(x => [x.farmer_ref ?? '—', x.full_name ?? 'Unnamed', x.phone_number ?? '—', [x.village,x.district].filter(Boolean).join(', ') || '—', x.primary_crop ?? '—', x.farm_count, formatDate(x.created_at)])} /></Card> : <Empty title="No farmers in this scope" body="No verified farmer records matched your current access scope." />}</Resource></>;
}

function BuyerContact({ offerId, initial, canReveal }: { offerId:string; initial:string|null; canReveal:boolean }) {
  const [contact,setContact]=useState(initial); const [busy,setBusy]=useState(false);
  async function reveal(){setBusy(true);try{const result=await api<{buyer_contact:string}>(`/admin/procurement/${offerId}/buyer-contact/reveal`,{method:'POST'});setContact(result.buyer_contact)}finally{setBusy(false)}}
  if(contact) return <span>{contact}</span>;
  return canReveal?<button className="table-action" disabled={busy} onClick={()=>void reveal()}>{busy?'Revealing…':'Reveal contact'}</button>:<span>Restricted</span>;
}

function LedgerSummary({ offerId }: { offerId:string }) {
  const [ledger,setLedger]=useState<JsonRecord|null>(null); const [busy,setBusy]=useState(false);
  async function load(){setBusy(true);try{setLedger(await api<JsonRecord>(`/admin/procurement/${offerId}/ledger`))}finally{setBusy(false)}}
  if(!ledger) return <button className="table-action" disabled={busy} onClick={()=>void load()}>{busy?'Loading…':'View ledger'}</button>;
  const transaction=ledger.transaction as JsonRecord|null;
  return <span>{transaction?`₹${String(transaction.gross_amount)} · `:''}{((ledger.payments??[]) as unknown[]).length} payments · {((ledger.commissions??[]) as unknown[]).length} commissions</span>;
}

export function ProducePage({ mode = 'produce', canReveal = false }: { mode?: 'produce'|'buyers'|'ledgers'; canReveal?:boolean }) {
  const state = useResource(() => api<{ page: Page<Procurement> }>('/admin/procurement?page=1&page_size=50'));
  const title = mode === 'buyers' ? 'Buyer CRM' : mode === 'ledgers' ? 'Procurement ledgers' : 'Sell My Produce';
  return <><PageTitle title={title} subtitle={mode === 'buyers' ? 'Buyer search, offers and negotiation follow-up.' : mode === 'ledgers' ? 'Pickup, transaction, payment and commission records.' : 'Farmer produce listings requiring team action.'} />
    <Resource state={state}>{data => data.page.items.length ? <Card><DataTable columns={['Listing','Farmer','Crop','Quantity','Harvest','Location','Stage','Buyer','Contact','Offer']} rows={data.page.items.map(x => [x.listing_ref ?? x.offer_id.slice(0,8), x.farmer_ref ?? x.farmer_name ?? '—', x.crop ?? '—', `${x.quantity} ${x.unit}`, formatDate(x.harvest_date), [x.village,x.district].filter(Boolean).join(', ') || '—', x.admin_status.replaceAll('_',' '), x.buyer_name ?? 'Not assigned', <BuyerContact offerId={x.offer_id} initial={x.buyer_contact_masked ? null : x.buyer_contact} canReveal={canReveal}/>, mode === 'ledgers' ? <LedgerSummary offerId={x.offer_id}/> : (x.buyer_offer_price ? `₹${x.buyer_offer_price}` : '—')])} /></Card> : <Empty title="No produce listings" body="New farmer listings will appear here automatically after backend submission." />}</Resource></>;
}

export function CropIntelligencePage() {
  const state = useResource(() => api<JsonRecord>('/admin/crop-intelligence?harvest_days=30'));
  return <><PageTitle title="Crop intelligence" subtitle="Registered crop, acreage, stage and 30-day harvest signals." /><Resource state={state}>{data => { const summary = (data.summary ?? {}) as JsonRecord; return <><div className="metrics">{Object.entries(summary).map(([k,v]) => <Metric key={k} label={k} value={String(v ?? '—')} />)}</div><Card><h2>Supply by crop</h2><DataTable columns={['Crop','Farms','Farmers','Known hectares']} rows={((data.by_crop ?? []) as JsonRecord[]).map(x => [String(x.label),String(x.farm_count),String(x.farmer_count),String(x.known_area_hectares)])} /></Card></>; }}</Resource></>;
}

function AiCosts() {
  const state = useResource(() => api<JsonRecord>('/admin/ai-costs?window_days=30'));
  return <Resource state={state}>{data => <Card><h2>AI cost — last 30 days</h2><div className="metrics compact"><Metric label="requests" value={String(data.total_requests ?? '—')}/><Metric label="cost INR" value={String(data.total_cost_inr ?? '—')}/></div></Card>}</Resource>;
}

export function AiPage({ canViewCosts }: { canViewCosts: boolean }) {
  const state = useResource(() => api<JsonRecord>('/admin/ai'));
  return <><PageTitle title="AI monitoring" subtitle="Production requests, abstentions and service health—not model accuracy." /><Resource state={state}>{data => <div className="metrics">{Object.entries(data).filter(([,v]) => typeof v !== 'object').map(([k,v]) => <Metric key={k} label={k} value={String(v ?? '—')} />)}</div>}</Resource>{canViewCosts&&<AiCosts/>}</>;
}

export function AuditPage() {
  const state = useResource(() => api<Page<AuditRow>>('/admin/audit?page=1&page_size=50'));
  return <><PageTitle title="Audit records" subtitle="Immutable record of privileged access and operational actions." /><Resource state={state}>{data => <Card><DataTable columns={['Time','Role','Action','Target','Reference']} rows={data.items.map(x => [formatDate(x.created_at), x.role ?? 'System', x.action.replaceAll('_',' '), x.target ?? '—', x.target_id ?? '—'])} /></Card>}</Resource></>;
}

export function FarmsPage() {
  const state = useResource(() => api<JsonRecord>('/admin/analytics'));
  return <><PageTitle title="Farms" subtitle="Crop and geographic distribution across registered farms." /><Resource state={state}>{data => <div className="split">{['crop_distribution','farmer_growth','produce_by_crop'].map(key => <Card key={key}><h2>{key.replaceAll('_',' ')}</h2><DataTable columns={['Label','Count']} rows={((data[key] ?? []) as JsonRecord[]).map(x => [String(x.label),String(x.count)])} /></Card>)}</div>}</Resource></>;
}

export function TeamPage() {
  type TeamMember = { id:string; full_name:string|null; email:string|null; role:string; status:string; created_at:string };
  const state = useResource(() => api<TeamMember[]>('/admin/team'));
  const [email,setEmail]=useState('');
  const [role,setRole]=useState('procurement_manager');
  const [district,setDistrict]=useState('');
  const [invite,setInvite]=useState<string|null>(null);
  const [error,setError]=useState<string|null>(null);
  async function create(event: React.FormEvent) {
    event.preventDefault(); setError(null);
    try {
      const result=await api<{token:string}>('/admin/invitations',{method:'POST',body:JSON.stringify({email,role,district_scope:role==='district_manager'?district:null,expires_in_hours:48})});
      setInvite(result.token); setEmail('');
    } catch(e) { setError(e instanceof Error?e.message:'Invitation failed.'); }
  }
  async function status(id:string,next:string) {
    await api(`/admin/team/${id}/status`,{method:'PUT',body:JSON.stringify({status:next})});
    await state.reload();
  }
  return <><PageTitle title="Team & permissions" subtitle="Owner-controlled access. There is no public Admin registration."/><div className="split"><Card><h2>Invite a team member</h2><form className="stack" onSubmit={create}><label>Work email<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required/></label><label>Role<select value={role} onChange={e=>setRole(e.target.value)}><option value="procurement_manager">Procurement manager</option><option value="agriculture_officer">Agriculture officer</option><option value="district_manager">District manager</option><option value="customer_support">Customer support</option><option value="super_admin">Super admin</option></select></label>{role==='district_manager'&&<label>District scope<input value={district} onChange={e=>setDistrict(e.target.value)} required/></label>}{error&&<p className="form-error">{error}</p>}<button>Create 48-hour invitation</button>{invite&&<div className="invite-token"><strong>Copy this once</strong><code>{invite}</code><small>Only its hash is stored. Send it through a trusted channel.</small></div>}</form></Card><Card><h2>Current team</h2><Resource state={state}>{rows=><DataTable columns={['Member','Role','Status','Action']} rows={rows.map(x=>[x.full_name??x.email??'Unnamed',x.role.replaceAll('_',' '),x.status,<button disabled={x.role==='owner'} onClick={()=>void status(x.id,x.status==='active'?'suspended':'active')}>{x.status==='active'?'Suspend':'Reactivate'}</button>])}/>}</Resource></Card></div></>;
}
