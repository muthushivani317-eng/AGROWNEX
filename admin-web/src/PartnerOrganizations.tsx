import { useState } from 'react';
import { Building2, PlusCircle, RefreshCw, Search, ShieldCheck, Trash2, UserPlus } from 'lucide-react';
import { getCsrfToken } from './api';
import { getConfig } from './config';
import { Card, DataTable, ErrorPanel, Loading, PageTitle } from './components';
import { useResource } from './useResource';
import type { Farmer, Page } from './types';

type Fpo = { id: string; name: string; district: string; registration_reference: string | null; is_test: boolean };
type Organization = { id: string; name: string; kind: 'fpo' | 'kvk' | 'agri_community'; fpo_id: string | null; is_test: boolean };
type StaffRole = 'manager' | 'advisor' | 'viewer';

// This module's endpoints (`/admin/organic-partner/...`) return raw JSON, not
// the `{success,data}` envelope the shared `api()` helper expects — same
// reason OrganicPilot.tsx has its own fetch wrapper instead of reusing `api()`.
async function partnerRequest<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`${getConfig().apiBaseUrl}${path}`, {
    method,
    credentials: 'include',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...(method !== 'GET' && getCsrfToken() ? { 'X-CSRF-Token': getCsrfToken()! } : {}) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null) as { detail?: { message?: string } | string } | null;
    const message = typeof detail?.detail === 'string' ? detail.detail : detail?.detail?.message;
    throw new Error(message ?? `Request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export function PartnerOrganizationsPage() {
  const fpos = useResource(() => partnerRequest<Fpo[]>('/admin/organic-partner/fpos'));
  const organizations = useResource(() => partnerRequest<Organization[]>('/admin/organic-partner/organizations'));

  // New FPO
  const [fpoName, setFpoName] = useState('');
  const [fpoDistrict, setFpoDistrict] = useState('');
  const [fpoRegRef, setFpoRegRef] = useState('');
  const [fpoIsTest, setFpoIsTest] = useState(false);
  const [fpoBusy, setFpoBusy] = useState(false);
  const [fpoError, setFpoError] = useState('');
  const [fpoSuccess, setFpoSuccess] = useState('');
  const [fpoDeletingId, setFpoDeletingId] = useState('');

  // New organization
  const [orgName, setOrgName] = useState('');
  const [orgKind, setOrgKind] = useState<Organization['kind']>('fpo');
  const [orgFpoId, setOrgFpoId] = useState('');
  const [orgIsTest, setOrgIsTest] = useState(false);
  const [orgBusy, setOrgBusy] = useState(false);
  const [orgError, setOrgError] = useState('');
  const [orgSuccess, setOrgSuccess] = useState('');

  // Add staff
  const [staffOrgId, setStaffOrgId] = useState('');
  const [staffRole, setStaffRole] = useState<StaffRole>('manager');
  const [staffSearch, setStaffSearch] = useState('');
  const [staffMatches, setStaffMatches] = useState<Farmer[]>([]);
  const [staffSearching, setStaffSearching] = useState(false);
  const [staffUserId, setStaffUserId] = useState('');
  const [staffLabel, setStaffLabel] = useState('');
  const [staffBusy, setStaffBusy] = useState(false);
  const [staffError, setStaffError] = useState('');
  const [staffSuccess, setStaffSuccess] = useState('');

  function refreshAll() { void fpos.reload(); void organizations.reload(); }

  async function createFpo() {
    setFpoBusy(true); setFpoError(''); setFpoSuccess('');
    try {
      if (!fpoName.trim() || !fpoDistrict.trim()) throw new Error('Name and district are required.');
      const result = await partnerRequest<{ id: string; name: string }>('/admin/organic-partner/fpos', 'POST', {
        name: fpoName.trim(), district: fpoDistrict.trim(),
        registration_reference: fpoRegRef.trim() || null, is_test: fpoIsTest,
      });
      setFpoSuccess(`FPO "${result.name}" created.`);
      setFpoName(''); setFpoDistrict(''); setFpoRegRef(''); setFpoIsTest(false);
      await fpos.reload();
    } catch (cause) { setFpoError(cause instanceof Error ? cause.message : 'Could not create FPO.'); }
    finally { setFpoBusy(false); }
  }

  async function deleteFpo(id: string, name: string) {
    if (!window.confirm(`Delete FPO "${name}"? This cannot be undone.`)) return;
    setFpoDeletingId(id); setFpoError(''); setFpoSuccess('');
    try {
      await partnerRequest<{ status: string }>(`/admin/organic-partner/fpos/${id}`, 'DELETE');
      setFpoSuccess(`FPO "${name}" deleted.`);
      await fpos.reload();
    } catch (cause) { setFpoError(cause instanceof Error ? cause.message : 'Could not delete FPO.'); }
    finally { setFpoDeletingId(''); }
  }

  async function createOrganization() {
    setOrgBusy(true); setOrgError(''); setOrgSuccess('');
    try {
      if (!orgName.trim()) throw new Error('Organization name is required.');
      if (orgKind === 'fpo' && !orgFpoId) throw new Error('Select the FPO this organization belongs to.');
      const result = await partnerRequest<{ id: string }>('/admin/organic-partner/organizations', 'POST', {
        name: orgName.trim(), kind: orgKind,
        fpo_id: orgKind === 'fpo' ? orgFpoId : null, is_test: orgIsTest,
      });
      setOrgSuccess(`Organization created (id ${result.id.slice(0, 8)}…).`);
      setOrgName(''); setOrgFpoId(''); setOrgIsTest(false);
      await organizations.reload();
    } catch (cause) { setOrgError(cause instanceof Error ? cause.message : 'Could not create organization.'); }
    finally { setOrgBusy(false); }
  }

  async function searchFarmers() {
    setStaffSearching(true); setStaffError('');
    try {
      const params = new URLSearchParams({ page: '1', page_size: '5', search: staffSearch.trim() });
      const result = await partnerRequest<Page<Farmer>>(`/admin/farmers?${params}`);
      setStaffMatches(result.items);
    } catch (cause) { setStaffError(cause instanceof Error ? cause.message : 'Search failed.'); }
    finally { setStaffSearching(false); }
  }

  async function addStaff() {
    setStaffBusy(true); setStaffError(''); setStaffSuccess('');
    try {
      if (!staffOrgId) throw new Error('Select an organization.');
      if (!staffUserId.trim()) throw new Error('Search for and select a user, or enter their user ID directly.');
      const result = await partnerRequest<{ id: string; status: string }>(
        `/admin/organic-partner/organizations/${staffOrgId}/staff`, 'POST',
        { user_id: staffUserId.trim(), role: staffRole });
      setStaffSuccess(`Added as ${staffRole} — staff record ${result.status}.`);
      setStaffUserId(''); setStaffLabel(''); setStaffSearch(''); setStaffMatches([]);
    } catch (cause) { setStaffError(cause instanceof Error ? cause.message : 'Could not add staff member.'); }
    finally { setStaffBusy(false); }
  }

  const loading = fpos.loading || organizations.loading;
  const error = fpos.error || organizations.error;

  return <section className="page">
    <PageTitle title="Partner organizations" subtitle="Create real FPOs, link them to partner organizations, and add staff access. Owner/Super Admin only — every action is audit-logged."
      action={<button onClick={refreshAll} disabled={loading}><RefreshCw size={16}/> Refresh</button>} />

    {loading ? <Loading /> : error ? <ErrorPanel message={error} retry={refreshAll} /> : <>

    <Card>
      <h2><Building2 size={18} aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 8 }}/>1. Add an FPO</h2>
      <p>Register a real Farmer Producer Organization. No sample/placeholder FPOs.</p>
      {fpoError && <p role="alert" className="error">{fpoError}</p>}
      {fpoSuccess && <p role="status" style={{ color: 'var(--leaf)' }}>{fpoSuccess}</p>}
      <div style={{ display: 'grid', gap: 14, maxWidth: 520 }}>
        <label>FPO name <input value={fpoName} onChange={e => setFpoName(e.target.value)} placeholder="Registered FPO name" /></label>
        <label>District <input value={fpoDistrict} onChange={e => setFpoDistrict(e.target.value)} placeholder="District" /></label>
        <label>Registration reference (optional) <input value={fpoRegRef} onChange={e => setFpoRegRef(e.target.value)} placeholder="Registrar/CIN reference" /></label>
        <label><input type="checkbox" checked={fpoIsTest} onChange={e => setFpoIsTest(e.target.checked)} /> Test FPO (kept out of production data)</label>
        <button disabled={fpoBusy || !fpoName.trim() || !fpoDistrict.trim()} onClick={() => void createFpo()}>
          <PlusCircle size={16} aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 6 }}/>{fpoBusy ? 'Creating…' : 'Create FPO'}
        </button>
      </div>
      <h3 style={{ marginTop: 22 }}>Existing FPOs ({fpos.data?.length ?? 0})</h3>
      {fpos.data && fpos.data.length > 0
        ? <DataTable columns={['Name', 'District', 'Registration ref.', 'Type', 'Actions']}
            rows={fpos.data.map(f => [f.name, f.district, f.registration_reference ?? '—', f.is_test ? 'Test' : 'Real',
              <button disabled={fpoDeletingId === f.id} onClick={() => void deleteFpo(f.id, f.name)} style={{ background: 'var(--danger)' }}>
                <Trash2 size={14} aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 6 }}/>{fpoDeletingId === f.id ? 'Deleting…' : 'Delete'}
              </button>])} />
        : <p>No FPOs recorded yet.</p>}
    </Card>

    <Card>
      <h2><Building2 size={18} aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 8 }}/>2. Create a partner organization</h2>
      <p>An organization is what gets platform access — it links to an FPO (or stands alone for a KVK/agri-community partner).</p>
      {orgError && <p role="alert" className="error">{orgError}</p>}
      {orgSuccess && <p role="status" style={{ color: 'var(--leaf)' }}>{orgSuccess}</p>}
      <div style={{ display: 'grid', gap: 14, maxWidth: 520 }}>
        <label>Organization name <input value={orgName} onChange={e => setOrgName(e.target.value)} placeholder="Organization display name" /></label>
        <label>Kind <select value={orgKind} onChange={e => setOrgKind(e.target.value as Organization['kind'])}>
          <option value="fpo">FPO</option><option value="kvk">KVK</option><option value="agri_community">Agri community</option>
        </select></label>
        {orgKind === 'fpo' && <label>Linked FPO <select value={orgFpoId} onChange={e => setOrgFpoId(e.target.value)}>
          <option value="">Select an FPO</option>
          {fpos.data?.map(f => <option key={f.id} value={f.id}>{f.is_test ? '[TEST] ' : ''}{f.name} · {f.district}</option>)}
        </select></label>}
        <label><input type="checkbox" checked={orgIsTest} onChange={e => setOrgIsTest(e.target.checked)} /> Test organization</label>
        <button disabled={orgBusy || !orgName.trim() || (orgKind === 'fpo' && !orgFpoId)} onClick={() => void createOrganization()}>
          <PlusCircle size={16} aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 6 }}/>{orgBusy ? 'Creating…' : 'Create organization'}
        </button>
      </div>
      <h3 style={{ marginTop: 22 }}>Existing organizations ({organizations.data?.length ?? 0})</h3>
      {organizations.data && organizations.data.length > 0
        ? <DataTable columns={['Name', 'Kind', 'Linked FPO', 'Type']}
            rows={organizations.data.map(o => [o.name, o.kind, fpos.data?.find(f => f.id === o.fpo_id)?.name ?? '—', o.is_test ? 'Test' : 'Real'])} />
        : <p>No organizations recorded yet.</p>}
    </Card>

    <Card>
      <h2><UserPlus size={18} aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 8 }}/>3. Add staff access to an organization</h2>
      <p>Search an existing user by name/phone, or paste their user ID directly. <b>Manager</b> is the privileged, org-scoped role — closest equivalent to an "FPO admin".</p>
      {staffError && <p role="alert" className="error">{staffError}</p>}
      {staffSuccess && <p role="status" style={{ color: 'var(--leaf)' }}>{staffSuccess}</p>}
      <div style={{ display: 'grid', gap: 14, maxWidth: 520 }}>
        <label>Organization <select value={staffOrgId} onChange={e => setStaffOrgId(e.target.value)}>
          <option value="">Select an organization</option>
          {organizations.data?.map(o => <option key={o.id} value={o.id}>{o.is_test ? '[TEST] ' : ''}{o.name} ({o.kind})</option>)}
        </select></label>
        <label>Role <select value={staffRole} onChange={e => setStaffRole(e.target.value as StaffRole)}>
          <option value="manager">Manager (org-scoped admin access)</option>
          <option value="advisor">Advisor</option>
          <option value="viewer">Viewer</option>
        </select></label>
        <label>Search existing user by name or phone
          <div style={{ display: 'flex', gap: 8 }}>
            <input value={staffSearch} onChange={e => setStaffSearch(e.target.value)} placeholder="Name or phone number" />
            <button type="button" disabled={staffSearching || !staffSearch.trim()} onClick={() => void searchFarmers()}>
              <Search size={16} aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 6 }}/>{staffSearching ? 'Searching…' : 'Search'}
            </button>
          </div>
        </label>
        {staffMatches.length > 0 && <div style={{ display: 'grid', gap: 6 }}>
          {staffMatches.map(m => <button key={m.user_id} type="button"
            style={{ textAlign: 'left', background: staffUserId === m.user_id ? 'var(--mint)' : undefined }}
            onClick={() => { setStaffUserId(m.user_id); setStaffLabel(`${m.full_name ?? 'Unnamed'} · ${m.farmer_ref ?? m.user_id.slice(0, 8)}`); }}>
            {m.full_name ?? 'Unnamed'} — {m.farmer_ref ?? m.user_id.slice(0, 8)} ({m.district ?? 'district unknown'})
          </button>)}
        </div>}
        <label>Selected user ID (or paste one directly)
          <input value={staffUserId} onChange={e => { setStaffUserId(e.target.value); setStaffLabel(''); }} placeholder="User ID (UUID)" />
        </label>
        {staffLabel && <p><ShieldCheck size={14} aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 4 }}/>Selected: {staffLabel}</p>}
        <button disabled={staffBusy || !staffOrgId || !staffUserId.trim()} onClick={() => void addStaff()}>
          <UserPlus size={16} aria-hidden="true" style={{ verticalAlign: 'middle', marginRight: 6 }}/>{staffBusy ? 'Adding…' : 'Add staff member'}
        </button>
      </div>
    </Card>
    </>}
  </section>;
}
