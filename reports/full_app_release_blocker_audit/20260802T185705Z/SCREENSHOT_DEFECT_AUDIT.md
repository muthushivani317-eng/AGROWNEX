# Screenshot Defect Audit

The authenticated-screen defects below are transcribed from the supplied real-device evidence and task brief. Where the original screenshot file is not present in the repository, the evidence identifier is `SUPPLIED_DEVICE_EVIDENCE`; this report does not fabricate a filename. Existing repository screenshots are predominantly authentication evidence and do not prove these authenticated features pass.

| Screenshot | Screen | Component | Exact visible defect | Severity | Probable code location | Probable root cause | Required acceptance evidence |
|---|---|---|---|---|---|---|---|
| SUPPLIED_DEVICE_EVIDENCE | Home | Feature grid | Inconsistent card sizes and broken two-column alignment | Stop-ship | `features/home/components/QuickActions.tsx` | Mixed NativeWind percentage width and content-driven height | Full-scroll release-device screenshot with equal measured columns |
| SUPPLIED_DEVICE_EVIDENCE | Home | Dashboard sections | Unnecessary gaps and overly long scrolling | High | `features/home/screens/HomeScreen.tsx` | All services in one undifferentiated grid | Screenshot showing required section order and compact grids |
| SUPPLIED_DEVICE_EVIDENCE | Home | Services | Nutrient Deficiency missing | Stop-ship | `features/home/routes.ts`, `QuickActions.tsx` | Route not registered on Home | Card visible and controlled destination captured |
| SUPPLIED_DEVICE_EVIDENCE | Home | Today tasks | Unfinished task controls and unexplained faint characters | High | Home task component | Release styling/text fallback defects | Readable task-row screenshot; no stray glyphs |
| SUPPLIED_DEVICE_EVIDENCE | Home | Bottom content | Content clipped near tab bar | Stop-ship | `HomeScreen.tsx`, shared screen container | Missing bottom safe-area/content inset | Full-scroll screenshot with last control unobscured |
| SUPPLIED_DEVICE_EVIDENCE | Add Farm | Location | GPS action difficult to discover | Stop-ship | `features/farm/screens/FarmFormScreen.tsx` | Location action buried in long form | Visible primary location action near Location heading |
| SUPPLIED_DEVICE_EVIDENCE | Add Farm | Boundary map | Raw controls overlap imagery | Stop-ship | farm boundary editor/map component | Unstyled text controls and missing floating toolbar layout | Device screenshot with styled non-overlapping toolbar |
| SUPPLIED_DEVICE_EVIDENCE | Add Farm | Date field | Raw key `farm.selectDate` visible | Stop-ship | farm translations/date field | Missing translation/fallback | Tamil and English screenshot with resolved label |
| SUPPLIED_DEVICE_EVIDENCE | Add Farm | Select/status fields | Dropdowns and status options appear as plain text | High | Farm form fields | Inconsistent shared field/control primitives | Device interaction video/screenshots showing proper controls |
| SUPPLIED_DEVICE_EVIDENCE | Add Farm | Submit | Disabled Add Farm has no explanation | Stop-ship | Farm form validation | Errors not surfaced before/near submit | Validation screenshot explaining every blocker |
| SUPPLIED_DEVICE_EVIDENCE | Add Farm | Form | Weak hierarchy and long unstructured form | High | `FarmFormScreen.tsx` | No section cards/progressive organization | Full-scroll screenshots with five required sections |
| SUPPLIED_DEVICE_EVIDENCE | AI | Composer | No visible composer box; send icon floats | Stop-ship | `features/ai/screens/ChatScreen.tsx`, composer | Release styles insufficient | Keyboard-open release screenshot with input/send bounds |
| SUPPLIED_DEVICE_EVIDENCE | AI | Suggestions/messages | Suggestions are plain text; no chat bubble UI | High | AI screen/components | Missing/unstyled reusable components | Tappable cards and rendered user/assistant bubbles |
| SUPPLIED_DEVICE_EVIDENCE | AI | State handling | No visible loading/error/offline state; unclear header controls | Stop-ship | AI screen/hooks | State not represented in UI | Production request evidence for success and failure/retry |
| SUPPLIED_DEVICE_EVIDENCE | Disease | Crop-ID stage | “Crop identification could not connect.” | Stop-ship | disease screen/provider/backend contract | Network/auth/path/body/provider failure not yet proven | Sanitized production request and Railway response evidence |
| SUPPLIED_DEVICE_EVIDENCE | Disease | Retry/retake/progress | Retry non-functional, Retake plain text, no stage/progress UI | Stop-ship | disease workflow screen | Incomplete state-machine rendering | Device capture showing upload stages, retry and abstain |
| SUPPLIED_DEVICE_EVIDENCE | Disease | Fixture image | Possibly copyrighted test imagery | High | fixture/assets/evidence workflow | Unverified test asset used in evidence | New user-captured or reuse-cleared evidence image |
| SUPPLIED_DEVICE_EVIDENCE | Government Schemes | Tabs | Tab labels concatenate | Stop-ship | schemes screen/filter component | Text row lacks measured scrollable tab control | Screenshot cycling four distinct tabs |
| SUPPLIED_DEVICE_EVIDENCE | Government Schemes | Scheme cards | Crowded cards, truncated descriptions, unclear save/action state | High | schemes card component | Content hierarchy/action styling inadequate | Readable structured card screenshots |
| SUPPLIED_DEVICE_EVIDENCE | Government Schemes | Claims | Eligibility percentages/status lack verification warning | Stop-ship | scheme rendering | Unverified backend facts rendered as authoritative | Every claim marked `VERIFY AGAINST OFFICIAL SOURCE.` |
| SUPPLIED_DEVICE_EVIDENCE | Plant Identifier | Copy | Raw `HUMAN_TAMIL_REVIEW_REQUIRED` visible | Stop-ship | plant identifier screen/localization mapping | Internal status passed directly to UI | Tamil-first reviewed fallback screenshot; no internal enum |
| SUPPLIED_DEVICE_EVIDENCE | Plant Identifier | Service state | Service unavailable with weak retry | Stop-ship | plant screen/provider | Endpoint/auth/upload/provider failure unresolved | Sanitized production request plus controlled unavailable UI |
| SUPPLIED_DEVICE_EVIDENCE | Plant Identifier | Workflow | No localization-safe fallback or stage/progress UI | High | plant identifier workflow | Missing explicit stages and safe error mapping | Capture/select/loading/result/uncertain screenshots |

## Initial screenshot gate

`PHYSICAL_DEVICE_REGRESSION=FAIL` and `READY_FOR_TESTING=NO`. Automated rendering cannot replace release-device evidence.
