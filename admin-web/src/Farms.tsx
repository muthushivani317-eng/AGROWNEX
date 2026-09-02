import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Download, Leaf, MapPin, RefreshCw, Search, ShieldCheck, ShoppingBasket, Sprout, Tractor, TrendingUp } from 'lucide-react';
import { api } from './api';
import { DataTable, ErrorPanel, Loading } from './components';
import { useResource } from './useResource';
import './Farms.css';

type Bucket = { label: string; count: number };
type FarmAnalytics = { crop_distribution: Bucket[]; produce_by_crop: Bucket[]; farmer_growth: Bucket[] };
export function farmCoverageRows(data: FarmAnalytics) {
  return data.crop_distribution.map(crop => ({ ...crop, listings: data.produce_by_crop.filter(p=>p.label.toLowerCase()===crop.label.toLowerCase()).reduce((n,p)=>n+p.count,0) }));
}
export function farmCoverageCsv(rows: ReturnType<typeof farmCoverageRows>) {
  const quote=(value: unknown)=>{const s=String(value);return `"${(/^[\s]*[=+@-]/.test(s) ? "'"+s : s).replaceAll('"','""')}"`;};
  return [['Crop','Registered farms','Produce listings for crop'],...rows.map(x=>[x.label,x.count,x.listings])].map(row=>row.map(quote).join(',')).join('\r\n');
}
export function FarmsPage() {
  const state=useResource(()=>api<FarmAnalytics>('/admin/analytics'));
  return <div className="farms-workspace"><div className="farms-breadcrumb"><Link to="/">Operations</Link><span>/</span><strong>Farms</strong><span className="farms-access"><ShieldCheck size={16} aria-hidden="true"/>Authorised analytics</span></div><header className="farms-heading"><div><h1>Farms</h1><p>Monitor registered farms and crop coverage.</p></div><button onClick={()=>void state.reload()} disabled={state.loading}><RefreshCw size={17} aria-hidden="true"/>Refresh</button></header>{state.loading ? <Loading/> : state.error ? <ErrorPanel message={state.error} retry={()=>void state.reload()}/> : state.data && <FarmOverview data={state.data}/>}</div>;
}
function FarmOverview({data}: {data:FarmAnalytics}) {
  const [search,setSearch]=useState('');
  const [crop,setCrop]=useState('');
  const [page,setPage]=useState(1);
  const [view,setView]=useState<'locations'|'coverage'>('locations');
  const rows=farmCoverageRows(data);
  const total=rows.reduce((n,x)=>n+x.count,0);
  const listings=data.produce_by_crop.reduce((n,x)=>n+x.count,0);
  const filtered=rows.filter(x=>(!crop || x.label===crop) && x.label.toLowerCase().includes(search.toLowerCase()));
  const pages=Math.max(1,Math.ceil(filtered.length/10));
  const visible=filtered.slice((page-1)*10,page*10);
  const colors=['#146345','#4b8b62','#8eb778','#ba9a50','#496f87','#8b7a9d'];
  let offset=0;
  const stops=rows.map((x,i)=>{const start=offset;offset+=total ? x.count/total*100 : 0;return `${colors[i%colors.length]} ${start}% ${offset}%`;}).join(',');
  function clear(){setSearch('');setCrop('');setPage(1);}
  function download(){const url=URL.createObjectURL(new Blob(['\uFEFF',farmCoverageCsv(filtered)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='agrowai-farm-crop-coverage.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  return <><div className="farms-metrics">{[[Tractor,'Registered Farms',total],[Sprout,'Recorded Crop Types',rows.filter(x=>x.label!=='unknown').length],[Leaf,'Paddy Farms',rows.filter(x=>x.label.toLowerCase()==='paddy').reduce((n,x)=>n+x.count,0)],[ShoppingBasket,'Produce Listings',listings]].map(([icon,label,value])=>{const Icon=icon as typeof Leaf;return <article key={String(label)}><span className="farms-icon"><Icon size={26} aria-hidden="true"/></span><div><span>{String(label)}</span><strong>{String(value)}</strong></div></article>;})}</div>
  <div className="farms-visual-grid"><section className="farms-panel farm-locations"><div className="farms-section-head"><h2>Farm locations</h2><div className="farms-segments"><button aria-pressed={view==='locations'} onClick={()=>setView('locations')}>Locations</button><button aria-pressed={view==='coverage'} onClick={()=>setView('coverage')}>Crop list</button></div></div>{view==='locations' ? <div className="farm-map-empty"><span className="location-symbol"><MapPin size={36} aria-hidden="true"/></span><strong>Farm map not available yet</strong><p>The admin analytics feed does not include farm coordinates or districts.</p><small>No estimated locations are shown.</small></div> : <div className="farm-location-list">{rows.length ? rows.map(x=><div key={x.label}><Leaf size={18} aria-hidden="true"/><span>{x.label==='unknown' ? 'Crop not specified' : x.label}</span><strong>{x.count} farms</strong></div>) : <p>No crop coverage records available.</p>}</div>}</section>
  <div className="farms-right"><section className="farms-panel"><h2>Crop distribution</h2><p className="farms-caption">Based on registered farms</p><div className="farm-distribution"><div className="farm-legend">{rows.length ? rows.map((x,i)=><div key={x.label}><span className="crop-swatch" style={{background:colors[i%colors.length]}}/><span>{x.label==='unknown' ? 'Not specified' : x.label}</span><strong>{x.count}</strong><span>{total ? Math.round(x.count/total*100) : 0}%</span></div>) : <p>No crop data available.</p>}</div><div className="farm-donut" role="img" aria-label={`Crop distribution: ${rows.map(x=>`${x.label} ${x.count} farms`).join(', ') || 'No data'}`} style={{background: total ? `conic-gradient(${stops})` : 'var(--farm-line)'}}><div><strong>{total}</strong><span>Farms</span></div></div></div></section><section className="farms-panel farm-coverage"><h2>Coverage</h2><div><span className="farms-icon"><MapPin aria-hidden="true"/></span><div><span>Districts</span><strong>Unavailable</strong></div><span className="farms-icon"><Leaf aria-hidden="true"/></span><div><span>Crop types</span><strong>{rows.filter(x=>x.label!=='unknown').length}</strong></div></div></section></div></div>
  <section className="farms-panel farm-register"><div className="farms-section-head"><div><h2>Registered farm coverage</h2><p className="farms-caption">Grouped by crop. Individual farm records are not included in this feed.</p></div><button className="farm-export" disabled={!filtered.length} onClick={download}><Download size={17} aria-hidden="true"/>Export</button></div><div className="farm-filters"><label>Search crops<div><Search size={17} aria-hidden="true"/><input value={search} onChange={e=>{setSearch(e.target.value);setPage(1);}} placeholder="Search registered crop"/></div></label><label>Crop<select value={crop} onChange={e=>{setCrop(e.target.value);setPage(1);}}><option value="">All crops</option>{rows.map(x=><option key={x.label}>{x.label}</option>)}</select></label><button onClick={clear}><RefreshCw size={16} aria-hidden="true"/>Clear filters</button></div>{visible.length ? <DataTable columns={['Primary crop','Registered farms','Share of farms','Produce listings for crop']} rows={visible.map(x=>[<span className="farm-crop-label"><Leaf size={16} aria-hidden="true"/>{x.label==='unknown' ? 'Not specified' : x.label}</span>,x.count,`${total ? (x.count/total*100).toFixed(1) : 0}%`,x.listings])}/> : <div className="farm-no-results"><h3>No matching crops</h3><p>Clear the filters or refresh to check for newly registered farms.</p></div>}<footer className="farm-pagination"><span>Showing {visible.length} of {filtered.length} crop groups</span><div><button aria-label="Previous page" disabled={page===1} onClick={()=>setPage(page-1)}><ChevronLeft size={18}/></button><span>{page} / {pages}</span><button aria-label="Next page" disabled={page>=pages} onClick={()=>setPage(page+1)}><ChevronRight size={18}/></button></div></footer></section>
  <div className="farm-data-note"><TrendingUp size={20} aria-hidden="true"/><p>Farm registration trends will appear once farm-specific history is available. Farmer registration history is shown on Overview.</p></div></>;
}
