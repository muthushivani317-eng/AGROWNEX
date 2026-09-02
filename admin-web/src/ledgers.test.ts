import { describe, expect, it } from 'vitest';
import { ledgerExport, moneyTotal, type CommerceLedger } from './ProcurementLedgers';
const entry = (amount: string, currency = 'INR', entry_type = 'farmer_payout') => ({ id: 'p', amount, currency, entry_type, occurred_at: '2026-08-31' });
describe('ledger records', () => {
  it('sums currency decimals exactly and excludes other entry types', () => {
    expect(moneyTotal([entry('0.10'), entry('0.20'), entry('99', 'INR', 'buyer_receipt')], 'farmer_payout', 'INR')).toBe('0.30');
  });
  it('does not combine currencies or silently treat invalid money as zero', () => {
    expect(moneyTotal([entry('20', 'USD')], 'farmer_payout', 'INR')).toBe('Unavailable');
    expect(moneyTotal([entry('broken')], 'farmer_payout', 'INR')).toBe('Unavailable');
  });
  it('shows zero only for an empty matching set', () => {
    expect(moneyTotal([], 'earned', 'INR')).toBe('0.00');
  });
  it('exports all record types and escapes spreadsheet formula cells', () => {
    const ledger: CommerceLedger = { offer_id: '=SUM(1)', case_status: 'new', transaction: null, pickups: [], payments: [entry('1')], commissions: [] };
    const csv = ledgerExport(ledger);
    expect(csv).toContain('"\'=SUM(1)"');
    expect(csv).toContain('"Payment"');
    expect(csv).not.toContain('reference');
  });
});
