from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.analyze import router as analyze_router
from app.api.agent import router as agent_router
from app.api.retrieve import router as retrieve_router
from app.api.playlist import router as playlist_router
from app.api.settings import router as settings_router

app = FastAPI(title="Music Agent Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(agent_router)
app.include_router(retrieve_router)
app.include_router(playlist_router)
app.include_router(settings_router)

@app.get("/")
def root():
    return {"status": "ok", "message": "Music Agent backend is running."}
