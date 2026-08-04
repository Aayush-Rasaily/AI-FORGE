from dataclasses import dataclass
from typing import Optional


@dataclass
class Evidence:
    """
    Represents one forensic finding produced by an analysis module.

    score:
        Suspicion score between 0.0 and 1.0

    confidence:
        Confidence in the finding between 0.0 and 1.0

    severity:
        LOW / MEDIUM / HIGH / CRITICAL

    reason:
        Human-readable explanation

    location:
        Optional location of suspicious evidence
    """

    module: str
    score: float
    confidence: float
    severity: str
    reason: str
    location: Optional[str] = None

    def __post_init__(self):

        # ---------------------------------------------------------
        # Normalize score
        # ---------------------------------------------------------

        try:
            self.score = float(self.score)
        except Exception:
            self.score = 0.0

        self.score = max(
            0.0,
            min(
                1.0,
                self.score
            )
        )

        # ---------------------------------------------------------
        # Normalize confidence
        # ---------------------------------------------------------

        try:
            self.confidence = float(self.confidence)
        except Exception:
            self.confidence = 0.0

        self.confidence = max(
            0.0,
            min(
                1.0,
                self.confidence
            )
        )

        # ---------------------------------------------------------
        # Normalize strings
        # ---------------------------------------------------------

        self.module = str(
            self.module
        )

        self.severity = str(
            self.severity
        ).upper()

        self.reason = str(
            self.reason
        )

        # ---------------------------------------------------------
        # Normalize location
        # ---------------------------------------------------------

        if self.location is not None:
            self.location = str(
                self.location
            )

    # =============================================================
    # Convert to dictionary
    # =============================================================

    def to_dict(self):

        return {

            "module":
                self.module,

            "score":
                round(
                    float(self.score),
                    4
                ),

            "confidence":
                round(
                    float(self.confidence),
                    4
                ),

            "severity":
                self.severity,

            "reason":
                self.reason,

            "location":
                self.location

        }


__all__ = [
    "Evidence"
]