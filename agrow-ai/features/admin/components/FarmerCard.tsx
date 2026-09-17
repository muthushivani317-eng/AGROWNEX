import { useRouter } from 'expo-router';
import { ChevronRight, MapPin, Sprout } from 'lucide-react-native';
import { View } from 'react-native';

import { AgCard, AgPressable, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';
import { formatIndianPhone } from '@/utils/format';

import type { FarmerRow } from '../types';

/** One farmer in the admin directory. Tapping opens the read-only farmer detail. */
export function FarmerCard({ farmer }: { farmer: FarmerRow }) {
  const { colors } = useAppTheme();
  const router = useRouter();
  const location = [farmer.village, farmer.district].filter(Boolean).join(', ');
  return (
    <AgPressable
      onPress={() =>
        router.push({ pathname: '/admin/farmers/[id]', params: { id: farmer.userId } })
      }
      accessibilityRole="button"
      accessibilityLabel={farmer.fullName ?? farmer.userId}
    >
      <AgCard className="flex-row items-center gap-3">
        <View className="flex-1 gap-1">
          <AgText variant="caption" weight="bold" color="primary">
            {farmer.farmerRef ?? farmer.userId}
          </AgText>
          <AgText variant="body" weight="semibold">
            {farmer.fullName ?? '—'}
          </AgText>
          {farmer.phoneNumber ? (
            <AgText variant="caption" color="muted">
              {formatIndianPhone(farmer.phoneNumber)}
            </AgText>
          ) : null}
          <View className="flex-row flex-wrap items-center gap-x-3 gap-y-0.5">
            {location ? (
              <View className="flex-row items-center gap-1">
                <MapPin size={12} color={colors.textMuted} />
                <AgText variant="caption" color="muted">
                  {location}
                </AgText>
              </View>
            ) : null}
            {farmer.primaryCrop ? (
              <View className="flex-row items-center gap-1">
                <Sprout size={12} color={colors.textMuted} />
                <AgText variant="caption" color="muted">
                  {farmer.primaryCrop}
                </AgText>
              </View>
            ) : null}
            <AgText variant="caption" color="muted">
              {farmer.farmCount} · farms
            </AgText>
          </View>
        </View>
        <ChevronRight size={20} color={colors.textMuted} />
      </AgCard>
    </AgPressable>
  );
}
