import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")


def post_json(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{API_BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def print_retrieve_summary(result):
    print("Retrieve: relaxing jazz")
    print(f"  status: {result.get('status')}")
    targets = result.get("parsed_targets") or {}
    print(f"  preferred_genres: {targets.get('preferred_genres', [])}")

    for row in (result.get("results") or [])[:3]:
        print(
            "  - "
            f"{row.get('clip_id')} | {row.get('genre')} | "
            f"{row.get('tempo_bpm')} BPM | score={row.get('final_score')}"
        )


def print_playlist_summary(result):
    print("Playlist: 40-minute workout")
    print(f"  status: {result.get('status')}")
    print(f"  stages: {len(result.get('stage_plan') or [])}")
    print(f"  clips: {len(result.get('playlist') or [])}")

    for row in (result.get("playlist") or [])[:6]:
        print(
            "  - "
            f"{row.get('stage')} | {row.get('clip_id')} | "
            f"{row.get('genre')} | score={row.get('final_score')}"
        )


def main():
    try:
        retrieve_result = post_json(
            "/retrieve",
            {"query": "relaxing calm late-night jazz", "top_k": 5},
        )
        playlist_result = post_json(
            "/playlist",
            {
                "goal": "40-minute workout playlist",
                "total_minutes": 40,
                "top_k_per_stage": 3,
            },
        )
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP error from backend: {exc.code} {exc.reason}", file=sys.stderr)
        print(body, file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Could not reach backend at {API_BASE}: {exc.reason}", file=sys.stderr)
        return 1

    print(f"API base: {API_BASE}")
    print_retrieve_summary(retrieve_result)
    print()
    print_playlist_summary(playlist_result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
