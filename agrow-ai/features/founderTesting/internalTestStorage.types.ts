export const INTERNAL_TEST_SCHEMA_VERSION = 1;
export const INTERNAL_TEST_DATA_LABEL = 'INTERNAL TEST DATA';
export type FounderSession = { sessionId: string; startedAt: string; endedAt?: string; language: 'ta' | 'en'; mode: 'local_ui_only'; label: typeof INTERNAL_TEST_DATA_LABEL };
export type InternalTestLog = { timestamp: string; sessionId: string; featureId: string; action: string; result: 'PASS' | 'FAIL' | 'BLOCKED'; errorCode?: string; note?: string };
