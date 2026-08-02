import time

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.logger import setup_logger
from src.routers.asr import router as asr_router

logger = setup_logger("phonetics")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.core.db import init_db
    from src.services import history
    from src.core.asr_registry import get_asr_service

    asr_service = get_asr_service()

    # 初始化数据库并登记服务会话
    init_db()
    app.state.session_id = history.start_session(
        app="api",
        model=asr_service.model_id,
    )

    # 启动时预加载模型
    logger.info("正在加载 ASR 模型...")
    start_time = time.time()
    asr_service.get_model()
    duration = round(time.time() - start_time, 2)
    logger.info(f"ASR 模型加载完成，耗时 {duration}s，服务已就绪")
    yield
    history.end_session(app.state.session_id)
    logger.info("服务已关闭，会话已结束")


app = FastAPI(title="Phonetics ASR API", lifespan=lifespan)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(asr_router, prefix="/api/v1/asr")


@app.get("/health")
async def health():
    return {"status": "ok"}
