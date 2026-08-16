# Production API Matrix

All paths are relative to the configured `/api/v1` base. Authentication is required except public capability/health contracts. No authenticated production requests were made because the required device was unavailable and no token was extracted or fabricated.

| Feature | Mobile contract | Production validation |
|---|---|---|
| AI | `POST /ai/chat`; history routes | NOT_RUN |
| Disease | `POST /disease/analyze`; crop-ID and capability-gated crop runtimes | FAIL from supplied device evidence; not revalidated |
| Weather | `GET /weather` | NOT_RUN |
| Farms | CRUD `/farms`; boundary/images subroutes | NOT_RUN |
| Calendar | `/calendar`, generate, summary, events | NOT_RUN |
| Growth | upload/history/timeline/latest | NOT_RUN |
| Market | `/market`, history/search/favourites | NOT_RUN |
| Schemes | `/schemes`, eligible/recommended/bookmarks | NOT_RUN |
| Produce | `/produce`, upcoming/history | NOT_RUN |
| Notifications | `/notifications`, unread/read/preferences | NOT_RUN |
| Plant Identifier | feature upload provider | FAIL from supplied evidence; not revalidated |
| Soil | `/soil`, latest/history/recommendation/report | NOT_RUN |
| Nutrient | client exists, but Home destination is intentionally controlled unavailable | BLOCKED_BY_EVIDENCE_GATE |
| Profile | `/farmers/me`, languages/preferences | NOT_RUN |

No mocks substitute for these missing production results.
