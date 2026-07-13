"""AgrowAI Administration Platform (docs: Admin Dashboard, MASTER_SPEC V1).

For the AgrowAI team only — NOT a farmer interface. Provides operational visibility,
farmer management, AI monitoring, procurement management, analytics, content management
and notification management on top of the existing modules.

Read-only over farmer data (no direct modification), role-based (RBAC), and audits every
admin action (docs/SECURITY.md → audit logs are immutable). Designed so multiple admin
roles and future enterprise/export dashboards plug in behind the same seam with no
redesign. Flow: Repository → Service → Admin Engine → Provider → API → Frontend.
"""
