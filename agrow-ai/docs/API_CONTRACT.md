# 📡 AGROWAI API CONTRACT

Version: Foundation Release (V1)

---

# PURPOSE

This document defines every REST API exposed by AgrowAI.

All clients must consume these APIs.

Clients

• Mobile App

• Admin Dashboard

• FPO Dashboard

• Future Buyer Portal

The API must remain backward compatible.

---

# API STANDARD

Architecture

REST API

Protocol

HTTPS Only

Base URL

/api/v1

Content Type

application/json

Authentication

Firebase JWT

Response Format

JSON

Encoding

UTF-8

---

# REQUEST STANDARD

Headers

Authorization

Bearer Token

Content-Type

application/json

Accept

application/json

Accept-Language

ta-IN

Request ID

X-Request-ID

---

# SUCCESS RESPONSE

{
  "success": true,
  "message": "Success",
  "data": {},
  "timestamp": "",
  "request_id": ""
}

---

# ERROR RESPONSE

{
  "success": false,
  "message": "",
  "error_code": "",
  "errors": [],
  "timestamp": "",
  "request_id": ""
}

---

# HTTP STATUS

200 Success

201 Created

400 Bad Request

401 Unauthorized

403 Forbidden

404 Not Found

409 Conflict

422 Validation Error

429 Too Many Requests

500 Internal Error

503 Service Unavailable

---

# AUTH MODULE

POST

/auth/login

POST

/auth/logout

POST

/auth/refresh

POST

/auth/google

POST

/auth/apple

POST

/auth/otp/send

POST

/auth/otp/verify

GET

/auth/profile

PUT

/auth/profile

---

# FARMER MODULE

GET

/farmers/me

PUT

/farmers/me

GET

/farmers/preferences

PUT

/farmers/preferences

GET

/farmers/languages

PUT

/farmers/languages

---

# FARM MODULE

GET

/farms

POST

/farms

GET

/farms/{id}

PUT

/farms/{id}

DELETE

/farms/{id}

POST

/farms/{id}/boundary

GET

/farms/{id}/media

POST

/farms/{id}/media

---

# CROP SESSION

GET

/crop-sessions

POST

/crop-sessions

PUT

/crop-sessions/{id}

DELETE

/crop-sessions/{id}

---

# AI CHAT

POST

/ai/chat

POST

/ai/voice

POST

/ai/image

GET

/ai/history

GET

/ai/history/{id}

DELETE

/ai/history/{id}

---

# DISEASE DETECTION

(Updated 2026-08 — see docs/AI_DECISION_MATRIX.md → DISEASE DETECTION for the
full routing rationale.)

Two release paths exist:

Controlled-tester release (internal/pilot tester, KVK reviewer roles only) is
exposed through the dedicated endpoints for the six supported crops (Banana
V3; paddy/cotton/groundnut legacy-joint; restricted Chilli/Redgram). Each
route applies its frozen classifier and abstention policy; accepted labels
resolve guidance from the verified disease registry. There is no
`POST /disease/analyze`, no `POST /disease/analyze-v2`, and no Gemini
diagnosis fallback in this path. Unsupported crops/classes return a clear
fail-closed response.

General farmer release (any authenticated farmer, any crop) is exposed
through `POST /disease/predict`. This path is primarily an OpenAI vision
diagnosis, cross-checked against a dedicated local classifier where one
exists for the crop (see AI_DECISION_MATRIX.md for why: most locally-trained
classifiers today are provisional, public-dataset models not yet validated
on real farmer photos, so restricting general release to only the six
locally-modeled crops would leave most farmers with no diagnosis at all).
Every response carries `verification_level`: `verified_by_local_model` when
a classifier independently confirmed the read, or `ai_vision_estimate`
otherwise — clients must render these with visibly different confidence, not
as equivalent results, and a local-model disagreement always forces
`needs_expert_review: true`.

Gemini crop/plant identification is a separate identification-only capability and
must not produce a disease label or treatment recommendation.

POST

/disease/predict

GET

/disease/history

GET

/disease/{id}

DELETE

/disease/{id}

---

# CROP GROWTH

POST

/growth/upload

GET

/growth/history

GET

/growth/timeline

GET

/growth/report

---

# FERTILIZER

POST

/fertilizer/recommendation

GET

/fertilizer/history

POST

/fertilizer/application

---

# WEATHER

GET

/weather/current

GET

/weather/forecast

GET

/weather/alerts

---

# MARKET

GET

/market/prices

GET

/market/trends

GET

/market/history

---

# GOVERNMENT SCHEMES

GET

/schemes

GET

/schemes/{id}

GET

/schemes/eligible

---

# PRODUCE

GET

/produce

POST

/produce

PUT

/produce/{id}

DELETE

/produce/{id}

POST

/produce/{id}/images

GET

/produce/history

---

# NOTIFICATIONS

GET

/notifications

PUT

/notifications/{id}/read

PUT

/notifications/read-all

GET

/notifications/preferences

PUT

/notifications/preferences

---

# FILES

POST

/upload/image

POST

/upload/document

POST

/upload/audio

DELETE

/upload/{id}

---

# ADMIN

GET

/admin/dashboard

GET

/admin/farmers

GET

/admin/farms

GET

/admin/disease

GET

/admin/produce

GET

/admin/market

GET

/admin/schemes

GET

/admin/notifications

GET

/admin/analytics

---

# ANALYTICS

GET

/analytics/dashboard

GET

/analytics/usage

GET

/analytics/ai

GET

/analytics/farmers

GET

/analytics/produce

---

# PAGINATION

?page=1

&page_size=20

&sort=created_at

&order=desc

---

# FILTERING

?district=

?block=

?village=

?crop=

?status=

?date=

---

# SEARCH

?q=banana

---

# API VERSIONING

/api/v1

Future

/api/v2

Never break existing APIs.

---

# RATE LIMITING

AI APIs

30 requests/minute/user

Authentication

10 requests/minute/IP

Uploads

20 uploads/hour

Admin

100 requests/minute

---

# SECURITY

Firebase JWT

HTTPS

Input Validation

Output Validation

Rate Limiting

Request Logging

Audit Logging

---

# CACHING

Weather

5 minutes

Market Prices

15 minutes

Government Schemes

24 hours

Static Master Data

7 days

---

# FUTURE APIs

Satellite

Drone

IoT

Buyer

Warehouse

Insurance

Carbon Credits

Financial Services

Expert Connect
