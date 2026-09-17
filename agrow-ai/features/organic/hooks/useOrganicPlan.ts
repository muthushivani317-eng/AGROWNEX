import { useQuery } from '@tanstack/react-query';
import { getOrganicPlanBundle } from '../services/organicPlanApi';
import { organicStorage } from '../services/organicStorage';
import { isOrganicOfflineError } from '../services/organicSync';
export const useOrganicPlan = (farmId: string) => useQuery({ queryKey: ['organic', 'plan', farmId], queryFn: async () => { try { const plan = await getOrganicPlanBundle(farmId); organicStorage.savePlan(plan); return plan; } catch (error) { const cached = organicStorage.plan(farmId); if (isOrganicOfflineError(error) && cached) return cached; throw error; } } });
