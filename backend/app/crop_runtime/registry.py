from __future__ import annotations

import json
from pathlib import Path

from .schemas import CropPublicView, CropRegistryDocument, CropRegistryEntry

DEFAULT_REGISTRY_PATH = Path(__file__).with_name("crop_registry.json")


class CropRegistry:
    def __init__(self, document: CropRegistryDocument) -> None:
        self.document = document
        self._by_id = {entry.crop_id: entry for entry in document.crops}
        self._aliases = {
            alias.strip().casefold(): entry.crop_id
            for entry in document.crops
            for alias in [entry.crop_id, *entry.aliases]
        }

    def normalize(self, crop_id: str) -> str:
        normalized = crop_id.strip().casefold()
        if normalized not in self._aliases:
            raise KeyError("INVALID_CROP_ID")
        return self._aliases[normalized]

    def get(self, crop_id: str) -> CropRegistryEntry:
        return self._by_id[self.normalize(crop_id)]

    def public(self, crop_id: str) -> CropPublicView:
        return CropPublicView.model_validate(
            self.get(crop_id).model_dump(
                exclude={
                    "aliases",
                    "runtime_path",
                    "checkpoint_sha256",
                    "deployment_zip_sha256",
                    "deployment_status",
                    "model_version",
                    "architecture",
                    "supported_classes",
                    "expected_temperature",
                    "expected_class_gates",
                    "thresholds_filename",
                    "frozen_fallback",
                    "pilot_inference_eligible",
                    "general_farmer_inference_authorized",
                    "expert_verified",
                    "tamil_nadu_field_validated",
                    "last_verified_at",
                    "registry_schema_version",
                }
            )
        )

    def list_public(self) -> list[CropPublicView]:
        return [self.public(entry.crop_id) for entry in self.document.crops]


def load_registry(path: Path = DEFAULT_REGISTRY_PATH) -> CropRegistry:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return CropRegistry(CropRegistryDocument.model_validate(raw))
