import { CalendarDays, MapPin, User } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { ScrollView, View } from 'react-native';

import { AgBadge, AgCard, AgChip, AgText } from '@/components/ui';
import { useAppTheme } from '@/hooks/useAppTheme';

import {
  PROCUREMENT_LABEL_KEY,
  PROCUREMENT_STATUSES,
  PROCUREMENT_TONE,
} from '../constants';
import type { ProcurementCaseInput, ProcurementRow, ProcurementStatus } from '../types';
import { formatShortDate } from './adminMeta';
import { ProcurementCaseEditor } from './ProcurementCaseEditor';
import { CommerceLedgerEditor } from './CommerceLedgerEditor';

/**
 * One future-harvest procurement offer. The admin status pill reflects the internal
 * pipeline (NOT a marketplace); the chip row advances it — every change is audited and
 * never mutates the farmer's own offer.
 */
export function ProcurementCard({
  row,
  onChangeStatus,
  disabled,
  adminId,
  revealedContact,
  onSaveCase,
  onRevealContact,
}: {
  row: ProcurementRow;
  onChangeStatus: (status: ProcurementStatus) => void;
  disabled?: boolean;
  adminId: string | null;
  revealedContact?: string;
  onSaveCase: (input: ProcurementCaseInput) => void;
  onRevealContact: () => void;
}) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const location = [row.village, row.district].filter(Boolean).join(', ');
  return (
    <AgCard className="gap-2">
      <View className="flex-row flex-wrap items-center gap-2">
        <AgBadge label={row.listingRef ?? row.offerId} tone="info" />
        <AgText variant="caption" color="muted">Farmer {row.farmerRef ?? '—'}</AgText>
      </View>
      <View className="flex-row items-start justify-between gap-2">
        <View className="flex-1">
          <AgText variant="body" weight="semibold">
            {row.crop ?? '—'}
            {row.variety ? ` · ${row.variety}` : ''}
          </AgText>
          <AgText variant="caption" color="muted">
            {row.quantity} {row.unit}
            {row.expectedGrade ? ` · ${t('admin.grade')} ${row.expectedGrade}` : ''}
          </AgText>
        </View>
        <AgBadge
          label={t(PROCUREMENT_LABEL_KEY[row.adminStatus])}
          tone={PROCUREMENT_TONE[row.adminStatus]}
        />
      </View>

      <View className="flex-row flex-wrap items-center gap-x-3 gap-y-0.5">
        {row.farmerName ? (
          <View className="flex-row items-center gap-1">
            <User size={12} color={colors.textMuted} />
            <AgText variant="caption" color="muted">
              {row.farmerName}
            </AgText>
          </View>
        ) : null}
        {location ? (
          <View className="flex-row items-center gap-1">
            <MapPin size={12} color={colors.textMuted} />
            <AgText variant="caption" color="muted">
              {location}
            </AgText>
          </View>
        ) : null}
        <View className="flex-row items-center gap-1">
          <CalendarDays size={12} color={colors.textMuted} />
          <AgText variant="caption" color="muted">
            {formatShortDate(row.harvestDate)}
          </AgText>
        </View>
      </View>

      <AgText variant="caption" color="muted">
        {row.cultivatedAreaHectares ? `${(row.cultivatedAreaHectares * 2.47105).toFixed(2)} acres · ` : ''}
        Expected {row.expectedTotalQuantity ?? '—'} {row.unit} · Available {row.availableQuantity ?? row.quantity} {row.unit}
      </AgText>
      {row.qualityNotes ? <AgText variant="caption">Quality: {row.qualityNotes}</AgText> : null}

      <AgText variant="caption" color="muted" className="mt-1">
        {t('admin.setStatus')}
      </AgText>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} className="-mx-1">
        <View className="flex-row gap-2 px-1">
          {PROCUREMENT_STATUSES.map((status) => (
            <AgChip
              key={status}
              label={t(PROCUREMENT_LABEL_KEY[status])}
              selected={row.adminStatus === status}
              onPress={disabled ? undefined : () => onChangeStatus(status)}
            />
          ))}
        </View>
      </ScrollView>
      <ProcurementCaseEditor
        row={row}
        adminId={adminId}
        saving={Boolean(disabled)}
        revealedContact={revealedContact}
        onSave={onSaveCase}
        onReveal={onRevealContact}
      />
      {row.adminStatus === 'farmer_accepted' ? <CommerceLedgerEditor offerId={row.offerId} /> : null}
    </AgCard>
  );
}
