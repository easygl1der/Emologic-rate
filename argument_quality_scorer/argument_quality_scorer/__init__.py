"""
ArgumentQualityScorer - 文本论述质量评估工具

对输入文本进行"论述质量/严谨程度"评估并打分，
区分"情绪化泛泛而谈 vs 有理有据、逻辑清晰、可核查"。
"""

__version__ = "0.1.0"
__author__ = "ArgumentQualityScorer Team"

from .schema import (
    ScoreReport,
    Highlight,
    Diagnostic,
    SegmentScore,
    ScoreBreakdown,
)
from .scorer import ArgumentQualityScorer

__all__ = [
    "ArgumentQualityScorer",
    "ScoreReport",
    "Highlight",
    "Diagnostic",
    "SegmentScore",
    "ScoreBreakdown",
]
