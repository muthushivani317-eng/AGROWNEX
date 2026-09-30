import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import {
  ArrowRight,
  Bot,
  CalendarDays,
  CheckCircle2,
  CloudSun,
  Droplets,
  FlaskConical,
  HeartPulse,
  Languages,
  Leaf,
  LineChart,
  MapPin,
  Satellite,
  ShieldCheck,
  Sprout,
  TrendingUp,
} from 'lucide-react-native';
import { useMemo, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';

type Language = 'en' | 'ta';

const COPY = {
  en: {
    nav: ['Capabilities', 'How it works', 'Trust'],
    open: 'Open AgrowNex',
    eyebrow: 'FIELD INTELLIGENCE, MADE PRACTICAL',
    title: 'One field. One clear next step.',
    lead:
      'AgrowNex brings satellite, weather, soil, crop health and farm records together—then turns them into guidance a farmer can actually use.',
    primary: 'Start with AgrowNex',
    secondary: 'Explore capabilities',
    safety: 'AI-assisted estimates. Important decisions stay with the farmer and agricultural experts.',
    scene: 'KVK Farm · Latest field view',
    priority: 'Today’s priority',
    priorityTitle: 'Inspect the dry north-west zone',
    priorityBody: 'Moisture is lower than the rest of the field. Check before irrigating.',
    signal: 'FIELD SIGNALS',
    sectionEyebrow: 'ONE CONNECTED FARM WORKFLOW',
    sectionTitle: 'Observe. Understand. Act.',
    sectionLead:
      'Every capability is designed to support the next field decision—not to create another dashboard to manage.',
    observe: 'Observe',
    observeBody: 'See what is changing across the farm and over time.',
    understand: 'Understand',
    understandBody: 'Combine evidence before deciding what it may mean.',
    act: 'Act',
    actBody: 'Turn insights into simple, trackable farm actions.',
    satellite: 'Satellite Intelligence',
    satelliteBody: 'True colour, vegetation, moisture, stress and water views with scene-quality details.',
    weather: 'Field Weather',
    weatherBody: 'Local forecasts, heat, rain and spraying guidance built around farm work.',
    growth: 'Growth Monitor',
    growthBody: 'Photo history and crop-stage records that reveal change over time.',
    soil: 'Soil Intelligence',
    soilBody: 'Separate satellite estimates from laboratory values, with smart sampling locations.',
    health: 'Crop & Farm Health',
    healthBody: 'Disease, nutrient and whole-farm screening with clear confidence and safety limits.',
    assistant: 'Bilingual AI Assistant',
    assistantBody: 'Farm-aware guidance in English and Tamil, grounded in current field context.',
    calendar: 'Calendar & Follow-up',
    calendarBody: 'Plan tasks, record actions and remember what happened on every farm.',
    market: 'Market & Schemes',
    marketBody: 'Verified-source market prices and potentially relevant government programmes.',
    howEyebrow: 'FROM FARM TO GUIDANCE',
    howTitle: 'Useful in the field, not just impressive on a screen.',
    steps: [
      ['Add your farm', 'Mark the boundary, crop, sowing date and location once.'],
      ['Build the evidence', 'AgrowNex checks available satellite, weather, soil and farm records.'],
      ['Get a clear next step', 'See what needs attention, why it matters and what to verify in the field.'],
    ],
    tamilTitle: 'Built for Tamil and English from the first screen.',
    tamilBody:
      'Farmers can switch language without losing context. Tamil guidance, offline field knowledge and accessible controls are part of the product—not an afterthought.',
    offline: 'Offline Tamil field guides',
    switch: 'Switch language anytime',
    small: 'Designed for small screens',
    trustEyebrow: 'TRUSTED DECISIONS NEED HONEST DATA',
    trustTitle: 'AgrowNex shows what it knows—and what it does not.',
    trustBody:
      'Confidence, source, scene age and missing evidence are shown clearly. Satellite screening is not a lab result; AI screening is not a diagnosis.',
    trustItems: ['Evidence source on every insight', 'Estimated vs measured labels', 'Expert verification for critical decisions'],
    finalTitle: 'Give every field a clearer next step.',
    finalBody: 'Bring your farm, crop and local context together in one bilingual assistant.',
    finalCta: 'Open the app',
    footer: 'AgrowNex · AI for every farmer, growth for every field.',
    disclaimer: 'General agricultural guidance. Verify critical decisions with an official source or agricultural expert.',
  },
  ta: {
    nav: ['வசதிகள்', 'எப்படி செயல்படுகிறது', 'நம்பிக்கை'],
    open: 'AgrowNex திறக்கவும்',
    eyebrow: 'பயனுள்ள பண்ணை நுண்ணறிவு',
    title: 'ஒரு வயல். ஒரு தெளிவான அடுத்த படி.',
    lead:
      'செயற்கைக்கோள், வானிலை, மண், பயிர் ஆரோக்கியம் மற்றும் பண்ணைப் பதிவுகளை AgrowNex ஒருங்கிணைத்து, விவசாயி பயன்படுத்தக்கூடிய வழிகாட்டலாக மாற்றுகிறது.',
    primary: 'AgrowNex தொடங்கவும்',
    secondary: 'வசதிகளைப் பார்க்கவும்',
    safety: 'AI உதவியுடன் மதிப்பீடுகள். முக்கிய முடிவுகள் விவசாயி மற்றும் வேளாண் நிபுணர்களிடமே இருக்கும்.',
    scene: 'KVK பண்ணை · சமீபத்திய வயல் காட்சி',
    priority: 'இன்றைய முன்னுரிமை',
    priorityTitle: 'வடமேற்கு உலர் பகுதியை பார்வையிடவும்',
    priorityBody: 'மற்ற பகுதிகளை விட ஈரப்பதம் குறைவாக உள்ளது. பாசனத்திற்கு முன் சரிபார்க்கவும்.',
    signal: 'வயல் குறியீடுகள்',
    sectionEyebrow: 'ஒருங்கிணைந்த பண்ணை செயல்முறை',
    sectionTitle: 'கவனிக்கவும். புரிந்துகொள்ளவும். செயல்படவும்.',
    sectionLead: 'ஒவ்வொரு வசதியும் அடுத்த வயல் முடிவை எளிதாக்குவதற்காக வடிவமைக்கப்பட்டுள்ளது.',
    observe: 'கவனிக்கவும்',
    observeBody: 'பண்ணையின் பகுதிகளிலும் காலப்போக்கிலும் ஏற்படும் மாற்றங்களைப் பார்க்கவும்.',
    understand: 'புரிந்துகொள்ளவும்',
    understandBody: 'முடிவு செய்வதற்கு முன் பல ஆதாரங்களை ஒன்றாகப் பார்க்கவும்.',
    act: 'செயல்படவும்',
    actBody: 'நுண்ணறிவுகளை எளிய, பதிவு செய்யக்கூடிய பண்ணை செயல்களாக மாற்றவும்.',
    satellite: 'செயற்கைக்கோள் நுண்ணறிவு',
    satelliteBody: 'வயல் படம், தாவர ஆரோக்கியம், ஈரப்பதம், அழுத்தம் மற்றும் நீர் அடுக்குகள்.',
    weather: 'வயல் வானிலை',
    weatherBody: 'உள்ளூர் முன்னறிவிப்பு, வெப்பம், மழை மற்றும் தெளிப்பு வழிகாட்டல்.',
    growth: 'வளர்ச்சி கண்காணிப்பு',
    growthBody: 'புகைப்பட வரலாறு மற்றும் பயிர் நிலைப் பதிவுகள்.',
    soil: 'மண் நுண்ணறிவு',
    soilBody: 'செயற்கைக்கோள் மதிப்பீடுகள் மற்றும் ஆய்வக மதிப்புகளைத் தெளிவாகப் பிரித்துக் காட்டுகிறது.',
    health: 'பயிர் மற்றும் பண்ணை ஆரோக்கியம்',
    healthBody: 'நோய், ஊட்டச்சத்து மற்றும் முழுப் பண்ணை மதிப்பீடு.',
    assistant: 'இருமொழி AI உதவியாளர்',
    assistantBody: 'ஆங்கிலம் மற்றும் தமிழில் பண்ணைச் சூழலுக்கேற்ற வழிகாட்டல்.',
    calendar: 'நாட்காட்டி மற்றும் தொடர்ச்சி',
    calendarBody: 'பணிகளைத் திட்டமிட்டு, செயல்களைப் பதிவு செய்து, பண்ணை வரலாற்றை நினைவில் வைத்துக்கொள்ளவும்.',
    market: 'சந்தை மற்றும் திட்டங்கள்',
    marketBody: 'அதிகாரப்பூர்வ ஆதார சந்தை விலைகள் மற்றும் பொருந்தக்கூடிய அரசு திட்டங்கள்.',
    howEyebrow: 'பண்ணையிலிருந்து வழிகாட்டலுக்கு',
    howTitle: 'திரையில் மட்டும் அல்ல—வயலில் பயனுள்ளதாக.',
    steps: [
      ['பண்ணையைச் சேர்க்கவும்', 'எல்லை, பயிர், விதைப்பு தேதி மற்றும் இடத்தை ஒருமுறை பதிவு செய்யவும்.'],
      ['ஆதாரங்களை உருவாக்கவும்', 'செயற்கைக்கோள், வானிலை, மண் மற்றும் பண்ணைப் பதிவுகளை AgrowNex பார்க்கும்.'],
      ['தெளிவான அடுத்த படியைப் பெறவும்', 'எதை கவனிக்க வேண்டும், ஏன், வயலில் எதை உறுதி செய்ய வேண்டும் என்பதைக் காணவும்.'],
    ],
    tamilTitle: 'முதல் திரையிலிருந்தே தமிழ் மற்றும் ஆங்கிலத்திற்காக.',
    tamilBody: 'விவசாயிகள் சூழலை இழக்காமல் மொழியை மாற்றலாம். தமிழ் வழிகாட்டல், இணையமில்லா அறிவு மற்றும் எளிய கட்டுப்பாடுகள் தயாரிப்பின் அடிப்படை பகுதிகள்.',
    offline: 'இணையமில்லா தமிழ் வயல் வழிகாட்டிகள்',
    switch: 'எப்போது வேண்டுமானாலும் மொழி மாற்றம்',
    small: 'சிறிய திரைகளுக்கான வடிவமைப்பு',
    trustEyebrow: 'நம்பகமான முடிவுக்கு நேர்மையான தரவு',
    trustTitle: 'AgrowNex தெரிந்ததையும் தெரியாததையும் தெளிவாகக் காட்டுகிறது.',
    trustBody: 'நம்பிக்கை, ஆதாரம், காட்சி வயது மற்றும் இல்லாத ஆதாரங்கள் தெளிவாகக் காட்டப்படும். செயற்கைக்கோள் மதிப்பீடு ஆய்வக முடிவு அல்ல; AI மதிப்பீடு நோய் தீர்ப்பு அல்ல.',
    trustItems: ['ஒவ்வொரு நுண்ணறிவுக்கும் ஆதாரம்', 'மதிப்பீடு மற்றும் அளவீடு குறிச்சொற்கள்', 'முக்கிய முடிவுகளுக்கு நிபுணர் உறுதிப்படுத்தல்'],
    finalTitle: 'ஒவ்வொரு வயலுக்கும் தெளிவான அடுத்த படி.',
    finalBody: 'உங்கள் பண்ணை, பயிர் மற்றும் உள்ளூர் சூழலை ஒரே இருமொழி உதவியாளரில் இணைக்கவும்.',
    finalCta: 'செயலியைத் திறக்கவும்',
    footer: 'AgrowNex · ஒவ்வொரு விவசாயிக்கும் AI, ஒவ்வொரு வயலுக்கும் வளர்ச்சி.',
    disclaimer: 'பொதுவான வேளாண் வழிகாட்டல். முக்கிய முடிவுகளை அதிகாரப்பூர்வ ஆதாரம் அல்லது வேளாண் நிபுணருடன் உறுதி செய்யவும்.',
  },
} as const;

const FEATURE_ICONS = [Satellite, CloudSun, LineChart, FlaskConical, HeartPulse, Bot, CalendarDays, TrendingUp];

export function WebsiteLandingScreen() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const [language, setLanguage] = useState<Language>('en');
  const copy = COPY[language];
  const desktop = width >= 960;
  const tablet = width >= 680;
  const contentWidth = Math.min(width - (desktop ? 64 : 32), 1180);
  const featureItems = useMemo(
    () => [
      [copy.satellite, copy.satelliteBody],
      [copy.weather, copy.weatherBody],
      [copy.growth, copy.growthBody],
      [copy.soil, copy.soilBody],
      [copy.health, copy.healthBody],
      [copy.assistant, copy.assistantBody],
      [copy.calendar, copy.calendarBody],
      [copy.market, copy.marketBody],
    ],
    [copy],
  );
  const openApp = () => router.push('/(auth)/login');
  const navTargets = ['capabilities', 'how-it-works', 'trust'];
  const scrollToSection = (id: string) => {
    if (typeof document === 'undefined') return;
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.pageContent}>
      <View style={[styles.header, { width: contentWidth }]}>
        <View style={styles.brand}>
          <Image source={require('@/assets/images/brand-logo-source.png')} style={styles.logo} contentFit="contain" />
          <Text style={styles.brandName}>AgrowNex</Text>
        </View>
        {desktop ? (
          <View style={styles.nav}>
            {copy.nav.map((item, index) => (
              <Pressable
                key={item}
                accessibilityRole="link"
                accessibilityLabel={item}
                onPress={() => scrollToSection(navTargets[index])}
                style={({ pressed }) => [styles.navButton, pressed && styles.pressed]}
              >
                <Text style={styles.navText}>{item}</Text>
              </Pressable>
            ))}
          </View>
        ) : null}
        <View style={styles.headerActions}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={language === 'en' ? 'Switch to Tamil' : 'Switch to English'}
            onPress={() => setLanguage(language === 'en' ? 'ta' : 'en')}
            style={styles.languageButton}
          >
            <Languages size={18} color="#14532D" />
            <Text style={styles.languageText}>{language === 'en' ? 'தமிழ்' : 'English'}</Text>
          </Pressable>
          {tablet ? <PrimaryButton label={copy.open} onPress={openApp} compact /> : null}
        </View>
      </View>

      <View style={[styles.hero, { width: contentWidth }, desktop && styles.heroDesktop]}>
        <View style={[styles.heroCopy, desktop && styles.heroCopyDesktop]}>
          <Text style={styles.eyebrow}>{copy.eyebrow}</Text>
          <Text style={[styles.heroTitle, language === 'ta' && styles.tamilHeroTitle]}>{copy.title}</Text>
          <Text style={styles.heroLead}>{copy.lead}</Text>
          <View style={styles.heroActions}>
            <PrimaryButton label={copy.primary} onPress={openApp} />
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={copy.secondary}
              onPress={() => scrollToSection('capabilities')}
              style={({ pressed }) => [styles.secondaryButton, pressed && styles.pressed]}
            >
              <Text style={styles.secondaryButtonText}>{copy.secondary}</Text>
              <ArrowRight size={19} color="#14532D" />
            </Pressable>
          </View>
          <View style={styles.safetyLine}>
            <ShieldCheck size={20} color="#15803D" />
            <Text style={styles.safetyText}>{copy.safety}</Text>
          </View>
        </View>
        <FieldVisual copy={copy} desktop={desktop} />
      </View>

      <View nativeID="capabilities" style={[styles.section, { width: contentWidth }]}>
        <Text style={styles.eyebrow}>{copy.sectionEyebrow}</Text>
        <Text style={styles.sectionTitle}>{copy.sectionTitle}</Text>
        <Text style={styles.sectionLead}>{copy.sectionLead}</Text>
        <View style={[styles.workflowRow, !desktop && styles.workflowStack]}>
          {[[copy.observe, copy.observeBody], [copy.understand, copy.understandBody], [copy.act, copy.actBody]].map((item, index) => (
            <View key={item[0]} style={styles.workflowItem}>
              <Text style={styles.workflowNumber}>0{index + 1}</Text>
              <Text style={styles.workflowTitle}>{item[0]}</Text>
              <Text style={styles.workflowBody}>{item[1]}</Text>
            </View>
          ))}
        </View>
        <View style={[styles.featureGrid, tablet && styles.featureGridWide]}>
          {featureItems.map(([title, body], index) => {
            const Icon = FEATURE_ICONS[index];
            return (
              <View key={title} style={[styles.featureCard, tablet && styles.featureCardWide]}>
                <View style={styles.iconTile}><Icon size={24} color="#15803D" /></View>
                <Text style={styles.featureTitle}>{title}</Text>
                <Text style={styles.featureBody}>{body}</Text>
              </View>
            );
          })}
        </View>
      </View>

      <View nativeID="how-it-works" style={styles.band}>
        <View style={[styles.bandInner, { width: contentWidth }, desktop && styles.bandDesktop]}>
          <View style={styles.bandCopy}>
            <Text style={styles.eyebrowLight}>{copy.howEyebrow}</Text>
            <Text style={styles.bandTitle}>{copy.howTitle}</Text>
          </View>
          <View style={styles.stepList}>
            {copy.steps.map((step, index) => (
              <View key={step[0]} style={styles.stepItem}>
                <View style={styles.stepNumber}><Text style={styles.stepNumberText}>{index + 1}</Text></View>
                <View style={styles.stepCopy}>
                  <Text style={styles.stepTitle}>{step[0]}</Text>
                  <Text style={styles.stepBody}>{step[1]}</Text>
                </View>
              </View>
            ))}
          </View>
        </View>
      </View>

      <View style={[styles.section, { width: contentWidth }, desktop && styles.splitSection]}>
        <View style={styles.languageVisual}>
          <View style={styles.languageCardBack} />
          <View style={styles.languageCardFront}>
            <Text style={styles.languageCardTamil}>வணக்கம்</Text>
            <Text style={styles.languageCardEnglish}>Vanakkam</Text>
            <View style={styles.contextPill}><Leaf size={17} color="#15803D" /><Text style={styles.contextText}>KVK · Sugarcane</Text></View>
          </View>
        </View>
        <View style={styles.splitCopy}>
          <Text style={styles.sectionTitle}>{copy.tamilTitle}</Text>
          <Text style={styles.sectionLead}>{copy.tamilBody}</Text>
          {[copy.offline, copy.switch, copy.small].map((item) => (
            <View key={item} style={styles.checkRow}><CheckCircle2 size={20} color="#15803D" /><Text style={styles.checkText}>{item}</Text></View>
          ))}
        </View>
      </View>

      <View nativeID="trust" style={[styles.trustCard, { width: contentWidth }, desktop && styles.trustDesktop]}>
        <View style={styles.trustIcon}><ShieldCheck size={34} color="#F59E0B" /></View>
        <View style={styles.trustCopy}>
          <Text style={styles.eyebrow}>{copy.trustEyebrow}</Text>
          <Text style={styles.sectionTitle}>{copy.trustTitle}</Text>
          <Text style={styles.sectionLead}>{copy.trustBody}</Text>
          <View style={[styles.trustItems, tablet && styles.trustItemsWide]}>
            {copy.trustItems.map((item) => <View key={item} style={styles.checkRow}><CheckCircle2 size={19} color="#15803D" /><Text style={styles.checkText}>{item}</Text></View>)}
          </View>
        </View>
      </View>

      <View style={[styles.finalCta, { width: contentWidth }]}>
        <Sprout size={42} color="#BBF7D0" />
        <Text style={styles.finalTitle}>{copy.finalTitle}</Text>
        <Text style={styles.finalBody}>{copy.finalBody}</Text>
        <PrimaryButton label={copy.finalCta} onPress={openApp} light />
      </View>

      <View style={[styles.footer, { width: contentWidth }]}>
        <Text style={styles.footerBrand}>{copy.footer}</Text>
        <Text style={styles.footerDisclaimer}>{copy.disclaimer}</Text>
        <Text style={styles.copyright}>© 2026 AgrowNex</Text>
      </View>
    </ScrollView>
  );
}

function PrimaryButton({ label, onPress, compact = false, light = false }: { label: string; onPress: () => void; compact?: boolean; light?: boolean }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={[styles.primaryButton, compact && styles.primaryButtonCompact, light && styles.primaryButtonLight]}>
      <Text style={[styles.primaryButtonText, light && styles.primaryButtonTextLight]}>{label}</Text>
      <ArrowRight size={19} color={light ? '#14532D' : '#FFFFFF'} />
    </Pressable>
  );
}

function FieldVisual({ copy, desktop }: { copy: (typeof COPY)[Language]; desktop: boolean }) {
  return (
    <View style={[styles.fieldShell, desktop && styles.fieldShellDesktop]}>
      <View style={styles.fieldHeader}>
        <View><Text style={styles.fieldLabel}>{copy.scene}</Text><Text style={styles.fieldDate}>24 Aug · 8% cloud · 10 m</Text></View>
        <Satellite size={24} color="#BBF7D0" />
      </View>
      <View style={styles.fieldMap}>
        <View style={[styles.fieldPlot, styles.plotOne]}><View style={styles.fieldRows} /></View>
        <View style={[styles.fieldPlot, styles.plotTwo]}><View style={styles.fieldRows} /></View>
        <View style={[styles.fieldPlot, styles.plotThree]}><View style={styles.fieldRows} /></View>
        <View style={[styles.fieldPlot, styles.plotFour]}><View style={styles.fieldRows} /></View>
        <View style={styles.mapPin}><MapPin size={18} color="#7C2D12" /></View>
      </View>
      <View style={styles.signalRow}>
        <Signal label="NDVI" value="0.64" />
        <Signal label="NDMI" value="0.18" />
        <Signal label={copy.signal} value="Good" />
      </View>
      <View style={styles.priorityCard}>
        <View style={styles.priorityIcon}><Droplets size={22} color="#A16207" /></View>
        <View style={styles.priorityCopy}>
          <Text style={styles.priorityEyebrow}>{copy.priority}</Text>
          <Text style={styles.priorityTitle}>{copy.priorityTitle}</Text>
          <Text style={styles.priorityBody}>{copy.priorityBody}</Text>
        </View>
      </View>
    </View>
  );
}

function Signal({ label, value }: { label: string; value: string }) {
  return <View style={styles.signal}><Text style={styles.signalLabel}>{label}</Text><Text style={styles.signalValue}>{value}</Text></View>;
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: '#F8FAF5' },
  pageContent: { alignItems: 'center' },
  header: { minHeight: 84, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 20 },
  brand: { flexDirection: 'row', alignItems: 'center', gap: 10 }, logo: { width: 46, height: 46 }, brandName: { fontSize: 25, fontWeight: '800', color: '#14532D' },
  nav: { flexDirection: 'row', gap: 18 }, navButton: { minHeight: 44, paddingHorizontal: 6, alignItems: 'center', justifyContent: 'center' }, navText: { color: '#475569', fontSize: 15, fontWeight: '600' },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 10 }, languageButton: { minHeight: 44, paddingHorizontal: 14, borderWidth: 1, borderColor: '#BBF7D0', borderRadius: 999, flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#FFFFFF' }, languageText: { color: '#14532D', fontWeight: '700', fontSize: 15 },
  primaryButton: { minHeight: 52, paddingHorizontal: 22, borderRadius: 14, backgroundColor: '#15803D', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 }, primaryButtonCompact: { minHeight: 44, paddingHorizontal: 16 }, primaryButtonText: { color: '#FFFFFF', fontWeight: '800', fontSize: 16 }, primaryButtonLight: { backgroundColor: '#FFFFFF' }, primaryButtonTextLight: { color: '#14532D' },
  pressed: { opacity: 0.72 },
  hero: { paddingTop: 60, paddingBottom: 96, gap: 48 }, heroDesktop: { flexDirection: 'row', alignItems: 'center', gap: 72 }, heroCopy: { flex: 1 }, heroCopyDesktop: { maxWidth: 570 }, eyebrow: { color: '#A16207', fontSize: 13, fontWeight: '800', letterSpacing: 1.2, marginBottom: 16 }, heroTitle: { color: '#14532D', fontSize: 58, lineHeight: 64, fontWeight: '900', letterSpacing: -2 }, tamilHeroTitle: { fontSize: 48, lineHeight: 64 }, heroLead: { color: '#475569', fontSize: 20, lineHeight: 32, marginTop: 22, maxWidth: 620 }, heroActions: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginTop: 30 }, secondaryButton: { minHeight: 52, paddingHorizontal: 20, borderRadius: 14, borderWidth: 1, borderColor: '#86A98F', backgroundColor: '#FFFFFF', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 }, secondaryButtonText: { color: '#14532D', fontWeight: '800', fontSize: 16 }, safetyLine: { marginTop: 24, flexDirection: 'row', alignItems: 'flex-start', gap: 10, maxWidth: 560 }, safetyText: { flex: 1, color: '#64748B', fontSize: 14, lineHeight: 21 },
  fieldShell: { flex: 1, minWidth: 0, backgroundColor: '#123F2A', borderRadius: 28, padding: 18, shadowColor: '#14532D', shadowOpacity: 0.18, shadowRadius: 30, shadowOffset: { width: 0, height: 18 } }, fieldShellDesktop: { maxWidth: 520 }, fieldHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 4, marginBottom: 14 }, fieldLabel: { color: '#FFFFFF', fontWeight: '800', fontSize: 16 }, fieldDate: { color: '#BBF7D0', fontSize: 12, marginTop: 3 }, fieldMap: { height: 250, backgroundColor: '#DFEAD7', borderRadius: 19, padding: 12, flexDirection: 'row', flexWrap: 'wrap', gap: 8, overflow: 'hidden' }, fieldPlot: { width: '48%', height: '47%', borderRadius: 38, overflow: 'hidden', borderWidth: 2, borderColor: 'rgba(255,255,255,0.55)' }, plotOne: { backgroundColor: '#76A968', transform: [{ rotate: '-4deg' }] }, plotTwo: { backgroundColor: '#9BC47D', transform: [{ rotate: '3deg' }] }, plotThree: { backgroundColor: '#D5B96F', transform: [{ rotate: '2deg' }] }, plotFour: { backgroundColor: '#548F57', transform: [{ rotate: '-3deg' }] }, fieldRows: { flex: 1, opacity: 0.34, borderWidth: 12, borderColor: 'rgba(255,255,255,0.38)', borderRadius: 34 }, mapPin: { position: 'absolute', left: '22%', top: '56%', width: 34, height: 34, borderRadius: 17, backgroundColor: '#FEF3C7', alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: '#FFFFFF' }, signalRow: { flexDirection: 'row', gap: 8, marginTop: 12 }, signal: { flex: 1, backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 12, padding: 10 }, signalLabel: { color: '#BBF7D0', fontSize: 10, fontWeight: '700' }, signalValue: { color: '#FFFFFF', fontWeight: '900', fontSize: 18, marginTop: 2 }, priorityCard: { backgroundColor: '#FFF7DD', borderRadius: 18, padding: 14, marginTop: 12, flexDirection: 'row', gap: 12 }, priorityIcon: { width: 42, height: 42, borderRadius: 12, backgroundColor: '#FEF3C7', alignItems: 'center', justifyContent: 'center' }, priorityCopy: { flex: 1 }, priorityEyebrow: { color: '#A16207', fontWeight: '800', fontSize: 11, textTransform: 'uppercase' }, priorityTitle: { color: '#14532D', fontWeight: '800', fontSize: 15, marginTop: 3 }, priorityBody: { color: '#475569', fontSize: 12, lineHeight: 18, marginTop: 3 },
  section: { paddingVertical: 96 }, sectionTitle: { color: '#14532D', fontSize: 40, lineHeight: 48, fontWeight: '900', letterSpacing: -1 }, sectionLead: { color: '#64748B', fontSize: 18, lineHeight: 29, marginTop: 14, maxWidth: 760 }, workflowRow: { flexDirection: 'row', gap: 22, marginTop: 46 }, workflowStack: { flexDirection: 'column' }, workflowItem: { flex: 1, borderTopWidth: 3, borderTopColor: '#22C55E', paddingTop: 16 }, workflowNumber: { color: '#A16207', fontWeight: '900', fontSize: 13 }, workflowTitle: { color: '#14532D', fontSize: 24, fontWeight: '900', marginTop: 8 }, workflowBody: { color: '#64748B', fontSize: 15, lineHeight: 23, marginTop: 7 }, featureGrid: { marginTop: 48, gap: 14 }, featureGridWide: { flexDirection: 'row', flexWrap: 'wrap' }, featureCard: { backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#D7E4D8', borderRadius: 20, padding: 22 }, featureCardWide: { width: '48.8%' }, iconTile: { width: 48, height: 48, borderRadius: 15, backgroundColor: '#F0FDF4', alignItems: 'center', justifyContent: 'center' }, featureTitle: { color: '#14532D', fontWeight: '900', fontSize: 20, marginTop: 18 }, featureBody: { color: '#64748B', fontSize: 15, lineHeight: 23, marginTop: 8 },
  band: { width: '100%', backgroundColor: '#123F2A', alignItems: 'center' }, bandInner: { paddingVertical: 84, gap: 42 }, bandDesktop: { flexDirection: 'row', gap: 88 }, bandCopy: { flex: 1 }, eyebrowLight: { color: '#FBBF24', fontSize: 13, fontWeight: '800', letterSpacing: 1.2, marginBottom: 14 }, bandTitle: { color: '#FFFFFF', fontSize: 39, lineHeight: 48, fontWeight: '900' }, stepList: { flex: 1.15, gap: 16 }, stepItem: { flexDirection: 'row', gap: 16, backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 18, padding: 18 }, stepNumber: { width: 38, height: 38, borderRadius: 19, backgroundColor: '#22C55E', alignItems: 'center', justifyContent: 'center' }, stepNumberText: { color: '#052E16', fontWeight: '900' }, stepCopy: { flex: 1 }, stepTitle: { color: '#FFFFFF', fontSize: 18, fontWeight: '800' }, stepBody: { color: '#D1FAE5', lineHeight: 22, marginTop: 5 },
  splitSection: { flexDirection: 'row', alignItems: 'center', gap: 80 }, languageVisual: { flex: 1, minHeight: 350, justifyContent: 'center' }, languageCardBack: { position: 'absolute', left: 34, right: 0, top: 36, bottom: 16, backgroundColor: '#DDF7E3', borderRadius: 26, transform: [{ rotate: '4deg' }] }, languageCardFront: { backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#BBF7D0', borderRadius: 26, padding: 34, marginRight: 24, shadowColor: '#14532D', shadowOpacity: 0.1, shadowRadius: 20, shadowOffset: { width: 0, height: 12 } }, languageCardTamil: { color: '#14532D', fontSize: 42, fontWeight: '900' }, languageCardEnglish: { color: '#A16207', fontSize: 22, fontWeight: '800', marginTop: 8 }, contextPill: { alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 34, backgroundColor: '#F0FDF4', borderRadius: 999, paddingHorizontal: 14, paddingVertical: 9 }, contextText: { color: '#14532D', fontWeight: '700' }, splitCopy: { flex: 1 }, checkRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginTop: 15 }, checkText: { flex: 1, color: '#475569', fontSize: 15, lineHeight: 22 },
  trustCard: { backgroundColor: '#FFF9E9', borderWidth: 1, borderColor: '#F5D98C', borderRadius: 28, padding: 30, marginVertical: 30, gap: 22 }, trustDesktop: { flexDirection: 'row', padding: 48, gap: 32 }, trustIcon: { width: 70, height: 70, borderRadius: 22, backgroundColor: '#FEF3C7', alignItems: 'center', justifyContent: 'center' }, trustCopy: { flex: 1 }, trustItems: { marginTop: 8 }, trustItemsWide: { flexDirection: 'row', flexWrap: 'wrap', columnGap: 24 },
  finalCta: { backgroundColor: '#15803D', borderRadius: 30, paddingVertical: 66, paddingHorizontal: 26, alignItems: 'center', marginTop: 88 }, finalTitle: { color: '#FFFFFF', fontSize: 40, lineHeight: 48, fontWeight: '900', textAlign: 'center', marginTop: 18 }, finalBody: { color: '#D1FAE5', fontSize: 18, lineHeight: 28, textAlign: 'center', marginTop: 12, marginBottom: 26, maxWidth: 660 },
  footer: { paddingVertical: 48, alignItems: 'center' }, footerBrand: { color: '#14532D', fontWeight: '900', fontSize: 17, textAlign: 'center' }, footerDisclaimer: { color: '#64748B', fontSize: 13, lineHeight: 20, textAlign: 'center', maxWidth: 760, marginTop: 10 }, copyright: { color: '#94A3B8', fontSize: 12, marginTop: 18 },
});
