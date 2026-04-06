from collections.abc import Sequence
from functools import lru_cache
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
SYSTEM_PROMPT_PATH = BACKEND_DIR / "assistant_system_prompt.txt"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

load_dotenv(REPO_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPO_ROOT / "frontend" / ".env.local")


def load_system_prompt() -> str | None:
    if not SYSTEM_PROMPT_PATH.exists():
        return None
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache
def get_ai_model():
    if str(BACKEND_DIR) not in sys.path:
        sys.path.append(str(BACKEND_DIR))

    try:
        from model import GeminiModel
    except Exception as exc:  # pragma: no cover - import path depends on local env
        raise RuntimeError(
            "The Gemini model backend is unavailable. Install backend requirements first."
        ) from exc

    return GeminiModel(
        model=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        system_prompt=load_system_prompt(),
        api_key=os.getenv("GEMINI_API_KEY"),
    )


def generate_response(
    prompt: str | None = None,
    messages: Sequence[dict[str, str]] | None = None,
) -> str:
    return get_ai_model().chat(prompt=prompt, messages=messages)
