"""
Voice catalog endpoints — list ElevenLabs voices for the user to pick from.
"""
import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()


# Default premade voices (ElevenLabs & Microsoft Edge AI)
# (voice_id, name, gender, description)
DEFAULT_PREMADE_VOICES: list[dict[str, str]] = [
    # ElevenLabs Premade Voices
    {"voice_id": "pNInz6obpgDQGcFmaJgB", "name": "Adam",   "gender": "male",   "description": "Trầm, rõ, broadcast — ElevenLabs, đọc tiếng Việt OK"},
    {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female", "description": "Nữ ấm, rõ, nhịp đều — ElevenLabs"},
    # Microsoft Edge Premium Voices (Miễn phí & Không giới hạn)
    {"voice_id": "edge-vi-VN-NamMinhNeural", "name": "Nam Minh", "gender": "male", "description": "Giọng Nam Việt AI trầm ấm, tự nhiên — Microsoft Edge (Miễn phí, Không giới hạn)"},
    {"voice_id": "edge-vi-VN-HoaiMyNeural", "name": "Hoài My", "gender": "female", "description": "Giọng Nữ Việt AI mượt mà, truyền cảm — Microsoft Edge (Miễn phí, Không giới hạn)"},
]


@router.get("/voices/elevenlabs")
async def list_elevenlabs_voices() -> dict[str, Any]:
    """
    Return the list of ElevenLabs voices available to the user.
    - Always includes premade defaults.
    - If ELEVENLABS_API_KEY is set, also fetches user-added voices (category != "premade").
    """
    custom: list[dict[str, Any]] = []
    error: str | None = None
    api_key = os.getenv("ELEVENLABS_API_KEY")

    if api_key:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.elevenlabs.io/v1/voices",
                    headers={"xi-api-key": api_key, "Accept": "application/json"},
                )
                if resp.status_code == 200:
                    raw = resp.json().get("voices", [])
                    # ElevenLabs categories: "premade" (built-in), "cloned" (instant clone),
                    # "professional" (PVC), "generated" (voice design), "famous", "voice_library_added"
                    # We want anything that is NOT a premade — those are user-added voices.
                    custom_categories = {"cloned", "professional", "generated", "famous", "voice_library_added"}
                    for v in raw:
                        cat = (v.get("category") or "").lower()
                        if cat not in custom_categories:
                            continue
                        labels = v.get("labels", {}) or {}
                        custom.append({
                            "voice_id": v.get("voice_id"),
                            "name": v.get("name") or "?",
                            "gender": labels.get("gender") or "",
                            "description": " · ".join(filter(None, [
                                labels.get("language") or labels.get("accent"),
                                labels.get("age"),
                                labels.get("descriptive"),
                                labels.get("use_case"),
                                (v.get("description") or "").strip()[:80],
                            ])) or v.get("category") or "Custom voice",
                            "category": v.get("category") or "custom",
                        })
                else:
                    error = f"ElevenLabs API HTTP {resp.status_code}"
        except Exception as e:
            error = f"{type(e).__name__}: {e}"

    # Smart Default Voice: If ElevenLabs key is missing, default to Microsoft Edge's Nam Minh voice.
    # Otherwise, default to ElevenLabs' Adam voice.
    resolved_default_voice = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB") if api_key else "edge-vi-VN-NamMinhNeural"

    return {
        "default_voice_id": resolved_default_voice,
        "premade": DEFAULT_PREMADE_VOICES,
        "custom": custom,
        "has_api_key": bool(api_key),
        "error": error,
    }
