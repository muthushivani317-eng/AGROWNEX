import { useEffect, useState } from 'react';
import { getConfig } from './config';
import { getCsrfToken } from './api';

type QueueRow = { farm_id: string; farm_name: string; state: string; partial_conversion: boolean; items_ticked: number; updated_at: string };
type Case = { state: string; partial_conversion?: boolean; checklist?: Record<string, boolean>; regional_council_approval_ref?: string | null; documents?: { id: string; file_name: string; review_status: string }[]; notice?: string };
async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`${getConfig().apiBaseUrl}${path}`, { method, credentials: 'include', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...(method !== 'GET' && getCsrfToken() ? { 'X-CSRF-Token': getCsrfToken()! } : {}) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  if (!response.ok) throw new Error(`PGS request failed (${response.status}). Verify role, evidence and conversion requirements.`);
  return response.json() as Promise<T>;
}
const states = [
  ['pgs_eligibility_review', 'PGS eligibility review'],
  ['regional_council_approval_required', 'Regional Council approval required'],
  ['pgs_registration_pending', 'PGS registration pending'],
  ['pgs_green_under_conversion', 'PGS-Green—under conversion'],
  ['pgs_organic', 'PGS-Organic'],
  ['non_compliance_review', 'Non-compliance review'],
] as const;
const stateLabel = (value: string) => value === 'pre_certification_trial' ? 'Pre-certification trial' : states.find(([key]) => key === value)?.[1] ?? value;
const CHECKLIST_LABELS: Record<string, string> = {
  whole_holding_reviewed: 'Whole holding reviewed',
  conversion_plan_recorded: 'Conversion plan recorded',
  conversion_completed: 'Conversion completed',
  no_major_non_compliance: 'No major non-compliance found',
};
const checklistLabel = (key: string) => CHECKLIST_LABELS[key] ?? key.replaceAll('_', ' ');
export function OrganicCertificationPage() {
  const [farmId, setFarmId] = useState(''); const [record, setRecord] = useState<Case | null>(null);
  const [state, setState] = useState<(typeof states)[number][0]>('pgs_eligibility_review');
  const [councilRef, setCouncilRef] = useState(''); const [documentId, setDocumentId] = useState('');
  const [certificateId, setCertificateId] = useState(''); const [authority, setAuthority] = useState('');
  const [validFrom, setValidFrom] = useState(''); const [validTo, setValidTo] = useState('');
  const [verified, setVerified] = useState(false); const [majorNonCompliance, setMajorNonCompliance] = useState(false);
  const [note, setNote] = useState(''); const [peerId, setPeerId] = useState(''); const [appraisalDate, setAppraisalDate] = useState('');
  const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  const [queue, setQueue] = useState<QueueRow[] | null>(null);
  const loadQueue = async () => {
    try { setQueue(await request<QueueRow[]>('/admin/organic-mvp/pgs/review-queue')); }
    catch { setQueue([]); } };
  useEffect(() => { void loadQueue(); }, []);
  const openCase = async (id: string) => { setFarmId(id); setBusy(true); setMessage('');
    try { setRecord(await request<Case>(`/admin/organic-mvp/farms/${id}/pgs`)); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Could not load PGS case.'); }
    finally { setBusy(false); } };
  const load = async () => { if (!farmId.trim()) return; setBusy(true); setMessage('');
    try { setRecord(await request<Case>(`/admin/organic-mvp/farms/${farmId.trim()}/pgs`)); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Could not load PGS case.'); }
    finally { setBusy(false); } };
  const review = async () => { setBusy(true); setMessage(''); try {
    await request(`/admin/organic-mvp/farms/${farmId.trim()}/pgs/review`, 'POST', {
      requested_state: state, regional_council_approval_ref: councilRef.trim() || null,
      certificate_document_id: documentId || null, certificate_id: certificateId.trim() || null,
      issuing_authority: authority.trim() || null, valid_from: validFrom || null, valid_to: validTo || null,
      verified_evidence: verified, major_non_compliance: majorNonCompliance,
      non_compliance_note: note.trim() || null,
    }); setMessage('External PGS status recorded. AgrowNex did not issue certification.'); await load(); await loadQueue();
  } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not review PGS case.'); }
    finally { setBusy(false); } };
  const schedule = async () => { setBusy(true); setMessage(''); try {
    await request(`/admin/organic-mvp/farms/${farmId.trim()}/pgs/appraisals`, 'POST',
      { scheduled_on: appraisalDate, peer_user_id: peerId || null }); setMessage('Peer appraisal scheduled.');
  } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not schedule appraisal.'); }
    finally { setBusy(false); } };
  return <section className="page" style={{ display: 'grid', gap: 22 }}>
    <h1>PGS certification companion</h1>
    <p>Record evidence and externally verified status only. AgrowNex does not certify farms. A demonstration plot remains “Pre-certification trial—not PGS certified.”</p>
    {message && <p role="status">{message}</p>}
    <div className="card" style={{ padding: 24, display: 'grid', gap: 10 }}>
      <strong>Waiting for review ({queue?.length ?? '…'})</strong>
      {queue && queue.length === 0 && <p>No farms waiting for review.</p>}
      {queue?.map(row => <div key={row.farm_id} style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <span>{row.farm_name} · {stateLabel(row.state)} · {row.items_ticked} ticked{row.partial_conversion ? ' · partial conversion' : ''} · {new Date(row.updated_at).toLocaleDateString()}</span>
        <button disabled={busy} onClick={() => void openCase(row.farm_id)}>Open</button>
      </div>)}
    </div>
    <div className="card" style={{ padding: 24, display: 'grid', gap: 12 }}>
      <label>Real farm ID <input value={farmId} onChange={event => setFarmId(event.target.value)} /></label>
      <button disabled={busy || !farmId.trim()} onClick={() => void load()}>Load PGS case</button>
      {record && <><strong>Current state: {stateLabel(record.state)}</strong><p>{record.notice}</p>
        {record.partial_conversion && <p>Partial conversion — Regional Council approval required.</p>}
        <p>Farmer checklist: {Object.entries(record.checklist || {}).map(([key, value]) => `${checklistLabel(key)} ${value ? '✓' : '✗'}`).join(' · ') || 'Not completed'}</p>
        <p>Submitted documents: {record.documents?.length || 0}</p>
        {record.documents?.map(document => <p key={document.id}>{document.file_name} · {document.review_status} · {document.id}</p>)}
      </>}
    </div>
    {record && <div className="card" style={{ padding: 24, display: 'grid', gap: 12 }}>
      <h2>Record external review</h2>
      <label>Verified external status <select value={state} onChange={event => setState(event.target.value as typeof state)}>{states.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>Regional Council approval reference (required for partial conversion) <input value={councilRef} onChange={event => setCouncilRef(event.target.value)} /></label>
      <label>Approved certificate document <select value={documentId} onChange={event => setDocumentId(event.target.value)}><option value="">Not selected</option>{record.documents?.filter(document => document.review_status === 'approved').map(document => <option key={document.id} value={document.id}>{document.file_name}</option>)}</select></label>
      <label>Certificate ID <input value={certificateId} onChange={event => setCertificateId(event.target.value)} /></label>
      <label>Issuing authority <input value={authority} onChange={event => setAuthority(event.target.value)} /></label>
      <label>Valid from <input type="date" value={validFrom} onChange={event => setValidFrom(event.target.value)} /></label>
      <label>Valid to <input type="date" value={validTo} onChange={event => setValidTo(event.target.value)} /></label>
      <label><input type="checkbox" checked={verified} onChange={event => setVerified(event.target.checked)} /> I verified the issuing authority, certificate and dates against the source</label>
      <label><input type="checkbox" checked={majorNonCompliance} onChange={event => setMajorNonCompliance(event.target.checked)} /> Major non-compliance found</label>
      <label>Review note <textarea value={note} onChange={event => setNote(event.target.value)} /></label>
      <button disabled={busy} onClick={() => void review()}>Save external status review</button>
    </div>}
    {record && <div className="card" style={{ padding: 24, display: 'grid', gap: 12 }}>
      <h2>Peer appraisal</h2><label>Date <input type="date" value={appraisalDate} onChange={event => setAppraisalDate(event.target.value)} /></label>
      <label>Peer user ID <input value={peerId} onChange={event => setPeerId(event.target.value)} /></label>
      <button disabled={busy || !appraisalDate || !peerId.trim()} onClick={() => void schedule()}>Schedule peer appraisal</button>
    </div>}
  </section>;
}
