"""Stage 5 — ML correction-factor layer. Fallback-only in this pass: no real
historical BOQ data has been sourced yet (blocked, tracked separately), so every
prediction is confidence='fallback' / factor=1.0, i.e. defers entirely to the Stage 4
theoretical quantity. get_active_correction_model is the ONE place a real trained
model plugs in later — boq_assembler never needs to change when that happens.
"""

from abc import ABC, abstractmethod
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.models.enums import CorrectionConfidence, ModelVersionStatus
from app.models.model_version import ModelVersion


class CorrectionResult(NamedTuple):
    correction_factor: float
    correction_confidence: CorrectionConfidence


class BaseCorrectionModel(ABC):
    @abstractmethod
    def predict(
        self, material_name: str, theoretical_quantity: float, room_type: str, **features
    ) -> CorrectionResult: ...


class FallbackCorrectionModel(BaseCorrectionModel):
    def predict(
        self, material_name: str, theoretical_quantity: float, room_type: str, **features
    ) -> CorrectionResult:
        return CorrectionResult(correction_factor=1.0, correction_confidence=CorrectionConfidence.FALLBACK)


def get_active_correction_model(db: Session) -> BaseCorrectionModel:
    active = db.query(ModelVersion).filter(ModelVersion.status == ModelVersionStatus.ACTIVE).first()
    if active is None or active.model_version == "fallback-constant-1.0":
        return FallbackCorrectionModel()
    # Future: deserialize the real trained artifact keyed by active.model_version
    # (e.g. a median-lookup-by-(room_type, material_category) table, later a
    # regularized tree ensemble) and wrap it in an adapter implementing
    # BaseCorrectionModel. Not built yet — no real model has been trained.
    return FallbackCorrectionModel()
