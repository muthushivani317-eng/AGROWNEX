import { useEffect, useState } from 'react';
import { getConfig } from './config';
import { getCsrfToken } from './api';

type Rule = { id: string; version: string; status: string; questions: unknown[]; scoring: Record<string, unknown> };
type Template = { id: string; crop_id: string; district: string; version: string; status: string; tasks: unknown[] };
async function request<T>(path: string, method = 'GET', payload?: unknown): Promise<T> {
  const response = await fetch(`${getConfig().apiBaseUrl}${path}`, { method, credentials: 'include', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...(method !== 'GET' && getCsrfToken() ? { 'X-CSRF-Token': getCsrfToken()! } : {}) },
    ...(payload === undefined ? {} : { body: JSON.stringify(payload) }) });
  if (!response.ok) throw new Error(`Request failed (${response.status}). Check role, reviewed content and pilot assignment.`);
  return response.json() as Promise<T>;
}
export function OrganicContentPage() {
  const [rules, setRules] = useState<Rule[]>([]); const [templates, setTemplates] = useState<Template[]>([]);
  const [version, setVersion] = useState(''); const [questions, setQuestions] = useState(''); const [scoring, setScoring] = useState('');
  const [crop, setCrop] = useState(''); const [district, setDistrict] = useState(''); const [templateVersion, setTemplateVersion] = useState(''); const [tasks, setTasks] = useState('');
  const [cycleId, setCycleId] = useState(''); const [templateId, setTemplateId] = useState('');
  const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  const reload = async () => { const [nextRules, nextTemplates] = await Promise.all([
    request<Rule[]>('/admin/organic-mvp/readiness-rules'), request<Template[]>('/admin/organic-mvp/task-templates')]);
    setRules(nextRules); setTemplates(nextTemplates); };
  useEffect(() => { void reload().catch(error => setMessage(String(error))); }, []);
  const run = async (work: () => Promise<unknown>, success: string) => { setBusy(true); setMessage('');
    try { await work(); await reload(); setMessage(success); } catch (error) { setMessage(error instanceof Error ? error.message : 'Operation failed.'); }
    finally { setBusy(false); } };
  return <section className="page" style={{ display: 'grid', gap: 24 }}>
    <h1>Organic content review</h1>
    <p>Only real, expert-authored content belongs here. Drafts do not appear to farmers. Crop tasks activate only after the assigned pilot agronomist reviews them.</p>
    {message && <p role="status">{message}</p>}
    <div className="card" style={{ padding: 24, display: 'grid', gap: 12 }}>
      <h2>Readiness question set</h2>
      <label>Version <input value={version} onChange={event => setVersion(event.target.value)} /></label>
      <label>Questions JSON (Tamil text, answer options and points) <textarea rows={8} value={questions} onChange={event => setQuestions(event.target.value)} /></label>
      <label>Scoring JSON (bands and Tamil recommendations) <textarea rows={6} value={scoring} onChange={event => setScoring(event.target.value)} /></label>
      <button disabled={busy} onClick={() => void run(() => request('/admin/organic-mvp/readiness-rules', 'POST',
        { version, questions: JSON.parse(questions), scoring: JSON.parse(scoring) }), 'Readiness draft saved.')}>Save readiness draft</button>
      {rules.map(rule => <div key={rule.id}><strong>{rule.version}</strong> · {rule.status} · {rule.questions.length} questions
        {rule.status === 'draft' && <button disabled={busy} onClick={() => void run(() => request(`/admin/organic-mvp/readiness-rules/${rule.id}/review`, 'POST', { approved: true }), 'Question set approved.')}>Approve reviewed questions</button>}</div>)}
    </div>
    <div className="card" style={{ padding: 24, display: 'grid', gap: 12 }}>
      <h2>90-day crop task template</h2>
      <label>Pilot crop ID <input value={crop} onChange={event => setCrop(event.target.value)} /></label>
      <label>Pilot district <input value={district} onChange={event => setDistrict(event.target.value)} /></label>
      <label>Version <input value={templateVersion} onChange={event => setTemplateVersion(event.target.value)} /></label>
      <label>Tasks JSON (day_offset 0–90, title_ta, body_ta; English optional) <textarea rows={8} value={tasks} onChange={event => setTasks(event.target.value)} /></label>
      <button disabled={busy} onClick={() => void run(() => request('/admin/organic-mvp/task-templates', 'POST',
        { crop_id: crop, district, version: templateVersion, tasks: JSON.parse(tasks) }), 'Task template draft saved.')}>Save task draft</button>
      {templates.map(template => <div key={template.id}><strong>{template.crop_id}</strong> · {template.district} · {template.version} · {template.status} · {template.tasks.length} tasks
        {template.status === 'draft' && <button disabled={busy} onClick={() => void run(() => request(`/admin/organic-mvp/task-templates/${template.id}/review`, 'POST', { approved: true, note: 'Reviewed by assigned pilot agronomist' }), 'Template reviewed.')}>Mark agronomist reviewed</button>}</div>)}
    </div>
    <div className="card" style={{ padding: 24, display: 'grid', gap: 12 }}>
      <h2>Activate an approved crop plan</h2>
      <p>Requires a real enrolled farm, matching crop and district, sowing date, and a reviewed template. This schedules the 90-day tasks and in-app reminders.</p>
      <label>Crop cycle ID <input value={cycleId} onChange={event => setCycleId(event.target.value)} /></label>
      <label>Reviewed template <select value={templateId} onChange={event => setTemplateId(event.target.value)}><option value="">Select template</option>{templates.filter(row => row.status === 'agronomist_reviewed').map(row => <option key={row.id} value={row.id}>{row.crop_id} · {row.district} · {row.version}</option>)}</select></label>
      <button disabled={busy || !cycleId || !templateId} onClick={() => void run(() => request(`/admin/organic-mvp/crop-cycles/${cycleId}/activate-plan?template_id=${templateId}`, 'POST'), 'Reviewed plan activated.')}>Activate reviewed plan</button>
    </div>
  </section>;
}
