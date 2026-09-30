import fs from 'node:fs';
import path from 'node:path';

const read = (relative: string) =>
  fs.readFileSync(path.resolve(__dirname, '../../..', relative), 'utf8');

describe('farmer organization links contract', () => {
  const hooks = read('features/partnerLinks/hooks/usePartnerLinks.ts');
  const screen = read('features/partnerLinks/screens/LinkedOrganizationsScreen.tsx');
  const endpoints = read('services/endpoints.ts');

  it('loads the district directory and joins only with explicit consent', () => {
    expect(endpoints).toContain('directory: "/organic-partner/directory"');
    expect(endpoints).toContain('`/organic-partner/organizations/${organizationId}/join`');
    expect(hooks).toContain("params: { kind, district: district || undefined }");
    expect(hooks).toContain('{ consent: true }');
  });

  it('keeps farmer requests distinct from organization invitations', () => {
    expect(hooks).toContain('initiated_by');
    expect(screen).toContain("link.status === 'join_requested'");
    expect(screen).toContain("link.initiatedBy === 'organization'");
    expect(screen).toContain("t('partnerLinks.approve')");
    expect(screen).toContain("t('partnerLinks.cancelRequest')");
    expect(screen).toContain("t('partnerLinks.leave')");
  });
});
