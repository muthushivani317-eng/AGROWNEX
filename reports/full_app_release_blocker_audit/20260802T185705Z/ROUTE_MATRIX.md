# Authenticated Route Matrix

This matrix records filesystem evidence before repair. A present route file does not mean the feature works.

| Feature | Home key | Intended pathname | Route file | Home mapping | Initial result |
|---|---|---|---|---|---|
| Home | — | `/(tabs)` | `agrow-ai/app/(tabs)/index.tsx` | Tab root | PRESENT; DEVICE_RETEST_REQUIRED |
| AI Assistant | `ai` | `/ai` | `agrow-ai/app/(tabs)/ai.tsx` | `/ai` | PRESENT |
| Disease Detection | `disease` | `/disease` | `agrow-ai/app/disease/index.tsx` | `/disease` | PRESENT; FUNCTIONAL_FAIL |
| Weather | `weather` | `/weather` | `agrow-ai/app/weather.tsx` | `/weather` | PRESENT |
| Add Farm | `addFarm` | `/farm/new` | `agrow-ai/app/farm/new.tsx` | `/farm/new` | PRESENT; UI_FAIL |
| Crop Calendar | `calendar` | `/calendar` | `agrow-ai/app/calendar/index.tsx` | `/calendar` | PRESENT |
| Growth Monitor | `growth` | `/growth` | `agrow-ai/app/growth/index.tsx` | `/growth` | PRESENT |
| Market Prices | `market` | `/market` | `agrow-ai/app/(tabs)/market.tsx` | `/market` | PRESENT |
| Government Schemes | `schemes` | `/schemes` | `agrow-ai/app/schemes/index.tsx` | `/schemes` | PRESENT; UI/CONTENT_FAIL |
| Sell Produce | `sell` | `/produce` | `agrow-ai/app/produce/index.tsx` | `/produce` | PRESENT |
| Notifications | `notifications` | `/notifications` | `agrow-ai/app/notifications/index.tsx` | `/notifications` | PRESENT |
| Plant Identifier | `plantIdentifier` | `/plant-identifier` | `agrow-ai/app/plant-identifier/index.tsx` | `/plant-identifier` | PRESENT; FUNCTIONAL/COPY_FAIL |
| Soil Intelligence | `soil` | `/soil` | `agrow-ai/app/soil/index.tsx` | `/soil` | PRESENT |
| Nutrient Deficiency | missing | `/nutrient` | `agrow-ai/app/nutrient/index.tsx` | MISSING | ROUTE_PRESENT_HOME_MISSING; EVIDENCE_AUDIT_REQUIRED |
| Farm tab | — | `/(tabs)/farm` | `agrow-ai/app/(tabs)/farm.tsx` | Tab | PRESENT |
| Profile | — | `/(tabs)/profile` | `agrow-ai/app/(tabs)/profile.tsx` | Tab | PRESENT |
| Profile edit | — | `/profile/edit` | `agrow-ai/app/profile/edit.tsx` | Profile action | PRESENT |
| Profile setup | — | `/complete-profile` | `agrow-ai/app/(auth)/complete-profile.tsx` | Startup guard | PRESENT |

## Navigation constraints

- The authenticated root-route guard was previously corrected so a valid authenticated non-auth route is not replaced by `/(tabs)`.
- No unsupported destination may silently redirect Home.
- Nutrient Deficiency cannot be marked operational merely because its route and API client exist.
- All destination rendering and non-redirect assertions still require automated and physical evidence.

## Physical route inventory

The baseline contains 74 files under `agrow-ai/app`. In addition to the matrix above, detail/history/edit routes exist for disease, farm, notifications, nutrient, produce, schemes, soil, AI history, consultations, experts, satellite, intelligence and memory. Administrative routes are out of the farmer Home scope and are not implicitly approved.
