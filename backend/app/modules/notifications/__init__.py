"""Notifications & Smart Alerts — the event center of AgrowAI
(docs/DATABASE_SCHEMA.md → Notifications domain, docs/API_CONTRACT.md → NOTIFICATIONS,
docs/USER_FLOWS.md → NOTIFICATION FLOW).

Not just push notifications: a centralized, deterministic **notification engine**
that receives events from every completed module (weather, disease, calendar,
growth, market, schemes, produce, AI), applies transparent rules to classify
severity/priority, stores them permanently (docs: notifications are never
permanently deleted → delete = dismiss/soft-delete) and delivers them through a
``NotificationProvider`` abstraction (in-app mock now; FCM / OneSignal / SMS /
WhatsApp / Email later) with no frontend change. Titles/messages are stored as
localization keys + a payload so the Tamil-first client renders them. No AI.
"""
