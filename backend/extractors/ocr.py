"""OCR via vision-capable LLM (claude-sonnet-4-6 / qwen3-vl).

Used as the primary path for PDF — it understands layout, tables, headers, mixed
text/images. Falls back to plain pypdf when the vision call errors out.
"""
import base64
import os
from typing import List

from routers.llm import chat_completions_with_fallback


def get_ocr_model() -> str:
    return os.getenv("OPENAI_OCR_MODEL") or os.getenv("OPENAI_COMPOSITION_MODEL", "gpt-4o")


def render_pdf_pages_to_images(data: bytes, dpi: int = 144, max_pages: int | None = None) -> List[bytes]:
    """Rasterize PDF pages to PNG bytes (one entry per page, capped at max_pages)."""
    import fitz  # PyMuPDF — imported lazily so the server can start without it

    if max_pages is None:
        try:
            max_pages = int(os.getenv("MAX_OCR_PAGES", "100"))
        except ValueError:
            max_pages = 100

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
    """Send page images in batches, ask the model to transcribe them in reading order.
    Returns the concatenated markdown text. Runs OCR batches in parallel.
    """
    import asyncio

    try:
        batch_size = int(os.getenv("OCR_BATCH_SIZE", "5"))
    except ValueError:
        batch_size = 5

    batches = [images[i : i + batch_size] for i in range(0, len(images), batch_size)]
    
    async def ocr_batch(batch_images: List[bytes]) -> str:
        content: list[dict] = [{
            "type": "text",
            "text": (
                "Transcribe every page in reading order as Markdown. "
                "Preserve headings, lists, tables, and obvious paragraph breaks. "
                "Do not add commentary, do not summarize. Output only the transcribed text."
            ),
        }]
        for png in batch_images:
            b64 = base64.b64encode(png).decode("ascii")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })

        resp, _provider, _model = await chat_completions_with_fallback(
            model_kind="ocr",
            _primary_model=get_ocr_model(),
            messages=[{"role": "user", "content": content}],
            temperature=0.1,
            max_tokens=8000,
        )
        return resp.choices[0].message.content or ""

    # Run OCR on all batches in parallel
    tasks = [ocr_batch(batch) for batch in batches]
    results = await asyncio.gather(*tasks)
    
    return "\n\n<!-- PAGE BREAK -->\n\n".join(results)


async def ocr_pdf(data: bytes) -> str:
    images = render_pdf_pages_to_images(data)
    if not images:
        return ""
    return await ocr_image_bytes(images)


async def ocr_pptx_via_pdf(pptx_bytes: bytes) -> str:
    """LibreOffice/soffice → PDF → OCR. Only used when the user explicitly
    requests OCR for slides (the native python-pptx parser is usually fine)."""
    raise NotImplementedError("OCR for PPTX requires LibreOffice — use python-pptx native path")
