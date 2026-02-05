"""
证据与可核查性模块（Evidence Module）

检测文本是否给出可核查的证据：
- 数据、数字、百分比
- 引用来源、机构名、研究/论文
- 时间地点、URL/DOI
- 空泛表述检测（"有研究表明"但不给出处）

输出：证据得分（越高越可核查），以及触发片段。
"""

import re
from .base import BaseModule, ModuleResult
from ..schema import Diagnostic, Highlight, ReasonTag, EvidenceFeatures


class EvidenceModule(BaseModule):
    """
    证据与可核查性分析模块
    
    使用规则检测各类证据信号和空泛表述。
    """
    
    # 空泛引用模式（负面信号）
    VAGUE_REFERENCE_PATTERNS = [
        r"有研究表明",
        r"有研究显示",
        r"研究发现",
        r"据研究",
        r"科学家(们)?发现",
        r"专家(们)?(表示|认为|指出)",
        r"有人说",
        r"有人认为",
        r"大家都知道",
        r"众所周知",
        r"常识告诉我们",
        r"事实证明",
        r"显而易见",
        r"不言而喻",
        r"毋庸置疑",
        r"据说",
        r"听说",
        r"有报道称",
        r"相关(研究|报告|数据)",
        r"某(些)?研究",
        r"有关(部门|机构|专家)",
    ]
    
    # 具体引用模式（正面信号）
    CITATION_PATTERNS = [
        r"根据.*?(\d{4}).*?(研究|报告|调查|论文|数据)",
        r"《[^》]+》",  # 书名号引用
        r'"[^"]+[研究|报告|调查]"',  # 引号引用
        r"(发表|刊登)于.*?(杂志|期刊|报|网)",
        r"(来源|出处|引自)[：:].+",
        r"DOI[：:]\s*\d+\.\d+",
        r"ISBN[：:]\s*[\d-]+",
    ]
    
    # 数据/数字模式（正面信号）
    DATA_PATTERNS = [
        r"\d+\.?\d*\s*%",  # 百分比
        r"\d+\.?\d*\s*(万|亿|千|百)",  # 中文数量级
        r"\d{4}\s*年",  # 年份
        r"\d+\s*(月|日|号|天|小时|分钟|秒)",  # 时间
        r"第?\s*\d+\s*(位|名|个|项|条|次)",  # 序数
        r"[\d,]+\s*(人|元|美元|美金|欧元|块)",  # 具体数量
        r"\d+\.?\d*\s*(km|m|cm|mm|kg|g|L|ml)",  # 单位
    ]
    
    # URL/链接模式
    URL_PATTERNS = [
        r"https?://[^\s<>\"]+",
        r"www\.[^\s<>\"]+",
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # 邮箱
    ]
    
    # 机构名模式
    INSTITUTION_PATTERNS = [
        r"(中国|美国|英国|日本|德国|法国)?[^，。！？\s]{2,}(大学|学院|研究院|研究所|实验室|中心)",
        r"(国家|省|市|县)?(统计局|卫生局|教育部|科技部|发改委)",
        r"(世界|国际|联合国|世卫组织|WHO|UNESCO|IMF|WTO)",
        r"(公司|企业|集团|有限公司|股份|Ltd|Inc|Corp)",
    ]
    
    # 具体事实标记
    SPECIFIC_FACT_PATTERNS = [
        r"(位于|坐落于|在)[^，。]+[省市县区镇村路街]",  # 地点
        r"(成立于|建于|始于|创建于)\s*\d+\s*年",  # 时间
        r"(身高|体重|面积|长度|宽度|高度|深度|距离)[为是约]?\s*\d+",  # 具体数值
    ]
    
    @property
    def name(self) -> str:
        return "evidence"
    
    def _find_all_matches(
        self, 
        text: str, 
        patterns: list[str]
    ) -> list[tuple[str, int, int, str]]:
        """
        查找所有匹配
        
        Returns:
            [(matched_text, start, end, pattern), ...]
        """
        matches = []
        for pattern in patterns:
            for m in re.finditer(pattern, text):
                matches.append((m.group(), m.start(), m.end(), pattern))
        return matches
    
    def analyze(self, text: str, **kwargs) -> ModuleResult:
        """
        分析文本的证据可核查性
        
        Returns:
            ModuleResult: 包含证据得分和诊断
        """
        diagnostics = []
        highlights = []
        
        total_chars = len(text)
        
        # 检测空泛引用（负面）
        vague_matches = self._find_all_matches(text, self.VAGUE_REFERENCE_PATTERNS)
        vague_reference_count = len(vague_matches)
        
        for matched, start, end, pattern in vague_matches:
            diagnostics.append(Diagnostic(
                category="evidence",
                reason_tag=ReasonTag.VAGUE_REFERENCE,
                description=f'空泛引用"{matched}"，未提供具体来源',
                span_text=matched,
                start_char=start,
                end_char=end,
                severity="medium",
                suggestion="建议提供具体的研究名称、作者、发表时间或机构"
            ))
            highlights.append(Highlight(
                span_text=matched,
                start_char=start,
                end_char=end,
                reason_tag=ReasonTag.VAGUE_REFERENCE,
                is_positive=False
            ))
        
        # 检测具体引用（正面）
        citation_matches = self._find_all_matches(text, self.CITATION_PATTERNS)
        citation_count = len(citation_matches)
        
        for matched, start, end, pattern in citation_matches:
            diagnostics.append(Diagnostic(
                category="evidence",
                reason_tag=ReasonTag.HAS_CITATION,
                description=f'有具体引用"{matched}"',
                span_text=matched,
                start_char=start,
                end_char=end,
                severity="low"
            ))
            highlights.append(Highlight(
                span_text=matched,
                start_char=start,
                end_char=end,
                reason_tag=ReasonTag.HAS_CITATION,
                is_positive=True
            ))
        
        # 检测数据（正面）
        data_matches = self._find_all_matches(text, self.DATA_PATTERNS)
        data_count = len(data_matches)
        
        # 只标注有意义的数据（避免过多高亮）
        data_highlighted = set()
        for matched, start, end, pattern in data_matches:
            # 避免重复标注相同位置
            if start not in data_highlighted:
                data_highlighted.add(start)
                if len(data_highlighted) <= 10:  # 限制数量
                    highlights.append(Highlight(
                        span_text=matched,
                        start_char=start,
                        end_char=end,
                        reason_tag=ReasonTag.HAS_DATA,
                        is_positive=True
                    ))
        
        if data_count > 0:
            diagnostics.append(Diagnostic(
                category="evidence",
                reason_tag=ReasonTag.HAS_DATA,
                description=f"文本包含 {data_count} 处数据/数字，增加可核查性",
                span_text=data_matches[0][0] if data_matches else "",
                start_char=data_matches[0][1] if data_matches else 0,
                end_char=data_matches[0][2] if data_matches else 1,
                severity="low"
            ))
        
        # 检测 URL/链接
        url_matches = self._find_all_matches(text, self.URL_PATTERNS)
        source_count = len(url_matches)
        
        for matched, start, end, pattern in url_matches:
            diagnostics.append(Diagnostic(
                category="evidence",
                reason_tag=ReasonTag.HAS_CITATION,
                description=f"提供了链接来源",
                span_text=matched,
                start_char=start,
                end_char=end,
                severity="low"
            ))
            highlights.append(Highlight(
                span_text=matched,
                start_char=start,
                end_char=end,
                reason_tag=ReasonTag.HAS_CITATION,
                is_positive=True
            ))
        
        # 检测机构名
        institution_matches = self._find_all_matches(text, self.INSTITUTION_PATTERNS)
        source_count += len(institution_matches)
        
        for matched, start, end, pattern in institution_matches[:5]:  # 限制数量
            highlights.append(Highlight(
                span_text=matched,
                start_char=start,
                end_char=end,
                reason_tag=ReasonTag.HAS_SPECIFIC_FACT,
                is_positive=True
            ))
        
        # 检测具体事实
        fact_matches = self._find_all_matches(text, self.SPECIFIC_FACT_PATTERNS)
        specific_fact_count = len(fact_matches)
        
        for matched, start, end, pattern in fact_matches[:5]:
            diagnostics.append(Diagnostic(
                category="evidence",
                reason_tag=ReasonTag.HAS_SPECIFIC_FACT,
                description=f"包含具体可核查事实",
                span_text=matched,
                start_char=start,
                end_char=end,
                severity="low"
            ))
            highlights.append(Highlight(
                span_text=matched,
                start_char=start,
                end_char=end,
                reason_tag=ReasonTag.HAS_SPECIFIC_FACT,
                is_positive=True
            ))
        
        # 计算证据得分
        # 正面信号加分，负面信号减分
        positive_signals = (
            citation_count * 15 +
            data_count * 5 +
            source_count * 10 +
            specific_fact_count * 8
        )
        
        negative_signals = vague_reference_count * 12
        
        # 基础分 + 正面 - 负面，限制在 0-100
        base_score = 30  # 基础分
        score = min(100, max(0, base_score + positive_signals - negative_signals))
        
        # 如果几乎没有任何证据信号，给低分
        if positive_signals == 0 and total_chars > 100:
            score = min(score, 20)
            diagnostics.append(Diagnostic(
                category="evidence",
                reason_tag=ReasonTag.NO_SOURCE,
                description="文本缺乏可核查的证据、数据或引用来源",
                span_text=text[:50] + "..." if len(text) > 50 else text,
                start_char=0,
                end_char=min(50, len(text)),
                severity="medium",
                suggestion="建议添加具体数据、引用来源或可核查的事实"
            ))
        
        # 计算可核查比例
        verifiable_chars = sum(len(m[0]) for m in data_matches + citation_matches + fact_matches)
        verifiable_ratio = (verifiable_chars / total_chars * 100) if total_chars > 0 else 0
        
        features = EvidenceFeatures(
            data_count=data_count,
            citation_count=citation_count,
            source_count=source_count,
            vague_reference_count=vague_reference_count,
            specific_fact_count=specific_fact_count,
            verifiable_ratio=round(verifiable_ratio, 2)
        )
        
        return ModuleResult(
            score=round(score, 1),
            diagnostics=diagnostics,
            highlights=highlights,
            features=features.model_dump()
        )
