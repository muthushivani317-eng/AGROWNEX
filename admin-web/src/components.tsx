import type { PropsWithChildren, ReactNode } from 'react';

export function Card({ children, className = '' }: PropsWithChildren<{ className?: string }>) {
  return <section className={`card ${className}`}>{children}</section>;
}
export function PageTitle({ title, subtitle, action }: { title: string; subtitle: string; action?: ReactNode }) {
  return <header className="page-title"><div><h1>{title}</h1><p>{subtitle}</p></div>{action}</header>;
}
export function Empty({ title, body }: { title: string; body: string }) {
  return <Card className="empty"><div className="empty-mark">A</div><h2>{title}</h2><p>{body}</p></Card>;
}
export function ErrorPanel({ message, retry }: { message: string; retry: () => void }) {
  return <Card className="empty danger"><h2>Information could not be loaded</h2><p>{message}</p><button onClick={retry}>Try again</button></Card>;
}
export function Loading() { return <div className="loading"><span /><span /><span /><p>Loading verified platform data…</p></div>; }
export function Metric({ label, value }: { label: string; value: string | number | null | undefined }) {
  return <Card className="metric"><p>{label.replaceAll('_', ' ')}</p><strong>{value ?? '—'}</strong></Card>;
}
export function DataTable({ columns, rows }: { columns: string[]; rows: ReactNode[][] }) {
  return <div className="table-wrap"><table><thead><tr>{columns.map(c => <th key={c}>{c}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j} data-label={columns[j]}>{cell}</td>)}</tr>)}</tbody></table></div>;
}
export const formatDate = (value: string | null | undefined) => value ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(value)) : '—';
