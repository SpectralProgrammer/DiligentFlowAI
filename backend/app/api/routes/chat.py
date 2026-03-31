from functools import lru_cache
import os
from pathlib import Path
import sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/chat", tags=["chat"])

BACKEND_DIR = Path(__file__).resolve().parents[3]
SYSTEM_PROMPT_PATH = BACKEND_DIR / "model_system_prompt.txt"
DEFAULT_OLLAMA_MODEL = "llama3:8b"


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    response: str


def load_system_prompt() -> str | None:
    if not SYSTEM_PROMPT_PATH.exists():
        return None
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache
def get_ai_model():
    if str(BACKEND_DIR) not in sys.path:
        sys.path.append(str(BACKEND_DIR))

    try:
        from model import Llama3
    except Exception as exc:  # pragma: no cover - import path depends on local env
        raise RuntimeError(
            "The local model backend is unavailable. Install backend requirements first."
        ) from exc

    return Llama3(
        model=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
        system_prompt=load_system_prompt(),
    )


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        response = get_ai_model().chat(prompt=request.prompt)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Model request failed. Confirm Ollama is running and the model is installed: {exc}",
        ) from exc

    return ChatResponse(response=response)
