import { AgText } from '@/components/ui';

import type { PublicCropAvailability } from '../cropRegistry';
import { toMobileCropRegistryEntry } from '../cropRegistry';

export function CropAvailabilityBadge({ crop }: { crop: PublicCropAvailability }) {
  const entry = toMobileCropRegistryEntry(crop, crop.api_integrated === true);
  const status = {
    internal_test_ready: 'Ready for internal testing',
    pilot_test_ready: 'Pilot testing only',
    general_farmer_ready: 'General farmer testing authorized',
    testing_blocked: 'General farmer testing not yet authorized',
    runtime_missing: 'Model runtime unavailable',
    adapter_missing: 'Inference integration incomplete',
    disabled: 'Disease testing disabled',
  }[entry.readiness];
  return (
    <>
      <AgText variant="bodySmall" weight="semibold">
        {status}
      </AgText>
      {entry.readiness !== 'general_farmer_ready' && (
        <AgText variant="bodySmall" color="muted">
          {entry.disabledReason}
        </AgText>
      )}
    </>
  );
}
