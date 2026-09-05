"""Today's Farm Task -- the unified daily-advisory layer.

Layers: signal_providers (1) -> schemas.EvidenceSignal (2) -> ranking_engine
(3) -> service/task_copy (4) -> evidence_pack (5). See
docs/agrowai-daily-task-unified-implementation-2026-09-05.md (Claude Project)
for the full design brief this module implements.
"""
