"""
主评分器 - ArgumentQualityScorer

整合所有模块，生成完整的评分报告。
"""

from typing import Optional
from .schema import (
    ScoreReport, 
    Highlight, 
    Diagnostic, 
    SegmentScore,
    ScoreBreakdown,
    EmotionFeatures,
    LogicFeatures,
    EvidenceFeatures,
)
from .modules import EmotionModule, LogicModule, EvidenceModule, LLMCritic
from .utils.config import Config
from .utils.text_processor import TextProcessor


class ArgumentQualityScorer:
    """
    论述质量评分器
    
    整合情绪、逻辑、证据三个模块，生成综合评分报告。
    支持规则模式和 LLM 增强模式。
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化评分器
        
        Args:
            config: 配置对象，如果为 None 则从环境变量加载
        """
        self.config = config or Config.from_env()
        
        # 初始化模块
        self.emotion_module = EmotionModule(use_senta=self.config.use_senta)
        self.logic_module = LogicModule()
        self.evidence_module = EvidenceModule()
        self.llm_critic = LLMCritic(self.config.llm)
        
        # 文本处理器
        self.text_processor = TextProcessor()
    
    def _calculate_overall_score(
        self,
        emotion_score: float,
        logic_score: float,
        evidence_score: float,
        bonus: float = 0.0,
        penalty: float = 0.0
    ) -> tuple[float, ScoreBreakdown]:
        """
        计算综合得分
        
        公式: overall = w1*logic + w2*evidence - w3*emotion + bonus - penalty
        
        注意：emotion 越高越情绪化（负面），所以要减去
        """
        w = self.config.weights
        
        logic_contribution = w.logic * logic_score
        evidence_contribution = w.evidence * evidence_score
        emotion_penalty = w.emotion * emotion_score
        
        overall = logic_contribution + evidence_contribution - emotion_penalty + bonus - penalty
        
        # 归一化到 0-100
        # 由于 emotion 是减法，理论最低可能为负，最高为 w1*100 + w2*100 + bonus
        # 需要重新映射
        # 简化处理：直接 clamp 到 0-100
        overall = max(0, min(100, overall + 30))  # +30 作为基础偏移
        
        breakdown = ScoreBreakdown(
            logic_contribution=round(logic_contribution, 2),
            evidence_contribution=round(evidence_contribution, 2),
            emotion_penalty=round(emotion_penalty, 2),
            bonus=round(bonus, 2),
            penalty=round(penalty, 2),
            formula=f"overall = {w.logic}*logic + {w.evidence}*evidence - {w.emotion}*emotion + bonus - penalty + 30"
        )
        
        return round(overall, 1), breakdown
    
    def _merge_diagnostics(
        self, 
        *diagnostic_lists: list[Diagnostic]
    ) -> list[Diagnostic]:
        """合并去重诊断列表"""
        seen = set()
        merged = []
        for diag_list in diagnostic_lists:
            for diag in diag_list:
                key = (diag.category, diag.start_char, diag.end_char, diag.reason_tag)
                if key not in seen:
                    seen.add(key)
                    merged.append(diag)
        return sorted(merged, key=lambda d: d.start_char)
    
    def _merge_highlights(
        self, 
        *highlight_lists: list[Highlight]
    ) -> list[Highlight]:
        """合并去重高亮列表"""
        seen = set()
        merged = []
        for hl_list in highlight_lists:
            for hl in hl_list:
                key = (hl.start_char, hl.end_char, hl.reason_tag)
                if key not in seen:
                    seen.add(key)
                    merged.append(hl)
        return sorted(merged, key=lambda h: h.start_char)
    
    def score(
        self, 
        text: str, 
        use_llm: bool = True,
        segment_mode: str = "auto"
    ) -> ScoreReport:
        """
        对文本进行评分
        
        Args:
            text: 输入文本
            use_llm: 是否使用 LLM 增强（默认 True，如果 LLM 不可用会自动降级）
            segment_mode: 分段模式 - "sentence" / "paragraph" / "auto"
        
        Returns:
            ScoreReport: 完整评分报告
        """
        # 清理文本
        cleaned_text = self.text_processor.clean_text(text)
        
        # 全文分析
        emotion_result = self.emotion_module.analyze(cleaned_text)
        logic_result = self.logic_module.analyze(cleaned_text)
        evidence_result = self.evidence_module.analyze(cleaned_text)
        
        # LLM 增强分析
        llm_result = None
        llm_used = False
        
        if use_llm and self.llm_critic.is_available:
            llm_result = self.llm_critic.analyze(
                cleaned_text,
                emotion_features=emotion_result.features,
                logic_features=logic_result.features,
                evidence_features=evidence_result.features
            )
            llm_used = llm_result.features.get("llm_available", False) and \
                       not llm_result.features.get("parse_failed", False)
        
        # 合并分数（如果有 LLM 结果，取加权平均）
        if llm_used and llm_result:
            llm_features = llm_result.features
            # 规则分数权重 0.6，LLM 分数权重 0.4
            emotion_score = emotion_result.score * 0.6 + llm_features.get("llm_emotion_score", emotion_result.score) * 0.4
            logic_score = logic_result.score * 0.6 + llm_features.get("llm_logic_score", logic_result.score) * 0.4
            evidence_score = evidence_result.score * 0.6 + llm_features.get("llm_evidence_score", evidence_result.score) * 0.4
        else:
            emotion_score = emotion_result.score
            logic_score = logic_result.score
            evidence_score = evidence_result.score
        
        # 计算综合分数
        overall_score, breakdown = self._calculate_overall_score(
            emotion_score, logic_score, evidence_score
        )
        
        # 合并诊断和高亮
        all_diagnostics = [
            emotion_result.diagnostics,
            logic_result.diagnostics,
            evidence_result.diagnostics,
        ]
        all_highlights = [
            emotion_result.highlights,
            logic_result.highlights,
            evidence_result.highlights,
        ]
        
        if llm_used and llm_result:
            all_diagnostics.append(llm_result.diagnostics)
            all_highlights.append(llm_result.highlights)
        
        diagnostics = self._merge_diagnostics(*all_diagnostics)
        highlights = self._merge_highlights(*all_highlights)
        
        # 分段分析
        segments = self.text_processor.split_for_analysis(cleaned_text, mode=segment_mode)
        per_segment = []
        
        for seg in segments:
            seg_emotion = self.emotion_module.analyze_segment(seg.text, seg.start_char)
            seg_logic = self.logic_module.analyze_segment(seg.text, seg.start_char)
            seg_evidence = self.evidence_module.analyze_segment(seg.text, seg.start_char)
            
            # 合并该段的诊断
            seg_diagnostics = self._merge_diagnostics(
                seg_emotion.diagnostics,
                seg_logic.diagnostics,
                seg_evidence.diagnostics
            )
            
            per_segment.append(SegmentScore(
                segment_index=seg.index,
                segment_text=seg.text[:200] + "..." if len(seg.text) > 200 else seg.text,
                start_char=seg.start_char,
                end_char=seg.end_char,
                emotion_score=seg_emotion.score,
                logic_score=seg_logic.score,
                evidence_score=seg_evidence.score,
                local_diagnostics=seg_diagnostics
            ))
        
        # 构建特征对象
        emotion_features = EmotionFeatures(**emotion_result.features) if emotion_result.features else EmotionFeatures()
        logic_features = LogicFeatures(**logic_result.features) if logic_result.features else LogicFeatures()
        evidence_features = EvidenceFeatures(**evidence_result.features) if evidence_result.features else EvidenceFeatures()
        
        # 确定分析模式
        if llm_used:
            analysis_mode = "hybrid"
        elif use_llm:
            analysis_mode = "rule_only"  # 请求了 LLM 但不可用
        else:
            analysis_mode = "rule_only"
        
        return ScoreReport(
            emotion_score=round(emotion_score, 1),
            logic_score=round(logic_score, 1),
            evidence_score=round(evidence_score, 1),
            overall_score=overall_score,
            score_breakdown=breakdown,
            highlights=highlights,
            diagnostics=diagnostics,
            emotion_features=emotion_features,
            logic_features=logic_features,
            evidence_features=evidence_features,
            per_segment=per_segment,
            input_text_length=len(cleaned_text),
            segment_count=len(segments),
            analysis_mode=analysis_mode,
            llm_used=llm_used
        )
    
    def score_file(self, file_path: str, **kwargs) -> ScoreReport:
        """
        对文件进行评分
        
        Args:
            file_path: 文件路径
            **kwargs: 传递给 score() 的额外参数
        
        Returns:
            ScoreReport: 完整评分报告
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return self.score(text, **kwargs)
