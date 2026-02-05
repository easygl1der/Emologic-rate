"""
命令行接口

用法:
    python -m argument_quality_scorer score --input file.txt --format json
    aqs score --input file.txt --format json
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from .scorer import ArgumentQualityScorer
from .utils.config import Config

console = Console()


def print_score_report(report, format: str = "rich"):
    """打印评分报告"""
    if format == "json":
        # 使用 json.dumps 确保中文正确显示
        click.echo(json.dumps(report.model_dump(), indent=2, ensure_ascii=False))
        return
    
    # Rich 格式输出
    console.print()
    
    # 分数面板
    score_table = Table(title="📊 评分结果", show_header=True, header_style="bold cyan")
    score_table.add_column("维度", style="dim")
    score_table.add_column("分数", justify="right")
    score_table.add_column("说明")
    
    # 情绪分（越高越情绪化，用红色警示）
    emotion_color = "red" if report.emotion_score > 60 else "yellow" if report.emotion_score > 40 else "green"
    score_table.add_row(
        "情绪化", 
        f"[{emotion_color}]{report.emotion_score:.1f}[/]",
        "越低越客观理性"
    )
    
    # 逻辑分（越高越好）
    logic_color = "green" if report.logic_score > 60 else "yellow" if report.logic_score > 40 else "red"
    score_table.add_row(
        "逻辑性",
        f"[{logic_color}]{report.logic_score:.1f}[/]",
        "越高越逻辑清晰"
    )
    
    # 证据分（越高越好）
    evidence_color = "green" if report.evidence_score > 60 else "yellow" if report.evidence_score > 40 else "red"
    score_table.add_row(
        "证据性",
        f"[{evidence_color}]{report.evidence_score:.1f}[/]",
        "越高越可核查"
    )
    
    # 综合分
    overall_color = "green" if report.overall_score > 60 else "yellow" if report.overall_score > 40 else "red"
    score_table.add_row(
        "[bold]综合评分[/]",
        f"[bold {overall_color}]{report.overall_score:.1f}[/]",
        "越高越严谨有据"
    )
    
    console.print(score_table)
    console.print()
    
    # 评分分解
    console.print(Panel(
        f"[dim]计算公式: {report.score_breakdown.formula}[/]\n"
        f"逻辑贡献: +{report.score_breakdown.logic_contribution:.2f} | "
        f"证据贡献: +{report.score_breakdown.evidence_contribution:.2f} | "
        f"情绪扣分: -{report.score_breakdown.emotion_penalty:.2f}",
        title="📐 评分分解"
    ))
    console.print()
    
    # 诊断问题
    if report.diagnostics:
        console.print("[bold red]⚠️ 发现的问题[/]")
        console.print()
        
        for i, diag in enumerate(report.diagnostics[:10], 1):  # 最多显示 10 条
            severity_emoji = "🔴" if diag.severity == "high" else "🟡" if diag.severity == "medium" else "🟢"
            console.print(f"  {severity_emoji} [{diag.category}] {diag.description}")
            console.print(f"     [dim]原文: \"{diag.span_text}\"[/]")
            if diag.suggestion:
                console.print(f"     [cyan]建议: {diag.suggestion}[/]")
            console.print()
        
        if len(report.diagnostics) > 10:
            console.print(f"  [dim]... 还有 {len(report.diagnostics) - 10} 条诊断[/]")
            console.print()
    
    # 正面亮点
    positive_highlights = [h for h in report.highlights if h.is_positive]
    if positive_highlights:
        console.print("[bold green]✅ 正面亮点[/]")
        console.print()
        for h in positive_highlights[:5]:
            console.print(f"  ✓ [green]\"{h.span_text}\"[/] ({h.reason_tag.value})")
        console.print()
    
    # 分段分析摘要
    if report.per_segment and len(report.per_segment) > 1:
        console.print("[bold]📝 分段分析摘要[/]")
        
        # 找出最情绪化和最缺证据的段落
        worst_emotion = max(report.per_segment, key=lambda s: s.emotion_score)
        worst_evidence = min(report.per_segment, key=lambda s: s.evidence_score)
        
        if worst_emotion.emotion_score > 50:
            console.print(f"  [yellow]最情绪化段落 (第{worst_emotion.segment_index + 1}段, 情绪分 {worst_emotion.emotion_score:.1f}):[/]")
            console.print(f"  [dim]{worst_emotion.segment_text[:100]}...[/]")
            console.print()
        
        if worst_evidence.evidence_score < 30:
            console.print(f"  [yellow]最缺证据段落 (第{worst_evidence.segment_index + 1}段, 证据分 {worst_evidence.evidence_score:.1f}):[/]")
            console.print(f"  [dim]{worst_evidence.segment_text[:100]}...[/]")
            console.print()
    
    # 元信息
    console.print(Panel(
        f"文本长度: {report.input_text_length} 字 | "
        f"段落数: {report.segment_count} | "
        f"分析模式: {report.analysis_mode} | "
        f"LLM: {'已启用' if report.llm_used else '未启用'}",
        title="ℹ️ 分析信息"
    ))


@click.group()
@click.version_option(version="0.1.0")
def main():
    """ArgumentQualityScorer - 文本论述质量评估工具
    
    对输入文本进行"论述质量/严谨程度"评估并打分，
    区分"情绪化泛泛而谈 vs 有理有据、逻辑清晰、可核查"。
    """
    pass


@main.command()
@click.option('--input', '-i', 'input_path', required=True, help='输入文本文件路径')
@click.option('--format', '-f', 'output_format', default='rich', 
              type=click.Choice(['json', 'rich']), help='输出格式')
@click.option('--no-llm', is_flag=True, help='禁用 LLM 增强（仅使用规则）')
@click.option('--segment-mode', '-s', default='auto',
              type=click.Choice(['sentence', 'paragraph', 'auto']), help='分段模式')
@click.option('--output', '-o', 'output_path', help='输出文件路径（JSON 格式时可用）')
def score(input_path: str, output_format: str, no_llm: bool, segment_mode: str, output_path: Optional[str]):
    """对文本文件进行评分"""
    try:
        # 检查输入文件
        input_file = Path(input_path)
        if not input_file.exists():
            console.print(f"[red]错误: 文件不存在 - {input_path}[/]")
            sys.exit(1)
        
        # 读取文本
        text = input_file.read_text(encoding='utf-8')
        if not text.strip():
            console.print("[red]错误: 文件为空[/]")
            sys.exit(1)
        
        # 创建评分器并评分
        with console.status("[bold green]正在分析文本..."):
            scorer = ArgumentQualityScorer()
            report = scorer.score(text, use_llm=not no_llm, segment_mode=segment_mode)
        
        # 输出结果
        if output_path:
            Path(output_path).write_text(
                json.dumps(report.model_dump(), indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            console.print(f"[green]结果已保存到: {output_path}[/]")
        
        print_score_report(report, output_format)
        
    except Exception as e:
        console.print(f"[red]错误: {e}[/]")
        if Config.from_env().debug:
            raise
        sys.exit(1)


@main.command()
@click.option('--text', '-t', required=True, help='直接输入文本')
@click.option('--format', '-f', 'output_format', default='json',
              type=click.Choice(['json', 'rich']), help='输出格式')
@click.option('--no-llm', is_flag=True, help='禁用 LLM 增强')
def quick(text: str, output_format: str, no_llm: bool):
    """快速评分（直接输入文本）"""
    try:
        scorer = ArgumentQualityScorer()
        report = scorer.score(text, use_llm=not no_llm)
        print_score_report(report, output_format)
    except Exception as e:
        console.print(f"[red]错误: {e}[/]")
        sys.exit(1)


@main.command()
def config():
    """显示当前配置"""
    cfg = Config.from_env()
    
    console.print(Panel(
        f"LLM API: {cfg.llm.api_base or '[未配置]'}\n"
        f"LLM 模型: {cfg.llm.model}\n"
        f"LLM 可用: {'是' if cfg.llm.is_available else '否'}\n"
        f"---\n"
        f"权重 - 逻辑: {cfg.weights.logic}\n"
        f"权重 - 证据: {cfg.weights.evidence}\n"
        f"权重 - 情绪: {cfg.weights.emotion}\n"
        f"---\n"
        f"使用 Senta: {'是' if cfg.use_senta else '否'}\n"
        f"调试模式: {'是' if cfg.debug else '否'}",
        title="⚙️ 当前配置"
    ))


if __name__ == "__main__":
    main()
