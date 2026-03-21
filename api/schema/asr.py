from pydantic import BaseModel


class ASRResponse(BaseModel):
    text: str