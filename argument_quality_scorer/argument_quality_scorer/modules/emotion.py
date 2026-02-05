"""
情绪化信号模块（Emotion Module）

使用词典法 + 规则检测情绪化信号：
- 情绪词计数（cnsenti）
- 极端化词
- 攻击性语言
- 感叹号/全称量词等

输出：情绪化得分（越高越情绪化），以及触发片段。
"""

import re
from typing import Optional
from .base import BaseModule, ModuleResult
from ..schema import Diagnostic, Highlight, ReasonTag, EmotionFeatures


class EmotionModule(BaseModule):
    """
    情绪化信号分析模块
    
    使用 cnsenti 作为基线，结合规则检测各类情绪化信号。
    """
    
    # 极端化词汇表
    EXTREME_WORDS = [
        "绝对", "肯定", "一定", "必须", "必然", "永远", "从来", "根本",
        "完全", "彻底", "全部", "所有", "任何", "没有任何", "不可能",
        "最", "极其", "非常", "太", "特别", "无比", "极度",
        "总是", "从不", "一直", "始终", "永不",
    ]
    
    # 攻击性/贬义词
    ATTACK_WORDS = [
        "傻", "蠢", "笨", "白痴", "脑残", "智障", "弱智",
        "垃圾", "废物", "渣", "贱", "烂", "臭",
        "滚", "死", "该死", "去死", "狗", "猪", "蠢货",
    ]
    
    # 空泛主观词
    SUBJECTIVE_MARKERS = [
        "我觉得", "我认为", "我感觉", "显然", "明显", "当然",
        "众所周知", "大家都知道", "不用说", "毫无疑问",
        "肯定是", "一看就", "谁都知道",
    ]
    
    def __init__(self, use_senta: bool = False):
        """
        初始化情绪模块
        
        Args:
            use_senta: 是否使用 Baidu Senta（需要 PaddlePaddle）
        """
        self.use_senta = use_senta
        self._cnsenti = None
        self._senta = None
        self._init_backends()
    
    def _init_backends(self):
        """初始化后端分析器"""
        # 初始化 cnsenti
        try:
            from cnsenti import Sentiment, Emotion
            self._sentiment = Sentiment()
            self._emotion = Emotion()
            self._cnsenti = True
        except ImportError:
            print("警告: cnsenti 未安装，情绪分析将使用纯规则模式")
            self._cnsenti = False
        
        # 初始化 Senta（可选）
        if self.use_senta:
            try:
                # Senta 需要 PaddlePaddle，这里只做导入检查
                # 实际使用时需要更复杂的初始化
                import paddle
                self._senta = True
            except ImportError:
                print("警告: PaddlePaddle 未安装，Senta 不可用")
                self._senta = False
    
    @property
    def name(self) -> str:
        return "emotion"
    
    def _count_patterns(self, text: str, patterns: list[str]) -> tuple[int, list[tuple[str, int, int]]]:
        """
        计数模式匹配并返回位置
        
        Returns:
            (count, [(word, start, end), ...])
        """
        matches = []
        for pattern in patterns:
            for m in re.finditer(re.escape(pattern), text):
                matches.append((pattern, m.start(), m.end()))
        return len(matches), matches
    
    def _analyze_with_cnsenti(self, text: str) -> dict:
        """使用 cnsenti 分析"""
        result = {
            "positive_count": 0,
            "negative_count": 0,
            "emotion_counts": {},
            "top_words": []
        }
        
        if not self._cnsenti:
            return result
        
        try:
            # 情感分析
            sentiment_result = self._sentiment.sentiment_count(text)
            result["positive_count"] = sentiment_result.get("pos", 0)
            result["negative_count"] = sentiment_result.get("neg", 0)
            
            # 情绪分类
            emotion_result = self._emotion.emotion_count(text)
            result["emotion_counts"] = emotion_result
            
        except Exception as e:
            print(f"cnsenti 分析出错: {e}")
        
        return result
    
    def analyze(self, text: str, **kwargs) -> ModuleResult:
        """
        分析文本的情绪化程度
        
        Returns:
            ModuleResult: 包含情绪化得分和诊断
        """
        diagnostics = []
        highlights = []
        
        # 基础统计
        total_chars = len(text)
        exclamation_count = text.count("！") + text.count("!")
        question_count = text.count("？") + text.count("?")
        
        # 使用 cnsenti 分析
        cnsenti_result = self._analyze_with_cnsenti(text)
        positive_count = cnsenti_result["positive_count"]
        negative_count = cnsenti_result["negative_count"]
        emotion_counts = cnsenti_result.get("emotion_counts", {})
        
        # 计算情绪词总数
        emotion_word_count = positive_count + negative_count
        
        # 检测极端化词
        extreme_count, extreme_matches = self._count_patterns(text, self.EXTREME_WORDS)
        for word, start, end in extreme_matches:
            diagnostics.append(Diagnostic(
                category="emotion",
                reason_tag=ReasonTag.EXTREME_WORD,
                description=f'使用极端化表述"{word}"，可能过于绝对',
                span_text=word,
                start_char=start,
                end_char=end,
                severity="medium"
            ))
            highlights.append(Highlight(
                span_text=word,
                start_char=start,
                end_char=end,
                reason_tag=ReasonTag.EXTREME_WORD,
                is_positive=False
            ))
        
        # 检测攻击性词汇
        attack_count, attack_matches = self._count_patterns(text, self.ATTACK_WORDS)
        for word, start, end in attack_matches:
            diagnostics.append(Diagnostic(
                category="emotion",
                reason_tag=ReasonTag.ATTACK_LANGUAGE,
                description=f'包含攻击性语言"{word}"',
                span_text=word,
                start_char=start,
                end_char=end,
                severity="high"
            ))
            highlights.append(Highlight(
                span_text=word,
                start_char=start,
                end_char=end,
                reason_tag=ReasonTag.ATTACK_LANGUAGE,
                is_positive=False
            ))
        
        # 检测主观标记
        subjective_count, subjective_matches = self._count_patterns(text, self.SUBJECTIVE_MARKERS)
        for word, start, end in subjective_matches:
            diagnostics.append(Diagnostic(
                category="emotion",
                reason_tag=ReasonTag.SUBJECTIVE_CLAIM,
                description=f'主观断言"{word}"，缺乏客观依据',
                span_text=word,
                start_char=start,
                end_char=end,
                severity="low"
            ))
            highlights.append(Highlight(
                span_text=word,
                start_char=start,
                end_char=end,
                reason_tag=ReasonTag.SUBJECTIVE_CLAIM,
                is_positive=False
            ))
        
        # 检测感叹号过多
        if exclamation_count > 3 or (total_chars > 0 and exclamation_count / total_chars > 0.02):
            # 找到感叹号位置
            for m in re.finditer(r'[！!]+', text):
                diagnostics.append(Diagnostic(
                    category="emotion",
                    reason_tag=ReasonTag.EXCLAMATION,
                    description="感叹号使用较多，可能带有情绪化表达",
                    span_text=m.group(),
                    start_char=m.start(),
                    end_char=m.end(),
                    severity="low"
                ))
        
        # 计算情绪化得分
        # 基础分：情绪词占比
        emotion_ratio = (emotion_word_count / max(total_chars / 2, 1)) * 100 if total_chars > 0 else 0
        
        # 加权计算
        score = min(100, (
            emotion_ratio * 0.3 +
            extreme_count * 8 +
            attack_count * 15 +
            subjective_count * 5 +
            min(exclamation_count * 3, 20)
        ))
        
        # 构建特征
        top_emotion_words = []
        if emotion_counts:
            # 取情绪最多的类别
            sorted_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)
            top_emotion_words = [e[0] for e in sorted_emotions[:5] if e[1] > 0]
        
        features = EmotionFeatures(
            positive_count=positive_count,
            negative_count=negative_count,
            emotion_word_count=emotion_word_count,
            extreme_word_count=extreme_count,
            exclamation_count=exclamation_count,
            question_count=question_count,
            total_chars=total_chars,
            emotion_ratio=round(emotion_ratio, 2),
            top_emotion_words=top_emotion_words
        )
        
        return ModuleResult(
            score=round(score, 1),
            diagnostics=diagnostics,
            highlights=highlights,
            features=features.model_dump()
        )
