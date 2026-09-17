import { useMutation } from '@tanstack/react-query';

import { uploadService } from '../services/uploadProvider';

/** Upload a locally-picked avatar image and resolve to its persisted URL. */
export function useUploadAvatar() {
  return useMutation({
    mutationFn: (localUri: string) => uploadService.uploadImage(localUri, 'profiles'),
  });
}
