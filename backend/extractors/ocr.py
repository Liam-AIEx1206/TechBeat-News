"""OCR via vision-capable LLM (claude-sonnet-4-6 / qwen3-vl).

Used as the primary path for PDF — it understands layout, tables, headers, mixed
text/images. Falls back to plain pypdf when the vision call errors out.
"""
import base64
import os
from typing import List

from routers.llm import get_async_client


def get_ocr_model() -> str:
    return os.getenv("OPENAI_OCR_MODEL") or os.getenv("OPENAI_COMPOSITION_MODEL", "claude-sonnet-4-6")


def render_pdf_pages_to_images(data: bytes, dpi: int = 144, max_pages: int = 30) -> List[bytes]:
    """Rasterize PDF pages to PNG bytes (one entry per page, capped at max_pages)."""
    import fitz  # PyMuPDF — imported lazily so the server can start without it

    doc = fitz.open(stream=data, filetype="pdf")
    images: list[bytes] = []
    try:
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            images.append(pix.tobytes("png"))
    finally:
        doc.close()
    return images


async def ocr_image_bytes(images: List[bytes]) -> str:
    """Send all page images in one multimodal request, ask the model to
    transcribe them in reading order. Returns the concatenated markdown text.
    """
    client = get_async_client()

    content: list[dict] = [{
        "type": "text",
        "text": (
            "Transcribe every page in reading order as Markdown. "
            "Preserve headings, lists, tables, and obvious paragraph breaks. "
            "Do not add commentary, do not summarize. Output only the transcribed text."
        ),
    }]
    for png in images:
        b64 = base64.b64encode(png).decode("ascii")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })

    resp = await client.chat.completions.create(
        model=get_ocr_model(),
        messages=[{"role": "user", "content": content}],
        temperature=0.1,
        max_tokens=8000,
    )
    return resp.choices[0].message.content or ""


async def ocr_pdf(data: bytes) -> str:
    images = render_pdf_pages_to_images(data)
    if not images:
        return ""
    return await ocr_image_bytes(images)


async def ocr_pptx_via_pdf(pptx_bytes: bytes) -> str:
    """LibreOffice/soffice → PDF → OCR. Only used when the user explicitly
    requests OCR for slides (the native python-pptx parser is usually fine)."""
    raise NotImplementedError("OCR for PPTX requires LibreOffice — use python-pptx native path")
