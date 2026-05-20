import re
import httpx
import trafilatura
from bs4 import BeautifulSoup


# MSN article ID pattern: /ar-XXXXX...
MSN_ID_RE = re.compile(r"/ar-([A-Za-z0-9]+)")


async def _try_msn_api(url: str, client: httpx.AsyncClient) -> dict | None:
    """
    MSN articles are JS-rendered. Their detail API returns clean JSON.
    Endpoint pattern: https://assets.msn.com/content/view/v3/Detail/{locale}/{articleId}
    """
    if "msn.com" not in url:
        return None
    m = MSN_ID_RE.search(url)
    if not m:
        return None
    article_id = m.group(1)

    # Locale from URL: /vi-vn/, /en-us/, etc.
    loc_match = re.search(r"msn\.com/([a-z]{2}-[a-z]{2})/", url)
    locale = loc_match.group(1) if loc_match else "vi-vn"

    api_url = f"https://assets.msn.com/content/view/v3/Detail/{locale}/{article_id}"
    try:
        resp = await client.get(api_url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception:
        return None

    title = (data.get("title") or "").strip()
    body_html = data.get("body") or ""
    if not body_html:
        return None

    # Strip HTML — keep paragraph text
    soup = BeautifulSoup(body_html, "html.parser")
    paras = [p.get_text(" ", strip=True) for p in soup.find_all(["p", "h2", "h3"])]
    paras = [p for p in paras if len(p) > 30]
    text = "\n\n".join(paras) if paras else soup.get_text(" ", strip=True)

    # Try to find canonical / source URL (MSN re-publishes from real outlets)
    source_url = data.get("provider", {}).get("profileId") or data.get("absoluteUrl") or url

    return {"title": title or "Untitled", "text": text, "source": source_url}


async def extract_from_url(url: str) -> dict:
    """
    Extract clean article content from URL.
    Strategy:
      1. Special handlers for known JS-rendered sites (MSN)
      2. trafilatura (best for news articles)
      3. BeautifulSoup fallback
    Raises ValueError if no usable content can be found.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
    }

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        # ── Special handler: MSN ──
        msn_result = await _try_msn_api(url, client)
        if msn_result and len(msn_result["text"]) >= 200:
            return {**msn_result, "text": msn_result["text"][:20000]}

        response = await client.get(url, headers=headers)
        response.raise_for_status()
        raw_html = response.text

    title = ""
    text = ""

    # ── Primary: trafilatura ──
    try:
        extracted = trafilatura.extract(
            raw_html,
            url=url,
            favor_recall=False,
            include_comments=False,
            include_tables=True,
            include_images=False,
            deduplicate=True,
            with_metadata=False,
        )
        if extracted:
            text = extracted.strip()

        meta = trafilatura.extract_metadata(raw_html)
        if meta and meta.title:
            title = meta.title.strip()
    except Exception:
        pass

    # ── Fallback: BeautifulSoup ──
    if not text:
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                         "iframe", "noscript", "form", "button"]):
            tag.decompose()

        bad_patterns = ("ad-", "ads-", "advert", "banner", "promo", "popup",
                        "newsletter", "subscribe", "social", "share-", "related-",
                        "comments", "sidebar", "cookie")
        for el in soup.find_all(True, class_=True):
            cls = " ".join(el.get("class", [])).lower()
            if any(p in cls for p in bad_patterns):
                el.decompose()

        article = (
            soup.select_one("article")
            or soup.select_one("main")
            or soup.select_one('[role="main"]')
            or soup.select_one(".content, .post, .entry-content, .article-body")
            or soup.body
        )
        if article:
            paras = [p.get_text(" ", strip=True) for p in article.find_all("p")]
            paras = [p for p in paras if len(p) > 40]
            if paras:
                text = "\n\n".join(paras)
            else:
                text = article.get_text(" ", strip=True)

    if not title:
        soup = BeautifulSoup(raw_html, "html.parser")
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            title = og["content"].strip()
        elif soup.find("title"):
            title = soup.find("title").get_text(strip=True)
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)
        else:
            title = "Untitled"

    for sep in [" | ", " - ", " — ", " · "]:
        if sep in title and len(title.split(sep)[0]) > 20:
            title = title.split(sep)[0].strip()
            break

    text = (text or "").strip()

    # ── Validation: empty content means JS-rendered or paywall ──
    if len(text) < 200:
        if "msn.com" in url:
            raise ValueError(
                "MSN là trang aggregator dùng JavaScript render — không thể trích xuất "
                "trực tiếp. Hãy mở bài viết, tìm tên nguồn ở đầu (vd: 'Lao Động', 'VnExpress', "
                "'Báo Mới') và dán URL từ trang gốc đó."
            )
        raise ValueError(
            "Không trích xuất được nội dung từ URL này. "
            "Trang có thể yêu cầu JavaScript (SPA), bị paywall, hoặc chặn bot. "
            "Hãy thử dán URL bài gốc (ví dụ: laodong.vn, vnexpress.net) thay vì trang aggregator."
        )

    return {
        "title": title or "Untitled",
        "text": text[:20000],
        "source": url,
    }
