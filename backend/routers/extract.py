from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
import logging
import traceback

from extractors.url import extract_from_url
from extractors.pdf import extract_from_pdf
from extractors.office import extract_from_docx, extract_from_pptx
from extractors.text import extract_from_text

logger = logging.getLogger(__name__)

router = APIRouter()

SUPPORTED_EXTENSIONS = {
    "pdf": extract_from_pdf,
    "docx": extract_from_docx,
    "pptx": extract_from_pptx,
    "md": extract_from_text,
    "txt": extract_from_text,
}


class UrlRequest(BaseModel):
    url: str


@router.post("/extract/url")
async def extract_url(body: UrlRequest):
    logger.info("[extract/url] url=%s", body.url)
    try:
        result = await extract_from_url(body.url)
        logger.info("[extract/url] OK title=%r text_len=%d", result.get("title"), len(result.get("text", "")))
        return result
    except ValueError as e:
        logger.warning("[extract/url] ValueError: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("[extract/url] Exception: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract/file")
async def extract_file(file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    logger.info("[extract/file] filename=%s ext=%s", filename, ext)

    if ext not in SUPPORTED_EXTENSIONS:
        logger.warning("[extract/file] unsupported ext=%s", ext)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    data = await file.read()
    logger.info("[extract/file] read %d bytes", len(data))

    try:
        extractor = SUPPORTED_EXTENSIONS[ext]
        raw = extractor(data, filename)
        import inspect
        result = await raw if inspect.isawaitable(raw) else raw
        logger.info("[extract/file] OK title=%r", result.get("title") if isinstance(result, dict) else "?")
        return result
    except Exception as e:
        logger.error("[extract/file] Exception: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

