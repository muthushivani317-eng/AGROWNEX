import { StatusBar } from 'expo-status-bar';
import { Image, StyleSheet, Text, View } from 'react-native';

interface SplashScreenProps {
  /** Called when the full-screen artwork is decoded and safe to reveal. */
  onReady?: () => void;
}

/**
 * Full-screen branded startup surface. Startup readiness owns its lifetime;
 * this component adds no artificial delay and never participates in routing.
 */
export function SplashScreen({ onReady }: SplashScreenProps) {
  return (
    <View
      testID="branded-splash-screen"
      style={styles.container}
      accessibilityLabel="AgrowAI is preparing your farm intelligence"
      accessibilityLiveRegion="polite"
    >
      <StatusBar style="dark" />

      <View style={styles.brandBlock}>
        <View style={styles.emblemHalo}>
          <Image
            testID="branded-splash-artwork"
            source={require('../../../assets/images/android-icon-foreground.png')}
            resizeMode="contain"
            style={styles.emblem}
            onLoadEnd={onReady}
            onError={onReady}
            accessibilityIgnoresInvertColors
            accessible={false}
          />
        </View>

        <Text style={styles.wordmark} accessibilityRole="header">
          Agrow<Text style={styles.wordmarkAccent}>AI</Text>
        </Text>
        <View style={styles.promiseRule}>
          <View style={styles.rule} />
          <View style={styles.seed} />
          <View style={styles.rule} />
        </View>
        <Text style={styles.promise}>Intelligence for every field</Text>
        <Text style={styles.promiseTamil}>விவசாயிக்கு அறிவு · வளர்ச்சிக்கு வழி</Text>
      </View>

      <View style={styles.loadingBlock}>
        <Text style={styles.loadingLabel}>Preparing your farm intelligence…</Text>
        <View
          style={styles.progressTrack}
          accessibilityRole="progressbar"
          accessibilityValue={{ text: 'Loading' }}
        >
          <View style={styles.progressFill} />
        </View>
      </View>

      <View pointerEvents="none" style={styles.fieldContours}>
        <View style={[styles.contour, styles.contourBack]} />
        <View style={[styles.contour, styles.contourMiddle]} />
        <View style={[styles.contour, styles.contourFront]} />
        <View style={styles.harvestLine} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FBF7EA',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 28,
    overflow: 'hidden',
  },
  brandBlock: {
    alignItems: 'center',
    zIndex: 2,
    transform: [{ translateY: -34 }],
  },
  emblemHalo: {
    width: 158,
    height: 158,
    borderRadius: 79,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFFDF6',
    borderWidth: 1,
    borderColor: '#DDE8D5',
    shadowColor: '#173B2B',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.1,
    shadowRadius: 24,
    elevation: 5,
  },
  emblem: {
    width: 132,
    height: 132,
  },
  wordmark: {
    marginTop: 20,
    color: '#165B33',
    fontFamily: 'Inter_700Bold',
    fontSize: 46,
    lineHeight: 54,
    letterSpacing: -2.2,
  },
  wordmarkAccent: {
    color: '#D99800',
  },
  promiseRule: {
    width: 214,
    marginTop: 10,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  rule: {
    flex: 1,
    height: 1,
    backgroundColor: '#9DBA91',
  },
  seed: {
    width: 10,
    height: 16,
    borderTopLeftRadius: 10,
    borderBottomRightRadius: 10,
    backgroundColor: '#4E9B45',
    transform: [{ rotate: '28deg' }],
  },
  promise: {
    marginTop: 14,
    color: '#173B2B',
    fontFamily: 'Inter_600SemiBold',
    fontSize: 16,
    lineHeight: 24,
    letterSpacing: 0.2,
    textAlign: 'center',
  },
  promiseTamil: {
    marginTop: 3,
    color: '#4F6658',
    fontFamily: 'NotoSansTamil_500Medium',
    fontSize: 13,
    lineHeight: 22,
    textAlign: 'center',
  },
  loadingBlock: {
    position: 'absolute',
    bottom: 92,
    zIndex: 3,
    width: '72%',
    maxWidth: 300,
    alignItems: 'center',
  },
  loadingLabel: {
    color: '#365445',
    fontFamily: 'Inter_500Medium',
    fontSize: 12,
    lineHeight: 18,
    letterSpacing: 0.2,
  },
  progressTrack: {
    width: '100%',
    height: 3,
    marginTop: 12,
    borderRadius: 3,
    overflow: 'hidden',
    backgroundColor: '#D7E4D0',
  },
  progressFill: {
    width: '42%',
    height: '100%',
    borderRadius: 3,
    backgroundColor: '#D99800',
  },
  fieldContours: {
    position: 'absolute',
    right: -120,
    bottom: -250,
    left: -120,
    height: 390,
  },
  contour: {
    position: 'absolute',
    alignSelf: 'center',
    borderStyle: 'solid',
  },
  contourBack: {
    bottom: 54,
    width: 720,
    height: 250,
    borderRadius: 360,
    borderWidth: 42,
    borderColor: '#DCEACF',
  },
  contourMiddle: {
    bottom: 20,
    width: 610,
    height: 220,
    borderRadius: 305,
    borderWidth: 46,
    borderColor: '#A7C98E',
  },
  contourFront: {
    bottom: -28,
    width: 500,
    height: 196,
    borderRadius: 250,
    borderWidth: 52,
    borderColor: '#4E9B45',
  },
  harvestLine: {
    position: 'absolute',
    top: 66,
    left: '35%',
    width: '30%',
    height: 3,
    borderRadius: 3,
    backgroundColor: '#D99800',
  },
});
