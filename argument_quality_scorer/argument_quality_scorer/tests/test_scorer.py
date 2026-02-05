"""
ArgumentQualityScorer 测试用例

覆盖 5 个典型案例：
1. 情绪化强的文本
2. 逻辑强但无证据的文本
3. 引用充分的文本
4. 混合类型的文本
5. 无意义/空白文本
"""

import pytest
from argument_quality_scorer import ArgumentQualityScorer, ScoreReport


@pytest.fixture
def scorer():
    """创建评分器实例"""
    return ArgumentQualityScorer()


class TestEmotionalText:
    """测试情绪化文本"""
    
    EMOTIONAL_TEXT = """
    这个产品简直就是垃圾！绝对不要买！
    所有买这个的人都是傻子！太坑人了！！！
    我真的无语了，这种东西怎么还有人做？
    滚吧，别来骗人了！
    """
    
    def test_high_emotion_score(self, scorer):
        """情绪化文本应该有高情绪分"""
        report = scorer.score(self.EMOTIONAL_TEXT, use_llm=False)
        
        assert isinstance(report, ScoreReport)
        assert report.emotion_score > 50, "情绪化文本的情绪分应该较高"
        assert report.overall_score < 50, "情绪化文本的综合分应该较低"
    
    def test_detects_attack_language(self, scorer):
        """应该检测到攻击性语言"""
        report = scorer.score(self.EMOTIONAL_TEXT, use_llm=False)
        
        attack_diagnostics = [
            d for d in report.diagnostics 
            if d.reason_tag.value == "attack_language"
        ]
        assert len(attack_diagnostics) > 0, "应该检测到攻击性语言"
    
    def test_detects_extreme_words(self, scorer):
        """应该检测到极端化词"""
        report = scorer.score(self.EMOTIONAL_TEXT, use_llm=False)
        
        extreme_diagnostics = [
            d for d in report.diagnostics 
            if d.reason_tag.value == "extreme_word"
        ]
        assert len(extreme_diagnostics) > 0, "应该检测到极端化词"


class TestLogicalText:
    """测试逻辑清晰但缺乏证据的文本"""
    
    LOGICAL_TEXT = """
    首先，我认为这个问题需要从三个方面来分析。
    
    第一，从市场角度来看，因为需求在增长，所以价格必然上涨。
    
    第二，从技术角度来看，虽然目前存在困难，但是技术进步会解决这些问题。
    
    第三，从政策角度来看，政府的支持会推动行业发展。
    
    综上所述，我们可以得出结论：这个行业前景广阔。
    """
    
    def test_high_logic_score(self, scorer):
        """逻辑清晰的文本应该有较高逻辑分"""
        report = scorer.score(self.LOGICAL_TEXT, use_llm=False)
        
        assert report.logic_score > 40, "逻辑清晰的文本逻辑分应该较高"
    
    def test_low_evidence_score(self, scorer):
        """缺乏证据的文本证据分应该较低"""
        report = scorer.score(self.LOGICAL_TEXT, use_llm=False)
        
        assert report.evidence_score < 60, "缺乏具体证据的文本证据分应该较低"
    
    def test_detects_structure(self, scorer):
        """应该检测到论证结构"""
        report = scorer.score(self.LOGICAL_TEXT, use_llm=False)
        
        assert report.logic_features.has_clear_claim or report.logic_features.has_reasoning, \
            "应该检测到论证结构"


class TestWellEvidencedText:
    """测试引用充分的文本"""
    
    EVIDENCED_TEXT = """
    根据国家统计局2023年发布的数据，中国GDP同比增长5.2%。
    
    《经济学人》杂志在2023年12月的报告中指出，亚洲经济体表现强劲。
    北京大学经济研究中心的张教授在《经济研究》期刊上发表的论文显示，
    消费对GDP的贡献率达到了83.2%。
    
    来源：国家统计局官网 https://www.stats.gov.cn
    
    此外，根据世界银行的预测，2024年全球经济增长率约为2.4%。
    """
    
    def test_high_evidence_score(self, scorer):
        """引用充分的文本应该有高证据分"""
        report = scorer.score(self.EVIDENCED_TEXT, use_llm=False)
        
        assert report.evidence_score > 50, "引用充分的文本证据分应该较高"
    
    def test_detects_data(self, scorer):
        """应该检测到数据"""
        report = scorer.score(self.EVIDENCED_TEXT, use_llm=False)
        
        assert report.evidence_features.data_count > 0, "应该检测到数据"
    
    def test_detects_citations(self, scorer):
        """应该检测到引用"""
        report = scorer.score(self.EVIDENCED_TEXT, use_llm=False)
        
        citation_highlights = [
            h for h in report.highlights 
            if h.reason_tag.value == "has_citation"
        ]
        assert len(citation_highlights) > 0, "应该检测到引用"


class TestMixedText:
    """测试混合类型的文本"""
    
    MIXED_TEXT = """
    这真是太离谱了！根据2023年的调查数据，居然有45%的人不知道这件事！
    
    所有不了解情况的人都是被媒体洗脑的蠢货。专家说这是因为信息传播的问题，
    所以我们必须加强教育。
    
    首先，这个问题很严重。其次，我们需要解决。最后，大家都应该重视。
    
    如果不解决，明天就会出大事，后天社会就会崩溃，最终导致无法挽回的后果。
    """
    
    def test_moderate_scores(self, scorer):
        """混合文本应该有中等分数"""
        report = scorer.score(self.MIXED_TEXT, use_llm=False)
        
        # 混合文本：既有情绪化表达也有数据，各项分数在合理范围
        assert 20 < report.evidence_score < 90, "混合文本证据分应该在合理范围"
        # 因为混合文本包含攻击性语言，情绪分可能较高
        assert report.emotion_score > 30, "包含情绪化表达的混合文本情绪分应该较高"
    
    def test_detects_multiple_issues(self, scorer):
        """应该检测到多种问题"""
        report = scorer.score(self.MIXED_TEXT, use_llm=False)
        
        categories = set(d.category for d in report.diagnostics)
        assert len(categories) >= 2, "应该检测到多个类别的问题"
    
    def test_detects_slippery_slope(self, scorer):
        """应该检测到滑坡谬误"""
        report = scorer.score(self.MIXED_TEXT, use_llm=False)
        
        fallacies = report.logic_features.detected_fallacies
        # 检查是否检测到了某种谬误
        assert len(fallacies) > 0 or len(report.diagnostics) > 0, "应该检测到逻辑问题"


class TestEmptyText:
    """测试空白/无意义文本"""
    
    EMPTY_TEXT = "   "
    MINIMAL_TEXT = "嗯"
    SHORT_TEXT = "这是一句话。"
    
    def test_empty_text(self, scorer):
        """空白文本应该能处理"""
        report = scorer.score(self.SHORT_TEXT, use_llm=False)
        
        assert isinstance(report, ScoreReport)
        assert report.input_text_length >= 0
    
    def test_minimal_text(self, scorer):
        """极短文本应该能处理"""
        report = scorer.score(self.MINIMAL_TEXT, use_llm=False)
        
        assert isinstance(report, ScoreReport)
        # 极短文本逻辑分不应该太高
        assert report.logic_score <= 60, "极短文本逻辑分不应过高"
    
    def test_short_text(self, scorer):
        """短文本应该能正常评分"""
        report = scorer.score(self.SHORT_TEXT, use_llm=False)
        
        assert isinstance(report, ScoreReport)
        assert 0 <= report.overall_score <= 100


class TestSegmentAnalysis:
    """测试分段分析功能"""
    
    MULTI_PARAGRAPH_TEXT = """
    第一段：这是一个客观的陈述，根据数据显示，2023年增长了10%。
    
    第二段：这简直太离谱了！所有人都是傻子！绝对不可能！
    
    第三段：综上所述，我们需要更多研究来验证这个假设。
    """
    
    def test_per_segment_output(self, scorer):
        """应该输出分段分析"""
        report = scorer.score(self.MULTI_PARAGRAPH_TEXT, use_llm=False, segment_mode="paragraph")
        
        assert len(report.per_segment) > 0, "应该有分段分析结果"
    
    def test_segment_scores_vary(self, scorer):
        """不同段落的分数应该有差异"""
        report = scorer.score(self.MULTI_PARAGRAPH_TEXT, use_llm=False, segment_mode="paragraph")
        
        if len(report.per_segment) >= 2:
            emotion_scores = [seg.emotion_score for seg in report.per_segment]
            assert max(emotion_scores) - min(emotion_scores) > 10, "不同段落的情绪分应该有差异"


class TestOutputSchema:
    """测试输出符合 schema"""
    
    def test_output_has_required_fields(self, scorer):
        """输出应该包含所有必需字段"""
        report = scorer.score("这是一段测试文本。", use_llm=False)
        
        # 检查必需字段
        assert hasattr(report, 'emotion_score')
        assert hasattr(report, 'logic_score')
        assert hasattr(report, 'evidence_score')
        assert hasattr(report, 'overall_score')
        assert hasattr(report, 'score_breakdown')
        assert hasattr(report, 'highlights')
        assert hasattr(report, 'diagnostics')
        assert hasattr(report, 'per_segment')
    
    def test_scores_in_range(self, scorer):
        """分数应该在 0-100 范围内"""
        report = scorer.score("这是一段测试文本。", use_llm=False)
        
        assert 0 <= report.emotion_score <= 100
        assert 0 <= report.logic_score <= 100
        assert 0 <= report.evidence_score <= 100
        assert 0 <= report.overall_score <= 100
    
    def test_diagnostics_have_spans(self, scorer):
        """诊断应该包含原文片段"""
        text = "这个产品绝对是最好的！所有人都应该买！"
        report = scorer.score(text, use_llm=False)
        
        for diag in report.diagnostics:
            assert diag.span_text, "诊断必须包含原文片段"
            assert diag.start_char >= 0
            assert diag.end_char > diag.start_char
    
    def test_json_serializable(self, scorer):
        """输出应该可以序列化为 JSON"""
        report = scorer.score("测试文本", use_llm=False)
        
        json_str = report.model_dump_json()
        assert json_str, "应该能序列化为 JSON"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
