import os
import hashlib
from typing import Any
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from routers.compositions import get_project_root
from routers.build import synthesize_tts

router = APIRouter()


class PreviewRequest(BaseModel):
    voice_id: str
    text: str


# Default premade voices (Microsoft Edge, Google Gemini AI, and OpenAI)
# Enriched with 'actor', 'traits', and 'service' for professional UI display.
DEFAULT_PREMADE_VOICES: list[dict[str, str]] = [
    # OpenAI tts-1 Voices (Pinkyne API)
    {
        "voice_id": "openai-onyx",
        "name": "OpenAI Onyx",
        "gender": "male",
        "description": "Giọng Nam trầm sâu, chuyên nghiệp — OpenAI TTS (tts-1)",
        "actor": "Onyx",
        "traits": "Trầm sâu, uy tín, bản lĩnh",
        "service": "OpenAI TTS"
    },
    {
        "voice_id": "openai-alloy",
        "name": "OpenAI Alloy",
        "gender": "male",
        "description": "Giọng đọc cân bằng, tự nhiên — OpenAI TTS (tts-1)",
        "actor": "Alloy",
        "traits": "Cân bằng, tự nhiên, đa dụng",
        "service": "OpenAI TTS"
    },
    {
        "voice_id": "openai-echo",
        "name": "OpenAI Echo",
        "gender": "male",
        "description": "Giọng Nam điềm tĩnh, ấm áp — OpenAI TTS (tts-1)",
        "actor": "Echo",
        "traits": "Điềm tĩnh, ấm áp, truyền cảm",
        "service": "OpenAI TTS"
    },
    {
        "voice_id": "openai-fable",
        "name": "OpenAI Fable",
        "gender": "male",
        "description": "Giọng Nam lôi cuốn, có chiều sâu — OpenAI TTS (tts-1)",
        "actor": "Fable",
        "traits": "Lôi cuốn, tự sự, chiều sâu",
        "service": "OpenAI TTS"
    },
    {
        "voice_id": "openai-nova",
        "name": "OpenAI Nova",
        "gender": "female",
        "description": "Giọng Nữ sống động, năng lượng — OpenAI TTS (tts-1)",
        "actor": "Nova",
        "traits": "Sống động, năng lượng, tươi vui",
        "service": "OpenAI TTS"
    },
    {
        "voice_id": "openai-shimmer",
        "name": "OpenAI Shimmer",
        "gender": "female",
        "description": "Giọng Nữ chuyên nghiệp, rõ ràng — OpenAI TTS (tts-1)",
        "actor": "Shimmer",
        "traits": "Chuyên nghiệp, rõ ràng, tin cậy",
        "service": "OpenAI TTS"
    },

    # Microsoft Edge Premium Voices (Miễn phí & Không giới hạn)
    {
        "voice_id": "edge-vi-VN-NamMinhNeural",
        "name": "Nam Minh",
        "gender": "male",
        "description": "Giọng Nam Việt AI trầm ấm, tự nhiên — Microsoft Edge (Miễn phí, Không giới hạn)",
        "actor": "Nam Minh",
        "traits": "Trầm ấm, chững chạc, truyền cảm",
        "service": "Microsoft Edge"
    },
    {
        "voice_id": "edge-vi-VN-HoaiMyNeural",
        "name": "Hoài My",
        "gender": "female",
        "description": "Giọng Nữ Việt AI mượt mà, truyền cảm — Microsoft Edge (Miễn phí, Không giới hạn)",
        "actor": "Hoài My",
        "traits": "Mượt mà, truyền cảm, dịu dàng",
        "service": "Microsoft Edge"
    },
]


@router.get("/voices/elevenlabs")
async def list_elevenlabs_voices() -> dict[str, Any]:
    """
    Backwards compatible endpoint to return the list of premium voices.
    ElevenLabs has been completely deprecated in favor of Microsoft Edge, Google Gemini, and OpenAI.
    """
    return {
        "default_voice_id": "openai-onyx",
        "premade": DEFAULT_PREMADE_VOICES,
        "custom": [],
        "has_api_key": False,
        "error": None,
    }


@router.get("/voices/demo")
async def get_voice_demo(voice_id: str) -> dict[str, str]:
    """
    Generate or get cached voice demo clip speaking about the voice itself.
    """
    # 1. Map voice_id to a suitable introductory text in Vietnamese
    intro_texts = {
        "openai-onyx": "Xin chào! Tôi là Onyx, giọng đọc nam trầm ấm và vô cùng uy lực từ OpenAI TTS. Rất hân hạnh được đồng hành cùng bạn.",
        "openai-alloy": "Xin chào! Tôi là Alloy, giọng đọc tự nhiên và vô cùng cân bằng từ OpenAI TTS. Chúc bạn có một video chất lượng cao.",
        "openai-echo": "Xin chào! Tôi là Echo, giọng đọc nam điềm tĩnh và ấm áp đến từ OpenAI TTS. Rất vui được đồng hành cùng dự án của bạn.",
        "openai-fable": "Xin chào! Tôi là Fable, giọng đọc nam lôi cuốn và đầy tự sự từ OpenAI TTS. Hãy cùng tôi kể câu chuyện của bạn.",
        "openai-nova": "Xin chào! Tôi là Nova, giọng đọc nữ vô cùng sống động và ngập tràn năng lượng từ OpenAI TTS. Hãy tạo nên điều đặc biệt nào!",
        "openai-shimmer": "Xin chào! Tôi là Shimmer, giọng đọc nữ chuyên nghiệp, rõ ràng và vô cùng tin cậy từ OpenAI TTS. Chúc bạn thành công.",
        "edge-vi-VN-NamMinhNeural": "Xin chào! Tôi là Nam Minh, trợ lý giọng nói trầm ấm và vô cùng tự nhiên đến từ Microsoft Edge. Tôi đã sẵn sàng đồng hành cùng video của bạn.",
        "edge-vi-VN-HoaiMyNeural": "Xin chào! Tôi là Hoài My, trợ lý giọng nói mượt mà và truyền cảm đến từ Microsoft Edge. Chúc bạn một ngày làm việc hiệu quả.",
    }

    matched_voice = next((v for v in DEFAULT_PREMADE_VOICES if v["voice_id"] == voice_id), None)
    voice_name = matched_voice["name"] if matched_voice else "AI Assistant"
    text = intro_texts.get(voice_id, f"Xin chào! Tôi là giọng đọc {voice_name}. Rất hân hạnh được giới thiệu chất giọng tới bạn.")

    project_root = get_project_root()
    demos_dir = project_root / "assets" / "demos"
    demos_dir.mkdir(parents=True, exist_ok=True)

    # Safe filename for voice_id
    safe_voice_id = voice_id.replace(":", "_").replace("-", "_").replace(".", "_")
    demo_file = demos_dir / f"voice_{safe_voice_id}.wav"
    relative_url = f"/assets/demos/voice_{safe_voice_id}.wav"

    if demo_file.exists():
        return {"url": relative_url}

    try:
        await synthesize_tts(text, demo_file, voice_id=voice_id)
        if not demo_file.exists():
            raise HTTPException(status_code=500, detail="Failed to synthesize voice demo audio file.")
    except Exception as e:
        print(f"[voices/demo] Failed to synthesize demo for voice {voice_id}: {e}")
        raise HTTPException(status_code=500, detail=f"TTS synthesis error: {str(e)}")

    return {"url": relative_url}


@router.post("/voices/preview-5s")
async def get_5s_preview(req: PreviewRequest) -> dict[str, str]:
    """
    Synthesize and cache a 5-second preview of the actual script narration of Scene 1.
    """
    # Take the first 15 words of the narration
    words = req.text.split()
    first_words = words[:15]
    text_preview = " ".join(first_words)
    if not text_preview:
        text_preview = "Xin chào, chào mừng đến với thước phim của bạn."

    # Hash the text and voice_id to get a unique cache key
    m = hashlib.md5()
    m.update(req.voice_id.encode("utf-8"))
    m.update(text_preview.encode("utf-8"))
    text_hash = m.hexdigest()

    project_root = get_project_root()
    previews_dir = project_root / "assets" / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)

    safe_voice_id = req.voice_id.replace(":", "_").replace("-", "_").replace(".", "_")
    preview_file = previews_dir / f"preview_{safe_voice_id}_{text_hash}.wav"
    relative_url = f"/assets/previews/preview_{safe_voice_id}_{text_hash}.wav"

    if preview_file.exists():
        return {"url": relative_url}

    try:
        await synthesize_tts(text_preview, preview_file, voice_id=req.voice_id)
        if not preview_file.exists():
            raise HTTPException(status_code=500, detail="Failed to synthesize 5s preview audio file.")
    except Exception as e:
        print(f"[voices/preview-5s] Failed to synthesize preview: {e}")
        raise HTTPException(status_code=500, detail=f"TTS synthesis error: {str(e)}")

    return {"url": relative_url}

