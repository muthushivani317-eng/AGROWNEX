import { describe, expect, it } from 'vitest';
import { auditCoverage, auditDay, auditModule, auditCsv, auditPath, auditTimestamp, searchAudit } from './AuditRecords';
import type { AuditRow } from './types';
const rows: AuditRow[] = [
  { id: '1', role: 'owner', action: 'view_ai', target: null, target_id: null, created_at: '2026-08-31T08:00:01Z' },
  { id: '2', role: 'owner', action: 'view_ai', target: null, target_id: null, created_at: '2026-08-31T08:00:02Z' },
];
describe('audit presentation', () => {
  it('uses IST dates at the UTC day boundary', () => {
    expect(auditDay('2026-08-30T20:00:00Z')).toBe('2026-08-31');
    expect(auditDay('invalid')).toBe('');
  });
  it('does not invent precise times for date-only records', () => {
    expect(auditTimestamp('2026-08-31')).toContain('Time not recorded');
    const coverage = auditCoverage({ ...rows[0], created_at: '2026-08-31' });
    expect(coverage).toContainEqual(['Precise timestamp', 'Missing']);
    expect(coverage).toContainEqual(['Request correlation', 'Not reported']);
  });
  it('recognises actual actor and timestamp evidence', () => {
    const coverage = auditCoverage({ ...rows[0], admin_id: 'admin-1' });
    expect(coverage).toContainEqual(['Actor ID', 'Available']);
    expect(coverage).toContainEqual(['Precise timestamp', 'Available']);
  });
  it('groups only known module codes', () => {
    expect(auditModule('view_ai')).toBe('AI Monitoring');
    expect(auditModule('unknown_action')).toBe('Other');
  });
  it('preserves repeated events and searches readable action labels', () => {
    expect(searchAudit(rows, 'view ai', 'owner')).toHaveLength(2);
    expect(searchAudit(rows, '', 'customer_support')).toHaveLength(0);
  });
  it('builds encoded server filters and pagination', () => {
    const query = new URLSearchParams(auditPath(' view_ai ', 'farmer & farm', 2, 20).split('?')[1]);
    expect(query.get('action')).toBe('view_ai');
    expect(query.get('target')).toBe('farmer & farm');
    expect(query.get('page')).toBe('2');
  });
  it('distinguishes seconds and handles invalid dates', () => {
    expect(auditTimestamp(rows[0].created_at)).not.toBe(auditTimestamp(rows[1].created_at));
    expect(auditTimestamp('invalid')).toBe('Timestamp unavailable');
    expect(auditTimestamp(rows[0].created_at)).toContain('1:30:01');
  });
  it('exports original timestamps and escapes formula injection', () => {
    const csv = auditCsv([{ ...rows[0], target_id: '=SUM(1)', target: 'a"b' }]);
    expect(csv).toContain('"\'=SUM(1)"');
    expect(csv).toContain('"a""b"');
    expect(csv).toContain(rows[0].created_at);
    expect(csv).not.toContain('ip_address');
  });
});
