"""
数据模型定义 - 使用 Pydantic v2 进行 JSON Schema 校验

所有输出必须符合此 schema，确保可解释性与可追溯性。
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ReasonTag(str, Enum):
    """诊断标签类型"""
    # 情绪化相关
    EMOTIONAL_WORD = "emotional_word"  # 情绪词
    EXTREME_WORD = "extreme_word"  # 极端化词
    EXCLAMATION = "exclamation"  # 感叹号过多
    ATTACK_LANGUAGE = "attack_language"  # 攻击性语言
    SUBJECTIVE_CLAIM = "subjective_claim"  # 主观断言
    
    # 逻辑相关
    AD_HOMINEM = "ad_hominem"  # 人身攻击
    APPEAL_TO_AUTHORITY = "appeal_to_authority"  # 诉诸权威
    STRAW_MAN = "straw_man"  # 稻草人谬误
    SLIPPERY_SLOPE = "slippery_slope"  # 滑坡谬误
    HASTY_GENERALIZATION = "hasty_generalization"  # 以偏概全
    FALSE_DILEMMA = "false_dilemma"  # 假二元对立
    CIRCULAR_REASONING = "circular_reasoning"  # 循环论证
    LOGIC_JUMP = "logic_jump"  # 逻辑跳跃
    MISSING_PREMISE = "missing_premise"  # 缺失前提
    
    # 证据相关
    VAGUE_REFERENCE = "vague_reference"  # 空泛引用（如"有研究表明"）
    NO_SOURCE = "no_source"  # 无来源
    UNVERIFIABLE = "unverifiable"  # 不可核查
    HAS_DATA = "has_data"  # 有数据支撑（正面）
    HAS_CITATION = "has_citation"  # 有引用来源（正面）
    HAS_SPECIFIC_FACT = "has_specific_fact"  # 有具体事实（正面）
    
    # 结构相关
    CLEAR_CLAIM = "clear_claim"  # 清晰论点（正面）
    CLEAR_REASONING = "clear_reasoning"  # 清晰推理（正面）
    WELL_STRUCTURED = "well_structured"  # 结构完整（正面）


class Highlight(BaseModel):
    """高亮片段 - 用于标记问题/亮点位置"""
    span_text: str = Field(..., description="原文片段文本")
    start_char: int = Field(..., ge=0, description="片段起始字符位置")
    end_char: int = Field(..., gt=0, description="片段结束字符位置")
    reason_tag: ReasonTag = Field(..., description="标签类型")
    is_positive: bool = Field(default=False, description="是否为正面标记")
    
    @field_validator("end_char")
    @classmethod
    def end_must_be_greater_than_start(cls, v, info):
        if "start_char" in info.data and v <= info.data["start_char"]:
            raise ValueError("end_char must be greater than start_char")
        return v


class Diagnostic(BaseModel):
    """诊断条目 - 每条诊断必须引用原文片段"""
    category: str = Field(..., description="诊断类别：emotion/logic/evidence")
    reason_tag: ReasonTag = Field(..., description="具体标签")
    description: str = Field(..., description="诊断描述")
    span_text: str = Field(..., description="触发此诊断的原文片段")
    start_char: int = Field(..., ge=0, description="片段起始字符位置")
    end_char: int = Field(..., gt=0, description="片段结束字符位置")
    severity: str = Field(default="medium", description="严重程度：low/medium/high")
    suggestion: Optional[str] = Field(default=None, description="改进建议")


class ScoreBreakdown(BaseModel):
    """评分分解 - 说明各项贡献值"""
    logic_contribution: float = Field(..., description="逻辑分贡献")
    evidence_contribution: float = Field(..., description="证据分贡献")
    emotion_penalty: float = Field(..., description="情绪化扣分")
    bonus: float = Field(default=0.0, description="额外加分")
    penalty: float = Field(default=0.0, description="额外扣分")
    formula: str = Field(..., description="计算公式说明")


class EmotionFeatures(BaseModel):
    """情绪化特征详情"""
    positive_count: int = Field(default=0, description="正面情感词数量")
    negative_count: int = Field(default=0, description="负面情感词数量")
    emotion_word_count: int = Field(default=0, description="情绪词总数")
    extreme_word_count: int = Field(default=0, description="极端化词数量")
    exclamation_count: int = Field(default=0, description="感叹号数量")
    question_count: int = Field(default=0, description="问号数量")
    total_chars: int = Field(default=0, description="总字符数")
    emotion_ratio: float = Field(default=0.0, description="情绪词占比")
    top_emotion_words: list[str] = Field(default_factory=list, description="主要情绪词")


class LogicFeatures(BaseModel):
    """逻辑特征详情"""
    detected_fallacies: list[str] = Field(default_factory=list, description="检测到的谬误类型")
    fallacy_count: int = Field(default=0, description="谬误数量")
    has_clear_claim: bool = Field(default=False, description="是否有清晰论点")
    has_reasoning: bool = Field(default=False, description="是否有推理过程")
    has_conclusion: bool = Field(default=False, description="是否有结论")
    structure_score: float = Field(default=0.0, description="结构完整度")


class EvidenceFeatures(BaseModel):
    """证据特征详情"""
    data_count: int = Field(default=0, description="数据/数字数量")
    citation_count: int = Field(default=0, description="引用数量")
    source_count: int = Field(default=0, description="来源提及数量")
    vague_reference_count: int = Field(default=0, description="空泛引用数量")
    specific_fact_count: int = Field(default=0, description="具体事实数量")
    verifiable_ratio: float = Field(default=0.0, description="可核查内容占比")


class SegmentScore(BaseModel):
    """分段评分 - 用于定位视频哪里有问题"""
    segment_index: int = Field(..., description="段落索引")
    segment_text: str = Field(..., description="段落文本")
    start_char: int = Field(..., ge=0, description="段落起始位置")
    end_char: int = Field(..., gt=0, description="段落结束位置")
    emotion_score: float = Field(..., ge=0, le=100, description="情绪化得分")
    logic_score: float = Field(..., ge=0, le=100, description="逻辑得分")
    evidence_score: float = Field(..., ge=0, le=100, description="证据得分")
    local_diagnostics: list[Diagnostic] = Field(default_factory=list, description="局部诊断")


class ScoreReport(BaseModel):
    """
    完整评分报告 - 主输出结构
    
    所有诊断都锚定到原文片段，确保可解释性。
    """
    # 核心分数
    emotion_score: float = Field(
        ..., ge=0, le=100, 
        description="情绪化得分（0-100，越高越情绪化/主观化）"
    )
    logic_score: float = Field(
        ..., ge=0, le=100,
        description="逻辑得分（0-100，越高越逻辑清晰/结构完整）"
    )
    evidence_score: float = Field(
        ..., ge=0, le=100,
        description="证据得分（0-100，越高越可核查/引用充分）"
    )
    overall_score: float = Field(
        ..., ge=0, le=100,
        description="综合得分（0-100，越高越严谨有据）"
    )
    
    # 评分分解
    score_breakdown: ScoreBreakdown = Field(..., description="评分详细分解")
    
    # 高亮与诊断（必须引用原文）
    highlights: list[Highlight] = Field(
        default_factory=list,
        description="问题/亮点原文片段数组"
    )
    diagnostics: list[Diagnostic] = Field(
        default_factory=list,
        description="诊断列表（每条必须引用原文片段）"
    )
    
    # 特征详情
    emotion_features: EmotionFeatures = Field(
        default_factory=EmotionFeatures,
        description="情绪化特征详情"
    )
    logic_features: LogicFeatures = Field(
        default_factory=LogicFeatures,
        description="逻辑特征详情"
    )
    evidence_features: EvidenceFeatures = Field(
        default_factory=EvidenceFeatures,
        description="证据特征详情"
    )
    
    # 分段评分
    per_segment: list[SegmentScore] = Field(
        default_factory=list,
        description="每段/每句的局部诊断与分数"
    )
    
    # 元信息
    input_text_length: int = Field(..., description="输入文本长度")
    segment_count: int = Field(..., description="段落数量")
    analysis_mode: str = Field(
        default="hybrid",
        description="分析模式：rule_only/llm_only/hybrid"
    )
    llm_used: bool = Field(default=False, description="是否使用了 LLM")
    
    class Config:
        json_schema_extra = {
            "example": {
                "emotion_score": 45.5,
                "logic_score": 62.0,
                "evidence_score": 38.0,
                "overall_score": 51.2,
                "score_breakdown": {
                    "logic_contribution": 21.7,
                    "evidence_contribution": 13.3,
                    "emotion_penalty": 13.65,
                    "bonus": 5.0,
                    "penalty": 0.0,
                    "formula": "overall = 0.35*logic + 0.35*evidence - 0.30*emotion + bonus - penalty"
                },
                "highlights": [],
                "diagnostics": [],
                "input_text_length": 500,
                "segment_count": 5,
                "analysis_mode": "hybrid",
                "llm_used": True
            }
        }
