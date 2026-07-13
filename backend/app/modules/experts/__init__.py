"""Expert Connect — a structured farmer↔verified-expert consultation platform.

Not a public chat room: every question is a tracked consultation with an immutable
conversation timeline, deterministic assignment to a verified expert desk (TNAU /
KVK / Government / Kisan Call Centre) and a logged status history. Reuses auth, the
farm repository, the upload service (attachments), the notification engine (expert
events), the response envelope and localization. Built future-ready so WhatsApp,
live chat, video, email and AI-assisted replies can be added behind the provider
seam with no frontend change.
"""
