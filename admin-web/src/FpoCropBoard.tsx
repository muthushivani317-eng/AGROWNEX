import { useEffect, useState } from 'react';
import { Card, DataTable, Empty, ErrorPanel, Loading, Metric, PageTitle, formatDate } from './components';
import { getCsrfToken } from './api';
import { getConfig } from './config';
import { reportReauthRequired } from './sessionTimeout';
import { useResource } from './useResource';

// /admin/fpo-board/* returns plain JSON (no {success,data} envelope).
async function boardFetch(path: string): Promise<Response> {
  const response = await fetch(`${getConfig().apiBaseUrl}${path}`, { credentials: 'include', cache: 'no-store' });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { message?: string; error_code?: string; detail?: string } | null;
    if (body?.error_code === 'admin_recent_auth_required') reportReauthRequired();
    throw new Error(body?.message ?? body?.detail ?? `Request failed (${response.status}).`);
  }
  return response;
}
const boardJson = async <T,>(path: string): Promise<T> => (await boardFetch(path)).json() as Promise<T>;

async function boardPost<T>(path: string, body: unknown): Promise<T> {
  const csrf = getCsrfToken();
  const response = await fetch(`${getConfig().apiBaseUrl}${path}`, {
    method: 'POST',
    credentials: 'include',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const data = (await response.json().catch(() => null)) as { message?: string; error_code?: string; detail?: unknown } | null;
    if (data?.error_code === 'admin_recent_auth_required') reportReauthRequired();
    throw new Error(data?.message ?? (typeof data?.detail === 'string' ? data.detail : `Request failed (${response.status}).`));
  }
  return response.json() as Promise<T>;
}

type LinkRequest = { id: string; farmer_ref: string; status: 'pending' | 'active' | 'revoked'; requested_at: string; approved_at: string | null };

function AddFarmers({ orgId, onLinked }: { orgId: string; onLinked: () => void }) {
  const links = useResource(() => boardJson<LinkRequest[]>(`/admin/fpo-board/organizations/${orgId}/link-requests`), [orgId]);
  const [farmerRef, setFarmerRef] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError(''); setMessage('');
    try {
      const ref = farmerRef.trim().toUpperCase();
      await boardPost(`/admin/fpo-board/organizations/${orgId}/link-requests`, { farmer_ref: ref });
      setMessage(`Request sent to ${ref}. They must approve it in the app: Profile → Organizations.`);
      setFarmerRef('');
      await links.reload();
      onLinked();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not send the request.');
    } finally {
      setBusy(false);
    }
  }

  const pending = (links.data ?? []).filter((l) => l.status === 'pending');
  return (
    <Card>
      <div className="section-head"><h2>Add farmers</h2><span>Farmer finds their ID in the app: Profile → Account settings (AGF-…)</span></div>
      <form className="stack" onSubmit={(e) => void submit(e)} style={{ display: 'flex', gap: 10, alignItems: 'end', flexWrap: 'wrap', marginTop: 12 }}>
        <label style={{ flex: '1 1 240px' }}>Farmer ID<input value={farmerRef} onChange={(e) => setFarmerRef(e.target.value)} placeholder="AGF-000000123" pattern="\s*[Aa][Gg][Ff]-[0-9]{9}\s*" required /></label>
        <button disabled={busy}>{busy ? 'Sending…' : 'Send request'}</button>
      </form>
      {message && <p className="panel-message">{message}</p>}
      {error && <p className="form-error">{error}</p>}
      {pending.length > 0 && (
        <>
          <p className="panel-message">Waiting for farmer approval ({pending.length}):</p>
          <DataTable columns={['Farmer ID', 'Requested']} rows={pending.map((l) => [l.farmer_ref, formatDate(l.requested_at)])} />
        </>
      )}
    </Card>
  );
}

type Organization = { id: string; name: string; kind: string; farmer_count: number };
type Window = { farmer_count: number; quantity: Record<string, number> };
type CropRow = {
  crop: string; farmer_count: number; farm_count: number; area_acres: number; varieties: string[];
  villages: { village: string; farmer_count: number; area_acres: number }[];
  expected_harvest: Record<'within_30_days' | 'within_60_days' | 'within_90_days', Window>;
};
type ProductRow = {
  name: string; source: 'produce' | 'organic_input'; category: string | null; unit: string; farmer_count: number;
  total_quantity: number; available_now_quantity: number; upcoming_quantity: number; earliest_ready_date: string | null;
};
type Board = {
  organization: { id: string; name: string; kind: string };
  generated_on: string;
  summary: { farmer_count: number; farmers_without_farm: number; farm_count: number; total_area_acres: number; crop_count: number; product_count: number };
  crops: CropRow[];
  products: ProductRow[];
};
type FarmerRow = {
  farmer_ref: string; name: string | null; phone: string | null; village: string | null; district: string | null;
  crops: { crop: string; variety: string | null; area_acres: number; sowing_date: string | null }[];
  products: { name: string; quantity: number; unit: string; ready_date: string | null; available_now: boolean }[];
};
type Filter = { crop?: string; product?: string } | null;

const qty = (map: Record<string, number>) => Object.entries(map).map(([unit, value]) => `${value.toLocaleString('en-IN')} ${unit}`).join(', ') || '—';
const windowText = (w: Window) => (w.farmer_count ? `${w.farmer_count} farmer${w.farmer_count > 1 ? 's' : ''} · ${qty(w.quantity)}` : '—');

export function FpoCropBoardPage() {
  const organizations = useResource(() => boardJson<Organization[]>('/admin/fpo-board/organizations'));
  const [orgId, setOrgId] = useState('');
  const [filter, setFilter] = useState<Filter>(null);
  const [exportError, setExportError] = useState('');

  useEffect(() => {
    if (!orgId && organizations.data?.length) setOrgId(organizations.data[0].id);
  }, [orgId, organizations.data]);

  const board = useResource(() => (orgId ? boardJson<Board>(`/admin/fpo-board/organizations/${orgId}`) : Promise.resolve(null)), [orgId]);
  const query = filter ? `?${new URLSearchParams(Object.entries(filter).filter(([, v]) => v) as [string, string][]).toString()}` : '';
  const farmers = useResource(
    () => (orgId && filter ? boardJson<FarmerRow[]>(`/admin/fpo-board/organizations/${orgId}/farmers${query}`) : Promise.resolve(null)),
    [orgId, query],
  );

  async function downloadCsv() {
    setExportError('');
    try {
      const blob = await (await boardFetch(`/admin/fpo-board/organizations/${orgId}/farmers.csv${query}`)).blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${board.data?.organization.name ?? 'fpo'}-farmers${filter?.crop ? `-${filter.crop}` : ''}${filter?.product ? `-${filter.product}` : ''}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'Download failed.');
    }
  }

  if (organizations.loading) return <Loading />;
  if (organizations.error) return <ErrorPanel message={organizations.error} retry={() => void organizations.reload()} />;
  if (!organizations.data?.length) {
    return <><PageTitle title="FPO Crop Board" subtitle="What your farmers grow and have to sell." /><Empty title="No FPO yet" body="Agrownex team: create the FPO in Partner organizations (FPO → organization → staff). FPO staff: ask the Agrownex team to add you to your FPO." /></>;
  }

  const data = board.data;
  return (
    <>
      <PageTitle
        title="FPO Crop Board"
        subtitle="Crops, harvests and products of farmers who have linked to your FPO."
        action={organizations.data.length > 1 ? (
          <label>FPO<select value={orgId} onChange={(e) => { setOrgId(e.target.value); setFilter(null); }}>{organizations.data.map((o) => <option key={o.id} value={o.id}>{o.name} ({o.farmer_count})</option>)}</select></label>
        ) : undefined}
      />
      {board.loading && <Loading />}
      {board.error && <ErrorPanel message={board.error} retry={() => void board.reload()} />}
      {data && (
        <>
          <div className="metrics">
            <Metric label="Farmers" value={data.summary.farmer_count} />
            <Metric label="Farms" value={data.summary.farm_count} />
            <Metric label="Total acres" value={data.summary.total_area_acres} />
            <Metric label="Crops" value={data.summary.crop_count} />
            <Metric label="Products" value={data.summary.product_count} />
          </div>
          {data.summary.farmers_without_farm > 0 && <p className="panel-message">{data.summary.farmers_without_farm} linked farmer(s) have not added a farm yet.</p>}

          <AddFarmers orgId={orgId} onLinked={() => void board.reload()} />

          <Card>
            <div className="section-head"><h2>Crops</h2><span>Harvest windows use dates farmers entered in Sell My Produce</span></div>
            {data.crops.length ? (
              <DataTable
                columns={['Crop', 'Farmers', 'Acres', 'Villages', 'Harvest ≤30 days', '≤60 days', '≤90 days', '']}
                rows={data.crops.map((c) => [
                  <strong key="c">{c.crop}{c.varieties.length ? <small> · {c.varieties.join(', ')}</small> : null}</strong>,
                  c.farmer_count,
                  c.area_acres,
                  c.villages.map((v) => `${v.village} (${v.farmer_count})`).join(', '),
                  windowText(c.expected_harvest.within_30_days),
                  windowText(c.expected_harvest.within_60_days),
                  windowText(c.expected_harvest.within_90_days),
                  <button key="b" onClick={() => setFilter({ crop: c.crop })}>Farmers</button>,
                ])}
              />
            ) : <p className="panel-message">No farms with a crop yet.</p>}
          </Card>

          <Card>
            <div className="section-head"><h2>Products &amp; stock</h2><span>From Sell My Produce and organic-input batches</span></div>
            {data.products.length ? (
              <DataTable
                columns={['Product', 'Type', 'Farmers', 'Available now', 'Upcoming', 'Earliest ready', '']}
                rows={data.products.map((p) => [
                  <strong key="n">{p.name}</strong>,
                  p.source === 'organic_input' ? 'Organic input' : (p.category ?? 'Produce').replaceAll('_', ' '),
                  p.farmer_count,
                  `${p.available_now_quantity.toLocaleString('en-IN')} ${p.unit}`,
                  `${p.upcoming_quantity.toLocaleString('en-IN')} ${p.unit}`,
                  formatDate(p.earliest_ready_date),
                  <button key="b" onClick={() => setFilter({ product: p.name })}>Farmers</button>,
                ])}
              />
            ) : <p className="panel-message">No farmer has listed produce or products yet.</p>}
          </Card>

          <Card>
            <div className="section-head">
              <h2>{filter ? `Farmers — ${filter.crop ?? filter.product}` : 'Farmer list'}</h2>
              <span style={{ display: 'flex', gap: 8 }}>
                {filter && <button onClick={() => setFilter(null)} className="secondary-button">Clear</button>}
                {!filter && <button onClick={() => setFilter({})}>Show all farmers</button>}
                {filter && <button onClick={() => void downloadCsv()}>Download Excel (CSV)</button>}
              </span>
            </div>
            {exportError && <p className="form-error">{exportError}</p>}
            {!filter && <p className="panel-message">Pick a crop or product above, or show all farmers.</p>}
            {farmers.loading && <Loading />}
            {farmers.error && <ErrorPanel message={farmers.error} retry={() => void farmers.reload()} />}
            {farmers.data && (farmers.data.length ? (
              <DataTable
                columns={['Farmer', 'Phone', 'Village', 'Crops', 'Has to sell']}
                rows={farmers.data.map((f) => [
                  <span key="f"><strong>{f.name ?? 'Unnamed'}</strong><br /><small>{f.farmer_ref}</small></span>,
                  f.phone ? <a key="p" href={`tel:${f.phone}`}>{f.phone}</a> : '—',
                  [f.village, f.district].filter(Boolean).join(', ') || '—',
                  f.crops.map((c) => `${c.crop} (${c.area_acres} ac)`).join(', ') || '—',
                  f.products.map((p) => `${p.name} ${p.quantity.toLocaleString('en-IN')} ${p.unit}${p.available_now ? '' : p.ready_date ? ` · ${formatDate(p.ready_date)}` : ''}`).join('; ') || '—',
                ])}
              />
            ) : <p className="panel-message">No farmers match.</p>)}
          </Card>
        </>
      )}
    </>
  );
}
