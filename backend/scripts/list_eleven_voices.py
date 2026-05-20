"""
List ElevenLabs voices available in your account.

Usage:
    cd backend
    python scripts/list_eleven_voices.py
    python scripts/list_eleven_voices.py --lang vi    # filter Vietnamese-tagged
    python scripts/list_eleven_voices.py --search nam # search name/description
"""
import argparse
import os
import sys
from pathlib import Path

# Allow running as `python scripts/list_eleven_voices.py` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from dotenv import load_dotenv

load_dotenv()


def fetch_voices(api_key: str) -> list[dict]:
    """Fetch all voices accessible to this API key."""
    r = httpx.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": api_key, "Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("voices", [])


def fetch_shared_voices(api_key: str, language: str | None = None,
                       search: str | None = None, page_size: int = 100) -> list[dict]:
    """Fetch voices from the public voice library (shared voices)."""
    params: dict[str, str | int] = {"page_size": page_size}
    if language:
        params["language"] = language
    if search:
        params["search"] = search

    r = httpx.get(
        "https://api.elevenlabs.io/v1/shared-voices",
        headers={"xi-api-key": api_key, "Accept": "application/json"},
        params=params,
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("voices", [])


def fmt_labels(labels: dict) -> str:
    if not labels:
        return ""
    bits = []
    for k in ("gender", "age", "accent", "use_case", "descriptive"):
        v = labels.get(k)
        if v:
            bits.append(f"{k}={v}")
    return " · ".join(bits)


def print_voice(v: dict, *, shared: bool = False) -> None:
    name = v.get("name", "?")
    vid = v.get("voice_id", "?")
    cat = v.get("category", "")
    desc = (v.get("description") or "").strip()[:120]
    labels = fmt_labels(v.get("labels", {}))
    if shared:
        public_owner = v.get("public_owner_id", "")
        prefix = f"[shared/{cat}]"
    else:
        prefix = f"[{cat}]"

    print(f"  {name:<28} {vid}  {prefix}")
    if labels:
        print(f"      {labels}")
    if desc:
        print(f"      {desc}")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", help="Filter by language code (vi, en, ja, ...)")
    parser.add_argument("--search", help="Search term (name or description)")
    parser.add_argument("--shared", action="store_true",
                       help="Browse the public voice library instead of My Voices")
    args = parser.parse_args()

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY not set in environment or .env")
        print("       Create one at https://elevenlabs.io/app/settings/api-keys")
        sys.exit(1)

    if args.shared:
        print(f"\n=== Shared voice library (lang={args.lang or 'any'}, search={args.search or '-'}) ===\n")
        voices = fetch_shared_voices(api_key, args.lang, args.search)
        if not voices:
            print("  (no voices matched)")
        for v in voices:
            print_voice(v, shared=True)
        print(f"Total: {len(voices)} voices\n")
        print("Tip: copy a voice_id, then run with that ID:")
        print('  ELEVENLABS_VOICE_ID=<voice_id> uvicorn main:app')
        return

    print("\n=== My voices (already added to your account) ===\n")
    voices = fetch_voices(api_key)

    if args.lang or args.search:
        filtered = []
        lang = (args.lang or "").lower()
        search = (args.search or "").lower()
        for v in voices:
            blob = " ".join([
                v.get("name", ""),
                v.get("description") or "",
                str(v.get("labels", {})),
            ]).lower()
            if lang and lang not in blob:
                continue
            if search and search not in blob:
                continue
            filtered.append(v)
        voices = filtered

    if not voices:
        print("  (no voices in your account match)")
        print()
        print("To browse the public library and add voices, run:")
        print(f"  python {Path(__file__).name} --shared --lang vi")
    else:
        for v in voices:
            print_voice(v)
    print(f"Total: {len(voices)} voices\n")


if __name__ == "__main__":
    main()
