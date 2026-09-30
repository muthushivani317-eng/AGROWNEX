# Onboarding v2 — API contract (for the app)

Backend for the new Profile → Farm → Crops → Needs → Complete flow.
All endpoints need the farmer's normal auth. Responses use the standard `{success, data, message}` envelope.

## 1. Catalog — `GET /api/v1/farm-catalog`
Load once and cache. Use the **codes** in every save, not display text.
```
data: {
  version: 1,
  categories: [{code:"crops"|"vegetables"|"fruits"|"plantation"|"livestock"|"other_products", en, ta}],
  items: [{code:"tomato", category:"vegetables", en:"Tomato", ta:"தக்காளி", default_unit:"kg"}, ...],
  other_code: "other",
  units: [{code:"kg"|"quintal"|"tonne"|"bag"|"litre"|"nos"|"head", en, ta}],
  farmer_types: [{code:"full_time_farmer", en, ta}, ...],
  needs: [{code:"quality_seeds", en, ta}, ...],
  months: [1..12]
}
```
The multi-select dropdowns (Crops / Vegetables / Fruits / Plantation / Livestock / Other farm products) are `items` grouped by `category`. For something not in the list, use `item_code:"other"` with `category` and `custom_name`.

## 2. Profile step — existing `PUT /api/v1/auth/profile` (or `PUT /farmers/me`)
New **optional** fields. Send them only when you have them; if a field is left out, its saved value is kept.
```
land_holding_acres: number (0–10000)        // "Total land holding (acres)"
farmer_type: farmer_types code              // "Main occupation / farmer type"
landmark: string ≤160                       // optional landmark
needs: [needs code]                         // Needs step
needs_note: string ≤300                     // optional free text on Needs step
```
district / block / village are unchanged. Mobile: show `user.phone_number` from login as read-only.
`GET /auth/profile/details` and `GET /farmers/me` return these fields.

## 3. Crops step — `PUT /api/v1/farmers/me/farm-items`
Replaces the farmer's whole list (send everything each time). `GET` returns the same list.
```
{ items: [
  { item_code: "tomato",
    harvest_months: [3,4],          // 1–12, per item
    approx_quantity: 800,           // optional
    unit: "kg",                     // optional, defaults to catalog default_unit
    area_acres: 1,                  // optional
    available_for_sale: true },
  { item_code: "other", category: "other_products", custom_name: "Dried chilli" }
] }
```
Rules: at most 60 items, and each item only once. Production details are **per item**. For livestock, `approx_quantity` is the number of animals and `unit` is `head`.

## 4. Join FPO / KVK
- `GET /api/v1/organic-partner/directory?kind=fpo|kvk&district=<farmer district>` → `[{id, name, kind, district}]`. Same-district organizations are listed first. Only organizations the Agrownex team has set to "Show in app" appear.
- `POST /api/v1/organic-partner/organizations/{id}/join` with body `{ "consent": true }` → `{id, organization_name, status}`.
  - `status: "join_requested"`: waiting for the FPO/KVK manager.
  - `status: "active"`: the organization had already invited this farmer, so joining approves the invite.
  - Before sending, show: *"Your name, phone, village, land and crops will be shared with <org>. You can leave any time."*
- Status list: existing `GET /organic-partner/my-link-requests`. Each row now includes `organization_id` and `initiated_by: "farmer"|"organization"`.
- Cancel a request or leave: existing `POST /organic-partner/my-link-requests/{id}/revoke`.
- Invites sent by the organization (`status: "pending"`, `initiated_by: "organization"`) are still approved with `POST /organic-partner/my-link-requests/{id}/approve`.

## Admin website (done)
The new page **FPO / KVK Members** has:
- Join requests with accept/reject.
- Items with quantity and for-sale amounts.
- Harvest calendar.
- Needs.
- Member list with filters and CSV export.
- "Show in app" and district settings (Owner/Super Admin only).

The FPO Crop Board also counts onboarding crops.
