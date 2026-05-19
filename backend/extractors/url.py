import httpx
from bs4 import BeautifulSoup


async def extract_from_url(url: str) -> dict:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; VideoBot/1.0)"}

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
        tag.decompose()

    title = (
        soup.find("meta", property="og:title") and soup.find("meta", property="og:title").get("content")
        or (soup.find("title") and soup.find("title").get_text())
        or (soup.find("h1") and soup.find("h1").get_text())
        or "Untitled"
    )

    # Extract from main content areas
    for selector in ["main", "article", '[role="main"]', ".content", ".post", "body"]:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(separator=" ", strip=True)
            break
    else:
        text = soup.get_text(separator=" ", strip=True)

    return {
        "title": title.strip(),
        "text": text[:20000],
        "source": url,
    }
