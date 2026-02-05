"""
LLM 解释器（LLM Critic）

使用 LLM 进行更高质量的结构化分析与解释。
支持任何 OpenAI-compatible API（如 GLM-4-Flash、Perplexity 等）。
"""

import json
import re
from typing import Optional
import httpx

from .base import BaseModule, ModuleResult
from ..schema import Diagnostic, Highlight, ReasonTag
from ..utils.config import LLMConfig


class LLMCritic(BaseModule):
    """
    LLM 批判性分析模块
    
    使用 LLM 进行深度分析，要求输出结构化 JSON 并引用原文。
    """
    
    SYSTEM_PROMPT = """你是一个专业的文本论述质量分析师。你的任务是分析输入文本的论述质量，从三个维度评估：
1. 情绪化程度：是否过于主观、情绪化、使用煽动性语言
2. 逻辑严谨性：论证是否完整、是否存在逻辑谬误
3. 证据可核查性：是否提供可核查的证据、数据、来源

重要规则：
- 你的每条诊断都必须引用原文具体片段（span_text）
- 不要泛泛而谈，必须指出具体问题所在
- 不要判断事实真假，只评估论述质量
- 使用中文回复"""

    ANALYSIS_PROMPT = """请分析以下文本的论述质量，并以严格的 JSON 格式输出。

待分析文本：
\"\"\"
{text}
\"\"\"

已检测到的规则特征（供参考）：
- 情绪化特征：{emotion_features}
- 逻辑特征：{logic_features}
- 证据特征：{evidence_features}

请输出以下 JSON 格式（不要添加任何其他内容）：
{{
  "emotion_analysis": {{
    "score": 0-100的数字（越高越情绪化）,
    "issues": [
      {{
        "span_text": "原文中的具体片段",
        "reason": "情绪化原因说明",
        "severity": "low/medium/high"
      }}
    ]
  }},
  "logic_analysis": {{
    "score": 0-100的数字（越高越逻辑清晰）,
    "strengths": [
      {{
        "span_text": "原文中体现逻辑清晰的片段",
        "reason": "为什么这是好的论证"
      }}
    ],
    "issues": [
      {{
        "span_text": "原文中的具体片段",
        "fallacy_type": "谬误类型（如人身攻击、以偏概全等）",
        "reason": "问题说明",
        "severity": "low/medium/high"
      }}
    ]
  }},
  "evidence_analysis": {{
    "score": 0-100的数字（越高越有证据支撑）,
    "verified_claims": [
      {{
        "claim": "文中的主张",
        "evidence": "支撑该主张的证据（如果有）",
        "is_verifiable": true/false
      }}
    ],
    "issues": [
      {{
        "span_text": "缺乏证据的断言片段",
        "reason": "为什么这缺乏可核查性",
        "suggestion": "改进建议"
      }}
    ]
  }},
  "overall_assessment": "整体评价，50字以内"
}}"""

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初始化 LLM Critic
        
        Args:
            config: LLM 配置，如果为 None 则不可用
        """
        self.config = config
        self._client = None
        
        if config and config.is_available:
            self._client = httpx.Client(timeout=config.timeout)
    
    @property
    def name(self) -> str:
        return "llm_critic"
    
    @property
    def is_available(self) -> bool:
        """检查 LLM 是否可用"""
        return self._client is not None and self.config and self.config.is_available
    
    def _call_llm(self, messages: list[dict]) -> Optional[str]:
        """调用 LLM API"""
        if not self.is_available:
            return None
        
        try:
            # 构建请求
            url = f"{self.config.api_base}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }
            
            response = self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return None
    
    def _parse_json_response(self, response: str) -> Optional[dict]:
        """解析 LLM 返回的 JSON"""
        if not response:
            return None
        
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _find_span_position(self, text: str, span_text: str) -> tuple[int, int]:
        """在原文中查找片段位置"""
        pos = text.find(span_text)
        if pos == -1:
            # 尝试模糊匹配
            for i in range(len(text) - len(span_text) + 1):
                if text[i:i+len(span_text)].replace(" ", "") == span_text.replace(" ", ""):
                    return (i, i + len(span_text))
            return (0, min(len(span_text), len(text)))
        return (pos, pos + len(span_text))
    
    def analyze(
        self, 
        text: str, 
        emotion_features: dict = None,
        logic_features: dict = None,
        evidence_features: dict = None,
        **kwargs
    ) -> ModuleResult:
        """
        使用 LLM 分析文本
        
        Args:
            text: 输入文本
            emotion_features: 已检测的情绪特征
            logic_features: 已检测的逻辑特征
            evidence_features: 已检测的证据特征
        
        Returns:
            ModuleResult: LLM 分析结果
        """
        if not self.is_available:
            return ModuleResult(
                score=0,
                diagnostics=[],
                highlights=[],
                features={"llm_available": False}
            )
        
        # 构建 prompt
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.ANALYSIS_PROMPT.format(
                text=text[:4000],  # 限制长度
                emotion_features=json.dumps(emotion_features or {}, ensure_ascii=False),
                logic_features=json.dumps(logic_features or {}, ensure_ascii=False),
                evidence_features=json.dumps(evidence_features or {}, ensure_ascii=False)
            )}
        ]
        
        # 调用 LLM
        response = self._call_llm(messages)
        parsed = self._parse_json_response(response)
        
        if not parsed:
            return ModuleResult(
                score=0,
                diagnostics=[],
                highlights=[],
                features={"llm_available": True, "parse_failed": True}
            )
        
        # 解析结果
        diagnostics = []
        highlights = []
        
        # 处理情绪分析结果
        emotion_data = parsed.get("emotion_analysis", {})
        for issue in emotion_data.get("issues", []):
            span_text = issue.get("span_text", "")
            start, end = self._find_span_position(text, span_text)
            diagnostics.append(Diagnostic(
                category="emotion",
                reason_tag=ReasonTag.EMOTIONAL_WORD,
                description=issue.get("reason", "情绪化表达"),
                span_text=span_text,
                start_char=start,
                end_char=end,
                severity=issue.get("severity", "medium")
            ))
        
        # 处理逻辑分析结果
        logic_data = parsed.get("logic_analysis", {})
        
        for strength in logic_data.get("strengths", []):
            span_text = strength.get("span_text", "")
            start, end = self._find_span_position(text, span_text)
            highlights.append(Highlight(
                span_text=span_text,
                start_char=start,
                end_char=end,
                reason_tag=ReasonTag.CLEAR_REASONING,
                is_positive=True
            ))
        
        fallacy_map = {
            "人身攻击": ReasonTag.AD_HOMINEM,
            "诉诸权威": ReasonTag.APPEAL_TO_AUTHORITY,
            "稻草人": ReasonTag.STRAW_MAN,
            "滑坡": ReasonTag.SLIPPERY_SLOPE,
            "以偏概全": ReasonTag.HASTY_GENERALIZATION,
            "假二元": ReasonTag.FALSE_DILEMMA,
            "循环论证": ReasonTag.CIRCULAR_REASONING,
        }
        
        for issue in logic_data.get("issues", []):
            span_text = issue.get("span_text", "")
            start, end = self._find_span_position(text, span_text)
            fallacy_type = issue.get("fallacy_type", "")
            reason_tag = ReasonTag.LOGIC_JUMP
            for key, tag in fallacy_map.items():
                if key in fallacy_type:
                    reason_tag = tag
                    break
            
            diagnostics.append(Diagnostic(
                category="logic",
                reason_tag=reason_tag,
                description=f"{fallacy_type}: {issue.get('reason', '')}",
                span_text=span_text,
                start_char=start,
                end_char=end,
                severity=issue.get("severity", "medium")
            ))
        
        # 处理证据分析结果
        evidence_data = parsed.get("evidence_analysis", {})
        for issue in evidence_data.get("issues", []):
            span_text = issue.get("span_text", "")
            start, end = self._find_span_position(text, span_text)
            diagnostics.append(Diagnostic(
                category="evidence",
                reason_tag=ReasonTag.NO_SOURCE,
                description=issue.get("reason", "缺乏证据支撑"),
                span_text=span_text,
                start_char=start,
                end_char=end,
                severity="medium",
                suggestion=issue.get("suggestion")
            ))
        
        # 计算综合分数（基于 LLM 返回的分数）
        llm_emotion_score = emotion_data.get("score", 50)
        llm_logic_score = logic_data.get("score", 50)
        llm_evidence_score = evidence_data.get("score", 50)
        
        features = {
            "llm_available": True,
            "llm_emotion_score": llm_emotion_score,
            "llm_logic_score": llm_logic_score,
            "llm_evidence_score": llm_evidence_score,
            "overall_assessment": parsed.get("overall_assessment", ""),
            "verified_claims": evidence_data.get("verified_claims", [])
        }
        
        # 综合分数：使用 LLM 的评分作为参考
        combined_score = (llm_logic_score + llm_evidence_score) / 2
        
        return ModuleResult(
            score=round(combined_score, 1),
            diagnostics=diagnostics,
            highlights=highlights,
            features=features
        )
    
    def __del__(self):
        """清理资源"""
        if self._client:
            self._client.close()
