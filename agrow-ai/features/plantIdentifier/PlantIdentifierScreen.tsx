import { Image } from 'expo-image';
import * as Location from 'expo-location';
import { useRouter } from 'expo-router';
import { ArrowLeft, BookOpen, Camera, CheckCircle2, Expand, Images, Info, Leaf, RefreshCw, ShieldCheck } from 'lucide-react-native';
import { useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, StyleSheet, View } from 'react-native';

import { AgButton, AgPressable, AgScreen, AgText } from '@/components/ui';
import type { CaptureMethod, PickedImage } from '@/features/disease/types';
import { checkImageQuality } from '@/features/disease/utils/imageQuality';
import { captureFromCamera, pickFromGallery } from '@/features/disease/utils/pickDiseaseImage';
import { ImageViewer } from '@/features/growth/components/ImageViewer';
import { useLanguage } from '@/hooks/useLanguage';
import { ApiError } from '@/types';

import { identifyPlant, type PlantIdentificationResult } from './plantIdentifierApi';
import { plantJournalStorage } from './services/plantJournalStorage';

const SCREEN_BG = '#090C0A';
const SURFACE = '#131715';
const TEXT = '#F4F7F4';
const MUTED = '#A9B0AB';
const GREEN = '#58C65A';

export function PlantIdentifierScreen() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const router = useRouter();
  const [picked, setPicked] = useState<PickedImage | null>(null);
  const [qualityIssues, setQualityIssues] = useState<string[]>([]);
  const [result, setResult] = useState<PlantIdentificationResult | null>(null);
  const [status, setStatus] = useState<'idle' | 'picking' | 'submitting' | 'capture_error' | 'network_error' | 'quota_exceeded'>('idle');
  const [savedToJournal, setSavedToJournal] = useState(false);
  const [viewerOpen, setViewerOpen] = useState(false);
  const pickLock = useRef(false);
  const lastCaptureMethod = useRef<CaptureMethod>('camera');

  const reset = useCallback(() => {
    if (status === 'picking' || status === 'submitting') return;
    setPicked(null);
    setQualityIssues([]);
    setResult(null);
    setSavedToJournal(false);
    setViewerOpen(false);
    setStatus('idle');
  }, [status]);

  const pick = async (method: CaptureMethod) => {
    if (pickLock.current || status === 'submitting') return;
    pickLock.current = true;
    lastCaptureMethod.current = method;
    setStatus('picking');
    try {
      const image = method === 'camera' ? await captureFromCamera({ base64: false }) : await pickFromGallery({ base64: false });
      if (!image) {
        setStatus('idle');
        return;
      }
      setPicked(image);
      setQualityIssues(checkImageQuality(image).issues);
      setResult(null);
      setSavedToJournal(false);
      setStatus('idle');
    } catch {
      setStatus('capture_error');
    } finally {
      pickLock.current = false;
    }
  };

  const analyze = async () => {
    if (!picked || qualityIssues.length) return;
    setStatus('submitting');
    try {
      setResult(await identifyPlant({ ...picked, preferredLanguage: language === 'ta' ? 'ta' : 'en' }));
      setStatus('idle');
    } catch (error) {
      setResult(null);
      setStatus(error instanceof ApiError && error.errorCode === 'ai_daily_quota_exceeded' ? 'quota_exceeded' : 'network_error');
    }
  };

  const confidencePercent = result && Number.isFinite(result.confidence) ? Math.round(result.confidence * 100) : null;

  const saveToJournal = async () => {
    if (!picked || result?.status !== 'identified') return;
    let latitude: number | null = null;
    let longitude: number | null = null;
    try {
      const permission = await Location.getForegroundPermissionsAsync();
      if (permission.granted) {
        const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        latitude = position.coords.latitude;
        longitude = position.coords.longitude;
      }
    } catch {
      // Location remains optional journal context.
    }
    try {
      plantJournalStorage.add({
        id: result.request_id,
        imageUri: picked.uri,
        commonName: result.common_name,
        scientificName: result.scientific_name,
        family: result.family,
        confidence: result.confidence,
        savedAt: new Date().toISOString(),
        latitude,
        longitude,
      });
      setSavedToJournal(true);
      Alert.alert(t('plantIdentifier.savedToJournal'));
    } catch {
      Alert.alert(t('common.error'), t('plantIdentifier.journalSaveFailed'));
    }
  };

  return (
    <AgScreen scroll backgroundColor={SCREEN_BG} contentContainerStyle={styles.screenContent}>
      <View style={styles.header}>
        <AgPressable onPress={() => router.back()} accessibilityRole="button" accessibilityLabel={t('common.back')} style={styles.backButton}>
          <ArrowLeft size={26} color={TEXT} />
        </AgPressable>
        <Leaf size={30} color={GREEN} />
        <View style={styles.titleRow} accessibilityLabel={t('plantIdentifier.title')}>
          <AgText variant="headingM" weight="bold" style={styles.primaryText}>{t('plantIdentifier.titlePlant')} </AgText>
          <AgText variant="headingM" weight="bold" style={styles.greenText}>{t('plantIdentifier.titleIdentifier')}</AgText>
        </View>
        <AgPressable onPress={reset} disabled={status === 'picking' || status === 'submitting'} accessibilityRole="button" accessibilityLabel={t('plantIdentifier.startOver')} style={styles.resetButton}>
          <RefreshCw size={21} color={GREEN} />
        </AgPressable>
        <AgPressable onPress={() => router.push('/plant-identifier/journal' as never)} accessibilityRole="button" accessibilityLabel={t('plantIdentifier.viewJournal')} style={styles.journalButton}>
          <BookOpen size={22} color={GREEN} />
          <AgText variant="caption" style={styles.secondaryText}>{t('plantIdentifier.journalShort')}</AgText>
        </AgPressable>
      </View>

      <View style={styles.serviceBadge}><AgText variant="caption" weight="semibold" style={styles.greenText}>{t('plantIdentifier.subtitle')}</AgText></View>
      <AgText variant="body" style={styles.secondaryText}>{t('plantIdentifier.intro')}</AgText>

      {!picked ? (
        <View style={styles.captureCard}>
          <View style={styles.captureIcon}><Camera size={30} color={GREEN} /></View>
          <AgText variant="bodyLarge" weight="bold" style={styles.primaryText}>{t('plantIdentifier.captureTitle')}</AgText>
          <AgText variant="bodySmall" center style={styles.secondaryText}>{t('plantIdentifier.captureHint')}</AgText>
          <AgButton title={t('plantIdentifier.takePhoto')} loading={status === 'picking' && lastCaptureMethod.current === 'camera'} disabled={status === 'picking'} leftIcon={<Camera size={20} color="#071008" />} onPress={() => void pick('camera')} />
          <AgButton title={t('plantIdentifier.chooseGallery')} loading={status === 'picking' && lastCaptureMethod.current === 'gallery'} disabled={status === 'picking'} variant="secondary" leftIcon={<Images size={20} color={GREEN} />} onPress={() => void pick('gallery')} />
          {status === 'capture_error' ? (
            <View style={styles.captureError} accessibilityRole="alert">
              <AgText weight="bold" style={styles.primaryText}>{t('plantIdentifier.photoAccessFailed')}</AgText>
              <AgButton title={t('plantIdentifier.retry')} variant="secondary" size="sm" onPress={() => void pick(lastCaptureMethod.current)} />
            </View>
          ) : null}
        </View>
      ) : (
        <View style={styles.content}>
          <View style={styles.imageFrame}>
            <Image source={{ uri: picked.uri }} style={styles.preview} contentFit="contain" />
            <AgPressable onPress={() => setViewerOpen(true)} accessibilityRole="button" accessibilityLabel={t('plantIdentifier.viewFullImage')} style={styles.fullImageButton}>
              <Expand size={17} color={TEXT} />
              <AgText variant="caption" weight="semibold" style={styles.primaryText}>{t('plantIdentifier.viewFullImage')}</AgText>
            </AgPressable>
          </View>

          <AgButton title={t('plantIdentifier.retakePhoto')} variant="secondary" size="sm" leftIcon={<Camera size={18} color={GREEN} />} onPress={() => void pick('camera')} />

          {qualityIssues.length ? <StateCard title={t('plantIdentifier.qualityIssue')} message={t('plantIdentifier.disclaimer')} tone="danger" /> : null}
          {!qualityIssues.length && !result ? (
            <AgButton title={t('plantIdentifier.identify')} loading={status === 'submitting'} disabled={status === 'submitting'} onPress={() => void analyze()} />
          ) : null}

          {result?.status === 'identified' ? (
            <>
              <View style={styles.resultCard}>
                <View style={styles.resultIcon}><Leaf size={30} color={GREEN} /></View>
                <View style={styles.resultCopy}>
                  <AgText variant="headingS" weight="bold" style={styles.primaryText}>{result.common_name ?? t('plantIdentifier.unknownPlant')}</AgText>
                  {result.scientific_name ? <AgText variant="bodyLarge" style={[styles.primaryText, styles.scientific]}>{result.scientific_name}</AgText> : null}
                  {result.family ? <AgText variant="body" style={styles.secondaryText}>{t('plantIdentifier.family', { family: result.family })}</AgText> : null}
                  {confidencePercent !== null ? (
                    <View style={styles.confidenceRow}><ShieldCheck size={18} color={GREEN} /><AgText variant="bodySmall" weight="semibold" style={styles.greenText}>{confidencePercent}% {t('plantIdentifier.confidence')}</AgText></View>
                  ) : null}
                  <AgText variant="caption" style={styles.secondaryText}>{t('plantIdentifier.aiResult')}</AgText>
                </View>
              </View>

              {result.description || result.visible_characteristics.length ? (
                <View style={styles.aboutCard}>
                  <View style={styles.sectionTitle}><Info size={20} color={GREEN} /><AgText variant="bodyLarge" weight="bold" style={styles.primaryText}>{t('plantIdentifier.about')}</AgText></View>
                  {result.description ? <AgText variant="body" style={styles.secondaryText}>{result.description}</AgText> : null}
                  {result.visible_characteristics.map((trait) => (
                    <View key={trait} style={styles.traitRow}><CheckCircle2 size={18} color={GREEN} /><AgText variant="bodySmall" style={[styles.secondaryText, styles.traitText]}>{trait}</AgText></View>
                  ))}
                </View>
              ) : null}

              <AgButton title={savedToJournal ? t('plantIdentifier.savedToJournal') : t('plantIdentifier.saveToJournal')} variant="secondary" disabled={savedToJournal} leftIcon={<BookOpen size={18} color={GREEN} />} onPress={() => void saveToJournal()} />
            </>
          ) : null}

          {result?.status === 'uncertain' ? (
            <View style={styles.aboutCard}>
              <AgText variant="bodyLarge" weight="bold" style={styles.primaryText}>{t('plantIdentifier.uncertainTitle')}</AgText>
              {confidencePercent !== null ? <AgText weight="semibold" style={styles.greenText}>{confidencePercent}% {t('plantIdentifier.confidence')}</AgText> : null}
              <AgText style={styles.secondaryText}>{t('plantIdentifier.uncertainMessage')}</AgText>
              {result.possible_alternatives.map((item) => <AgText key={`${item.common_name}-${item.scientific_name ?? ''}`} style={styles.primaryText}>{item.common_name}{item.scientific_name ? ` — ${item.scientific_name}` : ''}</AgText>)}
            </View>
          ) : null}
          {result?.status === 'non_plant' ? <StateCard title={t('plantIdentifier.nonPlantTitle')} message={t('plantIdentifier.nonPlantMessage')} /> : null}
          {result?.status === 'invalid_image' ? <StateCard title={t('plantIdentifier.invalidImageTitle')} message={t('plantIdentifier.invalidImageMessage')} /> : null}
          {status === 'quota_exceeded' ? <StateCard title={t('plantIdentifier.quotaExceeded')} /> : null}
          {result?.status === 'provider_error' || status === 'network_error' ? (
            <View style={styles.aboutCard}><AgText weight="bold" style={styles.primaryText}>{t('plantIdentifier.providerErrorTitle')}</AgText><AgText style={styles.secondaryText}>{t('plantIdentifier.providerErrorMessage')}</AgText><AgButton title={t('plantIdentifier.retry')} variant="secondary" onPress={() => void analyze()} /></View>
          ) : null}
        </View>
      )}

      <View style={styles.disclaimerCard}>
        <Info size={22} color={GREEN} />
        <AgText variant="bodySmall" style={[styles.secondaryText, styles.disclaimerText]}>{result?.disclaimer || t('plantIdentifier.disclaimer')}</AgText>
      </View>

      <ImageViewer uri={picked?.uri ?? null} caption={result?.common_name ?? t('plantIdentifier.title')} visible={viewerOpen} onClose={() => setViewerOpen(false)} />
    </AgScreen>
  );
}

function StateCard({ title, message, tone }: { title: string; message?: string; tone?: 'danger' }) {
  return <View style={[styles.aboutCard, tone === 'danger' && styles.dangerCard]}><AgText weight="bold" style={styles.primaryText}>{title}</AgText>{message ? <AgText style={styles.secondaryText}>{message}</AgText> : null}</View>;
}

const styles = StyleSheet.create({
  screenContent: { paddingHorizontal: 18, paddingTop: 14, paddingBottom: 38 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  backButton: { width: 42, height: 44, alignItems: 'center', justifyContent: 'center', marginLeft: -8 },
  titleRow: { flex: 1, flexDirection: 'row', flexWrap: 'wrap', alignItems: 'baseline' },
  journalButton: { minWidth: 70, minHeight: 64, alignItems: 'center', justifyContent: 'center', gap: 4, padding: 8, borderRadius: 18, borderWidth: 1, borderColor: '#303633', backgroundColor: '#111513' },
  resetButton: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center', borderRadius: 15, borderWidth: 1, borderColor: '#303633', backgroundColor: '#111513' },
  serviceBadge: { alignSelf: 'flex-start', marginTop: 18, paddingHorizontal: 12, paddingVertical: 7, borderRadius: 10, backgroundColor: '#1A211C' },
  primaryText: { color: TEXT }, secondaryText: { color: MUTED }, greenText: { color: GREEN },
  captureCard: { gap: 14, alignItems: 'center', marginTop: 24, padding: 22, borderRadius: 22, borderWidth: 1, borderColor: '#303633', backgroundColor: SURFACE },
  captureError: { width: '100%', gap: 10, padding: 14, borderRadius: 16, borderWidth: 1, borderColor: '#6A3431', backgroundColor: '#241514' },
  captureIcon: { width: 68, height: 68, alignItems: 'center', justifyContent: 'center', borderRadius: 34, backgroundColor: '#162A19' },
  content: { gap: 16, marginTop: 22 },
  imageFrame: { overflow: 'hidden', position: 'relative', width: '100%', aspectRatio: 4 / 3, borderRadius: 22, borderWidth: 1, borderColor: '#303633', backgroundColor: '#050706' },
  preview: { width: '100%', height: '100%' },
  fullImageButton: { position: 'absolute', right: 12, bottom: 12, flexDirection: 'row', alignItems: 'center', gap: 7, paddingHorizontal: 12, paddingVertical: 9, borderRadius: 16, backgroundColor: 'rgba(10,12,11,0.86)' },
  resultCard: { flexDirection: 'row', alignItems: 'center', gap: 17, padding: 18, borderRadius: 20, borderWidth: 1, borderColor: '#303633', backgroundColor: SURFACE },
  resultIcon: { width: 68, height: 68, alignItems: 'center', justifyContent: 'center', borderRadius: 34, borderWidth: 1, borderColor: '#29462C', backgroundColor: '#162319' },
  resultCopy: { flex: 1, gap: 5 }, scientific: { fontStyle: 'italic' },
  confidenceRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  aboutCard: { gap: 13, padding: 18, borderRadius: 20, borderWidth: 1, borderColor: '#303633', backgroundColor: SURFACE },
  dangerCard: { borderColor: '#6A3431' }, sectionTitle: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  traitRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 9 }, traitText: { flex: 1 },
  disclaimerCard: { flexDirection: 'row', alignItems: 'flex-start', gap: 11, marginTop: 20, padding: 16, borderRadius: 18, borderWidth: 1, borderColor: '#315C36', backgroundColor: '#101A12' },
  disclaimerText: { flex: 1 },
});
