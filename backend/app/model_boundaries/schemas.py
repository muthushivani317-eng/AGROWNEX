from typing import Literal

from pydantic import BaseModel, ConfigDict


class CropIdentificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["accepted", "uncertain", "unsupported", "model_not_available"]
    crop_id: Literal[
        "banana", "rice", "cotton", "groundnut", "coconut", "chilli", "redgram"
    ] | None = None
    raw_confidence_exposed: Literal[False] = False
    model_version: str | None = None


class PlantIdentificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["accepted", "uncertain", "unsupported", "model_not_available"]
    common_name: str | None = None
    scientific_name: str | None = None
    documented_uses: list["DocumentedPlantUse"] = []
    raw_confidence_exposed: Literal[False] = False
    model_version: str | None = None


class ExactSourceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_document: str
    printed_page: str
    pdf_page_index: int
    verification_status: Literal["VERIFIED"]


class DocumentedPlantUse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    use: str
    evidence: ExactSourceEvidence


class VerifiedDiseaseKnowledge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    crop_id: str
    disease_class_id: str
    symptoms: list[str]
    likely_cause: str
    recommended_actions: list[str]
    prevention: list[str]
    remedy_or_management: list[str]
    evidence: list[ExactSourceEvidence]
    verification_status: Literal["VERIFIED"]


PlantIdentificationResult.model_rebuild()
