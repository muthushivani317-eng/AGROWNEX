import * as SQLite from 'expo-sqlite';

import { logger } from './logger';

/**
 * Local SQLite database (docs/FRONTEND_ARCHITECTURE.md → Offline Database).
 *
 * Phase 1 provisions the schema for the offline outbox that powers the offline
 * strategy (queue requests while offline → auto-sync when back online). Feature
 * phases add their own cached tables through additive migrations here.
 */
const DB_NAME = 'agrowai.db';
const SCHEMA_VERSION = 1;

let dbPromise: Promise<SQLite.SQLiteDatabase> | null = null;

async function migrate(db: SQLite.SQLiteDatabase): Promise<void> {
  await db.execAsync(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS offline_mutations (
      id           TEXT PRIMARY KEY NOT NULL,
      endpoint     TEXT NOT NULL,
      method       TEXT NOT NULL,
      payload      TEXT,
      entity_type  TEXT,
      created_at   INTEGER NOT NULL,
      retry_count  INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS meta (
      key   TEXT PRIMARY KEY NOT NULL,
      value TEXT
    );
  `);
  await db.runAsync(
    'INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)',
    'schema_version',
    String(SCHEMA_VERSION),
  );
}

/** Open (once) and return the shared database handle. */
export function getDatabase(): Promise<SQLite.SQLiteDatabase> {
  if (!dbPromise) {
    dbPromise = SQLite.openDatabaseAsync(DB_NAME)
      .then(async (db) => {
        await migrate(db);
        logger.info('db', `SQLite ready (schema v${SCHEMA_VERSION})`);
        return db;
      })
      .catch((e) => {
        logger.error('db.open', e);
        dbPromise = null;
        throw e;
      });
  }
  return dbPromise;
}

/** Ensure the database is initialised during app bootstrap. */
export async function initDatabase(): Promise<void> {
  await getDatabase();
}

export interface OfflineMutation {
  id: string;
  endpoint: string;
  method: string;
  payload: string | null;
  entity_type: string | null;
  created_at: number;
  retry_count: number;
}

/** Minimal repository for the offline outbox. */
export const offlineQueue = {
  async enqueue(input: {
    id: string;
    endpoint: string;
    method: string;
    payload?: unknown;
    entityType?: string;
  }): Promise<void> {
    const db = await getDatabase();
    await db.runAsync(
      `INSERT OR REPLACE INTO offline_mutations
         (id, endpoint, method, payload, entity_type, created_at, retry_count)
       VALUES (?, ?, ?, ?, ?, ?, 0)`,
      input.id,
      input.endpoint,
      input.method,
      input.payload != null ? JSON.stringify(input.payload) : null,
      input.entityType ?? null,
      Date.now(),
    );
  },

  async all(): Promise<OfflineMutation[]> {
    const db = await getDatabase();
    return db.getAllAsync<OfflineMutation>(
      'SELECT * FROM offline_mutations ORDER BY created_at ASC',
    );
  },

  async count(): Promise<number> {
    const db = await getDatabase();
    const row = await db.getFirstAsync<{ c: number }>(
      'SELECT COUNT(*) AS c FROM offline_mutations',
    );
    return row?.c ?? 0;
  },

  async remove(id: string): Promise<void> {
    const db = await getDatabase();
    await db.runAsync('DELETE FROM offline_mutations WHERE id = ?', id);
  },

  async incrementRetry(id: string): Promise<void> {
    const db = await getDatabase();
    await db.runAsync(
      'UPDATE offline_mutations SET retry_count = retry_count + 1 WHERE id = ?',
      id,
    );
  },
};
