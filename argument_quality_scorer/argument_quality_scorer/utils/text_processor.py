"""
文本处理模块

支持中文文本的分句、分段处理，特别优化视频字幕稿场景。
"""

import re
from dataclasses import dataclass
from typing import Generator


@dataclass
class TextSegment:
    """文本片段"""
    index: int
    text: str
    start_char: int
    end_char: int
    segment_type: str = "sentence"  # sentence / paragraph


class TextProcessor:
    """
    文本处理器
    
    功能：
    - 中文分句（按句号、问号、感叹号等）
    - 分段处理（按换行符）
    - 字幕稿特殊处理（时间戳清理等）
    """
    
    # 中文句末标点
    SENTENCE_ENDINGS = r'[。！？；…\.\!\?\;]+'
    
    # 段落分隔符
    PARAGRAPH_SEPARATORS = r'\n\s*\n|\n'
    
    # 字幕时间戳模式（常见格式）
    TIMESTAMP_PATTERNS = [
        r'\d{1,2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[,\.]\d{3}',  # SRT
        r'\d{1,2}:\d{2}:\d{2}[,\.]\d{3}',  # 简单时间戳
        r'^\d+\s*$',  # 纯数字行（SRT 序号）
        r'\[[\d:,\.]+\]',  # [00:00:00,000] 格式
    ]
    
    def __init__(self, clean_subtitles: bool = True):
        """
        初始化文本处理器
        
        Args:
            clean_subtitles: 是否清理字幕时间戳等无关内容
        """
        self.clean_subtitles = clean_subtitles
    
    def clean_text(self, text: str) -> str:
        """
        清理文本
        
        - 移除字幕时间戳
        - 规范化空白字符
        - 移除多余空行
        """
        cleaned = text
        
        if self.clean_subtitles:
            for pattern in self.TIMESTAMP_PATTERNS:
                cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)
        
        # 规范化空白
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n\s*\n+', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def split_sentences(self, text: str) -> Generator[TextSegment, None, None]:
        """
        分句处理
        
        按中文句末标点切分，保留标点。
        """
        cleaned = self.clean_text(text)
        
        # 使用正则分句，保留分隔符
        parts = re.split(f'({self.SENTENCE_ENDINGS})', cleaned)
        
        current_pos = 0
        index = 0
        buffer = ""
        
        for i, part in enumerate(parts):
            if not part:
                continue
            
            # 如果是标点，附加到前一个句子
            if re.match(self.SENTENCE_ENDINGS, part):
                buffer += part
                # 输出完整句子
                if buffer.strip():
                    yield TextSegment(
                        index=index,
                        text=buffer.strip(),
                        start_char=current_pos,
                        end_char=current_pos + len(buffer),
                        segment_type="sentence"
                    )
                    index += 1
                current_pos += len(buffer)
                buffer = ""
            else:
                buffer = part
        
        # 处理最后一个没有标点的片段
        if buffer.strip():
            yield TextSegment(
                index=index,
                text=buffer.strip(),
                start_char=current_pos,
                end_char=current_pos + len(buffer),
                segment_type="sentence"
            )
    
    def split_paragraphs(self, text: str) -> Generator[TextSegment, None, None]:
        """
        分段处理
        
        按换行符切分为段落。
        """
        cleaned = self.clean_text(text)
        
        # 按段落分隔符切分
        paragraphs = re.split(self.PARAGRAPH_SEPARATORS, cleaned)
        
        current_pos = 0
        index = 0
        
        for para in paragraphs:
            para = para.strip()
            if para:
                # 在原文中找到实际位置
                actual_start = cleaned.find(para, current_pos)
                if actual_start == -1:
                    actual_start = current_pos
                
                yield TextSegment(
                    index=index,
                    text=para,
                    start_char=actual_start,
                    end_char=actual_start + len(para),
                    segment_type="paragraph"
                )
                index += 1
                current_pos = actual_start + len(para)
    
    def split_for_analysis(
        self, 
        text: str, 
        mode: str = "sentence",
        max_segment_length: int = 500
    ) -> list[TextSegment]:
        """
        为分析切分文本
        
        Args:
            text: 输入文本
            mode: 切分模式 - "sentence" / "paragraph" / "auto"
            max_segment_length: 单个片段最大长度（超过会强制切分）
        
        Returns:
            切分后的片段列表
        """
        if mode == "paragraph":
            segments = list(self.split_paragraphs(text))
        elif mode == "sentence":
            segments = list(self.split_sentences(text))
        else:  # auto
            # 先按段落，如果段落太长再按句子
            segments = []
            for para in self.split_paragraphs(text):
                if len(para.text) > max_segment_length:
                    # 段落太长，进一步按句子切分
                    for sent in self.split_sentences(para.text):
                        # 更新全局位置
                        sent.start_char += para.start_char
                        sent.end_char += para.start_char
                        sent.index = len(segments)
                        segments.append(sent)
                else:
                    para.index = len(segments)
                    segments.append(para)
        
        # 检查过长片段，强制切分
        final_segments = []
        for seg in segments:
            if len(seg.text) > max_segment_length:
                # 强制按字符数切分
                for i in range(0, len(seg.text), max_segment_length):
                    chunk = seg.text[i:i + max_segment_length]
                    final_segments.append(TextSegment(
                        index=len(final_segments),
                        text=chunk,
                        start_char=seg.start_char + i,
                        end_char=seg.start_char + i + len(chunk),
                        segment_type="chunk"
                    ))
            else:
                seg.index = len(final_segments)
                final_segments.append(seg)
        
        return final_segments
    
    def find_span_in_text(
        self, 
        text: str, 
        span_text: str, 
        search_start: int = 0
    ) -> tuple[int, int]:
        """
        在文本中定位片段位置
        
        Returns:
            (start_char, end_char) 或 (-1, -1) 如果未找到
        """
        pos = text.find(span_text, search_start)
        if pos == -1:
            return (-1, -1)
        return (pos, pos + len(span_text))
    
    def get_context(
        self, 
        text: str, 
        start: int, 
        end: int, 
        context_chars: int = 50
    ) -> str:
        """
        获取片段及其上下文
        
        Args:
            text: 原文
            start: 片段起始位置
            end: 片段结束位置
            context_chars: 上下文字符数
        
        Returns:
            带上下文的片段文本
        """
        ctx_start = max(0, start - context_chars)
        ctx_end = min(len(text), end + context_chars)
        
        result = ""
        if ctx_start > 0:
            result += "..."
        result += text[ctx_start:ctx_end]
        if ctx_end < len(text):
            result += "..."
        
        return result
