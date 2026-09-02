import { useState } from 'react';
import { CalendarDays, CheckCircle2, CircleHelp, Download, FileClock, Info, Lightbulb, RefreshCw, Search, ShieldCheck, Users } from 'lucide-react';
import { api } from './api';
import { DataTable, ErrorPanel, Loading } from './components';
import type { AuditRow, Page } from './types';
import { useResource } from './useResource';
import './AuditRecords.css';

export function auditPath(action: string, target: string, page: number, size: number) {
  const params = new URLSearchParams({ page: String(page), page_size: String(size) });
  if (action.trim()) params.set('action', action.trim());
  if (target.trim()) params.set('target', target.trim());
  return `/admin/audit?${params}`;
}
export function auditTimestamp(value: string) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return `${value} · Time not recorded`;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Timestamp unavailable' : new Intl.DateTimeFormat('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'medium' }).format(date);
}
export function auditDay(value: string) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' }).format(date);
}
export function auditModule(action: string) {
  const known: Record<string, string> = { view_ai: 'AI Monitoring', view_ai_costs: 'AI Monitoring', view_dashboard: 'Overview', view_analytics: 'Analytics', view_crop_intelligence: 'Crop Intelligence', view_audit: 'Governance', view_farmers: 'Farmers', view_farmer_detail: 'Farmers', view_procurement: 'Procurement' };
  return known[action] ?? 'Other';
}
export function auditCoverage(row: AuditRow): [string, string][] {
  return [
    ['Action captured', row.action ? 'Available' : 'Missing'],
    ['Role captured', row.role ? 'Available' : 'Missing'],
    ['Date captured', auditDay(row.created_at) ? 'Available' : 'Missing'],
    ['Precise timestamp', /T\d{2}:\d{2}:\d{2}/.test(row.created_at) && auditDay(row.created_at) ? 'Available' : 'Missing'],
    ['Actor ID', row.admin_id ? 'Available' : 'Not recorded'],
    ['Target reference', row.target_id ? 'Available' : 'Not recorded'],
    ['Request correlation', 'Not reported'],
  ];
}
export function searchAudit(rows: AuditRow[], search: string, role: string) {
  const query = search.trim().toLowerCase();
  return rows.filter(row => (!role || row.role === role) && (!query || [row.id, row.action, row.action.replaceAll('_', ' '), row.target, row.target_id, row.role].some(value => value?.toLowerCase().includes(query))));
}
export function auditCsv(rows: AuditRow[]) {
  const values = [['Record ID', 'Timestamp (original)', 'Role', 'Action', 'Target', 'Reference'], ...rows.map(r => [r.id, r.created_at, r.role ?? '', r.action, r.target ?? '', r.target_id ?? ''])];
  return values.map(row => row.map(value => { const safe = /^[\s]*[=+\-@]/.test(value) ? `'${value}` : value; return `"${safe.replaceAll('"','""')}"`; }).join(',')).join('\r\n');
}
function exportRows(rows: AuditRow[]) {
  const url = URL.createObjectURL(new Blob(['\uFEFF', auditCsv(rows)], { type: 'text/csv;charset=utf-8' }));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'agrowai-audit-visible-records.csv'; anchor.click(); URL.revokeObjectURL(url);
}
export function AuditPage() {
  const [draft, setDraft] = useState({ action: '', target: '' });
  const [filters, setFilters] = useState(draft);
  const [page, setPage] = useState(1); const [size, setSize] = useState(20);
  const path = auditPath(filters.action, filters.target, page, size);
  return <div className="audit-records"><nav className="audit-breadcrumb" aria-label="Breadcrumb"><span>Governance</span><span>/</span><strong>Audit Records</strong></nav>
    <header className="audit-heading"><div><h1>Audit Records</h1><p>Trace privileged access and operational actions across AgrowAI.</p></div><span className="audit-readonly"><ShieldCheck size={17} aria-hidden="true"/>Read-only history</span></header>
    <details className="audit-advanced"><summary>Search full history{filters.action || filters.target ? ' · Filters applied' : ''}</summary><form className="audit-server-filters" onSubmit={e => { e.preventDefault(); setFilters({ ...draft }); setPage(1); }}><label>Action code<input placeholder="All actions · e.g. view_ai" value={draft.action} onChange={e => setDraft({ ...draft, action: e.target.value })}/></label><label>Target type<input placeholder="All targets · e.g. farmer" value={draft.target} onChange={e => setDraft({ ...draft, target: e.target.value })}/></label><button>Apply filters</button><button type="button" className="audit-secondary" onClick={() => { const empty = { action: '', target: '' }; setDraft(empty); setFilters(empty); setPage(1); }}>Clear</button><small>Exact codes · searches the full audit history</small></form></details>
    <AuditResults key={path} path={path} page={page} size={size} setPage={setPage} setSize={value => { setSize(value); setPage(1); }}/>
  </div>;
}
function AuditResults({ path, page, size, setPage, setSize }: { path: string; page: number; size: number; setPage: (page: number) => void; setSize: (size: number) => void }) {
  const state = useResource(() => api<Page<AuditRow>>(path));
  const [search, setSearch] = useState(''); const [role, setRole] = useState(''); const [selected, setSelected] = useState<AuditRow | null>(null);
  const [module, setModule] = useState(''); const [day, setDay] = useState(''); const [action, setAction] = useState('');
  if (state.loading) return <Loading/>;
  if (state.error) return <ErrorPanel message={state.error} retry={() => void state.reload()}/>;
  if (!state.data) return null;
  const data = state.data; const rows = searchAudit(data.items, search, role).filter(row => (!module || auditModule(row.action) === module) && (!day || auditDay(row.created_at) === day) && (!action || row.action === action));
  const active = rows.find(row => row.id === selected?.id) ?? rows[0];
  const dates = [...new Set(rows.map(row => auditDay(row.created_at)).filter(Boolean))];
  function clearPage() { setSearch(''); setRole(''); setModule(''); setDay(''); setAction(''); }
  const stats = [
    ['Events shown', String(rows.length), 'Visible records on this page', FileClock],
    ['Roles observed', String(new Set(rows.flatMap(r => r.role ? [r.role] : [])).size), 'Recorded roles in visible events', Users],
    ['Dates represented', dates.length === 1 ? dates[0] : `${dates.length} dates`, 'IST · visible events', CalendarDays],
    ['Integrity status', 'Not reported', 'Verification telemetry is unavailable', Info],
  ] as const;
  return <><div className="audit-layout audit-reference-layout"><div className="audit-main"><div className="audit-stats">{stats.map(([label, value, note, Icon]) => <article key={label}><span className="audit-icon"><Icon size={22} aria-hidden="true"/></span><div><p>{label}</p><strong>{value}</strong><small>{note}</small></div></article>)}</div>
    <section className="audit-panel audit-history"><div className="audit-table-heading"><div><h2>Activity log</h2><p>Newest first · IST (UTC+05:30) · filters below apply to this page</p></div><div><button className="audit-secondary" onClick={() => { setSelected(null); void state.reload(); }}><RefreshCw size={16} aria-hidden="true"/>Refresh</button><button className="audit-secondary" disabled={!rows.length} onClick={() => exportRows(rows)}><Download size={16} aria-hidden="true"/>Export records</button></div></div>
    <div className="audit-local-filters"><label>Search this page<div><Search size={17} aria-hidden="true"/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Action, target or reference"/></div></label><label>Role<select value={role} onChange={e => setRole(e.target.value)}><option value="">All roles</option>{[...new Set(data.items.flatMap(r => r.role ? [r.role] : []))].map(r => <option key={r} value={r}>{r.replaceAll('_',' ')}</option>)}</select></label><label>Action<select value={action} onChange={e=>setAction(e.target.value)}><option value="">All actions</option>{[...new Set(data.items.map(r=>r.action))].map(a=><option key={a} value={a}>{a.replaceAll('_',' ')}</option>)}</select></label><label>Module<select value={module} onChange={e=>setModule(e.target.value)}><option value="">All modules</option>{[...new Set(data.items.map(r=>auditModule(r.action)))].map(m=><option key={m}>{m}</option>)}</select></label><label>Date (IST)<input type="date" value={day} onChange={e=>setDay(e.target.value)}/></label><button className="audit-secondary" onClick={clearPage}>Clear filters</button></div>
    {rows.length ? <DataTable columns={['Time (IST)', 'Actor / Role', 'Action', 'Module', 'Target / Reference', 'Details']} rows={rows.map(row => [<time dateTime={row.created_at}>{auditTimestamp(row.created_at)}</time>, <span className="audit-actor"><span title={row.admin_id ?? undefined}>{row.admin_id ? `Admin ${row.admin_id.slice(0,8)}…` : 'Actor not recorded'}</span><span className="audit-role">{row.role?.replaceAll('_',' ') ?? 'Role not recorded'}</span></span>, <span className="audit-action"><strong>{row.action.replaceAll('_',' ')}</strong><code>{row.action}</code></span>, <span className="audit-module" data-module={auditModule(row.action)} title="Grouped by action code">{auditModule(row.action)}</span>, <span className="audit-reference">{row.target ?? 'Not recorded'}{row.target_id && <small>{row.target_id}</small>}</span>, <button className="audit-view" aria-label={`View audit record ${row.id}`} aria-pressed={active?.id === row.id} onClick={() => setSelected(row)}>View</button>])}/> : <div className="audit-empty"><FileClock size={38} aria-hidden="true"/><h3>No matching audit records</h3><p>{data.items.length ? 'Try clearing the page filters.' : 'No recorded events match the selected action and target.'}</p>{data.items.length > 0 && <button onClick={clearPage}>Clear page filters</button>}</div>}
    <footer className="audit-pagination"><span>{rows.length} visible of {data.items.length} loaded · {data.total} matching records</span><label>Rows per page<select value={size} onChange={e => setSize(Number(e.target.value))}>{[20,50,100].map(n => <option key={n}>{n}</option>)}</select></label><div><button className="audit-secondary" disabled={page <= 1} onClick={() => setPage(page-1)}>Previous</button><span>{page} / {Math.max(1,data.total_pages)}</span><button className="audit-secondary" disabled={page >= data.total_pages} onClick={() => setPage(page+1)}>Next</button></div></footer></section>
    <section className="audit-panel audit-recommendations"><Lightbulb size={26} aria-hidden="true"/><div><strong>Recommended audit fields — recommendations, not proof of capture</strong><p>Timestamp, actor ID, action, resource type, resource ID, outcome, request ID and reason for privileged access.</p></div></section></div>
    <aside className="audit-sidebar"><section className="audit-panel audit-detail" aria-label="Selected audit record"><h2>Event details</h2>{active ? <><dl>{[['Action',active.action.replaceAll('_',' ')],['Role',active.role ?? 'Not recorded'],['Timestamp (IST)',auditTimestamp(active.created_at)],['Actor ID',active.admin_id ?? 'Not recorded'],['Target',active.target ?? 'Not recorded'],['Reference',active.target_id ?? 'Not recorded'],['Record ID',active.id]].map(([label,value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><div className="audit-context"><Info size={18} aria-hidden="true"/><p>Missing fields mean context was not supplied for this event. They do not establish whether the action succeeded or failed.</p></div></> : <p className="audit-note">No visible event to inspect. Clear filters or select another page.</p>}</section>
    <section className="audit-panel"><h2>Audit coverage</h2><p className="audit-note">For the selected event</p>{active && <ul className="audit-coverage">{auditCoverage(active).map(([label,status])=><li key={label}><span>{label}</span><strong data-available={status==='Available'}>{status==='Available'?<CheckCircle2 size={15} aria-hidden="true"/>:<CircleHelp size={15} aria-hidden="true"/>}{status}</strong></li>)}</ul>}<details className="audit-requirements"><summary>Review logging requirements</summary><p>Capture exact time, actor, action, resource, outcome and request correlation where applicable. Integrity verification needs separate telemetry; this API does not report it.</p></details></section></aside></div></>;
}
