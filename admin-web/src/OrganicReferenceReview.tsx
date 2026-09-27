import { useEffect, useState } from 'react';
import { api } from './api';

type ReviewItem = {
  id: string; slug: string; category: string; name_en: string; name_ta: string;
  purpose_en: string; purpose_ta: string; guidance: { key_points?: string[] } & Record<string, unknown>;
  applicable_crops: string[]; source_organization: string; document_reference: string;
  source_url: string; source_version: string;
};

/** Content reviewers approve cited organic inputs before farmers can see them. */
export function OrganicReferenceReviewPage() {
  const [items, setItems] = useState<ReviewItem[] | null>(null);
  const [message, setMessage] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    try { setItems(await api<ReviewItem[]>('/admin/organic-inputs/review-queue')); }
    catch (error) { setItems([]); setMessage(error instanceof Error ? error.message : 'Could not load the review queue.'); }
  };
  useEffect(() => { void load(); }, []);

  const approve = async (item: ReviewItem) => {
    setBusyId(item.id); setMessage('');
    try {
      await api(`/admin/organic-inputs/${item.id}/promote`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'Source link, content and Tamil text checked by reviewer' }),
      });
      setMessage(`Approved: ${item.name_en}. It is now visible in the farmer app.`);
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not approve.'); }
    finally { setBusyId(null); }
  };

  return <section className="page" style={{ display: 'grid', gap: 18 }}>
    <h1>Organic library review</h1>
    <p>These organic inputs come from public sources (TNAU, NITI Aayog, government pages). Farmers cannot see an input until you approve it. Open the source link, check the text and the Tamil, then approve.</p>
    {message && <p role="status">{message}</p>}
    {items === null && <p>Loading…</p>}
    {items?.length === 0 && <p>Nothing waiting for review.</p>}
    {items?.map(item => <div key={item.id} className="card" style={{ padding: 20, display: 'grid', gap: 8 }}>
      <strong>{item.name_en} · {item.name_ta}</strong>
      <small>{item.category.replaceAll('_', ' ')}{item.applicable_crops.length ? ` · ${item.applicable_crops.join(', ')}` : ''}</small>
      <p style={{ margin: 0 }}>{item.purpose_en}</p>
      <p style={{ margin: 0 }}>{item.purpose_ta}</p>
      {item.guidance.key_points?.length ? <ul style={{ margin: 0 }}>{item.guidance.key_points.map(point => <li key={point}>{point}</li>)}</ul> : null}
      <small>Source: {item.source_organization} — <a href={item.source_url} target="_blank" rel="noreferrer">{item.document_reference}</a></small>
      <div><button disabled={busyId !== null} onClick={() => void approve(item)}>{busyId === item.id ? 'Approving…' : 'Approve'}</button></div>
    </div>)}
  </section>;
}
