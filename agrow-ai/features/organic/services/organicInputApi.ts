import { api } from '@/services/apiClient'; import { endpoints } from '@/services/endpoints'; import type { Paginated } from '@/types';
import type { ApiOrganicInput, OrganicInputItem } from '../organicInputTypes'; import { apiToOrganicInput, buildOrganicInputQuery } from './organicInputMapper';
export async function listOrganicInputs(search = '', crop?: string): Promise<OrganicInputItem[]> { const page = await api.get<Paginated<ApiOrganicInput>>(endpoints.organic.inputs, { params: buildOrganicInputQuery(search, crop) }); return page.items.map(apiToOrganicInput); }
