from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers.asr import router as asr_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时预加载模型
    from src.services.sensevoice import sensevoice_service
    sensevoice_service.get_model()
    yield


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