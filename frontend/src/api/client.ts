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
export { facebook } from './facebook';

// Type re-exports so ``import type { Item } from '../api/client'`` keeps
// working. New code should prefer importing from ``./types`` directly —
// that module re-exports the generated OpenAPI types.
export type {
  AuthResponse,
  LoginCredentials,
  RegisterData,
  User,
  Item,
  ItemImage,
  ItemListResponse,
  SearchFilters,
  SearchFilter,
  Backup,
  BackupList,
  RestoreResult,
  AgeAnalysis,
  AgeBucket,
  ValueByCategory,
  ValueByLocation,
  ValueTrends,
  WarrantyItem,
  WarrantyStatus,
  EbayCategory,
  EbayCategoryResponse,
  EbayExportRequest,
  EbayExportResponse,
  EbayFields,
  FbAvailability,
  FbCatalogExportRequest,
  FbCategoriesResponse,
  FbCondition,
  FbCopyPasteBlock,
  FbFieldsData,
} from './types';
