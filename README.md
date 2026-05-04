# AI Music Agent Studio

AI Music Agent Studio is a local full-stack music intelligence app. It supports audio analysis, music discovery, playlist planning, conversational recommendations, image-based BGM suggestions, and Spotify / NetEase Cloud Music search links.

## Features

- Agent Studio: chat with a music agent, generate real-song recommendations, and refine playlists turn by turn.
- Analyze Audio: upload an audio file and view closest genre, top-3 probabilities, tempo, energy, brightness, and texture.
- Discover Music: describe a mood, activity, or sound and get real song and artist recommendations.
- Playlist Planner: create a staged playlist journey with a timeline, energy flow, and real songs grouped by stage.
- Image BGM: upload an image and get background music suggestions based on the visual atmosphere.
- Song Links: song cards can open Spotify search and NetEase Cloud Music search.

## Recommended Run Method

For demos, use the one-click launcher:

```text
start_music_agent.bat
```

On a new computer, run the setup script first:

```text
setup_music_agent.bat
```

After setup finishes, future runs only need `start_music_agent.bat`.

## Requirements

Install these before running the project:

- Python 3.10 or 3.11
- Node.js 18 or newer
- npm

Check them with:

```powershell
python --version
node --version
npm --version
```

## Clone From GitHub

If you are cloning the submitted repository on a new computer, use:

```powershell
git clone https://github.com/jt3645-arch/Music-Agent-Studio.git
cd Music-Agent-Studio
git lfs install
git lfs pull
```

`git lfs pull` downloads the local audio perception checkpoint stored under `backend/cache/`. Run it before the first setup so audio analysis can load the checkpoint correctly.

## First-Time Setup

From the project root, double-click:

```text
setup_music_agent.bat
```

The script will:

1. Create `backend/.venv` and install `backend/requirements.txt`.
2. Install frontend dependencies from `frontend/package.json`.

The setup can take a while because PyTorch, Transformers, and frontend dependencies are large.

## One-Click Start

After setup, double-click:

```text
start_music_agent.bat
```

It opens two terminal windows:

- Music Agent Backend
- Music Agent Frontend

Then it opens the app in your browser:

```text
http://127.0.0.1:3000
```

If the browser does not open automatically, copy the address above into your browser.

## Manual Start

If the launcher does not work, start the two parts manually.

Open the first PowerShell window:

```powershell
cd "PROJECT_PATH\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open the second PowerShell window:

```powershell
cd "PROJECT_PATH\frontend"
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Then open:

```text
http://127.0.0.1:3000
```

## Optional Configuration

The backend environment file is:

```text
backend/.env
```

Common options:

```text
LLM_PROVIDER=openai
LLM_MODEL=gpt-5-mini
LLM_BASE_URL=
OPENAI_API_KEY=your_openai_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here
DASHSCOPE_API_KEY=your_dashscope_key_here
VISION_MODEL_NAME=gpt-5-mini
ENABLE_WEB_SEARCH=true
```

Supported recommendation modes:

- `openai`: uses the default OpenAI client.
- `deepseek`: uses the OpenAI-compatible DeepSeek client with `https://api.deepseek.com`.
- `qwen`: uses the OpenAI-compatible DashScope client with `https://dashscope.aliyuncs.com/compatible-mode/v1`.
- `offline`: uses built-in deterministic fallback recommendations.

Without a configured key, the project can still use built-in best-effort song recommendations. Image understanding depends on the selected mode and model capability.

You can also switch the recommendation mode during a running session from the Advanced panel in the app sidebar. The `.env` values are still the recommended way to set defaults for another computer.

## Troubleshooting

### 1. The page does not open

Make sure both terminal windows are still running, then open:

```text
http://127.0.0.1:3000
```

If port 3000 is already in use, close the previous frontend window and run `start_music_agent.bat` again.

### 2. The backend does not start

Test the backend import:

```powershell
cd "PROJECT_PATH\backend"
.\.venv\Scripts\python.exe -c "from app.main import app; print('backend import ok')"
```

If dependencies are missing, run:

```text
setup_music_agent.bat
```

### 3. The frontend does not start

Reinstall frontend dependencies:

```powershell
cd "PROJECT_PATH\frontend"
npm.cmd install
```

Then run:

```text
start_music_agent.bat
```

### 4. Image recommendations are weak

Check whether `OPENAI_API_KEY` is set in `backend/.env`. Without it, the app uses a local color and brightness fallback for image mood analysis.

### 5. Song links are search links

If an exact platform URL is unavailable, the app generates Spotify and NetEase Cloud Music search links from the song title and artist. This avoids presenting a search result as a verified exact track page.

## Project Structure

```text
music-agent/
  backend/
    app/
      api/
      services/
    cache/
    data/
    requirements.txt
  frontend/
    app/
    lib/
    package.json
  setup_music_agent.bat
  start_music_agent.bat
  README.md
```

## Sharing on GitHub

Do not commit private environment files. Keep personal keys only in:

```text
backend/.env
```

Share the safe template instead:

```text
backend/.env.example
```

Before pushing, check that private files and local environments are not tracked:

```powershell
git status --short
git ls-files | findstr /i ".env .venv node_modules"
```

If `backend/.env` was accidentally tracked, remove it from Git while keeping the local file:

```powershell
git rm --cached backend/.env
```

### Large Model Files

The local audio perception checkpoint is stored under `backend/cache/` and can be larger than the normal GitHub file limit. Use Git LFS for model files such as `.pt`, `.pth`, and `.onnx` if you want teammates to clone and run the project directly.

Recommended Git LFS setup:

```powershell
git lfs install
git lfs track "*.pt"
git lfs track "*.pth"
git lfs track "*.onnx"
git add .gitattributes backend/cache/best_ast_gtzan.pt
```

If you do not use Git LFS, provide the files in `backend/cache/` separately and ask teammates to place them in the same folder after cloning.
