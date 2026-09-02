import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ProduceListings } from './ProduceListings';
import { BuyerCRM } from './BuyerCRM';
import { ProcurementLedgers } from './ProcurementLedgers';
import { api } from './api';
import { Card, DataTable, Empty, ErrorPanel, Loading, Metric, PageTitle, formatDate } from './components';
import type { AuditRow, Farmer, JsonRecord, Page, Procurement, SupportTicket } from './types';
import { useResource } from './useResource';
import { buildProcurementPath, marketplaceAvailabilityLabel, marketplaceFarmerReference, marketplacePickupLabel, marketplacePriceLabel, marketplaceProductLabel, produceCategories, type ProcurementFilters } from './procurement';

function Resource<T>({ state, children }: { state: ReturnType<typeof useResource<T>>; children: (data: T) => React.ReactNode }) {
  if (state.loading) return <Loading />;
  if (state.error) return <ErrorPanel message={state.error} retry={() => void state.reload()} />;
  return <>{state.data && children(state.data)}</>;
}

export { DashboardPage } from './Dashboard';

export { FarmersPage } from './Farmers';

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
  return mode === 'produce' ? <ProduceListings canReveal={canReveal}/> : mode === 'buyers' ? <BuyerCRM canReveal={canReveal}/> : <ProcurementLedgers/>;
}

function LegacyProducePage({ mode, canReveal }: { mode: 'buyers'|'ledgers'; canReveal:boolean }) {
  const [params] = useSearchParams();
  const [draftFilters,setDraftFilters]=useState<ProcurementFilters>({search:params.get('search') ?? '',category:'',availabilityType:''});
  const [filters,setFilters]=useState<ProcurementFilters>(draftFilters);
  const path=buildProcurementPath(filters);
  const state = useResource(() => api<{ page: Page<Procurement> }>(path), [path]);
  const title = mode === 'buyers' ? 'Buyer CRM' : mode === 'ledgers' ? 'Procurement ledgers' : 'Sell Agricultural Produce';
  function applyFilters(event: React.FormEvent) { event.preventDefault(); setFilters({...draftFilters}); }
  function clearFilters() { const cleared={search:'',category:'',availabilityType:''}; setDraftFilters(cleared); setFilters(cleared); }
  return <><PageTitle title={title} subtitle={mode === 'buyers' ? 'Buyer search, offers and negotiation follow-up.' : mode === 'ledgers' ? 'Pickup, transaction, payment and commission records.' : 'Farmer produce listings requiring team action.'} />
    <Card className="procurement-filters"><form onSubmit={applyFilters}><label>Search listings<input value={draftFilters.search} onChange={e=>setDraftFilters({...draftFilters,search:e.target.value})} placeholder="Listing, farmer or produce"/></label><label>Category<select value={draftFilters.category} onChange={e=>setDraftFilters({...draftFilters,category:e.target.value})}><option value="">All categories</option>{produceCategories.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label>Availability<select value={draftFilters.availabilityType} onChange={e=>setDraftFilters({...draftFilters,availabilityType:e.target.value})}><option value="">All availability</option><option value="available_now">Available now</option><option value="upcoming_harvest">Upcoming harvest</option></select></label><div className="filter-actions"><button type="submit">Apply filters</button><button type="button" className="secondary-button" onClick={clearFilters}>Clear</button></div></form><small>Results remain restricted to your role and assigned operational scope.</small></Card>
    <Resource state={state}>{data => data.page.items.length ? <Card><DataTable columns={['Listing','Farmer reference','Product','Availability','Quantity','Grade & packaging','Asking price','Pickup','Operational area','Stage','Buyer','Contact','Offer']} rows={data.page.items.map(x => [x.listing_ref ?? x.offer_id.slice(0,8), marketplaceFarmerReference(x), marketplaceProductLabel(x), <span><strong>{marketplaceAvailabilityLabel(x)}</strong>{x.harvest_date&&<small className="table-detail">Harvest {formatDate(x.harvest_date)}</small>}</span>, `${x.quantity} ${x.unit}`, [x.variety,x.expected_grade,x.packaging].filter(Boolean).join(' · ') || 'Not provided', marketplacePriceLabel(x), marketplacePickupLabel(x), [x.village,x.district].filter(Boolean).join(', ') || '—', x.admin_status.replaceAll('_',' '), x.buyer_name ?? 'Not assigned', <BuyerContact offerId={x.offer_id} initial={x.buyer_contact_masked ? null : x.buyer_contact} canReveal={canReveal}/>, mode === 'ledgers' ? <LedgerSummary offerId={x.offer_id}/> : (x.buyer_offer_price ? `₹${x.buyer_offer_price}` : '—')])} /></Card> : <Empty title="No produce listings" body="No farmer listings matched these filters in your authorised scope." />}</Resource></>;
}

export function SupportPage() {
  const [status, setStatus] = useState('');
  const [active, setActive] = useState<string | null>(null);
  const [response, setResponse] = useState('');
  const path = `/admin/support-tickets?page=1&page_size=100${status ? `&status=${encodeURIComponent(status)}` : ''}`;
  const state = useResource(() => api<Page<SupportTicket>>(path), [path]);
  async function update(ticket: SupportTicket, nextStatus?: SupportTicket['status']) {
    await api<SupportTicket>(`/admin/support-tickets/${ticket.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: nextStatus, response: response.trim() || undefined }),
    });
    setResponse(''); setActive(null); await state.reload();
  }
  return <><PageTitle title="Farmer Support" subtitle="Review farmer-reported issues, respond, and track them through resolution." />
    <Card className="support-toolbar"><label>Status<select value={status} onChange={event => setStatus(event.target.value)}><option value="">All tickets</option><option value="open">Open</option><option value="in_progress">In progress</option><option value="waiting_for_farmer">Waiting for farmer</option><option value="resolved">Resolved</option><option value="closed">Closed</option></select></label><button className="secondary-button" onClick={() => void state.reload()}>Refresh</button></Card>
    <Resource state={state}>{page => page.items.length ? <div className="support-grid">{page.items.map(ticket => <Card key={ticket.id} className="support-ticket"><div className="support-ticket-head"><div><small>{ticket.farmer_ref ?? 'Farmer reference unavailable'} · {ticket.category.replaceAll('_', ' ')}</small><h2>{ticket.subject}</h2></div><span className={`ticket-priority ${ticket.priority}`}>{ticket.priority}</span></div><p>{ticket.description}</p><div className="ticket-meta"><strong>{ticket.status.replaceAll('_', ' ')}</strong><span>{formatDate(ticket.created_at)}</span>{ticket.app_version && <span>App {ticket.app_version}</span>}</div>{ticket.messages.length > 1 && <div className="ticket-thread">{ticket.messages.slice(1).map(message => <p key={message.id}><strong>{message.author_type === 'admin' ? 'Support' : 'Farmer'}:</strong> {message.message}</p>)}</div>}{active === ticket.id ? <div className="support-response"><textarea rows={4} value={response} onChange={event => setResponse(event.target.value)} placeholder="Write a clear response for the farmer" maxLength={4000}/><div><button disabled={!response.trim()} onClick={() => void update(ticket, 'waiting_for_farmer')}>Send reply</button><button className="secondary-button" onClick={() => { setActive(null); setResponse(''); }}>Cancel</button></div></div> : <div className="ticket-actions"><button onClick={() => setActive(ticket.id)}>Reply</button><button className="secondary-button" onClick={() => void update(ticket, 'in_progress')}>Start work</button><button className="secondary-button" onClick={() => void update(ticket, 'resolved')}>Resolve</button></div>}</Card>)}</div> : <Empty title="No support tickets" body="No farmer issues matched this status." />}</Resource>
  </>;
}

export { CropIntelligencePage } from './CropIntelligence';

export { AiPage } from './AiMonitoring';

export { AuditPage } from './AuditRecords';

export { FarmsPage } from './Farms';

export { TeamPage } from './TeamPermissions';

function LegacyTeamPage() {
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
