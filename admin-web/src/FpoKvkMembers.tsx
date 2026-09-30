import { useEffect, useState } from 'react';
import { Card, DataTable, Empty, ErrorPanel, Loading, Metric, PageTitle, formatDate } from './components';
import { getCsrfToken } from './api';
import { getConfig } from './config';
import { reportReauthRequired } from './sessionTimeout';
import { useResource } from './useResource';

// FPO / KVK members from the new app onboarding: join requests, what members
// grow/rear/produce, harvest months, what they need. /admin/fpo-board/* is plain JSON.
async function call(path: string, init: RequestInit = {}): Promise<Response> {
  const csrf = init.method && init.method !== 'GET' ? getCsrfToken() : null;
  const response = await fetch(`${getConfig().apiBaseUrl}${path}`, {
    credentials: 'include',
    cache: 'no-store',
    ...init,
    headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { message?: string; error_code?: string; detail?: unknown } | null;
    if (body?.error_code === 'admin_recent_auth_required') reportReauthRequired();
    throw new Error(body?.message ?? (typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status}).`));
  }
  return response;
}
const getJson = async <T,>(path: string) => (await call(path)).json() as Promise<T>;
const send = async <T,>(path: string, method: 'POST' | 'PATCH', body?: unknown) =>
  (await call(path, { method, body: body === undefined ? undefined : JSON.stringify(body) })).json() as Promise<T>;

type Organization = { id: string; name: string; kind: string; district: string | null; listed_in_app: boolean; farmer_count: number; join_request_count: number };
type JoinRequest = {
  id: string; farmer_ref: string; status: string; initiated_by: 'farmer' | 'organization'; requested_at: string;
  farmer?: { name: string | null; phone: string | null; village: string | null; block: string | null; district: string | null; land_holding_acres: number | null; items: string[] };
};
type Coded = { code: string; name: string; name_ta?: string | null; farmer_count: number };
type FarmItem = Coded & {
  category: string; category_name: string; for_sale_farmer_count: number; area_acres: number;
  approx_quantity: Record<string, number>; for_sale_quantity: Record<string, number>; harvest_months: number[];
};
type Board = {
  organization: { id: string; name: string; kind: string; district: string | null; listed_in_app: boolean };
  summary: { farmer_count: number; total_land_holding_acres: number; farmers_with_farm_items: number; farmer_types: Coded[] };
  farm_items: FarmItem[];
  harvest_calendar: { month: number; month_name: string; items: { code: string; name: string; farmer_count: number }[] }[];
  needs: Coded[];
};
type Member = {
  farmer_ref: string; name: string | null; phone: string | null; village: string | null; district: string | null;
  land_holding_acres: number | null; farmer_type: string | null; needs: string[];
  farm_items: { name: string; harvest_months: number[]; approx_quantity: number | null; unit: string | null; available_for_sale: boolean }[];
};
type Filter = { need?: string; harvest_month?: string; crop?: string; label: string } | null;

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const qty = (map: Record<string, number>) => Object.entries(map).map(([u, v]) => `${v.toLocaleString('en-IN')} ${u}`).join(', ') || '—';
const kindLabel = (kind: string) => (kind === 'kvk' ? 'KVK' : kind === 'fpo' ? 'FPO' : 'Community');
const titleCase = (code: string) => code.replaceAll('_', ' ').replace(/^./, (c) => c.toUpperCase());

function Settings({ org, onSaved }: { org: Board['organization']; onSaved: () => void }) {
  const [district, setDistrict] = useState(org.district ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => setDistrict(org.district ?? ''), [org.id, org.district]);
  async function save(listed: boolean) {
    setBusy(true); setError('');
    try { await send(`/admin/fpo-board/organizations/${org.id}`, 'PATCH', { district: district.trim() || null, listed_in_app: listed }); onSaved(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not save.'); }
    finally { setBusy(false); }
  }
  return (
    <Card>
      <div className="section-head"><h2>Show in farmer app</h2><span>{org.listed_in_app ? 'Farmers can find and join this organization' : 'Hidden from farmers'}</span></div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'end', flexWrap: 'wrap', marginTop: 12 }}>
        <label style={{ flex: '1 1 220px' }}>District<input value={district} onChange={(e) => setDistrict(e.target.value)} placeholder="e.g. Thoothukudi" maxLength={80} /></label>
        <button disabled={busy} onClick={() => void save(org.listed_in_app)} className="secondary-button">Save district</button>
        <button disabled={busy} onClick={() => void save(!org.listed_in_app)}>{org.listed_in_app ? 'Hide from app' : 'Show in app'}</button>
      </div>
      {error && <p className="form-error">{error}</p>}
    </Card>
  );
}

function JoinRequests({ orgId, onChanged }: { orgId: string; onChanged: () => void }) {
  const links = useResource(() => getJson<JoinRequest[]>(`/admin/fpo-board/organizations/${orgId}/link-requests`), [orgId]);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  async function decide(id: string, action: 'accept' | 'reject') {
    setBusy(id); setError('');
    try { await send(`/admin/fpo-board/organizations/${orgId}/link-requests/${id}/${action}`, 'POST'); await links.reload(); onChanged(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not update the request.'); }
    finally { setBusy(''); }
  }
  const requests = (links.data ?? []).filter((l) => l.status === 'join_requested');
  return (
    <Card>
      <div className="section-head"><h2>Join requests</h2><span>Farmers who tapped “Join” in the app and agreed to share their details</span></div>
      {links.loading && <Loading />}
      {links.error && <ErrorPanel message={links.error} retry={() => void links.reload()} />}
      {error && <p className="form-error">{error}</p>}
      {links.data && (requests.length ? (
        <DataTable
          columns={['Farmer', 'Phone', 'Village', 'Land', 'Grows / rears', 'Requested', '']}
          rows={requests.map((r) => [
            <span key="n"><strong>{r.farmer?.name ?? 'Unnamed'}</strong><br /><small>{r.farmer_ref}</small></span>,
            r.farmer?.phone ? <a key="p" href={`tel:${r.farmer.phone}`}>{r.farmer.phone}</a> : '—',
            [r.farmer?.village, r.farmer?.block, r.farmer?.district].filter(Boolean).join(', ') || '—',
            r.farmer?.land_holding_acres != null ? `${r.farmer.land_holding_acres} ac` : '—',
            r.farmer?.items.join(', ') || '—',
            formatDate(r.requested_at),
            <span key="a" style={{ display: 'flex', gap: 6 }}>
              <button disabled={busy === r.id} onClick={() => void decide(r.id, 'accept')}>Accept</button>
              <button disabled={busy === r.id} className="secondary-button" onClick={() => void decide(r.id, 'reject')}>Reject</button>
            </span>,
          ])}
        />
      ) : <p className="panel-message">No join requests waiting.</p>)}
    </Card>
  );
}

export function FpoKvkMembersPage({ isPlatformAdmin }: { isPlatformAdmin: boolean }) {
  const organizations = useResource(() => getJson<Organization[]>('/admin/fpo-board/organizations'));
  const [orgId, setOrgId] = useState('');
  const [filter, setFilter] = useState<Filter>(null);
  const [exportError, setExportError] = useState('');

  useEffect(() => {
    if (!orgId && organizations.data?.length) setOrgId(organizations.data[0].id);
  }, [orgId, organizations.data]);

  const board = useResource(() => (orgId ? getJson<Board>(`/admin/fpo-board/organizations/${orgId}`) : Promise.resolve(null)), [orgId]);
  const params = filter ? new URLSearchParams(Object.entries(filter).filter(([k, v]) => k !== 'label' && v) as [string, string][]).toString() : '';
  const members = useResource(
    () => (orgId && filter ? getJson<Member[]>(`/admin/fpo-board/organizations/${orgId}/farmers${params ? `?${params}` : ''}`) : Promise.resolve(null)),
    [orgId, params, filter !== null],
  );
  const refresh = () => { void organizations.reload(); void board.reload(); if (filter) void members.reload(); };

  async function downloadCsv() {
    setExportError('');
    try {
      const blob = await (await call(`/admin/fpo-board/organizations/${orgId}/farmers.csv${params ? `?${params}` : ''}`)).blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${board.data?.organization.name ?? 'members'}-members.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : 'Download failed.');
    }
  }

  if (organizations.loading) return <Loading />;
  if (organizations.error) return <ErrorPanel message={organizations.error} retry={() => void organizations.reload()} />;
  if (!organizations.data?.length) {
    return <><PageTitle title="FPO / KVK Members" subtitle="Farmers who joined your organization from the app." /><Empty title="No organization yet" body="Agrownex team: create the FPO or KVK in Partner organizations and add its staff." /></>;
  }

  const data = board.data;
  const busiestMonth = Math.max(1, ...(data?.harvest_calendar.map((m) => m.items.reduce((s, i) => s + i.farmer_count, 0)) ?? [1]));
  return (
    <>
      <PageTitle
        title="FPO / KVK Members"
        subtitle="What members grow, rear and produce, when they harvest, and what they need."
        action={organizations.data.length > 1 ? (
          <label>Organization<select value={orgId} onChange={(e) => { setOrgId(e.target.value); setFilter(null); }}>
            {organizations.data.map((o) => <option key={o.id} value={o.id}>{kindLabel(o.kind)} · {o.name} ({o.farmer_count}{o.join_request_count ? `, ${o.join_request_count} waiting` : ''})</option>)}
          </select></label>
        ) : undefined}
      />
      {board.loading && <Loading />}
      {board.error && <ErrorPanel message={board.error} retry={() => void board.reload()} />}
      {data && (
        <>
          <div className="metrics">
            <Metric label="Members" value={data.summary.farmer_count} />
            <Metric label="Total land (acres)" value={data.summary.total_land_holding_acres} />
            <Metric label="Filled farm details" value={data.summary.farmers_with_farm_items} />
            <Metric label="Items grown / reared" value={data.farm_items.length} />
          </div>

          {isPlatformAdmin && <Settings org={data.organization} onSaved={refresh} />}
          <JoinRequests orgId={orgId} onChanged={refresh} />

          <Card>
            <div className="section-head"><h2>Crops, livestock &amp; products</h2><span>As entered by farmers at sign-up (approximate)</span></div>
            {data.farm_items.length ? (
              <DataTable
                columns={['Item', 'Type', 'Farmers', 'Approx. quantity', 'For sale', 'Harvest months', '']}
                rows={data.farm_items.map((i) => [
                  <span key="n"><strong>{i.name}</strong>{i.name_ta ? <><br /><small>{i.name_ta}</small></> : null}</span>,
                  i.category_name,
                  i.farmer_count,
                  qty(i.approx_quantity),
                  i.for_sale_farmer_count ? `${i.for_sale_farmer_count} farmer(s) · ${qty(i.for_sale_quantity)}` : '—',
                  i.harvest_months.map((m) => MONTHS[m - 1]).join(', ') || '—',
                  <button key="b" onClick={() => setFilter({ crop: i.code === 'other' ? i.name : i.code, label: i.name })}>Farmers</button>,
                ])}
              />
            ) : <p className="panel-message">No member has filled crop details yet.</p>}
          </Card>

          <Card>
            <div className="section-head"><h2>Harvest calendar</h2><span>Farmers harvesting each month — plan collection and buyers early</span></div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 10, marginTop: 12 }}>
              {data.harvest_calendar.map((m) => {
                const total = m.items.reduce((s, i) => s + i.farmer_count, 0);
                return (
                  <button
                    key={m.month}
                    className="secondary-button"
                    disabled={!total}
                    onClick={() => setFilter({ harvest_month: String(m.month), label: `harvesting in ${m.month_name}` })}
                    style={{ textAlign: 'left', padding: 10, display: 'block', opacity: total ? 1 : 0.55, borderLeft: `6px solid rgba(46,125,50,${0.15 + (0.85 * total) / busiestMonth})` }}
                  >
                    <strong>{m.month_name}</strong> <small>{total ? `${total} farmer(s)` : '—'}</small>
                    <br /><small>{m.items.slice(0, 3).map((i) => `${i.name} (${i.farmer_count})`).join(', ')}{m.items.length > 3 ? '…' : ''}</small>
                  </button>
                );
              })}
            </div>
          </Card>

          <Card>
            <div className="section-head"><h2>What members need</h2><span>Tap to see who needs it</span></div>
            {data.needs.length ? (
              <DataTable
                columns={['Need', 'Farmers', '']}
                rows={data.needs.map((n) => [
                  <span key="n"><strong>{n.name}</strong>{n.name_ta ? <><br /><small>{n.name_ta}</small></> : null}</span>,
                  n.farmer_count,
                  <button key="b" onClick={() => setFilter({ need: n.code, label: `needing ${n.name}` })}>Farmers</button>,
                ])}
              />
            ) : <p className="panel-message">No needs recorded yet.</p>}
            {data.summary.farmer_types.length > 0 && <p className="panel-message">Farmer types: {data.summary.farmer_types.map((t) => `${t.name} ${t.farmer_count}`).join(' · ')}</p>}
          </Card>

          <Card>
            <div className="section-head">
              <h2>{filter ? `Members — ${filter.label}` : 'Member list'}</h2>
              <span style={{ display: 'flex', gap: 8 }}>
                {filter && filter.label !== 'all' && <button onClick={() => setFilter(null)} className="secondary-button">Clear</button>}
                {!filter && <button onClick={() => setFilter({ label: 'all' })}>Show all members</button>}
                {filter && <button onClick={() => void downloadCsv()}>Download Excel (CSV)</button>}
              </span>
            </div>
            {exportError && <p className="form-error">{exportError}</p>}
            {!filter && <p className="panel-message">Pick an item, month or need above, or show all members.</p>}
            {members.loading && <Loading />}
            {members.error && <ErrorPanel message={members.error} retry={() => void members.reload()} />}
            {filter && members.data && (members.data.length ? (
              <DataTable
                columns={['Farmer', 'Phone', 'Village', 'Land', 'Type', 'Grows / rears', 'Needs']}
                rows={members.data.map((f) => [
                  <span key="f"><strong>{f.name ?? 'Unnamed'}</strong><br /><small>{f.farmer_ref}</small></span>,
                  f.phone ? <a key="p" href={`tel:${f.phone}`}>{f.phone}</a> : '—',
                  [f.village, f.district].filter(Boolean).join(', ') || '—',
                  f.land_holding_acres != null ? `${f.land_holding_acres} ac` : '—',
                  f.farmer_type ? titleCase(f.farmer_type) : '—',
                  f.farm_items.map((i) => `${i.name}${i.approx_quantity && i.unit ? ` ${i.approx_quantity.toLocaleString('en-IN')} ${i.unit}` : ''}${i.harvest_months.length ? ` (${i.harvest_months.map((m) => MONTHS[m - 1]).join('/')})` : ''}${i.available_for_sale ? ' · for sale' : ''}`).join('; ') || '—',
                  f.needs.map(titleCase).join(', ') || '—',
                ])}
              />
            ) : <p className="panel-message">No members match.</p>)}
          </Card>
        </>
      )}
    </>
  );
}
