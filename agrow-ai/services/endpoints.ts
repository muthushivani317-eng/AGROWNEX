/**
 * Central registry of backend endpoints (relative to `/api/v1`), mirroring
 * docs/API_CONTRACT.md. Feature services reference these instead of hardcoding
 * paths, so a contract change is a one-line edit.
 */
export const endpoints = {
  auth: {
    // No "login" key: this app's only login paths are OTP/Google/Apple below
    // (Firebase-verified, no password flow) -- a stale "/auth/login" entry
    // here pointed at a backend route that was never built. Nothing called
    // it, so it was harmless today, but it was a landmine for whoever wired
    // up a call expecting it to work (2026-08 pre-release audit).
    logout: "/auth/logout",
    refresh: "/auth/refresh",
    google: "/auth/google",
    apple: "/auth/apple",
    otpSend: "/auth/otp/send",
    otpVerify: "/auth/otp/verify",
    profile: "/auth/profile",
    account: "/auth/account",
  },
  farmers: {
    me: "/farmers/me",
    farmCatalog: "/farm-catalog",
    preferences: "/farmers/preferences",
    languages: "/farmers/languages",
  },
  farms: {
    root: "/farms",
    byId: (id: string) => `/farms/${id}`,
    boundary: (id: string) => `/farms/${id}/boundary`,
    images: (id: string) => `/farms/${id}/images`,
    media: (id: string) => `/farms/${id}/media`,
    team: (id: string) => `/farms/${id}/team-controlled`,
    teamMember: (id: string, memberId: string) =>
      `/farms/${id}/team-controlled/${memberId}`,
  },
  organic: {
    profile: (farmId: string) => `/farms/${farmId}/organic-profile`,
    practices: "/organic-logbook/entries",
    plan: (farmId: string) => `/farms/${farmId}/organic-plan`,
    inputs: "/organic-inputs",
    uploads: (farmId: string) => `/farms/${farmId}/organic-uploads`,
  },
  // organic-mvp is the separate readiness/PGS backend (see
  // backend/app/modules/organic_mvp) -- its routes return the raw payload
  // directly, not the { success, data } envelope the rest of the API uses,
  // so callers use httpClient directly (see organicReadinessApi.ts), same
  // pattern as cropRecommendation.predict below.
  organicMvp: {
    readinessQuestions: "/organic-mvp/readiness/questions",
    readiness: (farmId: string) => `/organic-mvp/farms/${farmId}/readiness`,
    plots: (farmId: string) => `/organic-mvp/farms/${farmId}/plots`,
    cropCycles: (plotId: string) => `/organic-mvp/plots/${plotId}/crop-cycles`,
    cropCycle: (cycleId: string) => `/organic-mvp/crop-cycles/${cycleId}`,
    cropCyclePlan: (cycleId: string) => `/organic-mvp/crop-cycles/${cycleId}/plan`,
    todayTask: (farmId: string) => `/organic-mvp/farms/${farmId}/today-task`,
    completeTask: (taskId: string) => `/organic-mvp/scheduled-tasks/${taskId}/complete`,
    pgsStatus: (farmId: string) => `/organic-mvp/farms/${farmId}/pgs`,
    pgsChecklist: (farmId: string) => `/organic-mvp/farms/${farmId}/pgs/checklist`,
    pgsPeerAssignments: "/organic-mvp/pgs/peer-assignments",
    pgsPeerAssignmentSubmit: (appraisalId: string) =>
      `/organic-mvp/pgs/peer-assignments/${appraisalId}/submit`,
  },
  // Backend routes live under /organic-partner (built first for the organic
  // certification pilot) but the mechanism is generic — any FPO/KVK/community
  // organization requesting read access to a farmer, with that farmer's
  // consent. See backend/app/modules/organic_mvp/partner_router.py.
  partnerLinks: {
    myRequests: "/organic-partner/my-link-requests",
    directory: "/organic-partner/directory",
    join: (organizationId: string) =>
      `/organic-partner/organizations/${organizationId}/join`,
    approve: (linkId: string) =>
      `/organic-partner/my-link-requests/${linkId}/approve`,
    revoke: (linkId: string) =>
      `/organic-partner/my-link-requests/${linkId}/revoke`,
  },
  weather: {
    bundle: "/weather",
    current: "/weather/current",
    forecast: "/weather/forecast",
    alerts: "/weather/alerts",
  },
  ai: {
    chat: "/ai/chat",
    history: "/ai/history",
    historyById: (id: string) => `/ai/history/${id}`,
  },
  disease: {
    history: "/disease/history",
    byId: (id: string) => `/disease/${id}`,
    predict: "/disease/predict",
    groundnutExperimental: "/doctor/groundnut/predict",
    groundnutSymptoms: "/doctor/groundnut/symptoms",
    groundnutTranscribe: "/doctor/groundnut/transcribe",
    groundnutMapTranscript: "/doctor/groundnut/symptoms/map-transcript",
    groundnutPestObservations: "/doctor/groundnut/pest-observations",
    greenGramExperimental: "/doctor/green-gram/predict",
  },
  calendar: {
    root: "/calendar",
    generate: "/calendar/generate",
    today: "/calendar/today",
    upcoming: "/calendar/upcoming",
    completed: "/calendar/completed",
    missed: "/calendar/missed",
    summary: "/calendar/summary",
    byFarm: (farmId: string) => `/calendar/${farmId}`,
    event: (id: string) => `/calendar/events/${id}`,
  },
  growth: {
    upload: "/growth/upload",
    history: "/growth/history",
    timeline: "/growth/timeline",
    latest: "/growth/latest",
    session: (id: string) => `/growth/session/${id}`,
    image: (id: string) => `/growth/image/${id}`,
    stage: "/growth/stage",
    scheduleStatus: "/growth/schedule-status",
    stageTransition: "/growth/stage/transition",
    stageHistory: (id: string) => `/growth/stage/${id}/history`,
    groundnutStageConfirmation: (id: string) =>
      `/growth/groundnut/session/${id}/stage-confirmation`,
  },
  market: {
    root: "/market",
    today: "/market/today",
    history: "/market/history",
    search: "/market/search",
    favourites: "/market/favourites",
    favourite: (id: string) => `/market/favourites/${id}`,
  },
  schemes: {
    root: "/schemes",
    byId: (id: string) => `/schemes/${id}`,
    eligible: "/schemes/eligible",
    recommended: "/schemes/recommended",
    bookmarks: "/schemes/bookmarks",
    bookmark: (id: string) => `/schemes/bookmarks/${id}`,
    myDocuments: "/schemes/my-documents",
    myDocument: (type: string) => `/schemes/my-documents/${type}`,
  },
  produce: {
    root: "/produce",
    byId: (id: string) => `/produce/${id}`,
    buyerOffer: (id: string) => `/produce/${id}/buyer-offer`,
    buyerOfferDecision: (id: string) => `/produce/${id}/buyer-offer/decision`,
    images: (id: string) => `/produce/${id}/images`,
    upcoming: "/produce/upcoming",
    history: "/produce/history",
    traceability: (id: string) => `/produce/${id}/traceability-controlled`,
    traceabilityInitialize: (id: string) =>
      `/produce/${id}/traceability-controlled/initialize`,
    traceabilityEvents: (id: string) =>
      `/produce/${id}/traceability-controlled/events`,
    traceabilityPublicShare: (id: string) =>
      `/produce/${id}/traceability-controlled/share`,
    traceabilityPublicShareRevoke: (id: string) =>
      `/produce/${id}/traceability-controlled/share/revoke`,
  },
  harvestReadiness: {
    evaluate: "/harvest-readiness/evaluate",
    current: "/harvest-readiness/current",
    history: (id: string) => `/harvest-readiness/${id}/history`,
    confirm: "/harvest-readiness/confirm",
  },
  actionVerification: {
    actions: "/action-verification/actions",
    detail: (id: string) => `/action-verification/actions/${id}`,
    respond: (id: string) => `/action-verification/actions/${id}/responses`,
    history: (id: string) => `/action-verification/actions/${id}/history`,
  },
  tasks: {
    today: "/tasks/today",
    history: "/tasks/history",
    byId: (id: string) => `/tasks/${id}`,
    advanced: (id: string) => `/tasks/${id}/advanced`,
    respond: (id: string) => `/tasks/${id}/respond`,
    snooze: (id: string) => `/tasks/${id}/snooze`,
    photo: (id: string) => `/tasks/${id}/photo`,
    voiceNote: (id: string) => `/tasks/${id}/voice-note`,
  },
  evidencePacks: {
    root: "/evidence-packs",
    byId: (id: string) => `/evidence-packs/${id}`,
    share: (id: string) => `/evidence-packs/${id}/share`,
  },
  notifications: {
    root: "/notifications",
    unread: "/notifications/unread",
    byId: (id: string) => `/notifications/${id}`,
    read: (id: string) => `/notifications/${id}/read`,
    readAll: "/notifications/read-all",
    preferences: "/notifications/preferences",
  },
  support: {
    tickets: "/support/tickets",
    byId: (id: string) => `/support/tickets/${id}`,
    messages: (id: string) => `/support/tickets/${id}/messages`,
  },
  experts: {
    root: "/experts",
    byId: (id: string) => `/experts/${id}`,
  },
  consultations: {
    root: "/consultations",
    byId: (id: string) => `/consultations/${id}`,
    reply: (id: string) => `/consultations/${id}/reply`,
    attachments: (id: string) => `/consultations/${id}/attachments`,
    statusOf: (id: string) => `/consultations/${id}/status`,
    pending: "/consultations/pending",
    history: "/consultations/history",
  },
  soil: {
    root: "/soil",
    latest: "/soil/latest",
    history: "/soil/history",
    recommendation: "/soil/recommendation",
    report: "/soil/report",
    remote: "/soil/remote",
    scan: "/soil/scan",
    scanLatest: "/soil/scan/latest",
    scanHistory: "/soil/scan/history",
    scanDetail: (id: string) => `/soil/scan/${id}`,
  },
  satellite: {
    root: "/satellite",
    readiness: "/satellite/readiness",
    latest: "/satellite/latest",
    history: "/satellite/history",
    timeline: "/satellite/timeline",
    indices: "/satellite/indices",
    alerts: "/satellite/alerts",
    refresh: "/satellite/refresh",
    imageRepair: "/satellite/images/repair",
    waterlogging: "/satellite/waterlogging",
    waterloggingRefresh: "/satellite/waterlogging/refresh",
    waterloggingHistory: "/satellite/waterlogging/history",
  },
  nutrient: {
    analyze: "/nutrient/analyze",
    history: "/nutrient/history",
    latest: "/nutrient/latest",
    recommendations: "/nutrient/recommendations",
    report: (id: string) => `/nutrient/report/${id}`,
  },
  lcc: {
    analyze: "/lcc/analyze",
  },
  inputs: {
    catalog: "/inputs/catalog",
    orders: "/inputs/orders",
  },
  cropRecommendation: {
    predict: "/crop-recommendation-controlled/predict",
    health: "/crop-recommendation-controlled/health",
  },
  equipment: {
    root: "/equipment-controlled",
    requests: (id: string) => `/equipment-controlled/${id}/requests`,
    mine: "/equipment-controlled/requests/mine",
    decision: (id: string) => `/equipment-controlled/requests/${id}/decision`,
  },
  community: {
    root: "/community-controlled",
    byId: (id: string) => `/community-controlled/${id}`,
    answers: (id: string) => `/community-controlled/${id}/answers`,
    reports: "/community-controlled/reports",
  },
  intelligence: {
    root: "/intelligence",
    latest: "/intelligence/latest",
    history: "/intelligence/history",
    refresh: "/intelligence/refresh",
    report: (id: string) => `/intelligence/report/${id}`,
  },
  memory: {
    root: "/memory",
    latest: "/memory/latest",
    history: "/memory/history",
    summary: "/memory/summary",
    rebuild: "/memory/rebuild",
    byId: (id: string) => `/memory/${id}`,
  },
  admin: {
    me: "/admin/me",
    dashboard: "/admin/dashboard",
    businessDashboard: "/admin/business-dashboard",
    farmers: "/admin/farmers",
    farmer: (id: string) => `/admin/farmers/${id}`,
    analytics: "/admin/analytics",
    cropIntelligence: "/admin/crop-intelligence",
    procurement: "/admin/procurement",
    procurementStatus: (offerId: string) =>
      `/admin/procurement/${offerId}/status`,
    procurementCase: (offerId: string) => `/admin/procurement/${offerId}/case`,
    procurementBuyerContact: (offerId: string) =>
      `/admin/procurement/${offerId}/buyer-contact/reveal`,
    procurementLedger: (offerId: string) =>
      `/admin/procurement/${offerId}/ledger`,
    procurementPickup: (offerId: string) =>
      `/admin/procurement/${offerId}/pickup`,
    procurementTransaction: (offerId: string) =>
      `/admin/procurement/${offerId}/transaction`,
    procurementPayment: (transactionId: string) =>
      `/admin/procurement/transactions/${transactionId}/payments`,
    procurementCommission: (transactionId: string) =>
      `/admin/procurement/transactions/${transactionId}/commissions`,
    ai: "/admin/ai",
    notifications: "/admin/notifications",
    broadcast: "/admin/broadcast",
    announcements: "/admin/announcements",
    audit: "/admin/audit",
  },
} as const;
