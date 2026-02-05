"""
配置管理模块

支持从环境变量和 .env 文件加载配置
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


@dataclass
class LLMConfig:
    """LLM 配置"""
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    model: str = "glm-4-flash"
    timeout: int = 30
    max_tokens: int = 4096
    temperature: float = 0.3
    
    @property
    def is_available(self) -> bool:
        """检查 LLM 是否可用"""
        return bool(self.api_base and self.api_key)


@dataclass
class ScoreWeights:
    """评分权重配置"""
    logic: float = 0.35
    evidence: float = 0.35
    emotion: float = 0.30
    
    def validate(self):
        """验证权重合理性"""
        total = self.logic + self.evidence + self.emotion
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"权重之和应接近 1.0，当前为 {total}")


@dataclass
class Config:
    """全局配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    use_senta: bool = False
    debug: bool = False
    
    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> "Config":
        """从环境变量加载配置"""
        # 加载 .env 文件
        if env_file:
            load_dotenv(env_file)
        else:
            # 尝试多个可能的位置
            for path in [
                Path.cwd() / ".env",
                Path(__file__).parent.parent.parent / ".env",
            ]:
                if path.exists():
                    load_dotenv(path)
                    break
        
        # LLM 配置
        llm_config = LLMConfig(
            api_base=os.getenv("LLM_API_BASE"),
            api_key=os.getenv("LLM_API_KEY"),
            model=os.getenv("LLM_MODEL", "glm-4-flash"),
            timeout=int(os.getenv("LLM_TIMEOUT", "30")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
        )
        
        # 权重配置
        weights = ScoreWeights(
            logic=float(os.getenv("WEIGHT_LOGIC", "0.35")),
            evidence=float(os.getenv("WEIGHT_EVIDENCE", "0.35")),
            emotion=float(os.getenv("WEIGHT_EMOTION", "0.30")),
        )
        
        return cls(
            llm=llm_config,
            weights=weights,
            use_senta=os.getenv("USE_SENTA", "false").lower() == "true",
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )
    
    def to_dict(self) -> dict:
        """导出为字典"""
        return {
            "llm": {
                "api_base": self.llm.api_base,
                "model": self.llm.model,
                "is_available": self.llm.is_available,
            },
            "weights": {
                "logic": self.weights.logic,
                "evidence": self.weights.evidence,
                "emotion": self.weights.emotion,
            },
            "use_senta": self.use_senta,
            "debug": self.debug,
        }
