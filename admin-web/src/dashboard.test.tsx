import { describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import type { AdminMe } from './types';
import { DashboardPage, formatDashboardValue } from './Dashboard';

vi.mock('./useResource', () => ({ useResource: () => ({ loading: false, error: null, reload: vi.fn(), data: { cards: [{ key: 'total_farmers', value: 3 }], procurement_status_counts: { new: 1 }, generated_at: '2026-08-31T00:00:00Z', farmer_growth: [], items: [] } }) }));
const me: AdminMe = { id: 'test', user_id: 'test', full_name: 'Owner', role: 'owner', status: 'active', permissions: ['view_dashboard'] };
const render = (user: AdminMe) => renderToStaticMarkup(<MemoryRouter><DashboardPage me={user}/></MemoryRouter>);
describe('Command Centre', () => {
  it('formats recorded values without turning unavailable data into zero', () => {
    expect(formatDashboardValue(null)).toBe('—');
    expect(formatDashboardValue(undefined, true)).toBe('—');
    expect(formatDashboardValue('invalid')).toBe('—');
    expect(formatDashboardValue(0)).toBe('0');
    expect(formatDashboardValue('1000.50', true)).toBe('₹1,000.50');
  });
  it('keeps privileged widgets out of a dashboard-only role', () => {
    const html = render(me);
    expect(html).toContain('Command Centre');
    expect(html).not.toContain('Recent Produce Listings');
    expect(html).not.toContain('Pending Payments');
    expect(html).not.toContain('href="/support"');
    expect(html).toContain('Analytics access required');
  });
  it('shows authorised widgets with honest empty and unmonitored states', () => {
    const html = render({ ...me, permissions: ['view_dashboard', 'view_analytics', 'manage_procurement', 'view_revenue', 'view_ai_costs', 'manage_support'] });
    expect(html).toContain('Recent Produce Listings');
    expect(html).toContain('No produce listings yet');
    expect(html).toContain('No registration history available');
    expect(html).toContain('Pending Payments');
    expect(html).toContain('Not monitored');
    expect(html).toContain('All Expenses');
    expect(html).toContain('Unified provider ledger');
    expect(html).not.toContain('Healthy');
  });
});
