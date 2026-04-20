/**
 * Backward-compat barrel.
 *
 * Historically every frontend module imported its API helper from
 * ``api/client.ts``. v2.3 splits those helpers into per-resource modules
 * (``api/auth.ts``, ``api/items.ts``, etc.) but keeps this file as a
 * re-export surface so the fifteen-plus existing import sites don't need
 * a sweeping rename pass.
 *
 * New code should import from the per-resource modules directly. This
 * barrel will be removed in a future release once downstream imports
 * have migrated.
 */

export { apiClient } from './http';
export { ApiError, apiErrorMessage, isApiError } from './errors';

// Per-resource modules (all re-exported at the top level).
export { auth } from './auth';
export { items } from './items';
export { images } from './images';
export { backups } from './backups';
export { analytics } from './analytics';
export { ebay } from './ebay';

// Type re-exports so ``import type { Item } from '../api/client'`` keeps
// working. New code should prefer importing from ``types/``.
export type {
  AuthResponse,
  LoginCredentials,
  RegisterData,
  User,
} from '../types/auth';
export type {
  Item,
  ItemImage,
  ItemListResponse,
  SearchFilters,
} from '../types/items';
// Legacy alias — some tests import ``SearchFilters`` using an older name.
export type { SearchFilters as SearchFilter } from '../types/items';
export type {
  Backup,
  BackupList,
  RestoreResult,
} from '../types/backups';
export type {
  AgeAnalysis,
  AgeBucket,
  ValueByCategory,
  ValueByLocation,
  ValueTrends,
  WarrantyItem,
  WarrantyStatus,
} from '../types/analytics';
export type {
  EbayCategory,
  EbayCategoryResponse,
  EbayExportRequest,
  EbayExportResponse,
  EbayFields,
} from '../types/ebay';
