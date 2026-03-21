from fastapi import APIRouter, UploadFile, File

from api.schema.asr import ASRResponse
from api.services.sensevoice import sensevoice_service

router = APIRouter(prefix="/api/v1/asr", tags=["asr"])


@router.post("", response_model=ASRResponse)
async def asr(file: UploadFile = File(...)):
    content = await file.read()
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(content)

    text = sensevoice_service.recognize(temp_path)
    return ASRResponse(text=text)