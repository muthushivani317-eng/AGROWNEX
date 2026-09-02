import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle2, Circle, Download, FileText, IndianRupee, Percent, Search, ShieldCheck, Wallet } from 'lucide-react';
import { api } from './api';
import { DataTable, ErrorPanel, Loading, formatDate } from './components';
import { useResource } from './useResource';
import type { Page, Procurement } from './types';
import './ProcurementLedgers.css';

type MoneyEntry = { id: string; entry_type: string; amount: string; currency: string; occurred_at: string; reference?: string };
export type CommerceLedger = {
  offer_id: string; case_status: string;
  transaction: { id: string; quantity: number; unit_price: string; gross_amount: string; currency: string; occurred_at: string } | null;
  pickups: { id: string; status: string; scheduled_at: string | null; occurred_at: string | null; location: string | null; created_at: string }[];
  payments: MoneyEntry[]; commissions: MoneyEntry[];
};
const tabs = ['Transactions', 'Pickups', 'Payments', 'Commissions', 'Reconciliation'] as const;
type Tab = typeof tabs[number];
export function moneyTotal(entries: MoneyEntry[], type: string, currency: string): string {
  const selected = entries.filter(entry => entry.entry_type === type);
  if (selected.some(entry => entry.currency !== currency || !/^\d+(\.\d{1,2})?$/.test(entry.amount))) return 'Unavailable';
  const cents = selected.reduce((sum, entry) => {
    const [whole, fraction = ''] = entry.amount.split('.');
    return sum + BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'));
  }, 0n);
  return `${cents / 100n}.${String(cents % 100n).padStart(2, '0')}`;
}
const amountLabel = (amount: string, currency: string) => amount === 'Unavailable' ? amount : `${currency} ${amount}`;
export function ledgerExport(ledger: CommerceLedger): string {
  const rows: unknown[][] = [['Listing ID', 'Record type', 'Record ID', 'Status / entry', 'Amount', 'Currency', 'Date']];
  if (ledger.transaction) { const t = ledger.transaction; rows.push([ledger.offer_id, 'Transaction', t.id, 'Recorded', t.gross_amount, t.currency, t.occurred_at]); }
  ledger.pickups.forEach(p => rows.push([ledger.offer_id, 'Pickup', p.id, p.status, '', '', p.occurred_at ?? p.scheduled_at]));
  for (const [name, entries] of [['Payment', ledger.payments], ['Commission', ledger.commissions]] as const) entries.forEach(e => rows.push([ledger.offer_id, name, e.id, e.entry_type, e.amount, e.currency, e.occurred_at]));
  return rows.map(row => row.map(value => { let text = String(value ?? ''); if (/^[\s]*[=+\-@]/.test(text)) text = `'${text}`; return `"${text.replaceAll('"', '""')}"`; }).join(',')).join('\r\n');
}
function download(ledger: CommerceLedger) {
  const url = URL.createObjectURL(new Blob(['\uFEFF', ledgerExport(ledger)], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a'); a.href = url; a.download = `procurement-ledger-${ledger.offer_id}.csv`; a.click(); URL.revokeObjectURL(url);
}
export function ProcurementLedgers() {
  const [params] = useSearchParams();
  const [draft, setDraft] = useState(params.get('search') ?? '');
  const [search, setSearch] = useState(draft);
  const [page, setPage] = useState(1);
  const path = `/admin/procurement?page=${page}&page_size=20&search=${encodeURIComponent(search)}`;
  return <div className="procurement-ledgers">
    <nav className="ledger-crumb" aria-label="Breadcrumb"><Link to="/produce">Marketplace</Link><span>/</span><span>Procurement ledgers</span></nav>
    <header className="ledger-heading"><h1>Procurement Ledgers</h1><p>Track transactions, pickups, payments and commission records.</p></header>
    <form className="ledger-selector" onSubmit={e => { e.preventDefault(); setSearch(draft); setPage(1); }}><label>Find a listing<div><Search size={17} aria-hidden="true"/><input value={draft} onChange={e => setDraft(e.target.value)} placeholder="Search listing, farmer or crop"/></div></label><button>Search</button><button type="button" className="ledger-secondary" onClick={() => { setDraft(''); setSearch(''); setPage(1); }}>Clear</button></form>
    <ListingLedgers key={path} path={path} page={page} setPage={setPage}/>
  </div>;
}
function ListingLedgers({ path, page, setPage }: { path: string; page: number; setPage: (page: number) => void }) {
  const state = useResource(() => api<{ page: Page<Procurement> }>(path));
  const [selected, setSelected] = useState('');
  if (state.loading) return <Loading/>;
  if (state.error) return <ErrorPanel message={state.error} retry={() => void state.reload()}/>;
  if (!state.data) return null;
  const data = state.data.page;
  const listing = data.items.find(item => item.offer_id === selected) ?? data.items[0];
  return <>{listing ? <><div className="ledger-selection"><label>Selected listing<select value={listing.offer_id} onChange={e => setSelected(e.target.value)}>{data.items.map(item => <option key={item.offer_id} value={item.offer_id}>{item.listing_ref ?? item.offer_id} · {item.crop ?? 'Produce'}</option>)}</select></label><span>Metrics and records below belong to this listing.</span></div><LedgerLoader key={listing.offer_id} listing={listing}/></> : <section className="ledger-panel ledger-empty"><FileText size={38}/><h2>No listings found</h2><p>Try another search or review your produce listings.</p><Link to="/produce">View produce listings</Link></section>}
    <footer className="ledger-pagination"><span>{data.total} matching listings · Page {page} of {Math.max(1, data.total_pages)}</span><div><button className="ledger-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button><button className="ledger-secondary" disabled={page >= data.total_pages} onClick={() => setPage(page + 1)}>Next</button></div></footer></>;
}
function LedgerLoader({ listing }: { listing: Procurement }) {
  const state = useResource(() => api<CommerceLedger>(`/admin/procurement/${listing.offer_id}/ledger`));
  if (state.loading) return <Loading/>;
  if (state.error) return <ErrorPanel message={`Ledger unavailable. ${state.error}`} retry={() => void state.reload()}/>;
  return state.data ? <LedgerView listing={listing} ledger={state.data} refresh={() => void state.reload()}/> : null;
}
function LedgerView({ listing, ledger, refresh }: { listing: Procurement; ledger: CommerceLedger; refresh: () => void }) {
  const [tab, setTab] = useState<Tab>('Transactions');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [from, setFrom] = useState('');
  const currency = ledger.transaction?.currency ?? 'INR';
  const summary = [
    ['Transactions', ledger.transaction ? '1' : '0', FileText],
    ['Gross Merchandise Value', amountLabel(ledger.transaction?.gross_amount ?? '0.00', currency), IndianRupee],
    ['Farmer Payments', amountLabel(moneyTotal(ledger.payments, 'farmer_payout', currency), currency), Wallet],
    ['Commission Earned', amountLabel(moneyTotal(ledger.commissions, 'earned', currency), currency), Percent],
  ] as const;
  const records = tab === 'Transactions' ? (ledger.transaction ? [{ id: ledger.transaction.id, status: 'recorded', date: ledger.transaction.occurred_at, amount: amountLabel(ledger.transaction.gross_amount, currency), detail: `${ledger.transaction.quantity} ${listing.unit}` }] : [])
    : tab === 'Pickups' ? ledger.pickups.map(p => ({ id: p.id, status: p.status, date: p.occurred_at ?? p.scheduled_at ?? p.created_at, amount: '—', detail: p.location ?? 'Location not provided' }))
    : (tab === 'Commissions' ? ledger.commissions : ledger.payments).map(p => ({ id: p.id, status: p.entry_type, date: p.occurred_at, amount: amountLabel(p.amount, p.currency), detail: tab === 'Commissions' ? 'Commission entry' : 'Payment entry' }));
  const filtered = records.filter(r => (!search || `${r.id} ${r.status} ${r.detail}`.toLowerCase().includes(search.toLowerCase())) && (!status || r.status === status) && (!from || r.date?.slice(0, 10) >= from));
  const counts = [ledger.transaction ? 1 : 0, ledger.pickups.length, ledger.payments.length, ledger.commissions.length];
  const link = `?search=${encodeURIComponent(listing.listing_ref ?? listing.offer_id)}`;
  const evidence = [['Buyer assigned', Boolean(listing.buyer_name)], ['Offer recorded', listing.buyer_offer_price != null], ['Pickup recorded', ledger.pickups.length > 0], ['Transaction recorded', Boolean(ledger.transaction)]] as const;
  return <>
    <div className="ledger-actions"><button className="ledger-secondary" onClick={refresh}>Refresh ledger</button><button className="ledger-secondary" onClick={() => download(ledger)}><Download size={17}/>Export ledger</button><button disabled title="Transaction creation is not available in this read-only ledger view">Create transaction</button></div>
    <div className="ledger-metrics">{summary.map(([label, value, Icon]) => <article key={label}><span className="ledger-icon"><Icon size={24} aria-hidden="true"/></span><div><p>{label}</p><strong>{value}</strong></div></article>)}</div>
    <div className="ledger-layout"><div className="ledger-main"><section className="ledger-panel ledger-records"><div className="ledger-tabs" aria-label="Ledger record types">{tabs.map((name, index) => <button key={name} aria-pressed={tab === name} onClick={() => { setTab(name); setStatus(''); setSearch(''); setFrom(''); }}>{name}{index < counts.length && <span>{counts[index]}</span>}</button>)}</div>
      <div className="ledger-record-body"><h2>{tab === 'Reconciliation' ? 'Reconciliation evidence' : `${tab === 'Transactions' ? 'Transaction' : tab} ledger`}</h2>
      {tab === 'Reconciliation' && <p className="ledger-note">Review recorded payment entries below. Payment entries alone do not confirm that a transaction is reconciled.</p>}
      <div className="ledger-filters"><label>Search records<input value={search} onChange={e => setSearch(e.target.value)} placeholder="Record ID, type or location"/></label><label>Status / type<select value={status} onChange={e => setStatus(e.target.value)}><option value="">All types</option>{[...new Set(records.map(r => r.status))].map(s => <option key={s} value={s}>{s.replaceAll('_', ' ')}</option>)}</select></label><label>From date<input type="date" value={from} onChange={e => setFrom(e.target.value)}/></label></div>
      {filtered.length ? <DataTable columns={['Record', 'Status / type', 'Amount', 'Date', 'Details']} rows={filtered.map(r => [r.id, r.status.replaceAll('_', ' '), r.amount, formatDate(r.date), r.detail])}/> : <div className="ledger-empty"><span className="ledger-empty-icon"><FileText size={32}/></span><h3>{records.length ? 'No records match these filters' : `No ${tab === 'Reconciliation' ? 'payment entries' : tab.toLowerCase()} recorded`}</h3><p>{records.length ? 'Clear the filters to see all records for this listing.' : 'Records appear here once they have been recorded for the selected listing.'}</p>{records.length ? <button onClick={() => { setSearch(''); setStatus(''); setFrom(''); }}>Clear record filters</button> : <div><Link className="ledger-link" to={`/produce${link}`}>View produce listing</Link><Link className="ledger-link secondary" to={`/buyers${link}`}>Open Buyer CRM</Link></div>}</div>}
      </div></section><section className="ledger-panel ledger-lifecycle"><h2>Procurement lifecycle</h2><p className="ledger-note">Workflow guide · not a completion indicator</p><ol>{['Offer accepted', 'Pickup scheduled', 'Produce received', 'Payment reconciled', 'Commission settled'].map((step, i) => <li key={step}><Circle size={24} aria-hidden="true"/><strong>{step}</strong><small>Step {i + 1}</small></li>)}</ol></section></div>
      <aside className="ledger-side"><section className="ledger-panel"><div className="ledger-side-heading"><h2>Selected listing</h2><span>{ledger.case_status.replaceAll('_', ' ')}</span></div><strong>{listing.listing_ref ?? listing.offer_id}</strong><p className="ledger-note">{listing.crop ?? 'Produce'} · {listing.quantity} {listing.unit} · {listing.district ?? 'District not provided'}</p><dl><div><dt>Buyer</dt><dd>{listing.buyer_name ?? 'Not assigned'}</dd></div><div><dt>Offer</dt><dd>{listing.buyer_offer_price == null ? 'None' : `${listing.buyer_offer_price} per ${listing.price_unit ?? listing.unit}`}</dd></div><div><dt>Harvest date</dt><dd>{listing.harvest_date ? formatDate(listing.harvest_date) : 'Not provided'}</dd></div></dl><Link className="ledger-link secondary" to={`/produce${link}`}>Review listing details</Link></section>
      <section className="ledger-panel"><h2>Transaction evidence</h2><ul className="ledger-checks">{evidence.map(([label, recorded]) => <li key={label}>{recorded ? <CheckCircle2 size={18}/> : <Circle size={18}/>}<span>{label}</span><small>{recorded ? 'Recorded' : 'Pending'}</small></li>)}</ul></section>
      <section className="ledger-panel ledger-controls"><ShieldCheck size={28}/><div><h2>Ledger controls</h2><ul><li>This view is read-only.</li><li>Access remains permission-controlled.</li><li>Exports exclude buyer contact details.</li><li>Amounts reflect recorded entries, not estimates.</li></ul></div></section></aside>
    </div>
  </>;
}
