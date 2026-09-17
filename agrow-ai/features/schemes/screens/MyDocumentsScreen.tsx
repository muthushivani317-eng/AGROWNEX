import { useRouter } from 'expo-router';
import { ArrowLeft, CheckCircle2, Circle } from 'lucide-react-native';
import { useTranslation } from 'react-i18next';
import { Alert, FlatList, StyleSheet, TouchableOpacity, View } from 'react-native';
import { useRef } from 'react';

import { AgErrorState, AgScreen, AgSkeleton, AgText } from '@/components/ui';

import { DOCUMENT_LABEL_KEY } from '../constants';
import { useFarmerDocuments, useSetFarmerDocument } from '../hooks/useSchemes';

export function MyDocumentsScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const query = useFarmerDocuments();
  const update = useSetFarmerDocument();
  const lock = useRef(false);

  return (
    <AgScreen padded={false} backgroundColor="#F7F3E8">
      <FlatList
        data={query.isError ? [] : query.data ?? []}
        refreshing={query.isRefetching}
        onRefresh={() => { if (!query.isFetching) void query.refetch(); }}
        keyExtractor={(item) => item.documentType}
        contentContainerStyle={styles.content}
        ListHeaderComponent={
          <View style={styles.header}>
            <TouchableOpacity onPress={() => router.back()} activeOpacity={0.7} style={styles.backRow}>
              <ArrowLeft size={22} color="#101713" />
              <AgText variant="headingM" weight="bold" style={styles.title}>{t('schemes.myDocuments')}</AgText>
            </TouchableOpacity>
            <AgText variant="bodySmall" style={styles.subtitle}>{t('schemes.myDocumentsSubtitle')}</AgText>
          </View>
        }
        renderItem={({ item }) => {
          const Icon = item.hasDocument ? CheckCircle2 : Circle;
          return (
            <TouchableOpacity
              disabled={update.isPending}
              onPress={() => {
                if (lock.current) return;
                lock.current = true;
                update.mutate({ documentType: item.documentType, hasDocument: !item.hasDocument }, {
                  onError: () => Alert.alert(t('common.somethingWrong'), t('schemes.saveFailed')),
                  onSettled: () => { lock.current = false; },
                });
              }}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: item.hasDocument, disabled: update.isPending }}
              activeOpacity={0.74}
              style={styles.documentCard}
            >
              <Icon size={22} color={item.hasDocument ? "#176B36" : "#536158"} />
              <AgText variant="body" style={styles.documentText}>{t(DOCUMENT_LABEL_KEY[item.documentType])}</AgText>
            </TouchableOpacity>
          );
        }}
        ListEmptyComponent={query.isLoading ? <AgSkeleton className="h-16 w-full rounded-card" /> : query.isError ? <AgErrorState light onRetry={() => void query.refetch()} /> : null}
      />
    </AgScreen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 12, paddingHorizontal: 20, paddingBottom: 40 },
  header: { gap: 8, marginTop: 8, marginBottom: 8 },
  backRow: { minHeight: 48, flexDirection: 'row', alignItems: 'center', gap: 8 },
  title: { color: '#101713' },
  subtitle: { color: '#536158' },
  documentCard: { minHeight: 64, flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 16, paddingVertical: 12, borderRadius: 16, borderWidth: 1, borderColor: '#D9D6C8', backgroundColor: '#FFFFFF' },
  documentText: { flex: 1, color: '#101713' },
});
