import { useEffect, useState } from 'react';
import { View } from 'react-native';

import { AgButton, AgInput, AgText } from '@/components/ui';

import type { ProcurementCaseInput, ProcurementRow } from '../types';

const numberOrNull = (value: string): number | null => {
  const parsed = Number(value);
  return value.trim() && Number.isFinite(parsed) ? parsed : null;
};

export function ProcurementCaseEditor({
  row,
  adminId,
  saving,
  revealedContact,
  onSave,
  onReveal,
}: {
  row: ProcurementRow;
  adminId: string | null;
  saving: boolean;
  revealedContact?: string;
  onSave: (input: ProcurementCaseInput) => void;
  onReveal: () => void;
}) {
  const [buyerName, setBuyerName] = useState(row.buyerName ?? '');
  const [buyerContact, setBuyerContact] = useState('');
  const [quantity, setQuantity] = useState(row.buyerOfferQuantity?.toString() ?? '');
  const [price, setPrice] = useState(row.buyerOfferPrice?.toString() ?? '');
  const [transport, setTransport] = useState(row.transportCost?.toString() ?? '');
  const [commission, setCommission] = useState(row.commissionRate?.toString() ?? '');
  const [followUp, setFollowUp] = useState(row.followUpAt?.slice(0, 16) ?? '');
  const [notes, setNotes] = useState(row.negotiationNotes ?? '');

  useEffect(() => setBuyerName(row.buyerName ?? ''), [row.buyerName]);

  return (
    <View className="mt-2 gap-3 border-t border-border pt-3">
      <AgText variant="label" weight="semibold">Buyer search and offer</AgText>
      <AgButton
        title={row.assignedAdminId ? 'Assigned' : 'Assign to me'}
        variant="secondary"
        disabled={!adminId || Boolean(row.assignedAdminId)}
        onPress={() => adminId && onSave({ assignedAdminId: adminId })}
      />
      <AgInput label="Buyer name" value={buyerName} onChangeText={setBuyerName} />
      <AgInput
        label={row.buyerContactMasked ? 'New buyer contact (existing contact is protected)' : 'Buyer contact'}
        value={buyerContact}
        onChangeText={setBuyerContact}
        keyboardType="phone-pad"
      />
      {row.buyerContactMasked ? (
        <AgButton title={revealedContact ?? 'Reveal buyer contact (audited)'} variant="secondary" onPress={onReveal} />
      ) : null}
      <View className="flex-row gap-2">
        <View className="flex-1"><AgInput label={`Buyer quantity (${row.unit})`} value={quantity} onChangeText={setQuantity} keyboardType="decimal-pad" /></View>
        <View className="flex-1"><AgInput label={`Price / ${row.unit}`} value={price} onChangeText={setPrice} keyboardType="decimal-pad" /></View>
      </View>
      <View className="flex-row gap-2">
        <View className="flex-1"><AgInput label="Transport cost" value={transport} onChangeText={setTransport} keyboardType="decimal-pad" /></View>
        <View className="flex-1"><AgInput label="Commission %" value={commission} onChangeText={setCommission} keyboardType="decimal-pad" /></View>
      </View>
      <AgInput label="Follow-up (YYYY-MM-DDTHH:mm)" value={followUp} onChangeText={setFollowUp} />
      <AgInput label="Negotiation notes" value={notes} onChangeText={setNotes} multiline numberOfLines={3} />
      <AgButton
        title="Save procurement case"
        loading={saving}
        onPress={() => onSave({
          buyerName: buyerName.trim() || null,
          buyerContact: buyerContact.trim() || undefined,
          buyerOfferQuantity: numberOrNull(quantity),
          buyerOfferPrice: numberOrNull(price),
          transportCost: numberOrNull(transport),
          commissionRate: numberOrNull(commission),
          currency: 'INR',
          priceUnit: row.unit,
          followUpAt: followUp.trim() ? new Date(followUp).toISOString() : null,
          negotiationNotes: notes.trim() || null,
        })}
      />
    </View>
  );
}
