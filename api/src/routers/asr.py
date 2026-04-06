import tempfile
import time
from fastapi import APIRouter, UploadFile, File, Request

from src.core.logger import setup_logger
from src.schema.asr import ASRResponse
from src.services.sensevoice import sensevoice_service

router = APIRouter(tags=["asr"])
logger = setup_logger("phonetics.asr")


@router.post("", response_model=ASRResponse)
async def asr(request: Request, file: UploadFile = File(...)):
    # 记录收到请求
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"收到请求 | method=POST | path=/api/v1/asr | client={client_ip} | time={time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 记录开始处理
    file_size = len(file.file.read()) if file.file else 0
    logger.info(f"开始处理 | filename={file.filename} | size={file_size} bytes")

    # 重置文件指针
    await file.seek(0)
    content = await file.read()

    start_time = time.time()
    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        text = sensevoice_service.recognize(tmp.name)

    duration_s = round(time.time() - start_time, 2)

    # 记录处理完成
    logger.info(f"处理完成 | text={text} | duration={duration_s}s")

    return ASRResponse(text=text)