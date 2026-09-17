import { useState } from 'react';
import { Alert, View } from 'react-native';

import { AgButton, AgInput, AgText } from '@/components/ui';

import { useCommerceLedger, useRecordCommission, useRecordPayment, useRecordPickup, useRecordTransaction } from '../hooks/useAdmin';

export function CommerceLedgerEditor({ offerId }: { offerId: string }) {
  const ledger = useCommerceLedger(offerId);
  const pickup = useRecordPickup(offerId);
  const transaction = useRecordTransaction(offerId);
  const payment = useRecordPayment(offerId);
  const commission = useRecordCommission(offerId);
  const [location, setLocation] = useState('');
  const [amount, setAmount] = useState('');
  const [reference, setReference] = useState('');
  const now = () => new Date().toISOString();
  const transactionId = ledger.data?.transaction?.id;
  const fail = () => Alert.alert('Could not record ledger entry');

  return (
    <View className="mt-3 gap-2 border-t border-border pt-3">
      <AgText variant="label" weight="semibold">Pickup, payment and commission ledger</AgText>
      <AgInput label="Pickup location" value={location} onChangeText={setLocation} />
      <View className="flex-row gap-2">
        <View className="flex-1"><AgButton title="Schedule pickup" variant="secondary" onPress={() => pickup.mutate({ status: 'scheduled', scheduled_at: now(), location: location || null }, { onError: fail })} /></View>
        <View className="flex-1"><AgButton title="Complete pickup" variant="secondary" onPress={() => pickup.mutate({ status: 'completed', occurred_at: now(), location: location || null }, { onError: fail })} /></View>
      </View>
      {ledger.data?.pickups.length ? <AgText variant="caption">Latest pickup: {ledger.data.pickups.at(-1)?.status}</AgText> : null}
      {!transactionId ? (
        <AgButton title="Record completed transaction" onPress={() => transaction.mutate(now(), { onError: fail })} />
      ) : (
        <>
          <AgText variant="caption">Transaction {transactionId.slice(0, 8)} · Gross ₹{ledger.data?.transaction?.gross_amount}</AgText>
          <AgInput label="Payment amount" value={amount} onChangeText={setAmount} keyboardType="decimal-pad" />
          <AgInput label="Payment reference" value={reference} onChangeText={setReference} />
          <View className="flex-row gap-2">
            <View className="flex-1"><AgButton title="Buyer receipt" variant="secondary" onPress={() => payment.mutate({ transactionId, input: { entry_type: 'buyer_receipt', amount: Number(amount), currency: 'INR', reference: reference || null, occurred_at: now() } }, { onError: fail })} /></View>
            <View className="flex-1"><AgButton title="Farmer payout" variant="secondary" onPress={() => payment.mutate({ transactionId, input: { entry_type: 'farmer_payout', amount: Number(amount), currency: 'INR', reference: reference || null, occurred_at: now() } }, { onError: fail })} /></View>
          </View>
          <AgButton title="Record earned commission" onPress={() => commission.mutate({ transactionId, occurredAt: now() }, { onError: fail })} />
          <AgText variant="caption">Payments: {ledger.data?.payments.length ?? 0} · Commission entries: {ledger.data?.commissions.length ?? 0}</AgText>
        </>
      )}
    </View>
  );
}
