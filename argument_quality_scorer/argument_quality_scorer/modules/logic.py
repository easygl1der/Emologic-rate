"""
逻辑/谬误模块（Logic Module）

识别论证结构缺失、跳步、常见谬误倾向：
- 人身攻击（Ad Hominem）
- 诉诸权威（Appeal to Authority）
- 稻草人谬误（Straw Man）
- 滑坡谬误（Slippery Slope）
- 以偏概全（Hasty Generalization）
- 假二元对立（False Dilemma）
- 循环论证（Circular Reasoning）

注意：不判断事实真假，只评估论证结构。
"""

import re
from .base import BaseModule, ModuleResult
from ..schema import Diagnostic, Highlight, ReasonTag, LogicFeatures


class LogicModule(BaseModule):
    """
    逻辑/谬误分析模块
    
    使用规则检测常见逻辑谬误和论证结构问题。
    """
    
    # 人身攻击模式
    AD_HOMINEM_PATTERNS = [
        r"(你|他|她|他们)(这种人|这样的人|之流|一类人)",
        r"(就凭|就你|就他|就她)(这样|那样|还)",
        r"什么(资格|身份|立场)(说|评|讲)",
        r"(屁股|立场|位置)决定(脑袋|观点|想法)",
        r"(拿钱|收钱|被买通)",
        r"(水军|五毛|公知|带路党|汉奸)",
    ]
    
    # 诉诸权威模式
    APPEAL_TO_AUTHORITY_PATTERNS = [
        r"(专家|教授|院士|大师|名人|明星)(说|认为|表示).*?所以",
        r"(权威|官方|正式)(说法|观点|结论)",
        r"连.*?都(说|认为|承认)",
        r"(马云|马化腾|李彦宏|任正非|雷军)说",
        r"(爱因斯坦|牛顿|霍金)(说|曾说|认为)",
    ]
    
    # 稻草人谬误模式
    STRAW_MAN_PATTERNS = [
        r"(你|他们|对方)(的意思|意思是说|无非是说|不就是)",
        r"按(你|他们)的(逻辑|说法|意思)",
        r"(换句话说|也就是说|说白了)(.*?)(就是|无非|不过是)",
    ]
    
    # 滑坡谬误模式
    SLIPPERY_SLOPE_PATTERNS = [
        r"(如果|一旦|只要).*?(就会|必然|肯定|迟早).*?(就会|必然|最终)",
        r"(今天|现在).*?(明天|以后|将来).*?(必然|肯定|就会)",
        r"(开了先例|开了口子|打开缺口).*?(以后|将来|迟早)",
        r"(第一步|下一步|接下来).*?(就是|肯定是|必然是)",
    ]
    
    # 以偏概全模式
    HASTY_GENERALIZATION_PATTERNS = [
        r"(所有|全部|一切|任何|每个|凡是).*?(都|全|皆)",
        r"(从来|从没|永远|绝对)(不|没|是)",
        r"(没有一个|没有任何|没有哪个)",
        r"(我认识的|我见过的|我知道的).*?(都|全|没有一个)",
        r"(中国人|美国人|日本人|韩国人)(都|全|没有一个)(是|不)",
    ]
    
    # 假二元对立模式
    FALSE_DILEMMA_PATTERNS = [
        r"(要么|不是).*?(要么|就是)",
        r"(非此即彼|非黑即白|二选一)",
        r"(只有|唯有|只能).*?(才能|才会|才行)",
        r"除了.*?(没有|别无)(其他|别的|选择)",
    ]
    
    # 循环论证模式
    CIRCULAR_REASONING_PATTERNS = [
        r"(因为|由于).*?(所以|因此).*?(因为|由于)",
        r"(之所以|因为).*?(是因为|就是因为).*?(之所以|因为)",
    ]
    
    # 逻辑跳跃标记
    LOGIC_JUMP_PATTERNS = [
        r"(所以|因此|可见|由此可知|综上所述)(?!.*?(因为|由于|根据|基于))",
        r"(不用说|不言自明|显而易见|理所当然)",
    ]
    
    # 论证结构正面标记
    STRUCTURE_POSITIVE_PATTERNS = [
        (r"(首先|第一|一方面)", "has_structure"),
        (r"(其次|第二|另一方面)", "has_structure"),
        (r"(最后|第三|总之|综上)", "has_conclusion"),
        (r"(因为|由于|原因是|理由是)", "has_reasoning"),
        (r"(所以|因此|故而|可以得出)", "has_conclusion"),
        (r"(我(的)?观点|我认为.*?(是|在于)|本文(认为|主张))", "has_claim"),
        (r"(论点|主张|核心观点)(是|在于|为)", "has_claim"),
        (r"(根据|基于|依据).*?(数据|研究|事实|证据)", "has_evidence_link"),
        (r"(虽然|尽管).*?(但是|然而|不过)", "has_qualification"),
    ]
    
    # 谬误类型映射
    FALLACY_PATTERNS = {
        ReasonTag.AD_HOMINEM: AD_HOMINEM_PATTERNS,
        ReasonTag.APPEAL_TO_AUTHORITY: APPEAL_TO_AUTHORITY_PATTERNS,
        ReasonTag.STRAW_MAN: STRAW_MAN_PATTERNS,
        ReasonTag.SLIPPERY_SLOPE: SLIPPERY_SLOPE_PATTERNS,
        ReasonTag.HASTY_GENERALIZATION: HASTY_GENERALIZATION_PATTERNS,
        ReasonTag.FALSE_DILEMMA: FALSE_DILEMMA_PATTERNS,
        ReasonTag.CIRCULAR_REASONING: CIRCULAR_REASONING_PATTERNS,
    }
    
    # 谬误描述
    FALLACY_DESCRIPTIONS = {
        ReasonTag.AD_HOMINEM: "人身攻击：攻击论述者本人而非其论点",
        ReasonTag.APPEAL_TO_AUTHORITY: "诉诸权威：仅因权威人士说了就认为正确",
        ReasonTag.STRAW_MAN: "稻草人谬误：歪曲对方观点后进行攻击",
        ReasonTag.SLIPPERY_SLOPE: "滑坡谬误：无根据地推导一连串后果",
        ReasonTag.HASTY_GENERALIZATION: "以偏概全：从少数案例得出普遍结论",
        ReasonTag.FALSE_DILEMMA: "假二元对立：将复杂问题简化为非此即彼",
        ReasonTag.CIRCULAR_REASONING: "循环论证：用结论来证明前提",
    }
    
    @property
    def name(self) -> str:
        return "logic"
    
    def _find_all_matches(
        self, 
        text: str, 
        patterns: list[str]
    ) -> list[tuple[str, int, int]]:
        """查找所有匹配"""
        matches = []
        for pattern in patterns:
            try:
                for m in re.finditer(pattern, text):
                    matches.append((m.group(), m.start(), m.end()))
            except re.error:
                continue
        return matches
    
    def analyze(self, text: str, **kwargs) -> ModuleResult:
        """
        分析文本的逻辑结构和谬误
        
        Returns:
            ModuleResult: 包含逻辑得分和诊断
        """
        diagnostics = []
        highlights = []
        detected_fallacies = []
        
        # 检测各类谬误
        for fallacy_tag, patterns in self.FALLACY_PATTERNS.items():
            matches = self._find_all_matches(text, patterns)
            for matched, start, end in matches:
                detected_fallacies.append(fallacy_tag.value)
                diagnostics.append(Diagnostic(
                    category="logic",
                    reason_tag=fallacy_tag,
                    description=self.FALLACY_DESCRIPTIONS[fallacy_tag],
                    span_text=matched,
                    start_char=start,
                    end_char=end,
                    severity="medium",
                    suggestion="建议检查论证逻辑，避免此类推理偏误"
                ))
                highlights.append(Highlight(
                    span_text=matched,
                    start_char=start,
                    end_char=end,
                    reason_tag=fallacy_tag,
                    is_positive=False
                ))
        
        # 检测逻辑跳跃
        jump_matches = self._find_all_matches(text, self.LOGIC_JUMP_PATTERNS)
        for matched, start, end in jump_matches:
            diagnostics.append(Diagnostic(
                category="logic",
                reason_tag=ReasonTag.LOGIC_JUMP,
                description="可能存在逻辑跳跃，缺少中间推理步骤",
                span_text=matched,
                start_char=start,
                end_char=end,
                severity="low",
                suggestion="建议补充推理过程，说明结论如何得出"
            ))
            highlights.append(Highlight(
                span_text=matched,
                start_char=start,
                end_char=end,
                reason_tag=ReasonTag.LOGIC_JUMP,
                is_positive=False
            ))
        
        # 检测正面结构信号
        structure_signals = {
            "has_claim": False,
            "has_reasoning": False,
            "has_conclusion": False,
            "has_structure": False,
            "has_qualification": False,
            "has_evidence_link": False,
        }
        
        for pattern, signal_type in self.STRUCTURE_POSITIVE_PATTERNS:
            matches = self._find_all_matches(text, [pattern])
            if matches:
                structure_signals[signal_type] = True
                # 只对重要结构添加高亮
                if signal_type in ["has_claim", "has_reasoning", "has_conclusion"]:
                    matched, start, end = matches[0]
                    highlights.append(Highlight(
                        span_text=matched,
                        start_char=start,
                        end_char=end,
                        reason_tag=ReasonTag.CLEAR_REASONING if signal_type == "has_reasoning" 
                                  else ReasonTag.CLEAR_CLAIM if signal_type == "has_claim"
                                  else ReasonTag.WELL_STRUCTURED,
                        is_positive=True
                    ))
        
        # 计算结构完整度
        structure_score = sum([
            structure_signals["has_claim"] * 25,
            structure_signals["has_reasoning"] * 25,
            structure_signals["has_conclusion"] * 20,
            structure_signals["has_structure"] * 15,
            structure_signals["has_qualification"] * 10,
            structure_signals["has_evidence_link"] * 15,
        ])
        
        # 如果有明确的论点和推理，额外加分
        if structure_signals["has_claim"] and structure_signals["has_reasoning"]:
            structure_score += 10
        
        # 计算谬误扣分
        fallacy_count = len(detected_fallacies)
        fallacy_penalty = min(fallacy_count * 15, 60)  # 最多扣 60 分
        
        # 逻辑跳跃扣分
        jump_penalty = min(len(jump_matches) * 8, 30)
        
        # 计算最终逻辑得分
        # 基础分 + 结构分 - 谬误扣分 - 跳跃扣分
        base_score = 30
        score = max(0, min(100, base_score + structure_score - fallacy_penalty - jump_penalty))
        
        # 如果文本太短，调整分数
        if len(text) < 50:
            score = min(score, 50)  # 短文本最高 50 分
        
        # 构建特征
        features = LogicFeatures(
            detected_fallacies=list(set(detected_fallacies)),
            fallacy_count=fallacy_count,
            has_clear_claim=structure_signals["has_claim"],
            has_reasoning=structure_signals["has_reasoning"],
            has_conclusion=structure_signals["has_conclusion"],
            structure_score=round(structure_score, 1)
        )
        
        return ModuleResult(
            score=round(score, 1),
            diagnostics=diagnostics,
            highlights=highlights,
            features=features.model_dump()
        )
