from __future__ import annotations

from dataclasses import dataclass

from .schemas import RewriteResult


@dataclass
class QualityThresholds:
    min_quality_score: float = 70.0
    min_voice_score: float = 55.0
    min_fact_score: float = 70.0


class QualityGate:
    """
    Simple threshold-based gate.

    Serves as a placeholder until the dedicated validators are extracted from
    the legacy rewriter.
    """

    def __init__(self, thresholds: QualityThresholds | None = None) -> None:
        self.thresholds = thresholds or QualityThresholds()

    def approve(self, result: RewriteResult) -> bool:
        if result.quality_score is not None and result.quality_score < self.thresholds.min_quality_score:
            return False
        if (
            result.voice_consistency_score is not None
            and result.voice_consistency_score < self.thresholds.min_voice_score
        ):
            return False
        if (
            result.fact_preservation_score is not None
            and result.fact_preservation_score < self.thresholds.min_fact_score
        ):
            return False
        return True


