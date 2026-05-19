"""DuckDuckGo image search.

DuckDuckGo doesn't expose an official image API, so we scrape the unofficial
2-step flow: GET the search page to obtain a `vqd` token, then call /i.js with
that token to get JSON results. No API key needed, no rate limit auth headers.
"""
import re
import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


async def get_vqd(client: httpx.AsyncClient, query: str) -> str:
    r = await client.get(
        "https://duckduckgo.com/",
        params={"q": query, "iax": "images", "ia": "images"},
        headers={"User-Agent": UA},
    )
    r.raise_for_status()
    # vqd shows up as either vqd='3-...' or vqd="3-..." or &vqd=3-...
    m = re.search(r'vqd=["\']?(\d-[\d-]+)["\']?', r.text)
    if not m:
        raise HTTPException(status_code=502, detail="Không lấy được vqd từ DuckDuckGo")
    return m.group(1)


@router.get("/image-search")
async def image_search(q: str, limit: int = 12, safe: bool = True):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query rỗng")

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        vqd = await get_vqd(client, q)
        params = {
            "l": "us-en",
            "o": "json",
            "q": q,
            "vqd": vqd,
            "f": ",,,,,",
            "p": "1" if safe else "-1",
            "v7exp": "a",
        }
        r = await client.get(
            "https://duckduckgo.com/i.js",
            params=params,
            headers={
                "User-Agent": UA,
                "Referer": "https://duckduckgo.com/",
                "Accept": "application/json",
            },
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"DDG i.js trả về {r.status_code}")

        try:
            data = r.json()
        except Exception:
            raise HTTPException(status_code=502, detail="DDG trả về không phải JSON")

        results = data.get("results", [])
        items = []
        for it in results[:limit]:
            img = it.get("image")
            thumb = it.get("thumbnail") or img
            if not img:
                continue
            items.append({
                "image": img,
                "thumbnail": thumb,
                "title": it.get("title", ""),
                "source": it.get("source", ""),
                "url": it.get("url", ""),
                "width": it.get("width"),
                "height": it.get("height"),
            })

        return {"query": q, "count": len(items), "results": items}
