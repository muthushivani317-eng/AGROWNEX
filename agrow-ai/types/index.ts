export * from './api';

export type Nullable<T> = T | null;

export type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

export type SupportedLanguage = 'ta' | 'en';

export interface GeoCoordinates {
  latitude: number;
  longitude: number;
}
