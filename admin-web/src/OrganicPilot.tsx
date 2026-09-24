import { useEffect, useState } from 'react';
import { getConfig } from './config';
import { getCsrfToken } from './api';

type Fpo = { id: string; name: string; district: string; is_test: boolean };
type Pilot = { id: string; fpo_id: string | null; fpo_name: string | null; district: string | null; crop_ids: string[]; agronomist_user_id: string | null; certification_pathway: string | null; is_test: boolean; statuses: string[] };
type Dashboard = { enrolled_farm_count: number; statuses: string[]; acreage_by_crop: Record<string, number>; forecast: Record<string, { farmer_entered_expected_kg: number; source: string }> | null; buyer_prices: null };

async function pilotRequest<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`${getConfig().apiBaseUrl}${path}`, {
    method, credentials: 'include', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...(method !== 'GET' && getCsrfToken() ? { 'X-CSRF-Token': getCsrfToken()! } : {}) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) throw new Error(`Pilot request failed (${response.status}).`);
  return response.json() as Promise<T>;
}

export function OrganicPilotPage() {
  const [pilots, setPilots] = useState<Pilot[]>([]);
  const [fpos, setFpos] = useState<Fpo[]>([]);
  const [fpoId, setFpoId] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [fpo, setFpo] = useState('');
  const [district, setDistrict] = useState('');
  const [crops, setCrops] = useState('');
  const [agronomist, setAgronomist] = useState('');
  const [pathway, setPathway] = useState('');
  const [isTest, setIsTest] = useState(false);
  const [enrollFarmId, setEnrollFarmId] = useState('');
  const [enrollFarmerId, setEnrollFarmerId] = useState('');
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const reload = async () => {
    try { setPilots(await pilotRequest<Pilot[]>('/admin/organic-mvp/pilots')); setFpos(await pilotRequest<Fpo[]>('/admin/organic-mvp/fpos')); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not load pilots.'); }
  };
  useEffect(() => { void reload(); }, []);
  useEffect(() => {
    if (!selected) { setDashboard(null); return; }
    void pilotRequest<Dashboard>(`/admin/organic-mvp/pilot/${selected}/harvest-dashboard`).then(setDashboard).catch(() => setDashboard(null));
  }, [selected]);

  const save = async () => {
    setBusy(true); setError('');
    try {
      const crop_ids = crops.split(',').map(value => value.trim()).filter(Boolean);
      if (crop_ids.length > 2) throw new Error('Select at most two real pilot crops.');
      const payload = { fpo_id: fpoId, fpo_name: null, district: district.trim() || null,
        crop_ids, agronomist_user_id: agronomist.trim() || null,
        certification_pathway: pathway || null, is_test: isTest };
      const result = await pilotRequest<{ id: string }>(
        selected ? `/admin/organic-mvp/pilot/${selected}` : '/admin/organic-mvp/pilot',
        selected ? 'PUT' : 'POST', payload);
      setSelected(result.id);
      await reload();
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save pilot.'); }
    finally { setBusy(false); }
  };

  const choose = (pilot: Pilot) => {
    setSelected(pilot.id); setFpo(pilot.fpo_name ?? ''); setDistrict(pilot.district ?? '');
    setFpoId(pilot.fpo_id);
    setCrops(pilot.crop_ids.join(', ')); setAgronomist(pilot.agronomist_user_id ?? '');
    setPathway(pilot.certification_pathway ?? ''); setIsTest(pilot.is_test);
  };
  const createFpo = async () => {
    if (!fpo.trim() || !district.trim()) { setError('A real FPO name and district are required.'); return; }
    setBusy(true); setError('');
    try { const result = await pilotRequest<Fpo>('/admin/organic-mvp/fpos', 'POST',
      { name: fpo.trim(), district: district.trim(), is_test: isTest });
      setFpoId(result.id); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not record FPO.'); }
    finally { setBusy(false); }
  };
  const enroll = async () => {
    if (!selected || !consent || !enrollFarmId.trim() || !enrollFarmerId.trim()) {
      setError('Select a pilot, enter real farmer/farm IDs, and confirm recorded consent.'); return;
    }
    setBusy(true); setError('');
    try {
      await pilotRequest(`/admin/organic-mvp/pilot/${selected}/enroll`, 'POST',
        { farm_id: enrollFarmId.trim(), farmer_user_id: enrollFarmerId.trim(), consent_confirmed: true });
      setEnrollFarmId(''); setEnrollFarmerId(''); setConsent(false);
      setDashboard(await pilotRequest<Dashboard>(`/admin/organic-mvp/pilot/${selected}/harvest-dashboard`));
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not enroll farm.'); }
    finally { setBusy(false); }
  };

  return <section className="page organic-pilot-page">
    <h1>Organic pilot setup</h1>
    <p>Configure a real FPO, crops, agronomist and certification pathway. No sample records are created.</p>
    {error && <p role="alert" className="error">{error}</p>}
    <div className="card" style={{ padding: 24, display: 'grid', gap: 14, maxWidth: 760 }}>
      <h2>{selected ? 'Update pilot' : 'New pilot'}</h2>
      <label>Selected real FPO <select value={fpoId ?? ''} onChange={event => { const id = event.target.value || null; const item = fpos.find(row => row.id === id); setFpoId(id); if (item) { setFpo(item.name); setDistrict(item.district); setIsTest(item.is_test); } }}>
        <option value="">FPO not selected</option>{fpos.map(item => <option key={item.id} value={item.id}>{item.is_test ? '[TEST] ' : ''}{item.name} · {item.district}</option>)}
      </select></label>
      <label>Or record a real FPO name <input value={fpo} onChange={event => setFpo(event.target.value)} placeholder="Do not enter a sample FPO" /></label>
      <label>District <input value={district} onChange={event => setDistrict(event.target.value)} /></label>
      <button disabled={busy || !fpo.trim() || !district.trim()} onClick={() => void createFpo()}>Record FPO for selection</button>
      <label>Pilot crops (up to two, comma-separated) <input value={crops} onChange={event => setCrops(event.target.value)} placeholder="Pilot crops not selected" /></label>
      <label>Agronomist user ID <input value={agronomist} onChange={event => setAgronomist(event.target.value)} placeholder="Assign an actual reviewer" /></label>
      <label>Certification pathway <select value={pathway} onChange={event => setPathway(event.target.value)}>
        <option value="">Not selected</option><option value="pre_certification_trial">Pre-certification trial</option><option value="pgs_eligibility_review">PGS eligibility review</option>
      </select></label>
      <label><input type="checkbox" checked={isTest} disabled={Boolean(selected)} onChange={event => setIsTest(event.target.checked)} /> Test pilot (permanently segregated from production)</label>
      <button disabled={busy} onClick={() => void save()}>{busy ? 'Saving…' : 'Save pilot setup'}</button>
    </div>
    <h2>Configured pilots</h2>
    {pilots.length === 0 ? <p>Pilot setup required · FPO not selected · Pilot crops not selected</p> :
      <div>{pilots.map(pilot => <button key={pilot.id} onClick={() => choose(pilot)} style={{ display: 'block', marginBottom: 10 }}>
        {pilot.is_test ? '[TEST] ' : ''}{pilot.fpo_name || 'FPO not selected'} — {pilot.statuses.join(' · ') || 'Configured'}
      </button>)}</div>}
    {selected && <div className="card" style={{ padding: 24, display: 'grid', gap: 12, maxWidth: 760 }}>
      <h2>Enroll a real farmer</h2>
      <p>Use only a farmer’s existing account and farm. Consent must already be recorded outside this form.</p>
      <label>Farm ID <input value={enrollFarmId} onChange={event => setEnrollFarmId(event.target.value)} /></label>
      <label>Farmer user ID <input value={enrollFarmerId} onChange={event => setEnrollFarmerId(event.target.value)} /></label>
      <label><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} /> I confirm this farmer gave pilot enrollment consent</label>
      <button disabled={busy || !consent} onClick={() => void enroll()}>Enroll farmer</button>
    </div>}
    {dashboard && <div className="card" style={{ padding: 24, marginTop: 20 }}>
      <h2>FPO harvest dashboard</h2>
      <p>{dashboard.enrolled_farm_count} real enrolled farms</p>
      {dashboard.statuses.map(status => <p key={status}>{status}</p>)}
      {Object.entries(dashboard.acreage_by_crop).map(([crop, area]) => <p key={crop}>{crop}: {area.toFixed(2)} ha</p>)}
      {dashboard.forecast && Object.entries(dashboard.forecast).map(([crop, entry]) =>
        <p key={crop}>{crop}: {entry.farmer_entered_expected_kg} kg farmer-entered expectation (not verified)</p>)}
      <p>Buyer prices unavailable until verified buyer demand is entered.</p>
    </div>}
  </section>;
}
