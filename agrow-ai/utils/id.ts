import * as Crypto from 'expo-crypto';

/** RFC4122 v4 UUID. */
export function uuid(): string {
  return Crypto.randomUUID();
}
