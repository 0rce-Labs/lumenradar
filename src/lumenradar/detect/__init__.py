"""Detection engine for covert optical signaling.

Three independent detectors combined by ``lumenradar.verdict``:
M1 narrow-band periodicity, M2 burst pulse-count structure, M3 session-baseline
spectral comparison — plus an artifact-rejection layer (auto-exposure hunting,
mains-flicker aliases).
"""

from .artifacts import ArtifactResult, classify, mains_alias_match, mains_aliases
from .baseline import BaselineResult, baseline_compare
from .burst import BurstResult, detect_bursts
from .periodicity import PeriodicityResult, band_periodicity

__all__ = [
    "ArtifactResult",
    "BaselineResult",
    "BurstResult",
    "PeriodicityResult",
    "band_periodicity",
    "baseline_compare",
    "classify",
    "detect_bursts",
    "mains_alias_match",
    "mains_aliases",
]
