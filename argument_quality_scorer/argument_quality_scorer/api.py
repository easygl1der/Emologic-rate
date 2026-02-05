"""
Web API - FastAPI 实现

端点:
    POST /score - 对文本进行评分
    GET /health - 健康检查
    GET /config - 获取当前配置

启动:
    uvicorn argument_quality_scorer.api:app --reload
"""

from typing import Optional
from pydantic import BaseModel, Field

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    raise ImportError("请安装 FastAPI: pip install 'argument-quality-scorer[api]'")

from .scorer import ArgumentQualityScorer
from .schema import ScoreReport
from .utils.config import Config


# 创建 FastAPI 应用
app = FastAPI(
    title="ArgumentQualityScorer API",
    description="文本论述质量评估 API - 评估情绪化/逻辑/证据多维度",
    version="0.1.0",
)

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局评分器实例
scorer: Optional[ArgumentQualityScorer] = None


def get_scorer() -> ArgumentQualityScorer:
    """获取或创建评分器实例"""
    global scorer
    if scorer is None:
        scorer = ArgumentQualityScorer()
    return scorer


class ScoreRequest(BaseModel):
    """评分请求"""
    text: str = Field(..., min_length=1, description="待评分的文本")
    use_llm: bool = Field(default=True, description="是否使用 LLM 增强")
    segment_mode: str = Field(default="auto", description="分段模式: sentence/paragraph/auto")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "这个产品绝对是最好的！所有人都应该买它！专家都这么说。",
                "use_llm": True,
                "segment_mode": "auto"
            }
        }


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    llm_available: bool
    version: str


class ConfigResponse(BaseModel):
    """配置响应"""
    llm_configured: bool
    llm_model: str
    weights: dict
    analysis_mode: str


@app.get("/", response_model=dict)
async def root():
    """API 根路径"""
    return {
        "name": "ArgumentQualityScorer API",
        "version": "0.1.0",
        "endpoints": {
            "POST /score": "对文本进行评分",
            "GET /health": "健康检查",
            "GET /config": "获取当前配置"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """健康检查"""
    s = get_scorer()
    return HealthResponse(
        status="healthy",
        llm_available=s.llm_critic.is_available,
        version="0.1.0"
    )


@app.get("/config", response_model=ConfigResponse)
async def get_config():
    """获取当前配置"""
    cfg = Config.from_env()
    return ConfigResponse(
        llm_configured=cfg.llm.is_available,
        llm_model=cfg.llm.model,
        weights={
            "logic": cfg.weights.logic,
            "evidence": cfg.weights.evidence,
            "emotion": cfg.weights.emotion
        },
        analysis_mode="hybrid" if cfg.llm.is_available else "rule_only"
    )


@app.post("/score", response_model=ScoreReport)
async def score_text(request: ScoreRequest):
    """
    对文本进行评分
    
    返回包含情绪化/逻辑/证据得分的完整报告。
    """
    try:
        s = get_scorer()
        report = s.score(
            text=request.text,
            use_llm=request.use_llm,
            segment_mode=request.segment_mode
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 用于直接运行
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
