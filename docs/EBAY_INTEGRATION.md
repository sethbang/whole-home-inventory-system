# eBay Integration

WHIS interacts with eBay along two distinct surfaces, both implemented as of v3.1:

1. **Listing assist (CSV export)** — composes per-item or bulk eBay listing CSVs from inventory. Operator uploads to eBay Seller Hub manually. Lives under `backend/app/ebay/` and `frontend/src/components/EbayFields.tsx`. Shipped in v2.3.
2. **Pricing (Browse API)** — server-to-server lookups of comparable listings via eBay's `Buy/Browse` API, used by the v3.1 `PricingService` to estimate item resale value. Lives at `backend/app/pricing/provider_ebay_browse.py`. Shipped in v3.1.

These are entirely separate code paths with different auth flows, different data shapes, and different operational implications. Read both sections.

---

## 1. Listing assist (CSV export)

### Components

- **`EbayFields` component** (`frontend/src/components/EbayFields.tsx`) — per-item UI for eBay-specific listing details (category, condition, listing format, shipping, returns, payment methods, item specifics).
- **`EbayFields` schema** (`backend/app/ebay/schemas.py`) — Pydantic v2 model that defines the strict shape of what gets stored on `Item.custom_fields.ebay`.
- **Category mapping** (`backend/app/ebay/category_mapping.py`) — maps WHIS categories to eBay category IDs and emits sensible item-specifics templates per category.
- **CSV formatter** (`backend/app/ebay/formatter.py`) — renders one or many items into a Seller-Hub-compatible CSV stream.
- **Router** (`backend/app/routers/ebay.py`) — `/api/ebay/categories`, `/api/ebay/csv`, etc. CSV download streams directly (since v2.3) — no intermediate file is created on disk.
- **Frontend bulk export** — Dashboard supports multi-select → "Export to eBay CSV" producing a single multi-row CSV.

### Storage

eBay-specific fields are stored under `Item.custom_fields.ebay` (a strict-typed JSON sub-object). The `custom_fields` column is otherwise free-form for `user_defined` keys — see `backend/app/schemas.py` for the top-level shape (`ebay` / `facebook` / `user_defined`).

```typescript
interface EbayFieldsData {
  category_id?: string;
  condition?: 'NEW' | 'LIKE_NEW' | 'VERY_GOOD' | 'GOOD' | 'ACCEPTABLE' | 'FOR_PARTS';
  listing_format?: 'FIXED_PRICE' | 'AUCTION';
  duration?: 'DAYS_3' | 'DAYS_5' | 'DAYS_7' | 'DAYS_10' | 'DAYS_30' | 'GTC';
  shipping_service?: 'USPS_FIRST_CLASS' | 'USPS_PRIORITY' | 'USPS_GROUND' | 'UPS_GROUND' | 'FEDEX_GROUND' | 'FREIGHT' | 'LOCAL_PICKUP';
  shipping_cost?: number;
  returns_accepted?: boolean;
  return_period?: 'DAYS_30' | 'DAYS_60' | 'NO_RETURNS';
  payment_methods?: Array<'PAYPAL' | 'CREDIT_CARD' | 'BANK_TRANSFER'>;
  starting_price?: number;
  reserve_price?: number;
  buy_it_now_price?: number;
  quantity?: number;
  domestic_shipping_only?: boolean;
  item_specifics?: Record<string, string>;
}
```

### Tests

- Frontend: `frontend/src/components/__tests__/EbayFields.test.tsx`, `frontend/src/api/__tests__/ebay.test.ts`, `frontend/src/pages/__tests__/ItemDetail.test.tsx`
- Backend: `backend/tests/test_ebay.py` (formatter + router round-trip)

### Limitations

- CSV import is manual — operator uploads to Seller Hub themselves.
- No real-time inventory sync, no listing edits via API.
- Image URLs are not yet emitted in the CSV (Phase 2).

---

## 2. Pricing (Browse API)

### Components

- **`EbayBrowseProvider`** (`backend/app/pricing/provider_ebay_browse.py`) — issues `client_credentials` OAuth, hits `/buy/browse/v1/item_summary/search`, parses results into our `PriceSource` shape.
- **`PricingService`** (`backend/app/pricing/service.py`) — orchestrates provider priority (`PRICING_PROVIDERS=ebay,llm` by default), cache reads/writes, and per-item stamping.
- **`PriceCache`** (`backend/app/models.py`) — composite-PK table keyed by `(identity_hash, provider)`. Holds the JSON-serialized `PriceEstimate` envelope per provider, with `expires_at` for TTL.
- **Router** (`backend/app/routers/pricing.py`) — `/api/pricing/estimate`, `/refresh/{id}`, `/estimate/{id}`. Routes through ARQ when `REDIS_URL` is set, sync otherwise.

### Auth

OAuth `client_credentials` (server-to-server). WHIS never acts on behalf of an eBay end user — there is no `authorization_code` flow, no per-user eBay account linking, and no buyer/bidder session.

Required env (in `backend/.env` or root `.env` for compose):

```bash
EBAY_APP_ID=YourCo-yourapp-PRD-xxxxxxxxx-xxxxxxxx
EBAY_CERT_ID=PRD-xxxxxxxxxxxx-xxxx-xxxx-xxxx-xxxx
EBAY_MARKETPLACE_ID=EBAY_US           # or EBAY_GB, EBAY_DE, ...
EBAY_ENVIRONMENT=production           # or sandbox
```

Sandbox keys (`SBX-` prefix) require `EBAY_ENVIRONMENT=sandbox` — production keys (`PRD-` prefix) require `EBAY_ENVIRONMENT=production`. Mismatch yields a 401 `invalid_client`.

### Marketplace Account Deletion exemption

WHIS holds an exemption from eBay's [Marketplace User Account Deletion notification system](https://developer.ebay.com/marketplace-account-deletion) on the basis that **we persist no eBay user data**. The exemption is load-bearing — keep it valid:

- The Browse API response includes a `seller` object (`username`, `userId`, `feedbackPercentage`, `email`). Our parser at `provider_ebay_browse.py:_parse_item_summaries` deliberately ignores it.
- We persist only the listing fields: `title`, `itemWebUrl`, `price`, `condition`, plus `source_site: "ebay"`. These land in `PriceCache.payload` and the `PriceSource` list returned to the UI.
- Listing titles are seller-authored copy but not personal data per eBay's deletion scope.
- A regression test (`backend/tests/test_pricing_providers.py::test_ebay_parser_drops_seller_pii_for_deletion_exemption`) feeds the parser a Browse response laden with seller PII and asserts none of it survives. **If that test ever fails, the exemption is invalidated** — you must reverse the exemption in the eBay developer portal and stand up the deletion-notification callback before shipping the change.

If you ever expand to a User-context API (Sell APIs, Trading API on behalf of users), the exemption no longer applies.

### Tests

- `backend/tests/test_pricing_providers.py` — full round-trip via `httpx.MockTransport`: OAuth, search, aggregation, rate-limit handling, no-result, zero-priced filtering, token caching, and the deletion-exemption regression.
- `backend/tests/test_pricing_service.py` — provider routing, cache hit/miss, force-refresh.
- `backend/tests/test_pricing_router.py` — HTTP layer.

### Operational notes

- Default rate limiting on the Browse API is generous; we surface 429s as `PriceProviderRateLimited` and fall through to the next provider in the priority list (typically the LLM provider).
- `PRICING_CACHE_DAYS` (default 14) controls how long aggregated estimates are retained. After expiry the next request re-queries.
- Daily LLM cost cap (`PRICING_DAILY_COST_CAP_USD`) does not apply to the eBay provider — Browse API has no per-call dollar cost. The cap only governs the LLM-provider fallback.

---

## Roadmap

### Shipped (current)

- ✅ Per-item eBay listing CSV export (v2.3)
- ✅ Bulk multi-row CSV export from Dashboard (v2.3)
- ✅ Strict-typed `EbayFields` schema, persisted on `custom_fields.ebay` (v2.3)
- ✅ Streaming CSV download — no intermediate disk file (v2.3)
- ✅ Browse API pricing provider with OAuth client_credentials, cache, P10/P50/P90 aggregation (v3.1)
- ✅ Marketplace Account Deletion exemption with regression-tested PII filter (v3.1)

### Future

- Image URLs in the CSV (currently CSV references images by filename; Seller Hub needs publicly-reachable URLs).
- Sell/Inventory API integration (`authorization_code` OAuth, real-time listing creation, inventory sync, order management). This would invalidate the deletion-notification exemption — implement only after standing up the callback listener.
- Trading API for legacy listing operations.
- Cached category lookups and category-suggestion improvements.

---

## Resources

- [eBay Developer Documentation](https://developer.ebay.com/docs)
- [Browse API (used by v3.1 pricing)](https://developer.ebay.com/api-docs/buy/browse/resources/methods)
- [Inventory API (future Sell-side integration)](https://developer.ebay.com/api-docs/sell/inventory/resources/methods)
- [Taxonomy / Category API](https://developer.ebay.com/api-docs/commerce/taxonomy/resources/methods)
- [Marketplace User Account Deletion notifications](https://developer.ebay.com/marketplace-account-deletion)
