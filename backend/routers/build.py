import asyncio
import base64
import json
import os
import re
from pathlib import Path

# Tự động dọn dẹp các biến môi trường proxy lỗi/placeholder để tránh làm hỏng kết nối của các thư viện (httpx, aiohttp, requests)
for var in ["HTTP_PROXY", "HTTPS_PROXY", "EDGE_TTS_PROXY", "http_proxy", "https_proxy"]:
    val = os.getenv(var)
    if val and ("your-proxy-ip" in val or "username:password" in val or not val.strip()):
        print(f"[system] Phát hiện và dọn dẹp proxy lỗi trong môi trường: {var}={val}")
        os.environ.pop(var, None)

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.compositions import (
    CompositionRequest,
    ScenePayload,
    get_project_root,
    stream_composition_events,
)

router = APIRouter()


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# -------- TTS via ElevenLabs (primary) + gTTS (fallback) --------

ELEVENLABS_API = "https://api.elevenlabs.io/v1/text-to-speech"
# Default Vietnamese-capable voice — Adam (multilingual). User can override via env.
DEFAULT_ELEVEN_VOICE_ID = "pNInz6obpgDQGcFmaJgB"

# Once ElevenLabs returns 401/402/quota_exceeded for ANY scene in a build, skip
# it for the remaining scenes so the final video has a single consistent voice
# (instead of one scene using a foreign male and the rest using gTTS).
# Reset to False at the start of each build via `reset_elevenlabs_state()`.
_elevenlabs_disabled = False


def reset_elevenlabs_state() -> None:
    """Call at the start of each build so a previous quota error doesn't
    permanently disable ElevenLabs for the process."""
    global _elevenlabs_disabled
    _elevenlabs_disabled = False


# -------- Microsoft Edge TTS (secondary fallback) --------
# Default Vietnamese natural voice: vi-VN-NamMinhNeural (Male).
# Other option: vi-VN-HoaiMyNeural (Female)
DEFAULT_EDGE_VOICE = "vi-VN-NamMinhNeural"


async def _edge_to_wav(text: str, target: Path, voice_name: str | None = None) -> bool:
    """Try Microsoft Edge TTS → wav. Returns True on success, False to fall back.
    Unlike ElevenLabs, Edge TTS is 100% free and has no rate limits, so it does
    not require a global disable state flag.
    """
    try:
        import edge_tts
        voice = voice_name or os.getenv("EDGE_VOICE", DEFAULT_EDGE_VOICE)
        
        # Làm sạch & chuẩn hóa text an toàn cho TTS
        clean_text = text or ""
        # Chuyển đổi ký tự & để tránh lỗi SSML XML và giúp giọng đọc tự nhiên
        clean_text = clean_text.replace("&", " và ")
        # Loại bỏ các thẻ HTML/XML
        clean_text = re.sub(r"<[^>]*>", "", clean_text)
        # Loại bỏ các dấu nhọn còn sót lại
        clean_text = clean_text.replace("<", "").replace(">", "")
        # Loại bỏ các dấu nháy đơn/nháy kép đặc biệt để tránh hỏng SSML
        clean_text = clean_text.replace("'", "").replace('"', "").replace("“", "").replace("”", "")
        clean_text = clean_text.strip()
        
        if not clean_text:
            print("[tts] Edge TTS: Cleaned text is empty, skipping")
            return False

        # We save to a temporary mp3 file first, then convert it to wav via pydub
        temp_mp3 = target.with_suffix(".mp3.tmp")
        proxy = os.getenv("EDGE_TTS_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
        
        # Defensive programming: auto-bypass invalid placeholder proxies
        if proxy and ("your-proxy-ip" in proxy or "username:password" in proxy or not proxy.strip()):
            proxy = None
            
        communicate = edge_tts.Communicate(clean_text, voice, proxy=proxy)
        await communicate.save(str(temp_mp3))

        if not temp_mp3.exists():
            print(f"[tts] Edge TTS failed to save file: {temp_mp3}")
            return False

        try:
            from pydub import AudioSegment
            seg = AudioSegment.from_file(str(temp_mp3), format="mp3")
            await asyncio.to_thread(seg.export, str(target), format="wav")
            if temp_mp3.exists():
                temp_mp3.unlink()
            return True
        except Exception as e:
            print(f"[tts] Edge mp3->wav conversion failed, renaming to wav directly: {e}")
            if temp_mp3.exists():
                temp_mp3.rename(target)
            return True

    except Exception as e:
        print(f"[tts] Edge TTS request failed: {e}")
        return False




async def _elevenlabs_to_wav(text: str, target: Path, voice_id: str | None = None) -> bool:
    """Try ElevenLabs TTS → wav. Returns True on success, False to fall back."""
    global _elevenlabs_disabled
    if _elevenlabs_disabled:
        return False

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return False

    voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_ELEVEN_VOICE_ID)
    model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

    url = f"{ELEVENLABS_API}/{voice_id}"
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.75,
            "style": 0.30,
            "use_speaker_boost": True,
        },
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                body = resp.text[:300]
                print(f"[tts] ElevenLabs HTTP {resp.status_code}: {body}")
                # Disable ElevenLabs for the rest of this build on quota/auth errors
                # so all scenes use the same engine (consistent voice).
                if resp.status_code in (401, 402, 403, 429) or "quota" in body.lower() or "payment" in body.lower():
                    _elevenlabs_disabled = True
                    print("[tts] ElevenLabs disabled for the rest of this build — falling back to gTTS for consistency.")
                return False
            mp3_bytes = resp.content
    except Exception as e:
        print(f"[tts] ElevenLabs request failed: {e}")
        return False

    # Convert mp3 → wav for HyperFrames
    try:
        from pydub import AudioSegment
        from io import BytesIO
        seg = AudioSegment.from_file(BytesIO(mp3_bytes), format="mp3")
        await asyncio.to_thread(seg.export, str(target), format="wav")
        return True
    except Exception as e:
        print(f"[tts] mp3→wav conversion failed, writing raw mp3: {e}")
        target.write_bytes(mp3_bytes)
        return True


def _gtts_to_wav_sync(text: str, lang: str, target: Path) -> None:
    """Run gTTS + mp3->wav conversion in a worker thread."""
    from gtts import gTTS
    from io import BytesIO

    mp3_buf = BytesIO()
    gTTS(text=text, lang=lang, slow=False).write_to_fp(mp3_buf)
    mp3_buf.seek(0)

    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(mp3_buf, format="mp3")
        seg.export(str(target), format="wav")
    except Exception:
        # Fallback: keep mp3, just rename — HyperFrames audio tag accepts both
        target.write_bytes(mp3_buf.getvalue())

def _trim_trailing_silence_sync(wav_path: Path, threshold_db: float = -30.0, padding_ms: int = 500) -> None:
    """Trim trailing silence of a WAV file to prevent Gemini TTS silence loop bug."""
    try:
        from pydub import AudioSegment
        sound = AudioSegment.from_file(str(wav_path), format="wav")
        duration_ms = len(sound)
        
        # Scan from end in 100ms steps
        step_ms = 100
        detected_end_ms = 0
        for pos in range(duration_ms - step_ms, -1, -step_ms):
            chunk = sound[pos : pos + step_ms]
            if chunk.dBFS > threshold_db:
                detected_end_ms = pos + step_ms
                break
        
        if detected_end_ms > 0 and detected_end_ms < duration_ms:
            padded_end_ms = min(duration_ms, detected_end_ms + padding_ms)
            if padded_end_ms < duration_ms:
                trimmed_sound = sound[:padded_end_ms]
                trimmed_sound.export(str(wav_path), format="wav")
                print(f"[tts] Programmatic silence trimming: Trimmed {wav_path.name} from {duration_ms/1000:.2f}s to {len(trimmed_sound)/1000:.2f}s (Threshold: {threshold_db} dB, Padding: {padding_ms}ms)")
    except Exception as e:
        print(f"[tts] Programmatic silence trimming failed for {wav_path}: {e}")


async def _openai_tts_to_wav(text: str, target: Path, voice_name: str = "onyx") -> bool:
    """Synthesize speech using OpenAI-compatible TTS (tts-1) via Pinkyne API.
    Returns True on success, False to fallback.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.pinkyne.com/v1").rstrip("/")
    if not api_key:
        api_key = "sk-ASUYq9R108cJ2M0B6Rb5xqNCk9lqdrsUpqXVoVDwd5dG77Yq"
        
    try:
        clean_text = text or ""
        clean_text = clean_text.replace("&", " và ")
        clean_text = re.sub(r"<[^>]*>", "", clean_text)
        clean_text = clean_text.replace("<", "").replace(">", "")
        clean_text = clean_text.replace("'", "").replace('"', "").replace("“", "").replace("”", "")
        clean_text = clean_text.strip()
        
        if not clean_text:
            print("[tts/openai] Cleaned text is empty, skipping")
            return False
            
        payload = {
            "model": "tts-1",
            "input": clean_text,
            "voice": voice_name,
            "response_format": "mp3",
            "speed": 1.0
        }
        
        temp_mp3 = target.with_suffix(".mp3.tmp")
        
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{base_url}/audio/speech",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
        if resp.status_code != 200:
            print(f"[tts/openai] HTTP {resp.status_code}: {resp.text[:200]}")
            return False
            
        temp_mp3.write_bytes(resp.content)
        
        if not temp_mp3.exists():
            print(f"[tts/openai] failed to save file: {temp_mp3}")
            return False
            
        try:
            from pydub import AudioSegment
            seg = AudioSegment.from_file(str(temp_mp3), format="mp3")
            await asyncio.to_thread(seg.export, str(target), format="wav")
            if temp_mp3.exists():
                temp_mp3.unlink()
            return True
        except Exception as e:
            print(f"[tts/openai] mp3->wav conversion failed, renaming directly: {e}")
            if temp_mp3.exists():
                temp_mp3.rename(target)
            return True
            
    except Exception as e:
        print(f"[tts/openai] request failed: {e}")
        return False


async def _gemini_to_wav(text: str, target: Path, voice_name: str | None = None) -> bool:
    """Try Gemini TTS:
    1. Direct Google Gemini API using GEMINI_API_KEY if available.
    2. Fallback to Pinky API proxy (Flash model) using OPENAI_API_KEY.
    3. Fallback to Pinky API proxy (Pro model) if Flash returns 429.
    Returns True on success, False to fall back.
    """
    voice = voice_name or "Puck"
    
    # Làm sạch & chuẩn hóa text an toàn cho TTS
    clean_text = text or ""
    # Chuyển đổi ký tự & để tránh lỗi SSML XML và giúp giọng đọc tự nhiên
    clean_text = clean_text.replace("&", " và ")
    # Loại bỏ các thẻ HTML/XML
    clean_text = re.sub(r"<[^>]*>", "", clean_text)
    # Loại bỏ các dấu nhọn còn sót lại
    clean_text = clean_text.replace("<", "").replace(">", "")
    # Loại bỏ các dấu nháy đơn/nháy kép đặc biệt để tránh hỏng SSML
    clean_text = clean_text.replace("'", "").replace('"', "").replace("“", "").replace("”", "")
    clean_text = clean_text.strip()
    
    if not clean_text:
        print("[tts] Gemini TTS: Cleaned text is empty, skipping")
        return False

    payload = {
        "contents": [{
            "parts": [{
                "text": clean_text
            }]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "temperature": 0.0,
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice
                    }
                }
            }
        }
    }

    # Xây dựng danh sách các endpoint thử nghiệm (Attempts) với gemini-3.1 làm ưu tiên hàng đầu
    attempts = []
    
    direct_key = os.getenv("GEMINI_API_KEY")
    pinky_key = os.getenv("OPENAI_API_KEY")
    
    # ── Tier 1: Gemini 3.1 (Ưu tiên hàng đầu) ──────────────────
    if direct_key:
        direct_url_31 = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-tts-preview:generateContent?key={direct_key}"
        attempts.append(("Direct Google Gemini API (Flash 3.1)", direct_url_31, {"Content-Type": "application/json"}))
        
    if pinky_key:
        pinky_headers = {
            "Authorization": f"Bearer {pinky_key}",
            "Content-Type": "application/json"
        }
        flash_url_31 = "https://api.pinkyne.com/v1beta/models/gemini-3.1-flash-tts-preview:generateContent"
        attempts.append(("Pinky Proxy (Flash 3.1)", flash_url_31, pinky_headers))
        
    # ── Tier 2: Gemini 2.5 Fallbacks ───────────────────────────
    if direct_key:
        direct_url_25 = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={direct_key}"
        attempts.append(("Direct Google Gemini API (Flash 2.5)", direct_url_25, {"Content-Type": "application/json"}))
        
    if pinky_key:
        pinky_headers = {
            "Authorization": f"Bearer {pinky_key}",
            "Content-Type": "application/json"
        }
        flash_url_25 = "https://api.pinkyne.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
        pro_url_25 = "https://api.pinkyne.com/v1beta/models/gemini-2.5-pro-preview-tts:generateContent"
        attempts.append(("Pinky Proxy (Flash 2.5)", flash_url_25, pinky_headers))
        attempts.append(("Pinky Proxy (Pro 2.5)", pro_url_25, pinky_headers))

    if not attempts:
        print("[tts] Gemini TTS: No API keys found in environment.")
        return False

    audio_bytes = None
    max_retries_per_endpoint = 2
    base_delay = 3

    try:
        async with httpx.AsyncClient(timeout=180, trust_env=False) as client:
            resp = None
            success = False
            
            for idx, (desc, url, headers) in enumerate(attempts):
                print(f"[tts] Trying Gemini TTS via {desc}...")
                
                for attempt in range(max_retries_per_endpoint + 1):
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 429:
                        if attempt < max_retries_per_endpoint:
                            wait = base_delay * (2 ** attempt)
                            print(f"[tts] {desc} got HTTP 429 (rate limit). Retry {attempt + 1}/{max_retries_per_endpoint} in {wait}s...")
                            await asyncio.sleep(wait)
                            continue
                        else:
                            print(f"[tts] {desc} failed with HTTP 429 after {max_retries_per_endpoint} retries.")
                            break  # Chuyển sang endpoint dự phòng tiếp theo
                    break  # Nhận 200 hoặc mã lỗi khác không phải 429, thoát khỏi loop retry
                
                if resp and resp.status_code == 200:
                    print(f"[tts] Gemini TTS via {desc} succeeded!")
                    success = True
                    break
                elif resp:
                    print(f"[tts] {desc} returned HTTP {resp.status_code}: {resp.text[:300]}")
            
            if not success or not resp:
                print("[tts] Gemini TTS: All endpoints failed.")
                return False
                
            res_json = resp.json()
            parts = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            b64_audio = None
            for part in parts:
                if "inlineData" in part:
                    b64_audio = part["inlineData"]["data"]
                    break
            
            if not b64_audio:
                candidate = res_json.get("candidates", [{}])[0]
                finish_reason = candidate.get("finishReason")
                safety_ratings = candidate.get("safetyRatings", [])
                print(f"[tts] Gemini TTS: Could not find audio inlineData. finishReason: {finish_reason}, safetyRatings: {safety_ratings}")
                return False
            
            audio_bytes = base64.b64decode(b64_audio)
    except Exception as e:
        print(f"[tts] Gemini TTS request failed: {type(e).__name__}: {e}")
        return False

    # Save and convert raw PCM L16 → wav natively
    try:
        import wave
        
        # Ensure length is a multiple of 2 (16-bit samples)
        if len(audio_bytes) % 2 != 0:
            audio_bytes = audio_bytes[:(len(audio_bytes) // 2) * 2]
            
        def _write_wav():
            with wave.open(str(target), 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(24000)
                wav_file.writeframes(audio_bytes)
                
        await asyncio.to_thread(_write_wav)
        # Apply programmatic trailing silence trimming to prevent Gemini silence loop bug
        await asyncio.to_thread(_trim_trailing_silence_sync, target)
        return True
    except Exception as e:
        print(f"[tts] Gemini raw PCM L16 → wav conversion failed: {e}")
        return False


async def synthesize_tts(text: str, target: Path, voice_id: str | None = None) -> str:
    """
    Synthesize speech for `text` to `target`.
    Order: If voice_id starts with 'openai-', use OpenAI TTS via Pinky.
           If voice_id starts with 'gemini-', use Gemini TTS.
           If voice_id starts with 'edge-', use Edge TTS directly.
           Else: ElevenLabs (if ELEVENLABS_API_KEY set) → Edge TTS → gTTS fallback.
    Returns the engine name actually used ('openai', 'gemini', 'elevenlabs', 'edge', or 'gtts').
    """
    # 0. Direct OpenAI TTS routing if explicitly selected in UI
    if voice_id and voice_id.startswith("openai-"):
        openai_voice = voice_id.replace("openai-", "")
        if await _openai_tts_to_wav(text, target, voice_name=openai_voice):
            return "openai"
        if await _edge_to_wav(text, target):
            return "edge"
        lang = os.getenv("TTS_LANG", "vi")
        await asyncio.to_thread(_gtts_to_wav_sync, text, lang, target)
        return "gtts"

    # 1. Direct Gemini TTS routing if explicitly selected in UI
    if voice_id and voice_id.startswith("gemini-"):
        voice_name = "Puck"
        if ":" in voice_id:
            parts = voice_id.split(":")
            if len(parts) > 1 and parts[1]:
                voice_name = parts[1]
        
        if await _gemini_to_wav(text, target, voice_name=voice_name):
            return "gemini"
            
        # If Gemini fails, fallback to Edge TTS or gTTS
        if await _edge_to_wav(text, target):
            return "edge"
        lang = os.getenv("TTS_LANG", "vi")
        await asyncio.to_thread(_gtts_to_wav_sync, text, lang, target)
        return "gtts"

    # 2. Direct Edge TTS routing if explicitly selected in UI
    if voice_id and voice_id.startswith("edge-"):
        edge_voice = voice_id.replace("edge-", "")
        if await _edge_to_wav(text, target, voice_name=edge_voice):
            return "edge"
        # If the specific Edge voice fails, try the default Edge voice
        if await _edge_to_wav(text, target):
            return "edge"
        # If that fails, fallback to gTTS (never fall through to ElevenLabs with an edge voice ID!)
        lang = os.getenv("TTS_LANG", "vi")
        await asyncio.to_thread(_gtts_to_wav_sync, text, lang, target)
        return "gtts"

    # 3. Standard pipeline (for ElevenLabs or unconfigured builds)
    if await _elevenlabs_to_wav(text, target, voice_id=voice_id):
        return "elevenlabs"

    if await _edge_to_wav(text, target):
        return "edge"

    # 4. Fallback
    lang = os.getenv("TTS_LANG", "vi")
    await asyncio.to_thread(_gtts_to_wav_sync, text, lang, target)
    return "gtts"


def get_audio_duration_s(path: Path) -> float:
    """Return duration in seconds of a wav/mp3 file. Falls back to 0 on error."""
    try:
        if path.suffix.lower() == '.wav':
            import wave
            with wave.open(str(path), 'rb') as r:
                frames = r.getnframes()
                rate = r.getframerate()
                if rate > 0:
                    return frames / float(rate)
    except Exception:
        pass

    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(str(path))
        return len(seg) / 1000.0
    except Exception:
        return 0.0


_faster_whisper_model_cache: dict = {}   # module-level model cache (avoid re-downloading)
_whisperx_model_cache: dict = {}          # WhisperX model cache (torch-based, GPU/CPU)


# Rich vocabulary prompt to guide Whisper for technical terms and project names
WHISPER_PROMPT = (
    "hyperframes, Heygen, Heygen-com, Claude, Claude Code, Codex, Vite, React, "
    "npx, skills, add, HTML, CSS, JavaScript, GSAP, keyframe, transition, overlay, "
    "canvas, scene, narration, karaoke, techbeat"
)


def _transcribe_whisperx_sync(wav_path: Path) -> list[dict]:
    """Transcribe with WhisperX using Wav2Vec word alignment for superior accuracy.
    Falls back to [] on any import/runtime error so caller can continue to faster-whisper.
    Each entry: {"word": str, "start": float, "end": float}
    """
    import traceback as _tb
    try:
        import torch  # type: ignore
        import whisperx  # type: ignore

        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"

        # Load or reuse cached WhisperX model
        cache_key = f"whisperx_{device}"
        if cache_key not in _whisperx_model_cache:
            print(f"[whisperx] Loading 'tiny' model on {device} (first run — may download ~39 MB)…")
            _whisperx_model_cache[cache_key] = whisperx.load_model(
                "tiny", device, compute_type=compute_type,
                language="vi", asr_options={"initial_prompt": WHISPER_PROMPT}
            )
            print(f"[whisperx] Model ready on {device}")

        model = _whisperx_model_cache[cache_key]

        # Step 1: transcribe
        import torchaudio  # type: ignore (ships with torch)
        audio = whisperx.load_audio(str(wav_path))
        result = model.transcribe(audio, batch_size=4, language="vi")

        if not result.get("segments"):
            print(f"[whisperx] {wav_path.name}: no segments found")
            return []

        # Step 2: align words with Wav2Vec
        try:
            align_model, metadata = whisperx.load_align_model(language_code="vi", device=device)
            aligned = whisperx.align(
                result["segments"], align_model, metadata,
                audio, device, return_char_alignments=False
            )
            segments = aligned.get("segments", result["segments"])
        except Exception as ae:
            print(f"[whisperx] Alignment skipped (no vi Wav2Vec model): {ae}")
            segments = result["segments"]

        # Flatten word-level entries
        words: list[dict] = []
        for seg in segments:
            for w in seg.get("words", []):
                text = str(w.get("word", "")).strip()
                if text:
                    words.append({
                        "word":  text,
                        "start": round(float(w.get("start", 0)), 3),
                        "end":   round(float(w.get("end",   0)), 3),
                    })

        print(f"[whisperx] {wav_path.name}: {len(words)} words (device={device})")
        return words
    except ImportError:
        print("[whisperx] whisperx or torch not installed — skipping")
    except Exception as e:
        print(f"[whisperx] error: {e}")
        _tb.print_exc()
        _whisperx_model_cache.clear()  # reset cache so next run retries cleanly
    return []


def _transcribe_sync(wav_path: Path) -> list[dict]:
    """Run Whisper synchronously (called via asyncio.to_thread).
    Tries faster-whisper (tiny, auto compute_type) first, then openai-whisper, then [].
    Each entry: {"word": str, "start": float, "end": float}
    """
    import traceback as _tb

    # ── faster-whisper (preferred: 4-10× faster on CPU) ──────────────────
    try:
        from faster_whisper import WhisperModel  # type: ignore
        if "model" not in _faster_whisper_model_cache:
            print("[whisper] Loading faster-whisper 'tiny' model (first run – may download ~39 MB) …")
            loaded = None
            for ct in ("int8", "float32"):
                try:
                    loaded = WhisperModel("tiny", device="cpu", compute_type=ct)
                    print(f"[whisper] faster-whisper model ready (compute_type={ct})")
                    break
                except Exception as le:
                    print(f"[whisper] load failed (compute_type={ct}): {le}")
            if loaded is None:
                raise RuntimeError("faster-whisper: could not load model with any compute_type")
            _faster_whisper_model_cache["model"] = loaded
        model = _faster_whisper_model_cache["model"]
        segments, _ = model.transcribe(str(wav_path), language="vi", word_timestamps=True, initial_prompt=WHISPER_PROMPT)
        words = []
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    text = w.word.strip()
                    if text:
                        words.append({"word": text, "start": round(w.start, 3), "end": round(w.end, 3)})
        print(f"[whisper/faster] {wav_path.name}: {len(words)} words")
        return words
    except ImportError:
        print("[whisper] faster-whisper not installed")
    except Exception as e:
        print(f"[whisper/faster] error: {e}")
        _tb.print_exc()
        _faster_whisper_model_cache.pop("model", None)  # reset so next build retries

    # ── openai-whisper (fallback) ─────────────────────────────────────────
    try:
        import whisper  # type: ignore
        model = whisper.load_model("tiny")
        result = model.transcribe(str(wav_path), language="vi", word_timestamps=True, verbose=False, initial_prompt=WHISPER_PROMPT)
        words = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                text = w["word"].strip()
                if text:
                    words.append({"word": text, "start": round(w["start"], 3), "end": round(w["end"], 3)})
        print(f"[whisper/openai] {wav_path.name}: {len(words)} words")
        return words
    except ImportError:
        print("[whisper] openai-whisper not installed — using chunk fallback")
    except Exception as e:
        print(f"[whisper/openai] error: {e}")
        _tb.print_exc()

    return []


async def _transcribe_openai_api(wav_path: Path) -> list[dict]:
    """Use OpenAI Whisper API (whisper-1) for word-level timestamps.
    Uses OPENAI_API_KEY + OPENAI_BASE_URL from .env.
    Returns [] on any failure so callers fall through to Groq / local.
    """
    api_key  = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if not api_key:
        return []
    try:
        file_bytes = wav_path.read_bytes()
        if len(file_bytes) > 24 * 1024 * 1024:
            print(f"[whisper/openai-api] {wav_path.name} too large — skipping")
            return []
        # Same httpx multipart workaround as Groq: encode all fields into files=
        multipart = [
            ("file",                       (wav_path.name, file_bytes, "audio/wav")),
            ("model",                      (None, "whisper-1")),
            ("language",                   (None, "vi")),
            ("response_format",            (None, "verbose_json")),
            ("timestamp_granularities[]",  (None, "word")),
            ("timestamp_granularities[]",  (None, "segment")),
            ("prompt",                     (None, WHISPER_PROMPT)),
        ]
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files=multipart,
            )
        if resp.status_code != 200:
            print(f"[whisper/openai-api] HTTP {resp.status_code}: {resp.text[:200]}")
            return []
        data = resp.json()
        words: list[dict] = []

        # Word-level timestamps (preferred)
        if data.get("words"):
            for w in data["words"]:
                text = str(w.get("word", "")).strip()
                if text:
                    words.append({
                        "word":  text,
                        "start": round(float(w.get("start", 0)), 3),
                        "end":   round(float(w.get("end",   0)), 3),
                    })

        # Segment-level fallback: interpolate within each segment
        if not words and data.get("segments"):
            for seg in data["segments"]:
                ws = [t for t in str(seg.get("text", "")).split() if t]
                if not ws:
                    continue
                t0   = float(seg.get("start", 0))
                t1   = float(seg.get("end", t0 + 1))
                step = (t1 - t0) / len(ws)
                for k, w in enumerate(ws):
                    words.append({
                        "word":  w,
                        "start": round(t0 + k * step,       3),
                        "end":   round(t0 + (k + 1) * step, 3),
                    })

        print(f"[whisper/openai-api] {wav_path.name}: {len(words)} words")
        return words
    except Exception as e:
        print(f"[whisper/openai-api] error: {e}")
        return []


async def _transcribe_groq_api(wav_path: Path) -> list[dict]:
    """Use Groq's hosted Whisper API (whisper-large-v3-turbo) for word-level timestamps.
    Returns [] on any failure so callers can transparently fall through to local Whisper.
    Requires GROQ_API_KEY in the environment.
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return []
    try:
        file_bytes = wav_path.read_bytes()
        if len(file_bytes) > 24 * 1024 * 1024:  # Groq limit is 25 MB
            print(f"[whisper/groq] {wav_path.name} too large ({len(file_bytes)//1024} KB) — skipping")
            return []
        # IMPORTANT: encode ALL fields (including form fields) into `files=`
        # using (None, value) tuples — mixing `data=list-of-tuples` with
        # `files=dict` triggers httpx's "sync request with AsyncClient" error
        # in 0.28+ because the multipart encoder takes an incompatible path.
        multipart = [
            ("file",                       (wav_path.name, file_bytes, "audio/wav")),
            ("model",                      (None, "whisper-large-v3-turbo")),
            ("language",                   (None, "vi")),
            ("response_format",            (None, "verbose_json")),
            ("timestamp_granularities[]",  (None, "word")),
            ("timestamp_granularities[]",  (None, "segment")),
            ("prompt",                     (None, WHISPER_PROMPT)),
        ]
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files=multipart,
            )
        if resp.status_code != 200:
            print(f"[whisper/groq] HTTP {resp.status_code}: {resp.text[:300]}")
            return []
        data = resp.json()
        words: list[dict] = []

        # Word-level timestamps (preferred — returned when Groq supports it)
        if data.get("words"):
            for w in data["words"]:
                text = str(w.get("word", "")).strip()
                if text:
                    words.append({
                        "word":  text,
                        "start": round(float(w.get("start", 0)), 3),
                        "end":   round(float(w.get("end",   0)), 3),
                    })

        # Segment-level fallback: interpolate word positions within each segment
        if not words and data.get("segments"):
            for seg in data["segments"]:
                ws = [t for t in str(seg.get("text", "")).split() if t]
                if not ws:
                    continue
                t0 = float(seg.get("start", 0))
                t1 = float(seg.get("end", t0 + 1))
                step = (t1 - t0) / len(ws)
                for k, w in enumerate(ws):
                    words.append({
                        "word":  w,
                        "start": round(t0 + k * step,       3),
                        "end":   round(t0 + (k + 1) * step, 3),
                    })

        print(f"[whisper/groq] {wav_path.name}: {len(words)} words")
        return words
    except Exception as e:
        print(f"[whisper/groq] error: {e}")
        return []


async def _transcribe_pinkyne_api(wav_path: Path) -> list[dict]:
    """Use Pinkyne Whisper API (https://api.pinkyne.com/v1/audio/transcriptions) for transcription with word timestamps.
    Returns [] on any failure to fallback to other Whisper engines.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = "https://api.pinkyne.com/v1"
    if not api_key:
        api_key = "sk-ASUYq9R108cJ2M0B6Rb5xqNCk9lqdrsUpqXVoVDwd5dG77Yq"
    try:
        file_bytes = wav_path.read_bytes()
        if len(file_bytes) > 24 * 1024 * 1024:
            print(f"[whisper/pinkyne] {wav_path.name} too large — skipping")
            return []
        
        multipart = [
            ("file",                       (wav_path.name, file_bytes, "audio/wav")),
            ("model",                      (None, "whisper-1")),
            ("language",                   (None, "vi")),
            ("response_format",            (None, "verbose_json")),
            ("timestamp_granularities[]",  (None, "word")),
            ("timestamp_granularities[]",  (None, "segment")),
            ("prompt",                     (None, WHISPER_PROMPT)),
        ]
        
        import asyncio
        max_retries = 5
        backoff = 30.0
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    resp = await client.post(
                        f"{base_url}/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        files=multipart,
                    )
                if resp.status_code == 429:
                    print(f"[whisper/pinkyne] Rate limit (429) on attempt {attempt+1}/{max_retries}. Backing off for {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                if resp.status_code != 200:
                    print(f"[whisper/pinkyne] HTTP {resp.status_code}: {resp.text[:200]}")
                    return []
                break
            except Exception as ex:
                if attempt == max_retries - 1:
                    raise ex
                print(f"[whisper/pinkyne] Request exception: {ex}. Retrying...")
                await asyncio.sleep(5.0)
        
        data = resp.json()
        words: list[dict] = []

        if data.get("words"):
            for w in data["words"]:
                text = str(w.get("word", "")).strip()
                if text:
                    words.append({
                        "word":  text,
                        "start": round(float(w.get("start", 0)), 3),
                        "end":   round(float(w.get("end",   0)), 3),
                    })

        if not words and data.get("segments"):
            for seg in data["segments"]:
                ws = [t for t in str(seg.get("text", "")).split() if t]
                if not ws:
                    continue
                t0   = float(seg.get("start", 0))
                t1   = float(seg.get("end", t0 + 1))
                step = (t1 - t0) / len(ws)
                for k, w in enumerate(ws):
                    words.append({
                        "word":  w,
                        "start": round(t0 + k * step,       3),
                        "end":   round(t0 + (k + 1) * step, 3),
                    })

        print(f"[whisper/pinkyne] {wav_path.name}: {len(words)} words")
        return words
    except Exception as e:
        print(f"[whisper/pinkyne] error: {e}")
        return []


async def transcribe_audio_whisper(wav_path: Path) -> tuple[list[dict], str]:
    """Transcribe audio → (word_list, engine_name).
    Priority: Pinkyne API → OpenAI API → Groq API → WhisperX local (Wav2Vec aligned) → faster-whisper local → chunk fallback.
    engine_name: 'pinkyne-whisper-1' | 'openai-whisper-1' | 'groq-whisper-v3-turbo' | 'whisperx-tiny' | 'faster-whisper-tiny' | 'chunk-fallback'
    """
    # 1. Pinkyne Whisper API (whisper-1 with 429 backoff)
    words = await _transcribe_pinkyne_api(wav_path)
    if words:
        return words, "pinkyne-whisper-1"
    # 2. OpenAI Whisper API (whisper-1)
    words = await _transcribe_openai_api(wav_path)
    if words:
        return words, "openai-whisper-1"
    # 2. Groq Whisper API (whisper-large-v3-turbo)
    words = await _transcribe_groq_api(wav_path)
    if words:
        return words, "groq-whisper-v3-turbo"
    # 3. WhisperX local (Wav2Vec word alignment — most accurate offline option)
    try:
        words = await asyncio.to_thread(_transcribe_whisperx_sync, wav_path)
        if words:
            return words, "whisperx-tiny"
    except Exception as e:
        print(f"[whisperx] thread error: {e}")
    # 4. Local faster-whisper / openai-whisper (lighter fallback)
    try:
        words = await asyncio.to_thread(_transcribe_sync, wav_path)
        if words:
            return words, "faster-whisper-tiny"
    except Exception as e:
        print(f"[whisper] local thread error: {e}")
    return [], "chunk-fallback"


def align_script_with_whisper(script: str, whisper_words: list[dict], audio_duration: float) -> list[dict]:
    """Align the original script narration text with the Whisper word-level timestamps,
    copying matched timings and interpolating unmatched timings.
    This guarantees that the exact script text (punctuation, casing) is shown in subtitles,
    but dynamically synchronized to the voice audio.
    """
    import difflib
    import re
    
    if not script:
        return []
    
    script_words = script.split()
    if not script_words:
        return []
        
    if not whisper_words:
        # Fallback: uniform linear interpolation over the entire audio duration
        n = len(script_words)
        step = audio_duration / n
        return [
            {
                "word": w,
                "start": round(i * step, 3),
                "end": round((i + 1) * step, 3)
            }
            for i, w in enumerate(script_words)
        ]
        
    def _clean_word(w: str) -> str:
        return re.sub(r'[^\w\s]', '', w.lower())
        
    clean_script = [_clean_word(w) for w in script_words]
    clean_whisper = [_clean_word(w.get("word", "")) for w in whisper_words]
    
    # 1. Match script words to whisper words using difflib.SequenceMatcher
    matcher = difflib.SequenceMatcher(None, clean_script, clean_whisper)
    matching_blocks = matcher.get_matching_blocks()
    
    matched_whisper_idx = [None] * len(script_words)
    for a, b, size in matching_blocks:
        for offset in range(size):
            if a + offset < len(script_words) and b + offset < len(whisper_words):
                matched_whisper_idx[a + offset] = b + offset
                
    # 2. Reconstruct script words with copied/interpolated timestamps
    aligned_words = []
    n_script = len(script_words)
    
    for i in range(n_script):
        w = script_words[i]
        j = matched_whisper_idx[i]
        if j is not None:
            aligned_words.append({
                "word": w,
                "start": float(whisper_words[j].get("start", 0.0)),
                "end": float(whisper_words[j].get("end", 0.0))
            })
        else:
            # Interpolate unmatched gap
            prev_end = 0.0
            for pi in range(i - 1, -1, -1):
                pj = matched_whisper_idx[pi]
                if pj is not None:
                    prev_end = float(whisper_words[pj].get("end", 0.0))
                    break
                    
            next_start = audio_duration
            for ni in range(i + 1, n_script):
                nj = matched_whisper_idx[ni]
                if nj is not None:
                    next_start = float(whisper_words[nj].get("start", 0.0))
                    break
                    
            # Find boundary of this unmatched run
            block_start_i = i
            while block_start_i > 0 and matched_whisper_idx[block_start_i - 1] is None:
                block_start_i -= 1
                
            block_end_i = i
            while block_end_i < n_script - 1 and matched_whisper_idx[block_end_i + 1] is None:
                block_end_i += 1
                
            block_len = block_end_i - block_start_i + 1
            idx_in_block = i - block_start_i
            
            time_range = max(0.0, next_start - prev_end)
            step = time_range / block_len
            
            w_start = prev_end + idx_in_block * step
            w_end = prev_end + (idx_in_block + 1) * step
            
            aligned_words.append({
                "word": w,
                "start": round(w_start, 3),
                "end": round(w_end, 3)
            })
            
    return aligned_words


def _word_data_to_js(word_data: list[list[dict]], n_scenes: int) -> str:
    """Serialize word_data to a JS array literal safe to embed in a <script>."""
    parts = []
    for i in range(n_scenes):
        if i < len(word_data) and word_data[i]:
            items = ",".join(
                f'{{"word":{json.dumps(w["word"], ensure_ascii=False)},"start":{w["start"]:.3f},"end":{w["end"]:.3f}}}'
                for w in word_data[i]
            )
            parts.append(f"[{items}]")
        else:
            parts.append("[]")
    return "[" + ",".join(parts) + "]"


def patch_html_timing(
    html: str,
    durations: list[float],
    scene_titles: list[str] | None = None,
    scene_narrations: list[str] | None = None,
    word_data: list[list[dict]] | None = None,
) -> str:
    """
    Sync HTML timing to actual TTS audio lengths:
    - Strips the LLM-authored GSAP timeline so HyperFrames doesn't capture a
      reference to a timeline built on the (wrong) estimated durations.
    - Patches data-start / data-duration on each <audio id="vN"> tag
    - Embeds scene title as data-title on each <audio> for fallback rendering
    - Patches root data-duration
    - Injects a fresh <script> that builds the SOLE GSAP timeline using actual
      audio durations and registers it on window.__timelines.
    Each scene gets ceil(audio_duration) seconds + 1s tail for breathing room.
    """
    import math

    # Automatically add data-layout-ignore to decorative elements (ghost-text, float-orb, retro-grid, etc.)
    # to prevent layout overflow errors during hyperframes inspect
    html = re.sub(
        r'class="([^"]*(?:ghost-text|float-orb|glow-orb|retro-grid|animated-grid)[^"]*)"(?!\\s+data-layout-ignore)',
        r'class="\\1" data-layout-ignore',
        html,
        flags=re.IGNORECASE
    )

    int_durs = [max(1, math.ceil(d) + 1) for d in durations]  # +1s buffer per scene
    starts: list[int] = []
    cursor = 0
    for d in int_durs:
        starts.append(cursor)
        cursor += d
    total = cursor

    # --- 1. Strip ALL <script> blocks that author a GSAP timeline ---
    # The LLM consistently builds a timeline based on its estimated scene
    # durations. HyperFrames captures the first registered timeline, so even
    # if we kill it client-side later, the render still uses the LLM's wrong
    # timing. Removing the original script entirely is the only reliable fix.
    def _is_timeline_script(body: str) -> bool:
        return ("gsap.timeline" in body or "GSAP" in body.upper() and "timeline" in body) \
               and ("__timelines" in body or "tl.to" in body or "tl.set" in body or "tl.from" in body)

    def _strip_timeline_scripts(s: str) -> str:
        out = []
        i = 0
        while True:
            m = re.search(r"<script\b[^>]*>", s[i:], flags=re.IGNORECASE)
            if not m:
                out.append(s[i:])
                break
            tag_start = i + m.start()
            tag_end = i + m.end()
            close = re.search(r"</script\s*>", s[tag_end:], flags=re.IGNORECASE)
            if not close:
                out.append(s[i:])
                break
            body_end = tag_end + close.start()
            block_end = tag_end + close.end()
            tag_open = s[tag_start:tag_end]
            body = s[tag_end:body_end]

            # ALWAYS preserve content between previous cursor and this script tag
            out.append(s[i:tag_start])

            # Keep external <script src="..."> (GSAP CDN) and any non-timeline script
            if re.search(r'\bsrc\s*=', tag_open, flags=re.IGNORECASE) or not _is_timeline_script(body):
                out.append(s[tag_start:block_end])
            # else: drop this <script>...</script> block (don't append it)

            i = block_end
        return "".join(out)

    html = _strip_timeline_scripts(html)

    # --- 2. Clean, Generate & Inject <audio> tags ---
    # Strip any existing <audio> tags matching vN to avoid duplicates or buggy formatting
    html = re.sub(r'<audio\s+[^>]*id=["\']v\d+["\'][^>]*>.*?</audio>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<audio\s+[^>]*id=["\']v\d+["\'][^>]*>', '', html, flags=re.IGNORECASE)

    audio_tags = []
    for i, (start, dur) in enumerate(zip(starts, int_durs)):
        n = i + 1
        safe_title = ""
        if scene_titles and i < len(scene_titles):
            safe_title = scene_titles[i].replace('"', '&quot;')
        audio_tags.append(
            f'<audio id="v{n}" src="assets/p{n}.wav" data-start="{start}" data-duration="{dur}" data-volume="1" data-title="{safe_title}"></audio>'
        )
    audio_block = "\n  " + "\n  ".join(audio_tags) + "\n"

    # Inject right after opening root div
    root_match = re.search(r'(<div\s+[^>]*?(?:id=["\']root["\']|data-composition-id=["\']main["\'])[^>]*>)', html, flags=re.IGNORECASE)
    if root_match:
        idx = root_match.end()
        html = html[:idx] + audio_block + html[idx:]
    else:
        # Fallback
        if "</body>" in html:
            html = html.replace("</body>", audio_block + "</body>")
        else:
            html += audio_block

    # --- 3. Patch root data-duration ---
    html = re.sub(
        r'(id=["\']root["\'][^>]*?)data-duration=["\'][^"\']*["\']',
        rf'\1data-duration="{total}"',
        html,
    )
    html = re.sub(
        r'(data-composition-id=["\']main["\'][^>]*?)data-duration=["\'][^"\']*["\']',
        rf'\1data-duration="{total}"',
        html,
    )

    # --- 4. Inject SOLE timeline that uses actual TTS durations ---
    starts_js = ", ".join(str(s) for s in starts)
    durs_js = ", ".join(str(d) for d in int_durs)
    actual_durs_js = ", ".join(f"{d:.3f}" for d in durations)

    scene_narrations = scene_narrations or []
    safe_narrations = []
    for narration in scene_narrations:
        clean = narration.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
        safe_narrations.append(clean)
    narrations_js = ", ".join(f'"{n}"' for n in safe_narrations)

    n_scenes = len(durations)
    word_data_js = _word_data_to_js(word_data or [], n_scenes)

    inject = f"""
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/TextPlugin.min.js"></script>
<script>
// Sole timeline injected by TechBeat build pipeline.
// The LLM's original timeline script has been stripped server-side so this
// is the ONLY timeline registered on window.__timelines["main"].
(function() {{
  var starts    = [{starts_js}];
  var durs      = [{durs_js}];
  var actualDurs= [{actual_durs_js}];
  var narrations= [{narrations_js}];
  var total     = {total};
  // Word-level Whisper data. Each entry: [{{word,start,end}},...] or []
  var wordData  = {word_data_js};
  var WLINE     = 7; // words per subtitle line

  function backspaceWord(tl, el, word, startTime, cps) {{
    var interval = 1 / cps;
    for (var k = word.length - 1; k >= 0; k--) {{
      (function(index) {{
        tl.call(function() {{
          el.textContent = word.slice(0, index);
        }}, [], startTime + (word.length - index) * interval);
      }})(k);
    }}
    return word.length * interval;
  }}

  function compileTextEffects(sceneId, sceneStart, tl) {{
    var scEl = document.querySelector(sceneId);
    if (!scEl) return;

    // A. Typewriter effect
    var typewriters = scEl.querySelectorAll("[data-effect='typewriter']");
    typewriters.forEach(function(el) {{
      var text = el.textContent.trim();
      if (!text) return;

      var cursor = el.nextElementSibling;
      var hasCursor = cursor && (cursor.className.indexOf("cursor") !== -1);

      var cps = 12; // conversational speed
      var dur = text.length / cps;
      var startOffset = sceneStart + 0.3; // wait briefly for badge entrance

      // Deterministically clear the element at the beginning of its typing
      tl.set(el, {{ text: "" }}, startOffset);

      if (hasCursor) {{
        tl.call(function() {{ cursor.className = "cursor-solid"; }}, [], startOffset);
      }}
      tl.to(el, {{ text: {{ value: text }}, duration: dur, ease: "none" }}, startOffset);
      if (hasCursor) {{
        tl.call(function() {{ cursor.className = "cursor-blink"; }}, [], startOffset + dur);
      }}
    }});

    // B. Word Rotations
    var rotators = scEl.querySelectorAll("[data-effect='word-rotate']");
    rotators.forEach(function(el) {{
      var wordsStr = el.getAttribute("data-words");
      if (!wordsStr) return;
      var words = wordsStr.split(",").map(function(w) {{ return w.trim(); }});
      if (words.length === 0) return;

      var cursor = el.nextElementSibling;
      var hasCursor = cursor && (cursor.className.indexOf("cursor") !== -1);

      var offset = sceneStart + 0.4;
      
      // Deterministically clear the element at the beginning of its rotation
      tl.set(el, {{ text: "" }}, offset);

      words.forEach(function(word, i) {{
        var typeDur = word.length / 10;

        // Type word
        if (hasCursor) {{
          tl.call(function() {{ cursor.className = "cursor-solid"; }}, [], offset);
        }}
        tl.to(el, {{ text: {{ value: word }}, duration: typeDur, ease: "none" }}, offset);
        if (hasCursor) {{
          tl.call(function() {{ cursor.className = "cursor-blink"; }}, [], offset + typeDur);
        }}

        offset += typeDur + 1.2; // hold word

        // Backspace if not the last word
        if (i < words.length - 1) {{
          if (hasCursor) {{
            tl.call(function() {{ cursor.className = "cursor-solid"; }}, [], offset);
          }}
          var clearDur = backspaceWord(tl, el, word, offset, 16);
          if (hasCursor) {{
            tl.call(function() {{ cursor.className = "cursor-blink"; }}, [], offset + clearDur);
          }}
          offset += clearDur + 0.2; // brief pause before next word
        }}
      }});
    }});
  }}

  function groupLines(ws) {{
    var r = [], i = 0;
    for (; i < ws.length; i += WLINE) r.push(ws.slice(i, i + WLINE));
    return r;
  }}

  function ensureScenes() {{
    var root = document.getElementById("root");
    if (!root) return;
    for (var i = 0; i < starts.length; i++) {{
      var n = i + 1;
      if (document.getElementById("scene" + n)) continue;
      var ph = document.createElement("div");
      ph.id = "scene" + n;
      ph.className = "scene scene-fallback centered";
      ph.style.cssText = "position:absolute;inset:0;opacity:0;visibility:hidden;background:linear-gradient(135deg,var(--bg,#08080f),var(--bg2,#0f0f1a));";
      var audio = document.querySelector("audio#v" + n);
      var title = audio ? (audio.getAttribute("data-title") || "") : "";
      var narration = narrations[i] || "";
      var sceneNumPadded = (n < 10 ? "0" + n : "" + n);
      var emojis = ["✨", "⚡", "🚀", "💫", "🎯", "🔥", "💎", "🌟"];
      var emoji = emojis[(n - 1) % emojis.length];
      ph.innerHTML =
        '<div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>' +
        '<div class="corner-bracket bl"></div><div class="corner-bracket br"></div>' +
        '<div class="top-line"></div>' +
        '<span class="scene-num">' + sceneNumPadded + '</span>' +
        '<div class="layout" style="padding:100px 140px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:36px;">' +
          '<div id="s' + n + '-badge" class="badge" style="margin:0 auto;">' + emoji + ' &nbsp; PHẦN ' + n + '</div>' +
          '<h1 id="s' + n + '-title" class="title-xl grad-text" style="max-width:1400px;margin:0 auto;">' + (title || ("Nội dung phân cảnh " + n)) + '</h1>' +
          (narration ? ('<p id="s' + n + '-desc" class="body-text" style="max-width:1000px;margin:0 auto;font-size:1.5rem;line-height:1.6;color:var(--text2,#a09db8);">' + narration.slice(0, 220) + (narration.length > 220 ? "…" : "") + '</p>') : '') +
          '<div style="display:flex;gap:16px;margin-top:20px;flex-wrap:wrap;justify-content:center;">' +
            '<div class="badge" style="background:var(--surface,#141420);">📺 &nbsp; ON AIR</div>' +
            '<div class="badge" style="background:var(--surface,#141420);">▶ &nbsp; SCENE ' + sceneNumPadded + '</div>' +
            '<div class="badge" style="background:var(--surface,#141420);">🎬 &nbsp; TECHBEAT</div>' +
          '</div>' +
        '</div>';
      root.appendChild(ph);
    }}
  }}

  // Chunk fallback: split text into uniform 6-word groups (natural reading pace).
  function chunkText(text) {{
    if (!text) return [];
    var maxWords = 6;
    var words = text.trim().split(/\\s+/).filter(Boolean);
    var chunks = [];
    for (var i = 0; i < words.length; i += maxWords) {{
      chunks.push(words.slice(i, i + maxWords).join(" "));
    }}
    return chunks;
  }}

  function ensureSubtitles() {{
    var root = document.getElementById("root");
    if (!root || document.getElementById("techbeat-subtitles")) return;
    var c = document.createElement("div");
    c.id = "techbeat-subtitles";
    c.className = "techbeat-subtitles";

    for (var i = 0; i < starts.length; i++) {{
      var n = i + 1;
      var ss = document.createElement("div");
      ss.id = "sub-scene" + n;
      ss.className = "sub-scene";
      ss.style.display = "none";

      var wd = wordData[i];
      if (wd && wd.length > 0) {{
        // ── Whisper word-level mode ──────────────────────────────────────
        var lines = groupLines(wd);
        for (var li = 0; li < lines.length; li++) {{
          var lineEl = document.createElement("div");
          lineEl.id = "sub-l" + n + "-" + li;
          lineEl.className = "sub-line";
          var lw = lines[li];
          for (var wi = 0; wi < lw.length; wi++) {{
            var sp = document.createElement("span");
            sp.id = "sub-w" + n + "-" + li + "-" + wi;
            sp.className = "sub-word";
            sp.textContent = lw[wi].word + (wi < lw.length - 1 ? " " : "");
            lineEl.appendChild(sp);
          }}
          ss.appendChild(lineEl);
        }}
      }} else {{
        // ── Chunk fallback ───────────────────────────────────────────────
        var chunks = chunkText(narrations[i] || "");
        chunks.forEach(function(chunk, ci) {{
          var ce = document.createElement("div");
          ce.id = "sub-" + n + "-" + ci;
          ce.className = "sub-chunk";
          ce.style.cssText = "display:none;opacity:0;";
          ce.innerText = chunk;
          ss.appendChild(ce);
        }});
      }}
      c.appendChild(ss);
    }}
    root.appendChild(c);
  }}

  function buildTimeline() {{
    if (!window.gsap) return;
    if (window.TextPlugin) gsap.registerPlugin(TextPlugin);
    ensureScenes();
    ensureSubtitles();

    // Bug5 fix: do NOT clearProps on ".scene *" — that forces opacity:1 on all children before
    // gsap.from() tweens run, making every block appear simultaneously.
    // Instead: explicitly preset children of non-first scenes to opacity:0 so from() has a valid start state.
    // Store natural opacities before presetting them to 0
    function getNaturalOpacity(target) {{
      if (target.classList.contains("ghost-text")) return 0.085;
      if (target.classList.contains("aurora-glow") || target.classList.contains("glow-orb")) return 0.48;
      if (target.classList.contains("animated-grid")) return 0.55;
      if (target.classList.contains("retro-grid")) return 0.45;
      if (target.classList.contains("light-rays")) return 0.35;
      if (target.classList.contains("particle-field")) return 0.5;
      if (target.classList.contains("float-orb-lg")) return 0.48;
      if (target.classList.contains("float-orb-md")) return 0.38;
      if (target.classList.contains("float-orb-sm")) return 0.32;
      
      var computed = window.getComputedStyle(target).opacity;
      if (computed && computed !== "1" && computed !== "0") {{
        return parseFloat(computed);
      }}
      return 1;
    }}

    gsap.utils.toArray(".scene").forEach(function(el) {{
      var ambientSelectors = [
        ".aurora-glow", ".animated-grid", ".retro-grid", ".light-rays",
        ".particle-field", ".ghost-text", ".float-orb-lg", ".float-orb-md",
        ".float-orb-sm", ".y2k-sparkle", ".glow-orb", ".marquee-strip"
      ];
      ambientSelectors.forEach(function(sel) {{
        el.querySelectorAll(sel).forEach(function(target) {{
          target._naturalOpacity = getNaturalOpacity(target);
        }});
      }});
    }});

    gsap.utils.toArray(".scene").forEach(function(el, idx) {{
      if (idx === 0) {{
        gsap.set(el, {{ opacity: 1, visibility: "visible", position: "absolute", inset: 0 }});
      }} else {{
        gsap.set(el, {{ opacity: 0, visibility: "hidden", position: "absolute", inset: 0 }});
      }}
      // Preset animatable children to opacity:0 for ALL scenes to prevent FOUC and ensure deterministic animation
      gsap.set(el.querySelectorAll("[id$='-badge'],[id$='-title'],[id$='-subtitle'],[id$='-desc']"), {{ opacity: 0 }});
      var presetEls = [];
      el.querySelectorAll(".bento-cell, .feat-card, .stat-list-card, .chat-bubble, .tl-item, .agent-card, .tech-card, .compare .col, .visual-block, .step-item, .formula-pill, .command-pill, .glass-card, .visual-col > *:not(.bento-grid):not(.bento-3x2):not(.feat-row):not(.stat-list):not(.agent-grid):not(.compare):not(.chat-box):not(.tl-list):not(.tech-card):not(.feat-card):not(.stat-list-card):not(.chat-bubble):not(.tl-item):not(.agent-card):not(.step-list):not(.formula-stack)").forEach(function(item) {{
        if (item.classList.contains("visual-block")) {{
          var hasSubBlocks = item.querySelector(".bento-cell, .feat-card, .stat-list-card, .chat-bubble, .tl-item, .agent-card, .tech-card, .compare .col, .step-item, .formula-pill, .command-pill, .glass-card");
          if (hasSubBlocks) return;
        }}
        presetEls.push(item);
      }});
      gsap.set(presetEls, {{ opacity: 0 }});
      
      // Preset ambient elements to opacity:0 so they fade in cleanly and deterministically
      gsap.set(el.querySelectorAll(".aurora-glow, .animated-grid, .retro-grid, .light-rays, .particle-field, .ghost-text, .float-orb-lg, .float-orb-md, .float-orb-sm, .y2k-sparkle, .glow-orb, .marquee-strip"), {{ opacity: 0 }});
    }});

    var tl = gsap.timeline({{ paused: true }});
    var lastIdx = starts.length - 1;

    function safeFromTo(sel, fromVars, toVars, at) {{
      if (document.querySelector(sel)) {{
        toVars.immediateRender = false;
        tl.fromTo(sel, fromVars, toVars, at);
      }}
    }}

    for (var i = 0; i < starts.length; i++) {{
      var n = i + 1;
      var s = starts[i];
      var d = durs[i];
      var sceneId = "#scene" + n;
      if (!document.querySelector(sceneId)) continue;
      var isLast = (i === lastIdx);

      // 1. Gather all subtitle times (chunk starts) for the current scene to sync visual block entrances
      var subtitleTimes = [];
      var scWd = wordData[i];
      if (scWd && scWd.length > 0) {{
        var lines = groupLines(scWd);
        for (var li = 0; li < lines.length; li++) {{
          subtitleTimes.push(s + lines[li][0].start);
        }}
      }} else {{
        var chunks = chunkText(narrations[i] || "");
        if (chunks.length > 0) {{
          var totalAudioTime = actualDurs[i] || d;
          var AUDIO_LEAD = 0.15;
          var speechDur = (totalAudioTime - AUDIO_LEAD) * 0.93;
          var chunkLens = [], totalLen = 0;
          chunks.forEach(function(c) {{
            var l = c.length || 1;
            chunkLens.push(l); totalLen += l;
          }});
          var elapsed = 0;
          chunks.forEach(function(c, ci) {{
            var chunkStart = s + AUDIO_LEAD + elapsed;
            subtitleTimes.push(chunkStart);
            var chunkDur_c = (chunkLens[ci] / totalLen) * speechDur;
            elapsed += chunkDur_c;
          }});
        }}
      }}

      if (i === 0) {{
        tl.set(sceneId, {{ opacity: 1, visibility: "visible" }}, s);
      }} else {{
        tl.set(sceneId, {{ opacity: 0, visibility: "visible" }}, s);
        tl.to(sceneId,  {{ opacity: 1, duration: 0.6, ease: "power3.out" }}, s);
      }}

      // Compile declarative typewriter & word rotation effects
      compileTextEffects(sceneId, s, tl);

      // ── SUBTITLE TIMING ────────────────────────────────────────────────
      var subSceneEl = document.getElementById("sub-scene" + n);
      if (subSceneEl) {{
        tl.set("#sub-scene" + n, {{ display: "block", opacity: 1 }}, s);
        var scWd = wordData[i];

        if (scWd && scWd.length > 0) {{
          // ── Whisper word-level timing ──────────────────────────────────
          var lines = groupLines(scWd);
          for (var li = 0; li < lines.length; li++) {{
            var lw       = lines[li];
            var lineId   = "#sub-l" + n + "-" + li;
            var lStart   = s + lw[0].start;

            tl.set(lineId, {{ display: "block", opacity: 0 }}, lStart);
            tl.to(lineId,  {{ opacity: 1, duration: 0.15, ease: "power2.out" }}, lStart);

            // Fade out previous line as new one appears
            if (li > 0) {{
              var pId = "#sub-l" + n + "-" + (li - 1);
              tl.to(pId,  {{ opacity: 0, duration: 0.1 }}, lStart);
              tl.set(pId, {{ display: "none" }}, lStart + 0.1);
            }}

            // Word-level karaoke highlight — RED (use literal hex; GSAP cannot
            // resolve CSS variables during headless HyperFrames rendering)
            for (var wi = 0; wi < lw.length; wi++) {{
              var w   = lw[wi];
              var wId = "#sub-w" + n + "-" + li + "-" + wi;
              // Active word: bright RED + scale + glow
              tl.set(wId, {{
                color: "#ff2d2d",
                fontWeight: "900",
                scale: 1.15,
                textShadow: "0 0 24px rgba(255,45,45,1), 0 0 10px rgba(255,45,45,0.95), 0 2px 4px rgba(0,0,0,0.9)"
              }}, s + w.start);
              // Spoken word: return to white but slightly dim
              tl.set(wId, {{
                color: "rgba(255,255,255,0.85)",
                fontWeight: "600",
                scale: 1,
                textShadow: "0 1px 4px rgba(0,0,0,0.85)"
              }}, s + w.end);
            }}
          }}
          // Fade out subtitle block at scene end
          tl.to("#sub-scene" + n,  {{ opacity: 0, duration: 0.3 }}, s + d - 0.3);
          tl.set("#sub-scene" + n, {{ display: "none", opacity: 1 }}, s + d);

        }} else {{
          // ── Chunk fallback timing ──────────────────────────────────────
          var chunkEls  = subSceneEl.querySelectorAll(".sub-chunk");
          var numChunks = chunkEls.length;
          if (numChunks > 0) {{
            var totalAudioTime = actualDurs[i] || d;
            // AUDIO_LEAD: TTS engines (ElevenLabs/gTTS) start speaking after a
            // brief silence (~0.15 s). Without this offset the subtitle would
            // appear before the voice, making it feel "ahead" of the audio.
            var AUDIO_LEAD = 0.15;
            var speechDur  = (totalAudioTime - AUDIO_LEAD) * 0.93;
            // Proportional timing: chunks with more characters get more screen time.
            var chunkLens = [], totalLen = 0;
            chunkEls.forEach(function(el) {{
              var l = (el.textContent || "").length || 1;
              chunkLens.push(l); totalLen += l;
            }});
            var fadeIn = 0.15, fadeOut = 0.15, elapsed = 0;
            chunkEls.forEach(function(chunkEl, ci) {{
              var chunkDur_c = (chunkLens[ci] / totalLen) * speechDur;
              var chunkStart = s + AUDIO_LEAD + elapsed;
              var chunkEnd   = chunkStart + chunkDur_c;
              tl.set(chunkEl, {{ display: "block", opacity: 0 }}, chunkStart);
              tl.to(chunkEl,  {{ opacity: 1, duration: fadeIn, ease: "power2.out" }}, chunkStart);
              if (ci < numChunks - 1) {{
                tl.to(chunkEl,  {{ opacity: 0, duration: fadeOut, ease: "power2.in" }}, chunkEnd - fadeOut);
                tl.set(chunkEl, {{ display: "none" }}, chunkEnd);
              }}
              elapsed += chunkDur_c;
            }});
            tl.to("#sub-scene" + n,  {{ opacity: 0, duration: 0.3 }}, s + d - 0.3);
            tl.set("#sub-scene" + n, {{ display: "none" }},           s + d);
            tl.set("#sub-scene" + n, {{ opacity: 1 }},                s + d + 0.001);
          }}
        }}
      }}

      // Ambient decoratives fade in IMMEDIATELY at scene start so the
      // background never feels empty (orbs, aurora, grid, ghost-text...)
      var ambientSelectors = [
        ".aurora-glow", ".animated-grid", ".retro-grid", ".light-rays",
        ".particle-field", ".ghost-text", ".float-orb-lg", ".float-orb-md",
        ".float-orb-sm", ".y2k-sparkle", ".glow-orb", ".marquee-strip"
      ];
      ambientSelectors.forEach(function(sel) {{
        if (document.querySelector(sceneId + " " + sel)) {{
          tl.fromTo(sceneId + " " + sel,
            {{ scale: 0.7, opacity: 0 }},
            {{ 
              scale: 1, 
              opacity: function(i, target) {{ return target._naturalOpacity || 1; }}, 
              duration: 0.7, 
              stagger: 0.06, 
              ease: "power2.out", 
              immediateRender: false 
            }},
            s);
        }}
      }});

      // Decorative chrome (corner brackets + top-line + scene-num) entrance
      var chromeClasses = [".corner-bracket", ".top-line", ".scene-num"];
      var existingChrome = [];
      chromeClasses.forEach(function(sel) {{
        var fullSel = sceneId + " " + sel;
        if (document.querySelector(fullSel)) {{
          existingChrome.push(fullSel);
        }}
      }});
      if (existingChrome.length > 0) {{
        tl.fromTo(existingChrome.join(", "),
          {{ opacity: 0 }},
          {{ opacity: 1, duration: 0.4, stagger: 0.05, ease: "power1.out", immediateRender: false }}, s);
      }}

      // Content entry — start IMMEDIATELY at t=s, tight stagger so the first
      // 0.5s is filled with motion instead of an empty stationary frame.
      safeFromTo(sceneId + " [id$='-badge']",    {{ y: -20, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.5, ease: "back.out(1.7)" }}, s);
      safeFromTo(sceneId + " [id$='-title']",    {{ y: 40,  opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.7, ease: "power4.out"   }}, s + 0.12);
      safeFromTo(sceneId + " [id$='-subtitle']", {{ y: 30,  opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.6, ease: "power3.out"   }}, s + 0.25);
      safeFromTo(sceneId + " [id$='-desc']",     {{ y: 20,  opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.5, ease: "power2.out"   }}, s + 0.38);
      var containerExclude = ":not(.bento-grid):not(.bento-3x2):not(.feat-row):not(.stat-list):not(.agent-grid):not(.compare):not(.chat-box):not(.tl-list):not(.tech-card):not(.feat-card):not(.stat-list-card):not(.chat-bubble):not(.tl-item):not(.agent-card):not(.step-list):not(.formula-stack)";
      if (document.querySelector(sceneId + " .visual-col > *" + containerExclude)) {{
        tl.fromTo(sceneId + " .visual-col > *" + containerExclude,
          {{ scale: 0.88, opacity: 0 }},
          {{ scale: 1, opacity: 1, duration: 0.7, stagger: 0.12, ease: "back.out(1.6)", immediateRender: false }},
          s + 0.18);
      }}

      var blockSelectors = [
        ".bento-cell", ".feat-card", ".stat-list-card", ".chat-bubble",
        ".tl-item", ".agent-card", ".tech-card", ".compare .col", ".visual-block",
        ".step-item", ".formula-pill", ".command-pill", ".glass-card",
        ".visual-col > *:not(.stat-list):not(.feat-row):not(.bento-grid):not(.bento-3x2):not(.agent-grid):not(.compare):not(.step-list):not(.formula-stack)"
      ];
      var blocks = [];
      blockSelectors.forEach(function(sel) {{
        var els = document.querySelectorAll(sceneId + " " + sel);
        els.forEach(function(el) {{
          if (blocks.indexOf(el) === -1) {{
            if (el.classList.contains("visual-block")) {{
              var hasSubBlocks = el.querySelector(".bento-cell, .feat-card, .stat-list-card, .chat-bubble, .tl-item, .agent-card, .tech-card, .compare .col, .step-item, .formula-pill, .command-pill, .glass-card");
              if (hasSubBlocks) return;
            }}
            blocks.push(el);
          }}
        }});
      }});

      // 3. Animate each block at its corresponding subtitle start timestamp!
      if (blocks.length > 0) {{
        blocks.forEach(function(blockEl, bi) {{
          var blockStart;
          if (subtitleTimes.length > 0) {{
            // Map block index to subtitle time index proportionally
            var subIdx = Math.floor((bi / blocks.length) * subtitleTimes.length);
            blockStart = subtitleTimes[subIdx];
          }} else {{
            // Fallback stagger if no subtitles exist
            blockStart = s + 0.2 + (bi * 0.45);
          }}
          
          // Animate the block dynamically at the exact timestamp!
          tl.fromTo(blockEl,
            {{ y: 28, opacity: 0 }},
            {{ y: 0, opacity: 1, duration: 0.65, ease: "back.out(1.4)", immediateRender: false }},
            blockStart);
        }});
      }}

      // Last scene stays visible until total — visuals never go black before audio ends.
      if (!isLast) {{
        tl.to(sceneId,  {{ opacity: 0, duration: 0.5, ease: "power2.in" }}, s + d - 0.6);
        tl.set(sceneId, {{ visibility: "hidden" }}, s + d);
      }}
    }}

    // Park timeline at t=0 so any pre-seek frame capture matches the
    // intended initial state instead of post-set hidden state.
    tl.progress(0).pause();

    // Register the timeline dynamically under the exact data-composition-id
    // of the root element (fallback to "main"). Avoid extra keys to prevent timeline_id_mismatch.
    window.__timelines = window.__timelines || {{}};
    var rootEl = document.getElementById("root");
    var compId = rootEl ? (rootEl.getAttribute("data-composition-id") || "main") : "main";
    
    console.log("[buildTimeline] Registering timeline under keys: " + compId + ", main");
    window.__timelines[compId] = tl;
    window.__timelines["main"] = tl;
    console.log("[buildTimeline] Timeline registered successfully!");
  }}

  function initTimeline() {{
    var root = document.getElementById("root");
    console.log("[buildTimeline] initTimeline. root element exists: " + (!!root) + ", readyState: " + document.readyState);
    if (!root) {{
      console.log("[buildTimeline] root element not found, waiting for DOMContentLoaded");
      document.addEventListener("DOMContentLoaded", buildTimeline);
    }} else {{
      buildTimeline();
    }}
  }}

  initTimeline();
}})();
</script>
"""

    # Insert before </body>
    if "</body>" in html:
        html = html.replace("</body>", inject + "</body>")
    else:
        html += inject

    return html


# -------- Render via npx hyperframes render --------

async def run_render(project_root: Path, on_log) -> Path:
    """Spawn `npx hyperframes render` in a thread (avoids asyncio subprocess
    on Windows, which fails on uvicorn's selector loop)."""
    import subprocess
    import threading

    log_queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _runner() -> int:
        if os.name == "nt":
            cmd = ["npx.cmd", "--yes", "hyperframes@0.6.20", "render"]
            kwargs = {"shell": False}
        else:
            cmd = ["npx", "--yes", "hyperframes@0.6.20", "render"]
            kwargs = {}

        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
            encoding="utf-8",
            errors="replace",
            **kwargs,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                asyncio.run_coroutine_threadsafe(log_queue.put(line), loop)
        rc = proc.wait()
        asyncio.run_coroutine_threadsafe(log_queue.put(None), loop)
        return rc

    runner_future = loop.run_in_executor(None, _runner)

    while True:
        item = await log_queue.get()
        if item is None:
            break
        await on_log(item)

    rc = await runner_future
    if rc != 0:
        raise RuntimeError(f"Render failed with exit code {rc}")

    renders_dir = project_root / "renders"
    if not renders_dir.exists():
        raise RuntimeError("Thư mục renders không tồn tại sau khi render")

    mp4s = sorted(renders_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp4s:
        raise RuntimeError("Không tìm thấy file mp4 sau khi render")
    return mp4s[0]


# -------- Orchestrator --------

class BuildRequest(BaseModel):
    title: str
    scenes: list[ScenePayload]
    totalDuration: int
    projectPath: str | None = None
    skipTts: bool = False
    theme: str | None = None
    voiceId: str | None = None
    # Pre-built composition HTML from the html-preview stage. When present,
    # we skip the LLM composition stage entirely and go straight to save.
    compositionHtml: str | None = None
    # Subtitle toggle — when False, inject CSS to hide .techbeat-subtitles in rendered video
    subtitlesEnabled: bool = True


async def build_pipeline(req: BuildRequest):
    """Yield SSE events for the full pipeline."""

    project_root = get_project_root(req.projectPath)
    if not project_root.exists():
        yield sse({"type": "error", "message": f"Project path không tồn tại: {project_root}"})
        return

    assets_dir = project_root / "assets"
    assets_dir.mkdir(exist_ok=True)

    # ---- Stage 0: Download / decode chosen illustration images ----
    # imageUrl can be:
    #   • https://… (CDN) — fetch via httpx
    #   • data:image/...;base64,…  (user upload via ImagePicker) — base64-decode
    #   • blob:…  (browser-only URL) — unusable, skip
    import base64 as _b64
    import re as _re

    scenes_with_assets: list[ScenePayload] = []
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as http:
        for s in req.scenes:
            asset_rel: str | None = None
            url = s.imageUrl or ""

            # ── Case 1: data: URL — decode locally ──────────────────────
            if url.startswith("data:image/"):
                m = _re.match(r"^data:image/([a-z0-9+.-]+);base64,(.+)$", url, _re.IGNORECASE)
                if m:
                    ext_raw = m.group(1).lower()
                    ext = {"jpeg": "jpg", "svg+xml": "svg"}.get(ext_raw, ext_raw)
                    if ext not in ("jpg", "png", "webp", "gif", "svg"):
                        ext = "jpg"
                    try:
                        raw = _b64.b64decode(m.group(2))
                        local = assets_dir / f"scene{s.index + 1}.{ext}"
                        local.write_bytes(raw)
                        asset_rel = f"assets/{local.name}"
                        print(f"[build] Lưu ảnh upload scene {s.index + 1} → {asset_rel}")
                    except Exception as e:
                        print(f"[build] Decode data URL scene {s.index + 1} lỗi: {e}")

            # ── Case 2: http(s) URL — fetch via httpx ────────────────────
            elif url.startswith(("http://", "https://")):
                ext = ".jpg"
                low = url.lower().split("?")[0]
                for cand in (".png", ".webp", ".jpeg", ".jpg", ".gif"):
                    if low.endswith(cand):
                        ext = ".jpg" if cand == ".jpeg" else cand
                        break
                local = assets_dir / f"scene{s.index + 1}{ext}"
                try:
                    resp = await http.get(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0",
                            "Referer": "https://duckduckgo.com/",
                        },
                    )
                    if resp.status_code == 200 and resp.content:
                        local.write_bytes(resp.content)
                        asset_rel = f"assets/{local.name}"
                except Exception as e:
                    print(f"[build] Tải ảnh scene {s.index + 1} lỗi: {e}")

            # ── Case 3: blob: or other — skip silently ───────────────────
            scenes_with_assets.append(s.model_copy(update={"imageAsset": asset_rel}))

    # ── Build log: collect info about every tool/model used ──────────────
    build_log: list[str] = []

    # ---- Stage 1: Composition ----
    # If the html-preview stage already produced an HTML, skip the LLM call
    # entirely and reuse it. Saves the composition cost AND lets the user
    # see the exact same visual they previewed.
    if req.compositionHtml and "<html" in req.compositionHtml.lower():
        yield sse({"type": "stage", "stage": "composition", "status": "start", "message": "Sử dụng HTML từ bước xem trước..."})
        html = req.compositionHtml
        build_log.append("🎨 HTML: cache (từ bước xem trước — không gọi LLM)")
        yield sse({"type": "stage", "stage": "composition", "status": "done", "message": "Bỏ qua sinh HTML — dùng cache"})
    else:
        yield sse({"type": "stage", "stage": "composition", "status": "start", "message": "Đang sinh composition HTML..."})

        comp_req = CompositionRequest(
            title=req.title,
            scenes=scenes_with_assets,
            totalDuration=req.totalDuration,
            theme=req.theme,
        )
        html = ""
        char_count = 0
        async for ev in stream_composition_events(comp_req):
            if ev["type"] == "chunk":
                char_count += len(ev["text"])
                # Forward the actual text chunk so frontend can show LLM stream live
                yield sse({"type": "comp_chunk", "text": ev["text"]})
                if char_count % 500 < 50:
                    yield sse({"type": "stage", "stage": "composition", "status": "progress", "chars": char_count})
            elif ev["type"] == "model_info":
                # Capture which LLM generated the HTML
                build_log.append(f"🎨 HTML: {ev['provider']} / {ev['model']}")
                yield sse({"type": "stage", "stage": "composition", "status": "progress",
                           "message": f"LLM: {ev['provider']} ({ev['model']})"})
            elif ev["type"] == "done":
                html = ev["html"]
            elif ev["type"] == "error":
                yield sse({"type": "error", "stage": "composition", "message": ev["message"]})
                return

    if not html:
        yield sse({"type": "error", "stage": "composition", "message": "Không nhận được HTML"})
        return

    # ---- Stage 2: Save ----
    yield sse({"type": "stage", "stage": "save", "status": "start", "message": "Đang lưu index.html..."})
    target_html = project_root / "index.html"
    target_html.write_text(html, encoding="utf-8")
    yield sse({"type": "stage", "stage": "save", "status": "done", "path": str(target_html)})

    # ---- Stage 3: TTS ----
    if not req.skipTts:
        # Reset ElevenLabs state so a previous build's quota error doesn't
        # carry over and skip ElevenLabs unnecessarily this run.
        reset_elevenlabs_state()
        engines_used: dict[str, int] = {}
        yield sse({"type": "stage", "stage": "tts", "status": "start", "message": f"Đang sinh giọng đọc cho {len(req.scenes)} scene..."})
        wav_paths: list[Path] = []
        for s in req.scenes:
            wav_path = assets_dir / f"p{s.index + 1}.wav"
            wav_paths.append(wav_path)
            yield sse({"type": "stage", "stage": "tts", "status": "progress", "scene": s.index + 1, "of": len(req.scenes)})
            try:
                engine = await synthesize_tts(s.narration, wav_path, voice_id=req.voiceId)
                engines_used[engine] = engines_used.get(engine, 0) + 1
            except Exception as e:
                yield sse({"type": "error", "stage": "tts", "message": f"TTS scene {s.index + 1}: {e}"})
                return

        engine_summary = ", ".join(f"{k}×{v}" for k, v in engines_used.items())
        build_log.append(f"🎙 TTS: {engine_summary}")
        print(f"[tts] engines: {engine_summary}")

        # Measure actual audio durations
        durations = [get_audio_duration_s(p) for p in wav_paths]
        measured = [f"p{i+1}.wav={d:.1f}s" for i, d in enumerate(durations)]
        print(f"[tts] Measured durations: {', '.join(measured)}")

        # ── Whisper word-level transcription ────────────────────────────
        yield sse({"type": "stage", "stage": "whisper", "status": "start",
                   "message": f"Đang nhận dạng giọng nói cho {len(wav_paths)} scene..."})
        word_data: list[list[dict]] = []
        whisper_engines_used: dict[str, int] = {}
        for idx, p in enumerate(wav_paths):
            yield sse({"type": "stage", "stage": "whisper", "status": "progress",
                       "scene": idx + 1, "of": len(wav_paths)})
            words, w_engine = await transcribe_audio_whisper(p)
            
            # Keep original script text (case & punctuation), align using Whisper timestamps
            aligned_words = align_script_with_whisper(req.scenes[idx].narration, words, durations[idx])
            word_data.append(aligned_words)
            whisper_engines_used[w_engine] = whisper_engines_used.get(w_engine, 0) + 1
        whisper_ok = sum(1 for w in word_data if w)
        whisper_engine_summary = ", ".join(f"{k}×{v}" for k, v in whisper_engines_used.items())
        build_log.append(f"🎤 Whisper: {whisper_engine_summary} ({whisper_ok}/{len(wav_paths)} scene có timestamp)")
        yield sse({"type": "stage", "stage": "whisper", "status": "done",
                   "engine": whisper_engine_summary,
                   "message": f"Hoàn tất: {whisper_engine_summary}"
                               + (" — chunk fallback cho scene còn lại" if whisper_ok < len(wav_paths) else "")})

        scene_titles = [s.title for s in req.scenes]
        scene_narrations = [s.narration for s in req.scenes]
        html = patch_html_timing(html, durations, scene_titles, scene_narrations, word_data)
        # ── Subtitle toggle: hide .techbeat-subtitles if user disabled them ─
        if not req.subtitlesEnabled:
            hide_css = '<style id="tb-subtitle-hide">.techbeat-subtitles{display:none!important}</style>'
            html = html.replace("</head>", hide_css + "</head>", 1)
        target_html.write_text(html, encoding="utf-8")
        # Total composition duration after timing patch (ceil(d) + 1 buffer per scene)
        import math as _math
        actual_total = sum(max(1, _math.ceil(d) + 1) for d in durations)
        yield sse({
            "type": "stage", "stage": "tts", "status": "done",
            "engine": engine_summary,
            "actualDuration": actual_total,
            "audioDurations": [round(d, 1) for d in durations],
        })
    else:
        # skipTts path — still apply subtitle toggle to already-saved index.html
        if not req.subtitlesEnabled:
            existing_html = target_html.read_text(encoding="utf-8")
            hide_css = '<style id="tb-subtitle-hide">.techbeat-subtitles{display:none!important}</style>'
            if 'id="tb-subtitle-hide"' not in existing_html:
                existing_html = existing_html.replace("</head>", hide_css + "</head>", 1)
                target_html.write_text(existing_html, encoding="utf-8")
        yield sse({"type": "stage", "stage": "tts", "status": "skipped"})

    # ---- Stage 4: Render ----
    yield sse({"type": "stage", "stage": "render", "status": "start", "message": "Đang render MP4..."})

    log_buffer: list[str] = []
    log_queue: asyncio.Queue[str] = asyncio.Queue()

    async def on_log(line: str):
        log_buffer.append(line)
        print(f"[render] {line}")
        await log_queue.put(line)

    render_task = asyncio.create_task(run_render(project_root, on_log))

    try:
        while not render_task.done() or not log_queue.empty():
            try:
                line = await asyncio.wait_for(log_queue.get(), timeout=1.5)
                yield sse({"type": "stage", "stage": "render", "status": "log", "line": line})
            except asyncio.TimeoutError:
                if render_task.done():
                    break
                continue
        mp4_path = await render_task
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[render ERROR] {tb}")
        yield sse({
            "type": "error",
            "stage": "render",
            "message": f"{type(e).__name__}: {e}",
            "log": "\n".join(log_buffer[-30:]) + "\n--- traceback ---\n" + tb,
        })
        return

    rel_url = f"/renders/{mp4_path.name}"

    # Save to history automatically
    try:
        import datetime
        import shutil

        # 1. Ensure history directory structures
        history_dir = project_root / "history"
        htmls_dir = history_dir / "htmls"
        videos_dir = history_dir / "videos"
        history_dir.mkdir(exist_ok=True)
        htmls_dir.mkdir(exist_ok=True)
        videos_dir.mkdir(exist_ok=True)

        # 2. Generate timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        hist_html_name = f"html_{timestamp}.html"
        hist_video_name = f"video_{timestamp}.mp4"

        # 3. Write HTML file copy
        (htmls_dir / hist_html_name).write_text(html, encoding="utf-8")

        # 4. Copy MP4 video file
        shutil.copy2(mp4_path, videos_dir / hist_video_name)

        # 5. Append to db.json
        db_path = history_dir / "db.json"
        history_list = []
        if db_path.exists():
            try:
                history_list = json.loads(db_path.read_text(encoding="utf-8"))
            except Exception:
                history_list = []

        new_entry = {
            "id": timestamp,
            "title": req.title,
            "html_url": f"/static-history/htmls/{hist_html_name}",
            "video_url": f"/static-history/videos/{hist_video_name}",
            "duration": actual_total if ('actual_total' in locals() and actual_total) else req.totalDuration,
            "created_at": datetime.datetime.now().isoformat()
        }
        history_list.insert(0, new_entry) # newest first
        db_path.write_text(json.dumps(history_list, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[history] Saved snapshot {timestamp} successfully!")
    except Exception as he:
        print(f"[history ERROR] Failed to save history snapshot: {he}")

    # ── Print build summary to backend console ──────────────────────────
    print("\n" + "=" * 55)
    print(f"[BUILD SUMMARY] {req.title}")
    for line in build_log:
        print(f"  {line}")
    print("=" * 55 + "\n")

    yield sse({
        "type": "done",
        "videoUrl": rel_url,
        "videoPath": str(mp4_path),
        "html": html,
        "buildLog": build_log,
    })


@router.post("/build-video")
async def build_video(body: BuildRequest):
    return StreamingResponse(
        build_pipeline(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
