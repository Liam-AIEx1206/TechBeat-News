import io
import re

from pypdf import PdfReader

from extractors.ocr import ocr_pdf


async def extract_from_pdf(data: bytes, filename: str) -> dict:
    title = re.sub(r"\.[^.]+$", "", filename).replace("-", " ").replace("_", " ").strip()

    text = ""
    used = "ocr"

    try:
        text = (await ocr_pdf(data)).strip()
    except Exception as e:
        print(f"[extract pdf] OCR failed, falling back to pypdf: {e}")
        text = ""

    if len(text) < 30:
        # OCR returned almost nothing — fall back to pypdf text extraction.
        try:
            reader = PdfReader(io.BytesIO(data))
            pages_text = [page.extract_text() or "" for page in reader.pages]
            fallback = "\n".join(pages_text).strip()
            if fallback:
                text = fallback
                used = "pypdf"
        except Exception as e:
            print(f"[extract pdf] pypdf fallback failed: {e}")

    print(f"[PDF] '{filename}' — {len(text)} ký tự ({used})")
    return {
        "title": title,
        "text": text,  # không giới hạn — gửi full để LLM có đủ nội dung
        "source": filename,
        "extractor": used,
    }
