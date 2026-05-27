import re

def extract_from_text(data: bytes, filename: str) -> dict:
    """Extract text content from raw markdown or plain text files.
    
    Attempts to decode as UTF-8, falling back to UTF-16 and Latin-1.
    Derives title from the first Markdown heading (e.g. # Title) or the first text line.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("utf-16")
        except UnicodeDecodeError:
            text = data.decode("latin-1")

    # Default title from filename
    title = re.sub(r"\.[^.]+$", "", filename).replace("-", " ").replace("_", " ")

    # Try to extract title from markdown H1 headers or first text line
    for line in text.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        if line_clean.startswith("#"):
            # Strip leading hash symbols
            h_title = re.sub(r"^#+\s*", "", line_clean).strip()
            if h_title:
                title = h_title
                break
        else:
            # Use the first text line as title limit to 100 chars
            title = line_clean[:100]
            break

    print(f"[TEXT/MD] '{filename}' — {len(text)} characters")
    return {"title": title.strip(), "text": text, "source": filename}
