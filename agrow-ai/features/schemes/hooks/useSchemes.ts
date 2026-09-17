import { useMutation, useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';

import type { FarmSummary } from '@/features/farm';
import { queryClient } from '@/lib/queryClient';

import { schemeKeys } from '../constants';
import { getSchemeProvider } from '../services/schemeProvider';
import { listCacheKey, queryCacheKey } from '../services/schemeStorage';
import type { DocumentType, SchemeListFilters, SchemeQuery } from '../types';

/**
 * Build the eligibility query from the selected farm. The engine derives the
 * rest server-side from the farmer's profile; the client passes the farm id and
 * its known crop/land/district so the API and offline engines evaluate the same.
 *
 * Takes the selected farm as a parameter so it shares the caller's
 * `useSelectedFarm` state — calling `useSelectedFarm` here would spin up a
 * second, independent copy that never sees farm switches from the screen.
 */
export function useSchemeQuery(selected: FarmSummary | null): {
  query: SchemeQuery;
  hasFarm: boolean;
} {
  return useMemo(
    () => ({
      hasFarm: Boolean(selected),
      query: {
        farmId: selected?.id ?? null,
        district: selected?.district ?? null,
        crop: selected?.crop ?? null,
        landHectares: selected?.areaHectares ?? null,
      },
    }),
    [selected],
  );
}

/** Schemes the farmer is eligible / likely-eligible for, ranked by score. */
export function useEligibleSchemes(query: SchemeQuery, enabled = true) {
  return useQuery({
    queryKey: schemeKeys.eligible(queryCacheKey(query)),
    enabled,
    queryFn: () => getSchemeProvider().eligible(query),
    staleTime: 30 * 60 * 1000,
  });
}

/** The highest-scoring eligible schemes for the farmer. */
export function useRecommendedSchemes(query: SchemeQuery, enabled = true) {
  return useQuery({
    queryKey: schemeKeys.recommended(queryCacheKey(query)),
    enabled,
    queryFn: () => getSchemeProvider().recommended(query),
    staleTime: 30 * 60 * 1000,
  });
}

/** All verified schemes (filter by category/search, paginated). */
export function useAllSchemes(filters: SchemeListFilters, enabled = true) {
  return useQuery({
    queryKey: schemeKeys.list(listCacheKey(filters)),
    enabled,
    queryFn: () => getSchemeProvider().list(filters),
    staleTime: 30 * 60 * 1000,
  });
}

/** The farmer's bookmarked schemes (with their current eligibility). */
export function useBookmarkedSchemes(query: SchemeQuery, enabled = true) {
  return useQuery({
    queryKey: [...schemeKeys.bookmarks, queryCacheKey(query)],
    enabled,
    queryFn: () => getSchemeProvider().bookmarks(query),
  });
}

/** Full scheme detail with the farmer's eligibility, documents and steps. */
export function useSchemeDetail(id: string, query: SchemeQuery) {
  return useQuery({
    queryKey: schemeKeys.detail(id, queryCacheKey(query)),
    enabled: Boolean(id),
    queryFn: () => getSchemeProvider().detail(id, query),
  });
}

export function useFarmerDocuments() {
  return useQuery({
    queryKey: schemeKeys.documents,
    queryFn: () => getSchemeProvider().myDocuments(),
  });
}

export function useSetFarmerDocument() {
  return useMutation({
    mutationFn: ({ documentType, hasDocument }: { documentType: DocumentType; hasDocument: boolean }) =>
      getSchemeProvider().setMyDocument(documentType, hasDocument),
    onSuccess: invalidateSchemes,
  });
}

/** Invalidate every scheme query so bookmark state refreshes across all tabs. */
function invalidateSchemes(): void {
  void queryClient.invalidateQueries({ queryKey: schemeKeys.all });
}

export function useAddBookmark() {
  return useMutation({
    mutationFn: (schemeId: string) => getSchemeProvider().addBookmark(schemeId),
    onSuccess: invalidateSchemes,
  });
}

export function useRemoveBookmark() {
  return useMutation({
    mutationFn: (schemeId: string) => getSchemeProvider().removeBookmark(schemeId),
    onSuccess: invalidateSchemes,
  });
}
