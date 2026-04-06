from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from app.services.llm import generate_response

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatTurn(BaseModel):
    role: Literal["assistant", "user"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    prompt: str | None = Field(default=None, max_length=4000)
    messages: list[ChatTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    prompt = request.prompt.strip() if request.prompt else None
    messages = [
        {"role": message.role, "content": message.content.strip()}
        for message in request.messages
        if message.content.strip()
    ]

    if not messages and not prompt:
        raise HTTPException(status_code=422, detail="Provide a prompt or at least one chat message.")

    try:
        response = generate_response(prompt=prompt, messages=messages or None)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Model request failed. Confirm GEMINI_API_KEY is configured and the Gemini API is reachable: {exc}",
        ) from exc

    return ChatResponse(response=response)
