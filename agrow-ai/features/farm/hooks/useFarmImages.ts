import { useMutation, useQuery } from '@tanstack/react-query';

import { queryClient } from '@/lib/queryClient';

import { farmKeys } from '../constants';
import { getFarmProvider } from '../services/farmProvider';
import type { FarmImageInput } from '../types';

/** List a farm's images (gallery). */
export function useFarmImages(id: string) {
  return useQuery({
    queryKey: farmKeys.images(id),
    queryFn: () => getFarmProvider().listImages(id),
  });
}

/** Attach an uploaded image (S3 URL + metadata) to a farm. */
export function useAddFarmImage(id: string) {
  return useMutation({
    mutationFn: (media: FarmImageInput) => getFarmProvider().addImage(id, media),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: farmKeys.images(id) });
      void queryClient.invalidateQueries({ queryKey: farmKeys.detail(id) });
    },
  });
}
