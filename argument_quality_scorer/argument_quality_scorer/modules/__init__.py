"""分析模块"""
from .base import BaseModule
from .emotion import EmotionModule
from .logic import LogicModule
from .evidence import EvidenceModule
from .llm_critic import LLMCritic

__all__ = [
    "BaseModule",
    "EmotionModule", 
    "LogicModule",
    "EvidenceModule",
    "LLMCritic",
]
