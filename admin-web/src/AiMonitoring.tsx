import { useState, type ReactNode } from 'react';
import { Activity, Brain, Download, Info, Leaf, MessageSquare, RefreshCw, Satellite, ShieldCheck, TriangleAlert } from 'lucide-react';
import { api } from './api';
import { useResource } from './useResource';
import './AiMonitoring.css';

export type MonitoringData = {
  today_requests: number | null; total_messages: number | null;
  disease_detections: number | null; nutrient_analyses: number | null;
  satellite_analyses: number | null; memory_generated: number | null;
  intelligence_reports: number | null; average_confidence: number | null;
  daily_requests: { label: string; count: number }[];
  model_latency_ms: number | null; api_failures: number | null;
};
type CostData = { window_days: number; total_requests: number; total_cost_inr: number; generated_at: string };

export function monitoringNumber(value: unknown): string {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value.toLocaleString('en-IN', { maximumFractionDigits: 6 }) : 'Not reported';
}
export function averageRecordedCost(cost: unknown, requests: unknown): string {
  return typeof cost === 'number' && Number.isFinite(cost) && cost >= 0 && typeof requests === 'number' && Number.isFinite(requests) && requests > 0
    ? `₹${(cost / requests).toFixed(3)} per recorded request` : 'Not available';
}
export function featureActivity(data: MonitoringData, search = '') {
  return [
    { label: 'Disease detection', value: data.disease_detections },
    { label: 'Satellite analysis', value: data.satellite_analyses },
    { label: 'Intelligence reports', value: data.intelligence_reports },
    { label: 'Memory generated', value: data.memory_generated },
    { label: 'Nutrient analysis', value: data.nutrient_analyses },
  ].filter(row => row.label.toLowerCase().includes(search.trim().toLowerCase()));
}
function exportSnapshot(data: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
}
function Panel({ title, children, className = '' }: { title: string; children: ReactNode; className?: string }) {
  return <section className={`aim-panel ${className}`}><h2>{title}</h2>{children}</section>;
}
function Stat({ label, value, note, icon }: { label: string; value: unknown; note: string; icon: ReactNode }) {
  return <article className="aim-stat"><div><span>{label}</span><strong>{monitoringNumber(value)}</strong><small>{note}</small></div><span className="aim-icon" aria-hidden="true">{icon}</span></article>;
}
function Facts({ rows }: { rows: [string, ReactNode][] }) {
  return <dl className="aim-facts">{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

export function AiPage({ canViewCosts }: { canViewCosts: boolean }) {
  const [revision, setRevision] = useState(0);
  return <MonitoringSnapshot key={revision} canViewCosts={canViewCosts} refresh={() => setRevision(value => value + 1)}/>;
}
function MonitoringSnapshot({ canViewCosts, refresh }: { canViewCosts: boolean; refresh: () => void }) {
  const state = useResource(() => api<MonitoringData>('/admin/ai'));
  const [search, setSearch] = useState('');
  const data = state.error ? null : state.data;
  const features = data ? featureActivity(data, search) : [];
  const max = Math.max(1, ...features.map(row => typeof row.value === 'number' && Number.isFinite(row.value) ? row.value : 0));
  return <div className="ai-monitoring">
    <div className="aim-breadcrumb"><span>Intelligence</span><span aria-hidden="true">/</span><strong>AI Monitoring</strong></div>
    <header className="aim-heading"><div><h1>AI Monitoring</h1><p>Operational usage, safety and cost telemetry.</p></div><button className="aim-secondary" disabled={!data || state.loading} onClick={() => exportSnapshot({ source: '/admin/ai', scope: 'All-time feature totals; today and daily series use server day boundaries', exported_at: new Date().toISOString(), data }, 'agrowai-ai-monitoring.json')}><Download size={17}/>Export usage</button><button className="aim-secondary" onClick={refresh} disabled={state.loading} aria-label="Refresh monitoring"><RefreshCw size={18}/></button></header>
    <div className="aim-notice"><Info size={23} aria-hidden="true"/><div><strong>Monitoring coverage is partial</strong><p>Service health, abstention and detailed request logs are not currently reported by this dashboard.</p></div><a href="#aim-telemetry-gaps">Review telemetry gaps <span aria-hidden="true">→</span></a></div>
    {state.loading && <p role="status" className="aim-feedback">Loading monitoring data…</p>}
    {state.error && <div role="alert" className="aim-warning"><TriangleAlert size={20}/><div><strong>Usage data could not be loaded</strong><p>{state.error}</p><button onClick={refresh}>Try again</button></div></div>}
    <Panel title="Usage overview"><div className="aim-stats">
      <Stat label="Conversations today" value={data?.today_requests} note="Server day boundary" icon={<Activity size={23}/>}/>
      <Stat label="Messages" value={data?.total_messages} note="All-time records" icon={<MessageSquare size={23}/>}/>
      <Stat label="Disease detections" value={data?.disease_detections} note="All-time reports" icon={<Leaf size={23}/>}/>
      <Stat label="Satellite analyses" value={data?.satellite_analyses} note="Available sessions" icon={<Satellite size={23}/>}/>
    </div></Panel>
    <div className="aim-two">
      <Panel title="Feature activity"><label className="aim-search">Search features<input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Disease, satellite, memory…"/></label><div className="aim-bars">{features.map(row => <div className="aim-bar-row" key={row.label}><span>{row.label}</span><span className="aim-track" aria-hidden="true"><span style={{ width: `${typeof row.value === 'number' && Number.isFinite(row.value) && row.value >= 0 ? row.value / max * 100 : 0}%` }}/></span><strong>{monitoringNumber(row.value)}</strong></div>)}{!features.length && <p className="aim-muted">{data ? 'No features match your search.' : 'Feature activity is unavailable.'}</p>}</div><p className="aim-footnote">All-time feature records. Event types are not additive to total requests.</p></Panel>
      {canViewCosts ? <CostGovernance/> : <Panel title="Cost governance"><div className="aim-empty"><ShieldCheck size={27}/><strong>Cost access restricted</strong><p>Your role does not include AI cost access.</p></div></Panel>}
    </div>
    <div className="aim-three">
      <Panel title="Safety telemetry"><Facts rows={[["Abstentions", 'Not reported'], ['Failed requests', monitoringNumber(data?.api_failures)], ['Human review', 'Not reported'], ['Model latency', data?.model_latency_ms != null ? `${monitoringNumber(data.model_latency_ms)} ms` : 'Not reported']]}/><a className="aim-panel-link" href="#aim-telemetry-gaps">Review telemetry gaps →</a></Panel>
      <Panel title="Service telemetry"><Facts rows={['AI assistant', 'Disease analysis', 'Satellite analysis', 'Intelligence pipeline'].map(label => [label, 'Not reported'])}/><p className="aim-footnote">Usage counts do not establish service health.</p></Panel>
      <Panel title="Confidence metric"><div className="aim-confidence">{monitoringNumber(data?.average_confidence)}</div><p className="aim-muted">Aggregate of available disease and nutrient averages; unit not supplied.</p><div className="aim-warning"><TriangleAlert size={20} aria-hidden="true"/><div><strong>Confidence is not accuracy.</strong><p>Verify definition and calibration before using this metric.</p></div></div></Panel>
    </div>
    <Panel title="Request activity"><div className="aim-request-head" aria-hidden="true"><span>Timestamp</span><span>Feature</span><span>Outcome</span><span>Latency</span><span>Cost</span></div><div className="aim-empty"><Brain size={28} aria-hidden="true"/><strong>Detailed request logs are unavailable.</strong><p>No request-level endpoint is exposed to this dashboard.</p><a href="#aim-telemetry-gaps">Review logging requirements</a></div>
      {data && <details className="aim-details"><summary>View recorded daily conversation counts</summary><p className="aim-muted">The API supplies up to seven days, using server day boundaries. These are conversation counts, not individual model calls.</p>{data.daily_requests?.length ? <Facts rows={data.daily_requests.map(row => [row.label, monitoringNumber(row.count)])}/> : <p>No daily series reported.</p>}</details>}
    </Panel>
    <details id="aim-telemetry-gaps" className="aim-panel aim-details"><summary>Telemetry gaps and logging requirements</summary><p>These are recommended additions, not existing measurements. Instrument them before using this dashboard for incident or safety decisions.</p><ul><li>Request timestamp, feature, outcome, latency and request correlation ID.</li><li>Abstention reason, failed calls and human-review outcomes.</li><li>Service health checks and metric definitions, including confidence units.</li><li>Budget thresholds and alert delivery. No cost-alert configuration is exposed here.</li></ul><p>Do not log farmer prompts or protected contact information in operational exports.</p></details>
    <footer className="aim-footer">Operational telemetry must not be used as agronomic accuracy evidence.</footer>
  </div>;
}
function CostGovernance() {
  const [days, setDays] = useState(30);
  return <Panel title="Cost governance"><label className="aim-window">Cost reporting window<select value={days} onChange={event => setDays(Number(event.target.value))}>{[7, 30, 90].map(value => <option key={value} value={value}>Last {value} days</option>)}</select></label><CostSnapshot key={days} days={days}/></Panel>;
}
function CostSnapshot({ days }: { days: number }) {
  const state = useResource(() => api<CostData>(`/admin/ai-costs?window_days=${days}`));
  if (state.loading) return <p role="status" className="aim-feedback">Loading cost records…</p>;
  if (state.error) return <div role="alert" className="aim-warning"><div><strong>Cost records could not be loaded</strong><p>{state.error}</p><button onClick={() => void state.reload()}>Retry costs</button></div></div>;
  const data = state.data;
  const cost = monitoringNumber(data?.total_cost_inr);
  return <><div className="aim-cost-value"><strong>{cost === 'Not reported' ? cost : `₹${Number(data?.total_cost_inr).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}</strong><span>Recorded estimated cost</span></div><Facts rows={[
    ['Exact recorded estimate', cost === 'Not reported' ? cost : `₹${cost}`],
    ['Recorded requests', monitoringNumber(data?.total_requests)],
    ['Calculated average', averageRecordedCost(data?.total_cost_inr, data?.total_requests)],
  ]}/><p className="aim-footnote">Cost estimates use the configured token price table. Unknown token counts contribute zero; this is not a billing invoice. This window applies only to costs.</p><div className="aim-cost-actions"><button className="aim-secondary" disabled={!data} onClick={() => exportSnapshot({ source: '/admin/ai-costs', ...data }, `agrowai-ai-costs-${days}d.json`)}><Download size={15}/>Export costs</button><a href="#aim-telemetry-gaps">Budget alerts: not configured here</a></div></>;
}
