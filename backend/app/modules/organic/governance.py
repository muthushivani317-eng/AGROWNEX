from __future__ import annotations

import hashlib
import json

from app.modules.organic.models import OrganicInput


def canonical_input_hash(item: OrganicInput) -> str:
    """Hash all recommendation-bearing fields using a deterministic encoding."""
    payload = {
        "slug": item.slug,
        "category": item.category,
        "name_en": item.name_en,
        "name_ta": item.name_ta,
        "purpose_en": item.purpose_en,
        "purpose_ta": item.purpose_ta,
        "guidance": item.guidance,
        "applicable_crops": item.applicable_crops,
        "applicable_stages": item.applicable_stages,
        "applicable_regions": item.applicable_regions,
        "limitations": item.limitations,
        "source_organization": item.source_organization,
        "document_reference": item.document_reference,
        "source_url": item.source_url,
        "source_version": item.source_version,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def input_hash_is_valid(item: OrganicInput) -> bool:
    return bool(item.content_hash) and item.content_hash == canonical_input_hash(item)
