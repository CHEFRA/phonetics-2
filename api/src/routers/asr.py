import os
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
    file_size_mb = file_size / (1024 * 1024)
    logger.info(f"开始处理 | filename={file.filename} | size={file_size_mb:.2f} MB")

    # 重置文件指针
    await file.seek(0)
    content = await file.read()

    # 从原始文件名提取后缀
    suffix = os.path.splitext(file.filename)[1] or ".mp3"

    start_time = time.time()
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(content)
        tmp.close()  # 先关闭，ffmpeg 才能读取
        text = sensevoice_service.recognize(tmp.name)
    finally:
        os.unlink(tmp.name)  # 用完再删除

    duration_s = round(time.time() - start_time, 2)

    # 记录处理完成
    logger.info(f"处理完成 | text={text} | duration={duration_s}s")

    return ASRResponse(text=text)