import tempfile
from fastapi import APIRouter, UploadFile, File

from schema.asr import ASRResponse
from services.sensevoice import sensevoice_service

router = APIRouter(tags=["asr"])


@router.post("", response_model=ASRResponse)
async def asr(file: UploadFile = File(...)):
    content = await file.read()

    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        text = sensevoice_service.recognize(tmp.name)

    return ASRResponse(text=text)