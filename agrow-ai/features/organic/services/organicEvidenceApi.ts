import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';

export interface OrganicUploadAttestation {
  id: string;
  upload_receipt: string;
}

/**
 * Uploads Farm Diary evidence (currently: photos) via the backend's
 * attest-then-reference flow (backend/app/modules/organic/
 * certification_receipt.py::store_and_attest_upload / upload_receipt_is_valid):
 * the file is written to storage and an attestation id + signed receipt are
 * returned. Both must be included as `evidence[].uploadAttestationId` /
 * `uploadReceipt` when creating the logbook entry (see organicMapper.ts).
 * The attestation expires in 30 minutes and can only be consumed once --
 * this is not a general-purpose upload endpoint, it exists specifically for
 * certification documents and logbook evidence (purpose must be
 * "logbook_evidence" here, matching backend/app/modules/organic/
 * certification_receipt.py::LOGBOOK_EVIDENCE).
 */
export async function uploadOrganicEvidence(
  farmId: string,
  fileUri: string,
  mimeType: string,
): Promise<OrganicUploadAttestation> {
  const form = new FormData();
  form.append('purpose', 'logbook_evidence');
  const ext = mimeType.split('/')[1] ?? 'jpg';
  form.append('file', { uri: fileUri, name: `evidence.${ext}`, type: mimeType } as unknown as Blob);
  return api.post<OrganicUploadAttestation>(endpoints.organic.uploads(farmId), form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}
