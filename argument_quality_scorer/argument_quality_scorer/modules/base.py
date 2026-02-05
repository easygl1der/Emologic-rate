"""
模块基类

所有分析模块的抽象基类，定义统一接口。
"""

from abc import ABC, abstractmethod
from typing import Any
from ..schema import Diagnostic, Highlight


class ModuleResult:
    """模块分析结果"""
    def __init__(
        self,
        score: float,
        diagnostics: list[Diagnostic] = None,
        highlights: list[Highlight] = None,
        features: dict[str, Any] = None
    ):
        self.score = score
        self.diagnostics = diagnostics or []
        self.highlights = highlights or []
        self.features = features or {}


class BaseModule(ABC):
    """
    分析模块基类
    
    所有模块必须实现 analyze 方法，返回统一格式的结果。
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """模块名称"""
        pass
    
    @abstractmethod
    def analyze(self, text: str, **kwargs) -> ModuleResult:
        """
        分析文本
        
        Args:
            text: 输入文本
            **kwargs: 额外参数
        
        Returns:
            ModuleResult: 分析结果，包含分数、诊断、高亮、特征
        """
        pass
    
    def analyze_segment(self, segment_text: str, offset: int = 0, **kwargs) -> ModuleResult:
        """
        分析单个片段（用于分段分析）
        
        Args:
            segment_text: 片段文本
            offset: 片段在原文中的偏移量
            **kwargs: 额外参数
        
        Returns:
            ModuleResult: 分析结果（位置已调整为全局位置）
        """
        result = self.analyze(segment_text, **kwargs)
        
        # 调整位置偏移
        for diag in result.diagnostics:
            diag.start_char += offset
            diag.end_char += offset
        
        for hl in result.highlights:
            hl.start_char += offset
            hl.end_char += offset
        
        return result
