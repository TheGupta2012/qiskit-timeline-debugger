"""Implements enum for the transpiler passes.
"""

from enum import Enum


class PassType(Enum):
    """Defines the analysis and transformation passes
    as enums.
    """

    ANALYSIS = "Analysis"
    TRANSFORMATION = "Transformation"
