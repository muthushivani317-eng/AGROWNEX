import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, CheckCircle2, CircleHelp, Info, Leaf, RefreshCw, Sprout, TriangleAlert } from 'lucide-react';
import { api, ApiError } from './api';
import { DataTable, formatDate } from './components';
import { useResource } from './useResource';
import './CropIntelligence.css';

export type CropIntelligenceData = {
  generated_at: string;
  summary: { farm_count: number; farmer_count: number; known_area_hectares: number; farms_with_area: number; farms_without_area: number; recorded_stage_farms: number; sale_listing_count: number; harvest_window_listing_count: number };
  by_crop: { label: string; farm_count: number; farmer_count: number; known_area_hectares: number; farms_with_area: number }[];
  crop_stages: { label: string; farm_count: number }[];
  farm_records?: { farm_id: string; name: string; crop: string | null; district: string | null; area_hectares: number | null; recorded_stage: string | null; harvest_dates: string[] }[];
};
export function cropCoverage(data: CropIntelligenceData) {
  const groups = new Map<string, { label: string; count: number }>();
  for (const crop of data.by_crop) {
    const key = crop.label.trim().toLowerCase();
    const row = groups.get(key) ?? { label: crop.label, count: 0 };
    row.count += crop.farm_count; groups.set(key, row);
  }
  return [...groups.values()].map(row => ({ ...row, percent: data.summary.farm_count ? Math.min(100, row.count / data.summary.farm_count * 100) : 0 }));
}
export function completeness(known: number | undefined, total: number | undefined) {
  if (known == null || total == null) return 'Unavailable';
  if (total === 0) return 'No farms';
  return known === total ? 'Complete' : known === 0 ? 'Missing' : `${known} of ${total} farms`;
}
export function CropIntelligencePage() {
  const [district, setDistrict] = useState(''); const [crop, setCrop] = useState('');
  const [filters, setFilters] = useState({ district: '', crop: '' });
  const params = new URLSearchParams({ harvest_days: '30' });
  if (filters.district) params.set('district', filters.district);
  if (filters.crop) params.set('crop', filters.crop);
  const path = `/admin/crop-intelligence?${params}`;
  return <div className="crop-intelligence"><nav className="ci-breadcrumb" aria-label="Breadcrumb"><span>Intelligence</span><span>/</span><strong>Crop Intelligence</strong></nav>
    <header className="ci-heading"><div><h1>Crop Intelligence</h1><p>Monitor registered crops, field stages and harvest readiness.</p></div><form onSubmit={e => { e.preventDefault(); setFilters({ district: district.trim(), crop: crop.trim() }); }}><label>District<input value={district} onChange={e => setDistrict(e.target.value)} placeholder="All districts"/></label><label>Crop<input value={crop} onChange={e => setCrop(e.target.value)} placeholder="All crops"/></label><button>Apply</button><button type="button" className="ci-secondary" onClick={() => { setDistrict(''); setCrop(''); setFilters({ district: '', crop: '' }); }}>Clear</button></form></header>
    <IntelligenceResults key={path} path={path}/>
  </div>;
}
function IntelligenceResults({ path }: { path: string }) {
  const state = useResource(async () => {
    try { return await api<CropIntelligenceData>(path); }
    catch (error) { if (error instanceof ApiError) throw new Error(`HTTP ${error.status}: ${error.message}`); throw error; }
  });
  const data = state.data; const summary = data?.summary;
  const coverage = data ? cropCoverage(data) : [];
  const farms = data?.farm_records;
  const [page, setPage] = useState(1);
  const visible = farms?.slice((page - 1) * 10, page * 10) ?? [];
  const retry = () => { setPage(1); void state.reload(); };
  const values = [
    ['Registered Farms', summary?.farm_count ?? 'Unavailable', Building2],
    ['Registered Crops', data ? coverage.filter(c => c.label.toLowerCase() !== 'unknown').length : 'Unavailable', Leaf],
    ['Recorded Stages', summary ? `${summary.recorded_stage_farms} farms` : 'Unavailable', Sprout],
    ['Reported Area', summary?.farms_with_area ? `${summary.known_area_hectares} ha` : 'Not available', CircleHelp],
  ] as const;
  const checks = [
    ['Crop identity', data ? completeness(coverage.filter(c => c.label.toLowerCase() !== 'unknown').reduce((n,c) => n+c.count,0), summary?.farm_count) : 'Unavailable'],
    ['Farm registration', completeness(summary?.farm_count, summary?.farm_count)],
    ['Area', completeness(summary?.farms_with_area, summary?.farm_count)],
    ['Recorded stage', completeness(summary?.recorded_stage_farms, summary?.farm_count)],
    ['Harvest dates', farms ? completeness(farms.filter(f => f.harvest_dates.length > 0).length, farms.length) : 'Unavailable'],
  ];
  return <div aria-busy={state.loading}>
    <div className="ci-update"><span>{data ? `Snapshot: ${new Date(data.generated_at).toLocaleString('en-IN')}${state.error ? ' · Last successful load (stale)' : ''}` : 'Last updated — unavailable'}</span><button className="ci-secondary" disabled={state.loading} onClick={retry}><RefreshCw size={16} aria-hidden="true"/>{state.loading ? 'Loading…' : 'Refresh'}</button></div>
    {state.error && <section className="ci-alert" role="alert"><TriangleAlert size={28} aria-hidden="true"/><div><h2>Live intelligence is temporarily unavailable</h2><p>{data ? 'Showing the last successful snapshot for these filters. It may be out of date.' : 'We couldn’t retrieve the latest stage, area and harvest signals.'}</p><details><summary>View technical details</summary><p>{state.error}</p><code>{path}</code><p>A network failure can be caused by connectivity, CORS or a server error. Check the failed request and backend logs.</p></details></div><button disabled={state.loading} onClick={retry}>Try again</button></section>}
    {state.loading && !data && <p className="ci-loading" role="status">Loading crop intelligence…</p>}
    <div className="ci-metrics">{values.map(([label, value, Icon]) => <article key={label}><span className="ci-icon"><Icon size={25} aria-hidden="true"/></span><div><p>{label}</p><strong>{state.loading && !data ? 'Loading…' : value}</strong><small>{data ? 'Recorded data' : 'Awaiting connection'}</small></div></article>)}</div>
    <div className="ci-grid"><section className="ci-card"><h2>Crop coverage <Info size={14} aria-hidden="true"/></h2>{coverage.length ? <div className="ci-coverage">{coverage.map(c => <div key={c.label}><strong>{c.label}</strong><div className="ci-track"><span style={{ width: `${c.percent}%` }}/></div><span>{c.count} farms</span><b>{c.percent.toFixed(0)}%</b></div>)}</div> : <p className="ci-placeholder">{data ? 'No registered farms match these filters.' : 'Crop coverage will appear when recorded data is available.'}</p>}<p className="ci-note">Based on registered farm records within the selected filters.</p></section>
    <section className="ci-card"><h2>Data completeness <Info size={14} aria-hidden="true"/></h2><ul className="ci-checks">{checks.map(([label, status]) => <li key={label}><span>{label}</span><strong className={status === 'Complete' ? 'complete' : 'pending'}>{status === 'Complete' ? <CheckCircle2 size={16} aria-hidden="true"/> : <CircleHelp size={16} aria-hidden="true"/>}{status}</strong></li>)}</ul></section>
    <section className="ci-card ci-records"><h2>Farm intelligence records</h2>{visible.length ? <DataTable columns={['Farm','Crop','Area','Recorded stage','Harvest dates']} rows={visible.map(f => [f.name, f.crop ?? 'Not provided', f.area_hectares == null ? 'Not provided' : `${f.area_hectares} ha`, f.recorded_stage?.replaceAll('_',' ') ?? 'Not provided', f.harvest_dates.length ? f.harvest_dates.map(formatDate).join(', ') : 'Not provided'])}/> : <p className="ci-placeholder">{farms ? 'No farms match these filters.' : data ? 'Individual farm records are not supplied by this backend version. Deploy the updated backend to enable this table.' : 'Farm records are unavailable. No sample records are shown.'}</p>}{farms && farms.length > 0 && <div className="ci-pagination"><span>Showing {(page-1)*10+1}–{Math.min(page*10,farms.length)} of {farms.length} farms</span><button className="ci-secondary" disabled={page===1} onClick={()=>setPage(page-1)}>Previous</button><button className="ci-secondary" disabled={page*10>=farms.length} onClick={()=>setPage(page+1)}>Next</button></div>}<p className="ci-note">Stages may be suggested or confirmed. Harvest dates come from active produce listings.</p></section>
    <section className="ci-card"><h2>What needs attention</h2><div className="ci-attention"><RefreshCw size={22} aria-hidden="true"/><div><strong>{state.error ? 'Restore intelligence connection' : 'Refresh intelligence'}</strong><p>Retrieve the latest recorded crop signals.</p></div><button className="ci-secondary" disabled={state.loading} onClick={retry}>{state.error ? 'Try again' : 'Refresh'}</button></div><div className="ci-attention"><Building2 size={22} aria-hidden="true"/><div><strong>Review farm records</strong><p>{summary ? `${summary.farms_without_area} farms have no recorded area.` : 'Check the completeness of registered farms.'}</p></div><Link to="/farms">Open farms</Link></div><div className="ci-attention"><Sprout size={22} aria-hidden="true"/><div><strong>Review harvest listings</strong><p>{summary ? `${summary.harvest_window_listing_count} listings dated within the next 30 days.` : 'Harvest readiness requires recorded dates.'}</p></div><Link to="/produce">Open listings</Link></div></section></div>
    <footer className="ci-footnote"><Info size={17} aria-hidden="true"/>No harvest forecast is inferred from missing dates or crop-stage data. Reported area includes only farms with recorded hectares.</footer>
  </div>;
}
