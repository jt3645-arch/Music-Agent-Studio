from pathlib import Path
import os
from dotenv import load_dotenv

# backend/app/config.py
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent

# Always load backend/.env
load_dotenv(BACKEND_DIR / ".env")


def resolve_backend_path(path_str: str) -> Path:
    """
    Resolve paths relative to the backend folder.
    Example:
    ./cache/full_clip_features.csv -> backend/cache/full_clip_features.csv
    """
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (BACKEND_DIR / p).resolve()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("MODEL_NAME", "gpt-5-mini"))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
MODEL_NAME = os.getenv("MODEL_NAME", LLM_MODEL)
VISION_MODEL_NAME = os.getenv("VISION_MODEL_NAME", LLM_MODEL)
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

DATA_DIR = resolve_backend_path(os.getenv("DATA_DIR", "./data/genres_original"))
CACHE_DIR = resolve_backend_path(os.getenv("CACHE_DIR", "./cache"))

AST_CHECKPOINT = resolve_backend_path(
    os.getenv("AST_CHECKPOINT", "./cache/best_ast_gtzan.pt")
)
FEATURE_CSV = resolve_backend_path(
    os.getenv("FEATURE_CSV", "./cache/full_clip_features.csv")
)
FINAL_METRICS = resolve_backend_path(
    os.getenv("FINAL_METRICS", "./cache/final_metrics.json")
)
