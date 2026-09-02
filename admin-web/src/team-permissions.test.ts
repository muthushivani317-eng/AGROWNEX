import { describe, expect, it } from 'vitest';
import { filterTeam, roleLabel, type TeamMember } from './TeamPermissions';
const rows: TeamMember[] = [
  { id: '1', full_name: null, email: 'owner@example.com', role: 'owner', status: 'active', created_at: '' },
  { id: '2', full_name: 'Procurement', email: null, role: 'procurement_manager', status: 'suspended', created_at: '' },
];
describe('team directory', () => {
  it('combines search, role and status filters', () => {
    expect(filterTeam(rows, 'OWNER@', 'owner', 'active')).toEqual([rows[0]]);
    expect(filterTeam(rows, '', '', 'suspended')).toEqual([rows[1]]);
    expect(filterTeam(rows, '', 'owner', 'suspended')).toEqual([]);
  });
  it('supports readable role searches without inventing roles', () => {
    expect(filterTeam(rows, 'procurement manager', '', '')).toEqual([rows[1]]);
    expect(roleLabel('agriculture_officer')).toBe('agriculture officer');
  });
});
