import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';

test('the /disease route renders the current typed workflow screen', () => {
  const route = readFileSync(resolve(process.cwd(), 'app/disease/index.tsx'), 'utf8');
  expect(route).toContain("import { DiseaseScreen } from '@/features/disease'");
  expect(route).toContain('export default DiseaseScreen');
  expect(route).not.toContain('DiagnosisIntegrationShell');
  expect(route).not.toContain('useDisease');
});

test('there is only one disease entry route', () => {
  const diseaseRoutes = readdirSync(resolve(process.cwd(), 'app/disease'));
  expect(diseaseRoutes.filter((name) => name === 'index.tsx')).toHaveLength(1);
});
