import re
import httpx
import trafilatura
from bs4 import BeautifulSoup


MSN_ID_RE = re.compile(r"/ar-([A-Za-z0-9]+)")
GITHUB_REPO_RE = re.compile(r"https?://github\.com/([^/]+)/([^/?#]+?)(?:\.git)?(?:[/?#].*)?$")


async def _try_msn_api(url: str, client: httpx.AsyncClient) -> dict | None:
    if "msn.com" not in url:
        return None
    m = MSN_ID_RE.search(url)
    if not m:
        return None
    article_id = m.group(1)

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

    soup = BeautifulSoup(body_html, "html.parser")
    paras = [p.get_text(" ", strip=True) for p in soup.find_all(["p", "h2", "h3"])]
    paras = [p for p in paras if len(p) > 30]
    text = "\n\n".join(paras) if paras else soup.get_text(" ", strip=True)

    source_url = data.get("provider", {}).get("profileId") or data.get("absoluteUrl") or url
    return {"title": title or "Untitled", "text": text, "source": source_url}


async def _try_github_api(url: str, client: httpx.AsyncClient) -> dict | None:
    m = GITHUB_REPO_RE.match(url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)

    gh_headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "xnew-extractor/1.0",
    }
    api_base = f"https://api.github.com/repos/{owner}/{repo}"

    try:
        r = await client.get(api_base, headers=gh_headers)
        if r.status_code != 200:
            return None
        meta = r.json()
    except Exception:
        return None

    title: str = meta.get("full_name", f"{owner}/{repo}")
    description: str = meta.get("description") or ""
    topics: str = ", ".join(meta.get("topics") or [])
    stars: int = meta.get("stargazers_count", 0)
    language: str = meta.get("language") or ""

    readme_text = ""
    try:
        r2 = await client.get(f"{api_base}/readme", headers=gh_headers)
        if r2.status_code == 200:
            import base64 as _b64
            raw = _b64.b64decode(r2.json()["content"]).decode("utf-8", errors="replace")
            raw = re.sub(r"!\[.*?\]\(.*?\)", "", raw)
            raw = re.sub(r"\[!\[.*?\]\(.*?\)\]\(.*?\)", "", raw)
            raw = re.sub(r"<[^>]+>", " ", raw)
            readme_text = raw[:15000].strip()
    except Exception:
        pass

    parts = [f"GitHub repository: {title}"]
    if description:
        parts.append(f"Description: {description}")
    if language:
        parts.append(f"Primary language: {language}")
    if stars:
        parts.append(f"Stars: {stars}")
    if topics:
        parts.append(f"Topics: {topics}")
    if readme_text:
        parts.append("\n--- README ---\n" + readme_text)

    text = "\n".join(parts)
    if len(text) < 100:
        return None
    return {"title": title, "text": text, "source": url}


async def extract_from_url(url: str) -> dict:
    """
    Extract clean article content from URL.
    Strategy:
      1. GitHub repos → GitHub REST API (README + metadata)
      2. MSN articles → MSN assets API
      3. trafilatura (best for news articles)
      4. BeautifulSoup fallback
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
        # ── Special handler: GitHub ──
        github_result = await _try_github_api(url, client)
        if github_result and len(github_result["text"]) >= 200:
            return {**github_result, "text": github_result["text"][:20000]}

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
            classes = el.get("class")
            cls = " ".join(classes if isinstance(classes, list) else [classes or ""]).lower()
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
        og_content = og.get("content") if og else None
        if og_content and isinstance(og_content, str):
            title = og_content.strip()
        else:
            h_title = soup.find("title")
            h1 = soup.find("h1")
            if h_title:
                title = h_title.get_text(strip=True)
            elif h1:
                title = h1.get_text(strip=True)
            else:
                title = "Untitled"

    for sep in [" | ", " - ", " — ", " · "]:
        if sep in title and len(title.split(sep)[0]) > 20:
            title = title.split(sep)[0].strip()
            break

    text = (text or "").strip()

    # ── Validation ──
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
