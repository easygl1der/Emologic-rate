# ArgumentQualityScorer

**文本论述质量评估工具** - 对输入文本进行"论述质量/严谨程度"评估并打分，区分"情绪化泛泛而谈 vs 有理有据、逻辑清晰、可核查"。

特别适合分析：视频字幕稿、文章、评论、社交媒体帖子等。

## 特性

- 🎯 **多维度评分**：情绪化、逻辑性、证据可核查性、综合评分
- 📍 **可追溯解释**：每条诊断都锚定到原文具体片段
- 🔧 **模块化设计**：可独立使用或组合各分析模块
- 🤖 **LLM 增强**：支持接入 GLM-4-Flash 或其他 OpenAI 兼容 API
- 📊 **分段分析**：定位文本中哪里在"水/煽动/跳步"
- 🚀 **离线可用**：无 LLM 时自动降级为纯规则模式

## 快速开始

### 安装

```bash
# 基础安装
pip install -r requirements.txt

# 或使用 pip 安装（开发模式）
pip install -e .

# 安装可选依赖（Web API）
pip install -e ".[api]"
```

### 命令行使用

```bash
# 对文件评分
python -m argument_quality_scorer score --input examples/sample_subtitle_1.txt --format rich

# 快速评分（直接输入文本）
python -m argument_quality_scorer quick --text "这个产品绝对是最好的！所有人都应该买！"

# 输出 JSON 格式
python -m argument_quality_scorer score --input file.txt --format json --output result.json

# 查看当前配置
python -m argument_quality_scorer config
```

### Python API 使用

```python
from argument_quality_scorer import ArgumentQualityScorer

# 创建评分器
scorer = ArgumentQualityScorer()

# 评分
text = """
这个产品绝对是最好的！所有人都应该买！
专家都这么说，不买就是傻子！
"""
report = scorer.score(text)

# 查看结果
print(f"情绪化得分: {report.emotion_score}")  # 越高越情绪化
print(f"逻辑得分: {report.logic_score}")      # 越高越逻辑清晰
print(f"证据得分: {report.evidence_score}")   # 越高越可核查
print(f"综合得分: {report.overall_score}")    # 越高越严谨有据

# 查看诊断（每条都引用原文）
for diag in report.diagnostics:
    print(f"[{diag.category}] {diag.description}")
    print(f"  原文: \"{diag.span_text}\"")
```

### Web API 使用

```bash
# 启动服务
uvicorn argument_quality_scorer.api:app --host 0.0.0.0 --port 8000

# 调用 API
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{"text": "这是要评分的文本", "use_llm": true}'
```

## 评分说明

### 评分维度

| 维度 | 分数范围 | 含义 |
|------|----------|------|
| `emotion_score` | 0-100 | 越高越情绪化/主观化（风险指标） |
| `logic_score` | 0-100 | 越高越逻辑清晰/结构完整 |
| `evidence_score` | 0-100 | 越高越可核查/引用充分 |
| `overall_score` | 0-100 | 越高越"言之有物且严谨" |

### 评分公式

```
overall_score = 0.35 × logic_score + 0.35 × evidence_score - 0.30 × emotion_score + 30
```

- 逻辑和证据得分正向贡献
- 情绪化得分负向贡献（越情绪化越扣分）
- +30 作为基础偏移，确保合理的分数区间

### 检测的问题类型

**情绪化信号**：
- 极端化词（绝对、必须、永远、从不...）
- 攻击性语言
- 过多感叹号
- 主观断言（"显然"、"众所周知"...）

**逻辑谬误**：
- 人身攻击（Ad Hominem）
- 诉诸权威（Appeal to Authority）
- 稻草人谬误（Straw Man）
- 滑坡谬误（Slippery Slope）
- 以偏概全（Hasty Generalization）
- 假二元对立（False Dilemma）
- 循环论证（Circular Reasoning）

**证据问题**：
- 空泛引用（"有研究表明"但不给出处）
- 缺乏可核查数据
- 无来源支撑

## 配置

### 环境变量配置

复制 `.env.example` 为 `.env` 并配置：

```bash
# LLM 配置（可选，不配置则使用纯规则模式）
LLM_API_BASE=https://open.bigmodel.cn/api/paas/v4
LLM_API_KEY=your-api-key
LLM_MODEL=glm-4-flash

# 评分权重（可选）
WEIGHT_LOGIC=0.35
WEIGHT_EVIDENCE=0.35
WEIGHT_EMOTION=0.30
```

### 支持的 LLM

任何 OpenAI 兼容 API 都可以使用：

- **智谱 GLM-4-Flash**（推荐）
- **OpenAI GPT-4**
- **Perplexity**
- **本地 Ollama**
- 其他兼容 API

## 项目结构

```
argument_quality_scorer/
├── argument_quality_scorer/
│   ├── __init__.py          # 包入口
│   ├── __main__.py          # CLI 入口
│   ├── cli.py               # 命令行接口
│   ├── api.py               # FastAPI Web API
│   ├── scorer.py            # 主评分器
│   ├── schema.py            # 数据模型定义
│   ├── modules/
│   │   ├── base.py          # 模块基类
│   │   ├── emotion.py       # 情绪化分析模块
│   │   ├── logic.py         # 逻辑/谬误分析模块
│   │   ├── evidence.py      # 证据分析模块
│   │   └── llm_critic.py    # LLM 增强分析
│   ├── utils/
│   │   ├── config.py        # 配置管理
│   │   └── text_processor.py # 文本处理
│   ├── data/
│   │   └── fallacy_dataset.py # 谬误数据集接口
│   └── tests/
│       └── test_scorer.py   # 测试用例
├── examples/
│   ├── sample_subtitle_1.txt    # 示例：情绪化字幕稿
│   ├── sample_subtitle_2.txt    # 示例：有理有据字幕稿
│   ├── output_sample_1.json     # 示例输出
│   └── output_sample_2.json     # 示例输出
├── pyproject.toml           # 项目配置
├── requirements.txt         # 依赖
├── .env.example            # 环境变量示例
└── README.md               # 本文档
```

## 扩展开发

### 添加新的分析模块

```python
from argument_quality_scorer.modules.base import BaseModule, ModuleResult

class MyModule(BaseModule):
    @property
    def name(self) -> str:
        return "my_module"
    
    def analyze(self, text: str, **kwargs) -> ModuleResult:
        # 实现你的分析逻辑
        diagnostics = []
        highlights = []
        
        # ... 分析代码 ...
        
        return ModuleResult(
            score=75.0,
            diagnostics=diagnostics,
            highlights=highlights,
            features={"custom_feature": value}
        )
```

### 使用谬误数据集

```python
from argument_quality_scorer.data import FallacyDataset

# 下载数据集
dataset = FallacyDataset()
dataset.download_all()

# 加载数据
for item in dataset.load("train"):
    print(item["text"], item["label"])

# 获取统计
stats = dataset.get_statistics("train")
print(stats)
```

## 运行测试

```bash
# 安装测试依赖
pip install pytest

# 运行测试
pytest argument_quality_scorer/tests/ -v
```

## 局限性声明

⚠️ **重要说明**：

1. **不判断事实真假**：本工具只评估"论述结构、证据可追溯性、情绪化与谬误倾向"，不验证内容的事实准确性
2. **规则有限**：基于规则的检测无法覆盖所有情况，可能存在误报或漏报
3. **语言限制**：主要针对中文文本优化，其他语言效果可能不佳
4. **LLM 依赖**：使用 LLM 增强时，结果受模型能力影响

## 依赖说明

### 核心依赖

- `pydantic>=2.0.0` - 数据模型与校验
- `jieba>=0.42.1` - 中文分词
- `cnsenti>=0.0.7` - 情感分析词典
- `httpx>=0.25.0` - HTTP 客户端
- `click>=8.1.0` - CLI 框架
- `rich>=13.0.0` - 终端美化

### 可选依赖

- `fastapi>=0.104.0` - Web API
- `uvicorn>=0.24.0` - ASGI 服务器
- `paddlepaddle>=2.5.0` - Baidu Senta 支持

## 参考资源

- [cnsenti](https://github.com/hiDaDeng/cnsenti) - 中文情绪/情感词典
- [Baidu Senta](https://github.com/baidu/Senta) - 情感分析系统
- [logical-fallacy](https://github.com/tmakesense/logical-fallacy) - 逻辑谬误数据集
- [Logical.ly](https://github.com/SeanFlannery/Logical.ly) - 逻辑谬误检测参考

## License

MIT License
