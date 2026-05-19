from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from extractors.url import extract_from_url
from extractors.pdf import extract_from_pdf
from extractors.office import extract_from_docx, extract_from_pptx

router = APIRouter()

SUPPORTED_EXTENSIONS = {
    "pdf": extract_from_pdf,
    "docx": extract_from_docx,
    "pptx": extract_from_pptx,
}


class UrlRequest(BaseModel):
    url: str


@router.post("/extract/url")
async def extract_url(body: UrlRequest):
    try:
        result = await extract_from_url(body.url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract/file")
async def extract_file(file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    data = await file.read()

    try:
        extractor = SUPPORTED_EXTENSIONS[ext]
        result = extractor(data, filename)
        if hasattr(result, "__await__"):
            result = await result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
