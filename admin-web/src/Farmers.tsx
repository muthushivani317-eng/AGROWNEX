import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Download, Leaf, MapPin, RefreshCw, Search, ShieldCheck, Sprout, Tractor, Trash2, Users } from 'lucide-react';
import { api } from './api';
import { DataTable, ErrorPanel, Loading, formatDate } from './components';
import type { Farmer, Page } from './types';
import { useResource } from './useResource';
import './Farmers.css';

export function maskFarmerPhone(phone: string | null) {
  if (!phone) return '—';
  const digits = phone.replace(/\D/g, '');
  return digits.length > 4 ? `•••••• ${digits.slice(-4)}` : '••••';
}
export function farmerDirectoryPath(search: string, district: string, crop: string, page: number, size: number) {
  const params = new URLSearchParams({ page: String(page), page_size: String(size) });
  for (const [key, value] of Object.entries({ search, district, crop })) if (value.trim()) params.set(key, value.trim());
  return `/admin/farmers?${params}`;
}
export function directoryCsv(rows: Farmer[]) {
  const cell = (value: unknown) => { const text = String(value ?? ''); return `"${(/^[\s]*[=+@-]/.test(text) ? "'" + text : text).replaceAll('"','""')}"`; };
  return [['Reference','Farmer','Phone (masked)','District','Crop','Farms','Joined'], ...rows.map(x => [x.farmer_ref, x.full_name, maskFarmerPhone(x.phone_number), x.district, x.primary_crop, x.farm_count, x.created_at])].map(row => row.map(cell).join(',')).join('\r\n');
}
function distribution(rows: Farmer[], key: 'district' | 'primary_crop') {
  const counts = new Map<string, number>();
  rows.forEach(row => { const label = row[key] || 'Not specified'; counts.set(label, (counts.get(label) ?? 0) + 1); });
  return [...counts].sort((a,b) => b[1]-a[1]);
}
export function FarmersPage({ canDelete = false }: { canDelete?: boolean }) {
  const [draft, setDraft] = useState({ search: '', district: '', crop: '' });
  const [filters, setFilters] = useState(draft);
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(10);
  const [selected, setSelected] = useState<string | null>(null);
  const path = farmerDirectoryPath(filters.search, filters.district, filters.crop, page, size);
  // A keyed resource prevents an older in-flight search from replacing a newer result.
  return <div className="farmer-directory"><div className="directory-topbar"><div><Link to="/">Operations</Link><ChevronRight size={16}/><strong>Farmers</strong></div><span><ShieldCheck size={16}/>Authorised directory</span></div><DirectoryResults key={path} {...{path,draft,setDraft,setFilters,page,setPage,size,setSize,selected,setSelected,canDelete}}/></div>;
}
type ResultsProps = { path: string; draft: { search: string; district: string; crop: string }; setDraft: React.Dispatch<React.SetStateAction<ResultsProps['draft']>>; setFilters: React.Dispatch<React.SetStateAction<ResultsProps['draft']>>; page: number; setPage: (n:number)=>void; size:number; setSize:(n:number)=>void; selected:string|null; setSelected:(id:string|null)=>void; canDelete:boolean };
function DirectoryResults({path,draft,setDraft,setFilters,page,setPage,size,setSize,selected,setSelected,canDelete}: ResultsProps) {
  const state = useResource(() => api<Page<Farmer>>(path));
  const rows = state.data?.items ?? [];
  const districts = distribution(rows,'district');
  const crops = distribution(rows,'primary_crop');
  const current = rows.find(x => x.user_id === selected);
  function clear() { const empty = {search:'',district:'',crop:''}; setDraft(empty); setFilters(empty); setPage(1); setSelected(null); }
  function exportPage() { const url = URL.createObjectURL(new Blob(['\uFEFF',directoryCsv(rows)], {type:'text/csv;charset=utf-8'})); const a=document.createElement('a'); a.href=url; a.download=`agrowai-farmers-page-${page}.csv`; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000); }
  return <div className="directory-layout"><section className="directory-main"><header className="directory-heading"><div><h1>Farmers</h1><p>View and manage registered farmer records within your authorised scope.</p></div><div><button className="directory-refresh" onClick={()=>void state.reload()} disabled={state.loading}><RefreshCw size={16}/>Refresh</button>{canDelete&&<FirebaseSyncButton onDone={()=>void state.reload()}/>}<button className="directory-export" onClick={exportPage} disabled={!rows.length || state.loading || !!state.error}><Download size={16}/>Export page</button></div></header>
    <div className="directory-stats">{[[Users,'Matching Farmers',state.data?.total,'Across all result pages'],[Tractor,'Farms on This Page',rows.reduce((n,x)=>n+x.farm_count,0),'Registered farms'],[Sprout,'Crop Types',crops.filter(([label])=>label!=='Not specified').length,'On this page'],[MapPin,'Districts',districts.filter(([label])=>label!=='Not specified').length,'On this page']].map(([icon,label,value,note]) => { const Icon=icon as typeof Users; return <article key={String(label)}><span className="dashboard-icon"><Icon size={25}/></span><div><p>{String(label)}</p><strong>{state.loading || state.error ? '—' : String(value ?? '—')}</strong><small>{String(note)}</small></div></article>; })}</div>
    <section className="directory-table-card" aria-label="Farmer directory"><form className="directory-filters" onSubmit={e=>{e.preventDefault();setFilters({...draft});setPage(1);setSelected(null);}}><label className="directory-search"><Search size={18}/><input aria-label="Search by farmer, reference or phone" placeholder="Search by farmer, reference or phone" value={draft.search} onChange={e=>setDraft({...draft,search:e.target.value})}/></label><input aria-label="District filter" placeholder="District" list="directory-districts" value={draft.district} onChange={e=>setDraft({...draft,district:e.target.value})}/><datalist id="directory-districts">{districts.filter(([x])=>x!=='Not specified').map(([x])=><option key={x} value={x}/>)}</datalist><input aria-label="Crop filter" placeholder="Crop" list="directory-crops" value={draft.crop} onChange={e=>setDraft({...draft,crop:e.target.value})}/><datalist id="directory-crops">{crops.filter(([x])=>x!=='Not specified').map(([x])=><option key={x} value={x}/>)}</datalist><button type="submit">Apply filters</button><button type="button" className="directory-clear" onClick={clear}>Clear filters</button></form>
    {state.loading ? <Loading/> : state.error ? <ErrorPanel message={state.error} retry={()=>void state.reload()}/> : rows.length ? <DataTable columns={['Reference','Farmer','Phone','District','Primary crop','Farms','Joined','Actions']} rows={rows.map(x=>[x.farmer_ref ?? '—',<span className="farmer-identity"><span className="farmer-avatar">{(x.full_name ?? '?').split(/\s+/).map(s=>s.charAt(0)).slice(0,2).join('')}</span><strong>{x.full_name ?? 'Unnamed farmer'}</strong></span>,maskFarmerPhone(x.phone_number),x.district ?? '—',<span className="farmer-crop">{x.primary_crop ?? 'Not specified'}</span>,x.farm_count,formatDate(x.created_at),<button className="farmer-view" aria-expanded={selected===x.user_id} onClick={()=>setSelected(selected===x.user_id ? null : x.user_id)}>{selected===x.user_id ? 'Close' : 'View'}</button>])}/> : <div className="directory-empty"><Users size={30}/><h2>No farmers found</h2><p>Try a different name, reference, phone, district or crop.</p><button onClick={clear}>Clear filters</button></div>}
    <footer className="directory-pagination"><span aria-live="polite">{state.loading ? 'Loading records…' : state.error ? 'Records unavailable' : `Showing ${rows.length ? (page-1)*size+1 : 0}–${(page-1)*size+rows.length} of ${state.data?.total ?? 0} farmers`}</span><label>Rows per page<select value={size} onChange={e=>{setSize(Number(e.target.value));setPage(1);setSelected(null);}}>{[10,25,50].map(n=><option key={n}>{n}</option>)}</select></label><div><button aria-label="Previous page" disabled={page===1 || state.loading} onClick={()=>{setPage(page-1);setSelected(null);}}><ChevronLeft size={17}/></button><span>Page {page}</span><button aria-label="Next page" disabled={state.loading || !!state.error || page >= (state.data?.total_pages ?? 1)} onClick={()=>{setPage(page+1);setSelected(null);}}><ChevronRight size={17}/></button></div></footer></section>
    {current && !state.loading && !state.error && <section className="farmer-record" aria-label="Selected farmer record"><div><h2>{current.full_name ?? 'Unnamed farmer'}</h2><button className="farmer-view" onClick={()=>setSelected(null)}>Close</button></div><dl>{[['Reference',current.farmer_ref],['Phone',maskFarmerPhone(current.phone_number)],['Village',current.village],['District',current.district],['Primary crop',current.primary_crop],['Farms',current.farm_count],['Joined',formatDate(current.created_at)]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value ?? 'Not provided'}</dd></div>)}</dl>{canDelete&&<DeleteFarmer farmer={current} onDeleted={()=>{setSelected(null);void state.reload();}}/>}</section>}
  </section><section className="directory-insights" aria-label="Directory insights"><h2>Directory insights</h2><p className="insights-scope">Based on this result page</p>{[[MapPin,'District coverage',districts],[Leaf,'Crop mix',crops]].map(([icon,title,items])=>{const Icon=icon as typeof Leaf;return <div className="insights-group" key={String(title)}><h3><Icon size={20}/>{String(title)}</h3>{state.loading ? <p>Loading…</p> : state.error ? <p>Unavailable</p> : (items as [string,number][]).length ? (items as [string,number][]).map(([label,count])=><div key={label}><span>{label}</span><strong>{count}</strong></div>) : <p>No records on this page</p>}</div>;})}<div className="directory-privacy"><ShieldCheck size={20}/><p>Phone numbers are masked in this view and exported files.</p></div></section></div>;
}

function FirebaseSyncButton({ onDone }: { onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  async function sync() {
    setBusy(true); setNote('');
    try {
      const r = await api<{ checked: number; closed: number; aborted: boolean }>('/admin/farmers/sync-firebase', { method: 'POST' });
      setNote(r.aborted ? 'Stopped: too many accounts looked missing — check Firebase.' : r.closed ? `Removed ${r.closed} farmer(s) deleted in Firebase.` : 'Already in sync with Firebase.');
      onDone();
    } catch (e) { setNote(e instanceof Error ? e.message : 'Sync failed.'); }
    finally { setBusy(false); }
  }
  return <><button className="directory-refresh" onClick={() => void sync()} disabled={busy} title="Remove farmers whose Firebase account was deleted"><RefreshCw size={16}/>{busy ? 'Syncing…' : 'Sync with Firebase'}</button>{note && <small className="directory-sync-note" role="status">{note}</small>}</>;
}

function DeleteFarmer({ farmer, onDeleted }: { farmer: Farmer; onDeleted: () => void }) {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const ref = farmer.farmer_ref ?? '';
  async function remove() {
    setBusy(true); setError('');
    try {
      await api(`/admin/farmers/${farmer.user_id}?${new URLSearchParams({ confirm_ref: typed.trim() })}`, { method: 'DELETE' });
      onDeleted();
    } catch (e) { setError(e instanceof Error ? e.message : 'Delete failed.'); }
    finally { setBusy(false); }
  }
  if (!open) return <button className="farmer-delete" onClick={() => setOpen(true)}><Trash2 size={16}/>Delete farmer</button>;
  return <div className="farmer-delete-confirm">
    <p><strong>Delete {farmer.full_name ?? ref}?</strong> Their Firebase login is deleted and they disappear from the admin portal. History (orders, ledgers, audit) is kept.</p>
    <label>Type <code>{ref}</code> to confirm<input value={typed} onChange={e => setTyped(e.target.value)} autoFocus/></label>
    {error && <p className="form-error">{error}</p>}
    <div><button className="secondary-button" onClick={() => { setOpen(false); setTyped(''); }}>Cancel</button><button className="farmer-delete" disabled={busy || typed.trim().toUpperCase() !== ref.toUpperCase()} onClick={() => void remove()}>{busy ? 'Deleting…' : 'Delete permanently'}</button></div>
  </div>;
}
