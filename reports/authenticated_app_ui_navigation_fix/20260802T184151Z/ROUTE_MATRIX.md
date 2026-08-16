# Authenticated feature route matrix

| Feature | Pathname | Physical route | Parent | Guard result | Status |
|---|---|---|---|---|---|
| AI Assistant | `/ai` | `app/(tabs)/ai.tsx` | tabs | allowed | test pass; device pending |
| Disease Detection | `/disease` | `app/disease/index.tsx` | root stack | allowed | test pass; device pending |
| Weather | `/weather` | `app/weather.tsx` | root stack | allowed | test pass; device pending |
| Add Farm | `/farm/new` | `app/farm/new.tsx` | root stack | allowed | test pass; device pending |
| Crop Calendar | `/calendar` | `app/calendar/index.tsx` | root stack | allowed | test pass; device pending |
| Growth Monitor | `/growth` | `app/growth/index.tsx` | root stack | allowed | test pass; device pending |
| Market Prices | `/market` | `app/(tabs)/market.tsx` | tabs | allowed | test pass; device pending |
| Government Schemes | `/schemes` | `app/schemes/index.tsx` | root stack | allowed | test pass; device pending |
| Sell Produce | `/produce` | `app/produce/index.tsx` | root stack | allowed | test pass; device pending |
| Notifications | `/notifications` | `app/notifications/index.tsx` | root stack | allowed | test pass; device pending |
| Plant Identifier | `/plant-identifier` | `app/plant-identifier/index.tsx` | root stack | allowed | test pass; device pending |
| Soil Intelligence | `/soil` | `app/soil/index.tsx` | root stack | allowed | test pass; device pending |
| Profile Edit | `/profile/edit` | `app/profile/edit.tsx` | root stack | allowed | test pass; device pending |

No Home feature uses `/` as a placeholder.
