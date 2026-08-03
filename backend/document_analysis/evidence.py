from dataclasses import dataclass
from typing import Optional


@dataclass
class Evidence:

    # Name of the forensic module
    module: str

    # Suspicion score
    # 0.0 = no suspicious evidence
    # 1.0 = very strong suspicious evidence
    score: float

    # Reliability of this module's result
    # 0.0 = unreliable
    # 1.0 = highly reliable
    confidence: float

    # LOW / MEDIUM / HIGH / CRITICAL
    severity: str

    # Human-readable explanation
    reason: str

    # Optional location
    location: Optional[str] = None

    def __post_init__(self):

        # Keep values within valid range
        self.score = max(
            0.0,
            min(
                1.0,
                float(self.score)
            )
        )

        self.confidence = max(
            0.0,
            min(
                1.0,
                float(self.confidence)
            )
        )

        self.severity = str(
            self.severity
        ).upper()

        self.module = str(
            self.module
        )

        self.reason = str(
            self.reason
        )

    def weighted_score(self):

        return (

            self.score

            *

            self.confidence

        )

    def to_dict(self):

        return {

            "module":
                self.module,

            "score":
                round(
                    self.score,
                    4
                ),

            "confidence":
                round(
                    self.confidence,
                    4
                ),

            "severity":
                self.severity,

            "reason":
                self.reason,

            "location":
                self.location,

            "weighted_score":
                round(
                    self.weighted_score(),
                    4
                )

        }