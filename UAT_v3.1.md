# WHIS v3.1 manual UAT

Run order is roughly cheapest → heaviest. The two starred (⭐) sections are the
v3.1 hot paths — spend the most time there. Keep DevTools open the whole pass.

## Pre-flight
- [ ] Open https://localhost:5173 — page loads, no cert warning
      (if warning, trust frontend/certs/whis-dev-ca.crt)
- [ ] Browser console: 0 errors, 0 unexpected warnings
- [ ] Network tab: /api/health → 200

## Auth
- [ ] Log in as sethbangert@gmail.com — lands on Dashboard
- [ ] Hard refresh — still logged in (token persists)
- [ ] Log out — redirects to /login, can't reach /items by URL
- [ ] Bad password → error message, not a 500
- [ ] Register new user (any email) → auto-logged-in, empty Dashboard

## Items CRUD (golden path)
- [ ] Add Item → fill name + category, save → appears in list
- [ ] Click into item → all fields render, no console errors
- [ ] Edit a field, save → change persists after refresh
- [ ] Delete item → gone from list, no orphan in detail-by-URL

## Images
- [ ] Upload one image (JPG, ~1–3MB) → thumbnail appears
- [ ] Upload multiple at once → all attach
- [ ] Reorder thumbnails (drag) → order persists after refresh
- [ ] Delete an image → gone from gallery; check uploads/ folder
      (filename + thumb_*.webp both removed) ← F6 regression
- [ ] Delete the whole item → all its image files gone from disk
- [ ] Upload a 15MB image → rejected with size error (cap is 10MB)
- [ ] Upload a .txt renamed to .jpg → rejected (magic-byte check)

## ⭐ Vision auto-fill (v3.1)
- [ ] Add Item → take/upload photo → click "Auto-fill from image"
- [ ] Spinner → result appears within ~10–20s
- [ ] Suggested name/brand/model populate; confidence chip visible
- [ ] Tags suggested make sense; can edit before saving
- [ ] Run on a deliberately tough image (cluttered scene) →
      lower confidence chip, warnings array if any
- [ ] Run on a non-product image (landscape) →
      either refuses politely OR returns very low confidence
- [ ] Backend logs: only sha256 hashes, never image bytes
      (`docker compose logs backend | grep -i image`)

## ⭐ Pricing (v3.1)
- [ ] Item with brand + model + name → "Get price estimate"
- [ ] First call: ~3–6s, returns P10/P50/P90 + sources
- [ ] Source links open real eBay listings in new tab
- [ ] Provider chip shows "ebay"
- [ ] Same item, click again → instant cache hit (provider unchanged)
- [ ] Force refresh → re-fetches; new queried_at timestamp
- [ ] Junk item (e.g. brand="zzz" model="qqq" name="asdf") →
      eBay returns no results → falls through to LLM provider
      → returns LLM estimate with prompt_version stamped
- [ ] Pricing on an item missing brand+model+name →
      validation error, not a 500

## Custom fields
- [ ] Add a custom field (e.g. "Serial Number") → save
- [ ] Re-open → field persists with value
- [ ] Add same key twice → handled (rejected or merged)

## Search (FTS)
- [ ] Search box: partial word from a name → finds it
- [ ] Search by brand → finds items
- [ ] Search by custom-field value (if FTS covers it) → either
      finds OR is documented as not covered
- [ ] Empty search → all items
- [ ] Search with quotes "exact phrase" → exact match only

## eBay export
- [ ] Single item: Marketplace tab → eBay → "Generate CSV"
- [ ] CSV downloads; open in Numbers/Excel
- [ ] Required eBay columns present (Title, Category, Condition,
      Price, Quantity, Description, Item Specifics)
- [ ] Item Specifics map sensibly to chosen category
- [ ] Bulk: Dashboard → select items → "Export to eBay CSV"
- [ ] Multi-row CSV opens cleanly

## Facebook Marketplace
- [ ] Item → Marketplace tab → Facebook → "Copy-paste dialog"
- [ ] Each block (Title, Price, Description) has a working copy button
- [ ] "Generate Meta Commerce CSV" → downloads, opens cleanly
- [ ] Required FB catalog columns present (id, title, description,
      availability, condition, price, link, image_link, brand)

## Backups
- [ ] Backups page → "Create backup" → completes (sync) within ~15s
- [ ] New backup row appears with size + timestamp
- [ ] Download backup file → opens as .tar.gz / .zip
- [ ] Restore from backup → confirmation prompt → completes
- [ ] After restore, items + images intact
- [ ] Delete a backup → row disappears, file gone from disk

## (Optional) Async path
Only if you bring up `docker compose --profile worker up --build`:
- [ ] Trigger backup create → "queued" status, Job ID shown
- [ ] Poll job status → progresses → completes
- [ ] Trigger vision → goes async, returns job ref
- [ ] Trigger pricing → goes async, returns job ref
- [ ] Force a deliberate failure (e.g., disable LLM_API_KEY mid-job)
      → job status shows error message, not a serialization crash
      ← F10b regression

## Analytics / Reports
- [ ] Dashboard tiles show counts (items, value if priced)
- [ ] Reports page renders without errors
- [ ] Charts populated; empty-state for unused dimensions

## Bulk actions
- [ ] Select 3+ items → bulk delete → confirmation → all gone
- [ ] Select items → bulk export eBay → multi-row CSV
- [ ] Image files for bulk-deleted items also gone from disk

## PWA / mobile
- [ ] Open https://192.168.1.122:5173 (or your LAN URL) on phone
- [ ] Cert trusted (after installing whis-dev-ca.crt)
- [ ] "Add to Home Screen" → installs as PWA
- [ ] Open from home screen → no browser chrome
- [ ] Camera capture → works → uploads
- [ ] Barcode scan (zxing) → finds + parses a real barcode
- [ ] Offline — open app from home screen with wifi off →
      shell loads (cached SW); read-only behavior is graceful

## Error handling
- [ ] Stop backend (`docker compose stop backend`) → frontend
      shows reasonable error, not blank page
- [ ] Restart → frontend recovers without manual reload
- [ ] Hit a non-existent /items/<random-uuid> → 404 page,
      not a hard crash

## Settings sanity
- [ ] LLM_VISION_MODEL=google/gemini-3-flash-preview is in effect
      (vision call should be sub-$0.005)
- [ ] Daily budget caps respected — try ~10 vision calls in a row,
      should not error until cap is hit (then graceful 503)
- [ ] Try LLM_ALLOW_CLOUD=false in .env → backend refuses to start
      (only valid when LLM_BASE_URL points at a private host)

---

## Findings template

When you hit something off, jot:
- **What you clicked** (page → element)
- **What you expected**
- **What happened** (UI behavior + error message text)
- **Backend logs** (5–10 relevant lines from `docker compose logs backend`)
