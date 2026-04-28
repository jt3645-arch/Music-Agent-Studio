from pathlib import Path
import json

ROOT = Path(r"C:\Users\29358\Desktop\6895\final project\music-agent")

DIRS = [
    "backend/app/api",
    "backend/app/services",
    "backend/app/utils",
    "backend/cache",
    "backend/data",
    "backend/outputs/playlists",
    "backend/outputs/analysis",
    "backend/outputs/generated_audio",
    "backend/tests",
    "frontend/app",
    "frontend/components",
    "frontend/lib",
    "frontend/public",
]

FILES = {
    "README.md": """# Music Agent

Local full-stack music agent project.

## Goals
- Audio -> Language analysis
- Language -> Audio retrieval
- Time-segmented playlist generation
- Future: music creation / accompaniment generation

## Structure
- backend/: FastAPI backend
- frontend/: frontend UI
""",

    ".gitignore": """.env
__pycache__/
*.pyc
.venv/
node_modules/
.next/
dist/
build/
""",

    "backend/.env": """OPENAI_API_KEY=your_openai_api_key_here
MODEL_NAME=gpt-5-mini

BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

DATA_DIR=./data/genres_original
CACHE_DIR=./cache
AST_CHECKPOINT=./cache/best_ast_gtzan.pt
FEATURE_CSV=./cache/full_clip_features.csv
FINAL_METRICS=./cache/final_metrics.json
""",

    "backend/requirements.txt": """fastapi
uvicorn[standard]
python-dotenv
pydantic
pandas
numpy
librosa
soundfile
scikit-learn
matplotlib
torch
transformers
accelerate
openai
python-multipart
""",

    "backend/app/__init__.py": "",
    "backend/app/api/__init__.py": "",
    "backend/app/services/__init__.py": "",
    "backend/app/utils/__init__.py": "",

    "backend/app/config.py": """from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5-mini")

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

DATA_DIR = (BASE_DIR / os.getenv("DATA_DIR", "./data/genres_original")).resolve()
CACHE_DIR = (BASE_DIR / os.getenv("CACHE_DIR", "./cache")).resolve()
AST_CHECKPOINT = (BASE_DIR / os.getenv("AST_CHECKPOINT", "./cache/best_ast_gtzan.pt")).resolve()
FEATURE_CSV = (BASE_DIR / os.getenv("FEATURE_CSV", "./cache/full_clip_features.csv")).resolve()
FINAL_METRICS = (BASE_DIR / os.getenv("FINAL_METRICS", "./cache/final_metrics.json")).resolve()
""",

    "backend/app/schemas.py": """from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class AnalyzeResponse(BaseModel):
    status: str
    predicted_genre: Optional[str] = None
    top3: Optional[List[Any]] = None
    features: Optional[Dict[str, Any]] = None
    recommendation: Optional[str] = None


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5


class RetrieveResponse(BaseModel):
    status: str
    parsed_targets: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None
    explanation: Optional[str] = None


class PlaylistRequest(BaseModel):
    goal: str
    total_minutes: int
    top_k_per_stage: int = 5
    preferred_genres: Optional[List[str]] = None
    custom_plan: Optional[List[Dict[str, Any]]] = None


class PlaylistResponse(BaseModel):
    status: str
    stage_plan: List[Dict[str, Any]]
    playlist: List[Dict[str, Any]]
    explanation: str
""",

    "backend/app/services/feature_service.py": """import pandas as pd
from app.config import FEATURE_CSV

_feature_df = None

def load_feature_df():
    global _feature_df
    if _feature_df is None:
        if not FEATURE_CSV.exists():
            raise FileNotFoundError(f"Feature CSV not found: {FEATURE_CSV}")
        _feature_df = pd.read_csv(FEATURE_CSV)
    return _feature_df
""",

    "backend/app/services/ast_service.py": """from pathlib import Path

def model_status():
    # TODO: replace with real AST model loading and inference
    return {
        "status": "placeholder",
        "message": "AST service scaffold created. Load your trained checkpoint here."
    }

def analyze_audio(audio_path: str):
    # TODO: connect your notebook inference logic here
    return {
        "status": "ok",
        "predicted_genre": "TODO",
        "top3": [],
        "features": {},
        "recommendation": "TODO: connect analyze_audio_path logic from your notebook."
    }
""",

    "backend/app/services/retrieval_service.py": """from app.services.feature_service import load_feature_df

def retrieve_from_text(query: str, top_k: int = 5):
    df = load_feature_df()
    # TODO: replace with your real parse_text_to_targets + retrieve logic
    sample = df.head(top_k).copy()
    rows = sample.to_dict(orient="records")
    return {
        "status": "ok",
        "parsed_targets": {"query": query},
        "results": rows,
        "explanation": "TODO: replace with real retrieval explanation."
    }
""",

    "backend/app/services/playlist_service.py": """from typing import List, Dict, Any
from app.services.feature_service import load_feature_df

def auto_plan(goal: str, total_minutes: int) -> List[Dict[str, Any]]:
    goal_lower = goal.lower()

    if "workout" in goal_lower or "gym" in goal_lower or "fitness" in goal_lower:
        return [
            {"stage": "warmup", "minutes": max(5, total_minutes // 4), "tempo_hint": "medium", "energy_hint": "medium"},
            {"stage": "intense", "minutes": max(10, total_minutes // 2), "tempo_hint": "fast", "energy_hint": "high"},
            {"stage": "cooldown", "minutes": total_minutes - max(5, total_minutes // 4) - max(10, total_minutes // 2), "tempo_hint": "slow", "energy_hint": "low"},
        ]

    if "study" in goal_lower or "focus" in goal_lower:
        return [
            {"stage": "settle_in", "minutes": max(5, total_minutes // 4), "tempo_hint": "slow", "energy_hint": "low"},
            {"stage": "deep_focus", "minutes": total_minutes - max(5, total_minutes // 4), "tempo_hint": "medium", "energy_hint": "low-medium"},
        ]

    return [
        {"stage": "main", "minutes": total_minutes, "tempo_hint": "medium", "energy_hint": "medium"}
    ]

def generate_playlist(goal: str, total_minutes: int, preferred_genres=None, custom_plan=None, top_k_per_stage: int = 5):
    df = load_feature_df()
    stage_plan = custom_plan if custom_plan else auto_plan(goal, total_minutes)

    playlist = []
    used = set()

    for stage in stage_plan:
        stage_name = stage["stage"]
        stage_minutes = stage["minutes"]

        candidates = df.copy()

        if preferred_genres:
            genre_col = "genre" if "genre" in candidates.columns else None
            if genre_col:
                preferred = {g.lower() for g in preferred_genres}
                candidates = candidates[candidates[genre_col].str.lower().isin(preferred)]

        candidates = candidates.head(top_k_per_stage)

        selected = []
        for _, row in candidates.iterrows():
            clip_id = row.get("clip_id", "")
            if clip_id in used:
                continue
            used.add(clip_id)
            selected.append({
                "stage": stage_name,
                "clip_id": clip_id,
                "genre": row.get("genre", ""),
                "audio_path": row.get("audio_path", ""),
                "minutes_allocated": stage_minutes,
            })

        playlist.extend(selected)

    return {
        "status": "ok",
        "stage_plan": stage_plan,
        "playlist": playlist,
        "explanation": "TODO: replace with real time-segmented playlist retrieval logic."
    }
""",

    "backend/app/services/llm_service.py": """from app.config import OPENAI_API_KEY, MODEL_NAME

def llm_status():
    return {
        "has_key": bool(OPENAI_API_KEY),
        "model": MODEL_NAME
    }
""",

    "backend/app/api/analyze.py": """from fastapi import APIRouter, UploadFile, File
from pathlib import Path
import tempfile
from app.services.ast_service import analyze_audio

router = APIRouter(prefix="/analyze", tags=["analyze"])

@router.post("")
async def analyze_endpoint(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    return analyze_audio(tmp_path)
""",

    "backend/app/api/retrieve.py": """from fastapi import APIRouter
from app.schemas import RetrieveRequest
from app.services.retrieval_service import retrieve_from_text

router = APIRouter(prefix="/retrieve", tags=["retrieve"])

@router.post("")
def retrieve_endpoint(req: RetrieveRequest):
    return retrieve_from_text(req.query, req.top_k)
""",

    "backend/app/api/playlist.py": """from fastapi import APIRouter
from app.schemas import PlaylistRequest
from app.services.playlist_service import generate_playlist

router = APIRouter(prefix="/playlist", tags=["playlist"])

@router.post("")
def playlist_endpoint(req: PlaylistRequest):
    return generate_playlist(
        goal=req.goal,
        total_minutes=req.total_minutes,
        preferred_genres=req.preferred_genres,
        custom_plan=req.custom_plan,
        top_k_per_stage=req.top_k_per_stage,
    )
""",

    "backend/app/main.py": """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.analyze import router as analyze_router
from app.api.retrieve import router as retrieve_router
from app.api.playlist import router as playlist_router

app = FastAPI(title="Music Agent Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(retrieve_router)
app.include_router(playlist_router)

@app.get("/")
def root():
    return {"status": "ok", "message": "Music Agent backend is running."}
""",

    "frontend/package.json": json.dumps({
        "name": "music-agent-frontend",
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start"
        },
        "dependencies": {
            "next": "14.2.5",
            "react": "^18.2.0",
            "react-dom": "^18.2.0"
        }
    }, indent=2),

    "frontend/app/page.tsx": """export default function HomePage() {
  return (
    <main style={{ padding: 32, fontFamily: "Arial, sans-serif" }}>
      <h1>Music Agent</h1>
      <p>Frontend scaffold created successfully.</p>
      <p>Next step: build a polished UI for audio analysis, retrieval, and playlist planning.</p>
    </main>
  );
}
""",

    "frontend/lib/api.ts": """export const API_BASE = "http://127.0.0.1:8000";
""",
}


def safe_write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")
        print(f"[CREATED] {path}")
    else:
        print(f"[SKIPPED ] {path} (already exists)")


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    print(f"Project root: {ROOT}")

    for d in DIRS:
        p = ROOT / d
        p.mkdir(parents=True, exist_ok=True)
        print(f"[DIR     ] {p}")

    for rel_path, content in FILES.items():
        safe_write(ROOT / rel_path, content)

    print("\\nDone.")
    print("Next steps:")
    print(f"1) Put your files into:")
    print(f"   {ROOT / 'backend/cache'}")
    print(f"   {ROOT / 'backend/data/genres_original'}")
    print("2) In VS Code terminal:")
    print("   cd backend")
    print("   pip install -r requirements.txt")
    print("   uvicorn app.main:app --reload")
    print("3) Then build the frontend separately.")


if __name__ == "__main__":
    main()