# schemas.py
# Espejo estricto del esquema de /v1/chat/completions de OpenAI.
# extra="forbid" rechaza cualquier campo no contemplado: un payload
# malformado o con inyección de parámetros se corta antes del modelo.
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["system", "user", "assistant", "tool"]
    content: Union[str, list[dict]]        # soporta contenido multimodal
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(..., min_length=1, max_length=128)
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=256)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    n: Optional[int] = Field(default=None, ge=1, le=8)
    stream: Optional[bool] = False
    stop: Optional[Union[str, list[str]]] = None
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32768)
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    seed: Optional[int] = None
    user: Optional[str] = Field(default=None, max_length=256)
    response_format: Optional[dict] = None
    tools: Optional[list[dict]] = None
    tool_choice: Optional[Union[str, dict]] = None
