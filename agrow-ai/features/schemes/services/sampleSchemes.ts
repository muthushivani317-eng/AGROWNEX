/**
 * Verified sample schemes for the local / offline provider. These mirror the
 * backend ``CuratedSchemeProvider`` (backend/app/modules/schemes/curated_data.py)
 * -- same slugs, same structured eligibility rules, same real content -- so the
 * offline engine produces the same verdicts a farmer would see from the live
 * API. Each scheme was individually looked up on its own official government
 * page (or a corroborating PIB/state-government factsheet); nothing here is
 * fabricated (docs/PRODUCT_RULES.md rule 4). The local provider is only used
 * when no verified backend is configured.
 *
 * Kept in sync by hand with the backend list (2026-08 pre-release audit
 * follow-up: this file previously still had the old dev-mock schemes,
 * including one -- "tn-free-electricity" -- that was dropped from the real
 * backend data for lack of a solid official citation). If you add/change a
 * scheme in curated_data.py, mirror the change here too.
 */
import type { SchemeCategory, SchemeStatus } from '../types';
import type { SchemeRules } from './eligibility';

export interface LocalScheme {
  id: string;
  slug: string;
  title: string;
  category: SchemeCategory;
  description: string;
  benefits: string;
  eligibilitySummary: string;
  applicationSteps: string[];
  departments: string[];
  officialUrl: string;
  documents: { name: string; required: boolean }[];
  source: string;
  state: string;
  status: SchemeStatus;
  lastDate: string | null;
  verifiedAt: string;
  rules: SchemeRules;
}

const ANY = ['all'];

function openRules(overrides: Partial<SchemeRules> = {}): SchemeRules {
  return {
    states: ANY,
    districts: ANY,
    crops: ANY,
    farmerCategories: ANY,
    minLandHectares: null,
    maxLandHectares: null,
    maxAnnualIncome: null,
    status: 'active',
    ...overrides,
  };
}

// Matches curated_data.py's SOURCE_CURATED / LAST_VERIFIED_DATE.
const SOURCE_CURATED = 'curated_verified';
const VERIFIED_AT = '2026-08-16T00:00:00Z';

export const SAMPLE_SCHEMES: LocalScheme[] = [
  {
    id: 'local-pm-kisan',
    slug: 'pm-kisan',
    title: 'PM-KISAN Samman Nidhi',
    category: 'income_support',
    description:
      'Central Sector scheme providing direct income support to eligible landholding farmer families across India.',
    benefits:
      '₹6,000 per year, paid in three equal instalments of ₹2,000 directly to the farmer’s bank account (DBT).',
    eligibilitySummary:
      'Landholding farmer families (husband, wife and minor children). Not eligible: institutional landholders; holders of constitutional posts; serving or retired government officers/employees; pensioners earning ₹10,000+ per month; anyone who paid income tax in the last assessment year; and licensed professionals (doctors, engineers, lawyers, chartered accountants, architects).',
    applicationSteps: [
      'Register as a new farmer via pmkisan.gov.in or your nearest Common Service Centre (CSC).',
      'Provide Aadhaar, land ownership records and bank account details.',
      'Complete e-KYC (required to receive instalments).',
      "Check status anytime with 'Know Your Status' on the portal.",
    ],
    departments: ['Department of Agriculture & Farmers Welfare'],
    officialUrl: 'https://pmkisan.gov.in',
    documents: [
      { name: 'Aadhaar card', required: true },
      { name: 'Land ownership records', required: true },
      { name: 'Bank account passbook', required: true },
    ],
    source: SOURCE_CURATED,
    state: 'all',
    status: 'active',
    lastDate: null,
    verifiedAt: VERIFIED_AT,
    rules: openRules(),
  },
  {
    id: 'local-pmfby',
    slug: 'pmfby',
    title: 'Pradhan Mantri Fasal Bima Yojana (Crop Insurance)',
    category: 'insurance',
    description:
      'Government crop insurance covering yield and production losses from non-preventable natural risks (drought, flood, pest and disease attack, and more) from pre-sowing through post-harvest stages.',
    benefits:
      'Low, uniform-premium insurance cover for notified crops, with claims increasingly assessed using remote sensing, drones and geotagged photography rather than manual yield surveys alone.',
    eligibilitySummary:
      "All farmers growing a notified crop in a notified area, including tenant farmers and sharecroppers. Enrollment is voluntary for every farmer. Exact premium share and the enrollment window are set per season and state -- confirm current dates on pmfby.gov.in or with your bank/CSC before the cut-off.",
    applicationSteps: [
      "Apply through your bank, Common Service Centre, or the National Crop Insurance Portal (pmfby.gov.in) before your state's notified cut-off date for the season.",
      'Submit land records/tenancy proof and sowing details.',
      'Loanee farmers with a crop loan are enrolled by their bank unless they opt out in writing; non-loanee farmers enroll directly.',
    ],
    departments: ['Ministry of Agriculture & Farmers Welfare'],
    officialUrl: 'https://pmfby.gov.in',
    documents: [
      { name: 'Aadhaar card', required: true },
      { name: 'Land records / tenancy proof', required: true },
      { name: 'Bank account passbook', required: true },
      { name: 'Sowing certificate', required: false },
    ],
    source: SOURCE_CURATED,
    state: 'all',
    status: 'active',
    lastDate: null,
    verifiedAt: VERIFIED_AT,
    rules: openRules(),
  },
  {
    id: 'local-rwbcis',
    slug: 'rwbcis',
    title: 'Restructured Weather Based Crop Insurance Scheme (RWBCIS)',
    category: 'insurance',
    description:
      'Insurance payout triggered by adverse weather (rainfall, temperature, humidity, etc.) measured at a Reference Weather Station, rather than by a manually assessed crop yield loss -- runs alongside PMFBY as a weather-index option in notified areas.',
    benefits:
      'Faster claim settlement based on weather-station data instead of field-by-field yield assessment.',
    eligibilitySummary:
      'Farmers growing a notified crop in a notified area covered by a Reference Weather Station. Same enrollment channel as PMFBY.',
    applicationSteps: [
      'Apply through your bank, Common Service Centre, or the National Crop Insurance Portal (pmfby.gov.in) -- same portal as PMFBY.',
      'Submit land and sowing details before the notified cut-off date.',
    ],
    departments: ['Ministry of Agriculture & Farmers Welfare'],
    officialUrl: 'https://pmfby.gov.in',
    documents: [
      { name: 'Aadhaar card', required: true },
      { name: 'Land records / tenancy proof', required: true },
      { name: 'Bank account passbook', required: true },
    ],
    source: SOURCE_CURATED,
    state: 'all',
    status: 'active',
    lastDate: null,
    verifiedAt: VERIFIED_AT,
    rules: openRules(),
  },
  {
    id: 'local-kcc',
    slug: 'kcc',
    title: 'Kisan Credit Card (KCC)',
    category: 'loan',
    description:
      'Short-term credit from the banking system for cultivation, post-harvest expenses and farm investment needs, at a concessional interest rate.',
    benefits:
      "Short-term crop loans up to ₹3 lakh benefit from the Government's Interest Subvention Scheme. Marginal farmers can get a simplified 'Flexi KCC' of ₹10,000-₹50,000 without land valuation; other farmers' limits are based on cultivated area and the district's crop scale of finance.",
    eligibilitySummary:
      'Individual or joint owner-cultivators, tenant farmers, oral lessees and sharecroppers, plus Self Help Groups and Joint Liability Groups of farmers.',
    applicationSteps: [
      'Visit your bank branch (or a Common Service Centre) with a simple one-page KCC application form, available from the bank or agriculture ministry websites.',
      'Submit a copy of your land records and details of crops sown.',
      'Bank verifies and issues the card/limit.',
    ],
    departments: ['Department of Financial Services'],
    officialUrl: 'https://www.myscheme.gov.in/schemes/kcc',
    documents: [
      { name: 'Identity proof (Aadhaar/Voter ID)', required: true },
      { name: 'Land ownership documents', required: true },
      { name: 'Passport-size photograph', required: true },
    ],
    source: SOURCE_CURATED,
    state: 'all',
    status: 'active',
    lastDate: null,
    verifiedAt: VERIFIED_AT,
    rules: openRules(),
  },
  {
    id: 'local-soil-health-card',
    slug: 'soil-health-card',
    title: 'Soil Health Card Scheme',
    category: 'other',
    description:
      'Free soil testing that gives farmers a report on 12 soil parameters (N, P, K, sulphur; zinc, iron, copper, manganese, boron; pH, EC and organic carbon) with crop-wise fertilizer-dosage recommendations. Implemented since 2022-23 under the Rashtriya Krishi Vikas Yojana.',
    benefits:
      'A soil health card, renewed roughly every farming cycle, with tailored nutrient/fertilizer guidance to improve soil health and yield.',
    eligibilitySummary: 'All farmers with cultivable land.',
    applicationSteps: [
      'Register with your local agriculture office / village-level Soil Testing Lab.',
      'Provide a soil sample from your field (typically collected twice a year or when the field is fallow).',
      'Collect your Soil Health Card, or check it on the mobile app.',
    ],
    departments: ['Department of Agriculture & Farmers Welfare'],
    officialUrl: 'https://soilhealth.dac.gov.in',
    documents: [
      { name: 'Land records', required: true },
      { name: 'Aadhaar card', required: true },
    ],
    source: SOURCE_CURATED,
    state: 'all',
    status: 'active',
    lastDate: null,
    verifiedAt: VERIFIED_AT,
    rules: openRules(),
  },
  {
    id: 'local-pm-kusum',
    slug: 'pm-kusum',
    title: 'PM-KUSUM Solar Pump Subsidy',
    category: 'irrigation',
    description:
      'Subsidy scheme to replace diesel irrigation pumps with solar pumps (Component B) and to solarise existing grid-connected pumps (Component C), reducing diesel dependence and giving farmers reliable daytime power for irrigation.',
    benefits:
      'For individual off-grid solar pumps (Component B): Central Financial Assistance of 30% of the benchmark cost plus a further 30% state subsidy -- the farmer pays about 40% (higher Central assistance of 50% applies in North-Eastern and hilly states). Feeder solarisation (Component C) is subsidised at 30% (50% in special-category regions).',
    eligibilitySummary: 'Farmers with cultivable land needing an irrigation pump.',
    applicationSteps: [
      "For an individual pump: apply through your state's renewable energy implementing agency.",
      'Submit land records and details of your existing pump/electrical connection, if any.',
    ],
    departments: ['Ministry of New and Renewable Energy'],
    officialUrl: 'https://pmkusum.mnre.gov.in',
    documents: [
      { name: 'Land records', required: true },
      { name: 'Aadhaar card', required: true },
      { name: 'Bank account passbook', required: true },
    ],
    source: SOURCE_CURATED,
    state: 'all',
    status: 'active',
    lastDate: null,
    verifiedAt: VERIFIED_AT,
    rules: openRules(),
  },
  {
    id: 'local-pkvy',
    slug: 'pkvy',
    title: 'Paramparagat Krishi Vikas Yojana (PKVY)',
    category: 'organic_farming',
    description:
      'Cluster-based support for farmer groups transitioning to organic, chemical-free farming, covering inputs, certification and market linkage over three years.',
    benefits:
      '₹31,500 per hectare over 3 years, paid via bank transfer: ₹15,000 for organic inputs, ₹4,500 for marketing/packaging/branding/value addition, ₹3,000 for certification and residue testing, and ₹9,000 for training.',
    eligibilitySummary:
      'Farmers willing to join an organic-farming cluster in their area (the scheme is cluster-based, not an individual application).',
    applicationSteps: [
      'Approach your Regional Council or district agriculture office to join (or help form) an organic cluster.',
      'Enroll for PGS-India (Participatory Guarantee System) organic certification at pgsindia-ncof.gov.in.',
    ],
    departments: ['Ministry of Agriculture & Farmers Welfare'],
    officialUrl: 'https://pgsindia-ncof.gov.in',
    documents: [
      { name: 'Aadhaar card', required: true },
      { name: 'Land records', required: true },
    ],
    source: SOURCE_CURATED,
    state: 'all',
    status: 'active',
    lastDate: null,
    verifiedAt: VERIFIED_AT,
    rules: openRules(),
  },
  {
    id: 'local-nfsm',
    slug: 'nfsm',
    title: 'National Food Security Mission (NFSM)',
    category: 'seeds',
    description:
      'Central mission to raise production and productivity of rice, wheat, pulses and coarse cereals in a sustainable way, implemented through the states.',
    benefits:
      'Assistance for certified seed of newly released varieties/hybrids, crop demonstrations, integrated pest management training, and other production-technology incentives -- exact assistance amounts are set by each state’s action plan.',
    eligibilitySummary:
      "Farmers growing rice, wheat, pulses or coarse cereals in a district covered by the state's NFSM action plan.",
    applicationSteps: [
      'Register with your district agriculture office.',
      'Collect certified seed / inputs from the notified distribution centre for your area.',
    ],
    departments: ['Department of Agriculture & Farmers Welfare'],
    officialUrl: 'https://www.nfsm.gov.in',
    documents: [
      { name: 'Land records', required: true },
      { name: 'Aadhaar card', required: true },
    ],
    source: SOURCE_CURATED,
    state: 'all',
    status: 'active',
    lastDate: null,
    verifiedAt: VERIFIED_AT,
    rules: openRules(),
  },
  {
    id: 'local-tn-farm-mechanization',
    slug: 'tn-farm-mechanization',
    title: 'Sub-Mission on Agricultural Mechanisation (Tamil Nadu)',
    category: 'equipment',
    description:
      'Subsidy on farm machinery -- tractors, rotavators, power tillers (8 BHP+), paddy transplanters, power weeders and similar implements -- to bring mechanization to small and marginal farmers in Tamil Nadu.',
    benefits:
      '50% subsidy for SC/ST, small, marginal and women farmers; 40% for other farmers (funded 60% by the Union Government and 40% by the Tamil Nadu Government).',
    eligibilitySummary: 'All Tamil Nadu farmers, in all districts except Chennai.',
    applicationSteps: [
      'Contact the Assistant Executive Engineer (Agricultural Engineering Department) in your project district.',
      'Submit land records and bank details for verification.',
    ],
    departments: ['Agricultural Engineering Department, Government of Tamil Nadu'],
    officialUrl:
      'https://aed.tn.gov.in/en/schemes/agricultural-mechanisation/sub-mission-on-agricultural-mechanisation/',
    documents: [
      { name: 'Aadhaar card', required: true },
      { name: 'Land records', required: true },
      { name: 'Bank account passbook', required: true },
    ],
    source: SOURCE_CURATED,
    state: 'Tamil Nadu',
    status: 'active',
    lastDate: null,
    verifiedAt: VERIFIED_AT,
    rules: openRules({ states: ['Tamil Nadu'] }),
  },
  {
    id: 'local-tn-drip-subsidy',
    slug: 'tn-drip-subsidy',
    title: 'Tamil Nadu Micro Irrigation (Drip) Subsidy',
    category: 'irrigation',
    description:
      "Subsidy on drip/sprinkler micro-irrigation systems for Tamil Nadu farmers under PMKSY's Per Drop More Crop component, to improve water-use efficiency.",
    benefits:
      '100% subsidy for small and marginal farmers, 75% for other farmers, for up to 5 hectares.',
    eligibilitySummary: 'Tamil Nadu farmers, for holdings up to 5 hectares.',
    applicationSteps: [
      "Register on TNHORTNET and apply through the Horticulture Department's Micro Irrigation (MIMIS) portal.",
      'Submit land records (Chitta and Adangal), an FMB sketch, water source and soil-test details, and bank passbook copy.',
      'Field inspection by the local Horticulture Officer before installation.',
    ],
    departments: ['Horticulture and Plantation Crops Department, Government of Tamil Nadu'],
    officialUrl: 'https://tnhorticulture.tn.gov.in',
    documents: [
      { name: 'Land records (Chitta and Adangal)', required: true },
      { name: 'Aadhaar card', required: true },
      { name: 'Water source proof', required: true },
      { name: 'Bank account passbook', required: true },
    ],
    source: SOURCE_CURATED,
    state: 'Tamil Nadu',
    status: 'active',
    lastDate: null,
    verifiedAt: VERIFIED_AT,
    rules: openRules({
      states: ['Tamil Nadu'],
      maxLandHectares: 5.0,
    }),
  },
  {
    id: 'local-tn-farmers-security-scheme',
    slug: 'tn-farmers-security-scheme',
    title: "Chief Minister's Uzhavar Pathukappu Thittam (Farmers' Security Scheme)",
    category: 'other',
    description:
      'Tamil Nadu welfare scheme (since September 2011) providing financial assistance to registered small/marginal farmers and agricultural labourers, and their dependents, covering accidents, old age, illness and death.',
    benefits:
      'For the member: old-age pension (₹1,000/month), accident relief (₹20,000-₹1,00,000 depending on severity), natural death assistance (₹20,000), funeral expenses (₹2,500), monthly support during serious illness (₹1,000), and marriage assistance (₹8,000-₹10,000). Dependents (non-earning spouse, children, parents) are covered for marriage assistance, educational grants, orphan support and funeral expenses.',
    eligibilitySummary:
      'Small or marginal farmers, or agricultural labourers, aged 18-65, engaged in farming, horticulture, sericulture, dairy, poultry or inland fishing.',
    applicationSteps: [
      'Register with your Village Administrative Officer / Taluk Office under the Revenue Administration Department.',
      'File a claim through the same office when an eligible event (accident, illness, death, marriage) occurs.',
    ],
    departments: [
      'Revenue Administration and Disaster Management Department, Government of Tamil Nadu',
    ],
    officialUrl: 'https://landreforms.tn.gov.in/UPT.html',
    documents: [
      { name: 'Aadhaar card', required: true },
      { name: 'Land records / labourer registration', required: true },
    ],
    source: SOURCE_CURATED,
    state: 'Tamil Nadu',
    status: 'active',
    lastDate: null,
    verifiedAt: VERIFIED_AT,
    rules: openRules({
      states: ['Tamil Nadu'],
      farmerCategories: ['marginal', 'small'],
    }),
  },
];
