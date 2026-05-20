"""Openverse image search (https://openverse.org).

Openverse is a WordPress Foundation project providing CC-licensed images.
No API key required for anonymous use (100 req/min rate limit).
"""
import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

OPENVERSE_URL = "https://api.openverse.org/v1/images/"

UA = "TechBeat/1.0 (video-news-app)"


@router.get("/image-search")
async def image_search(q: str, limit: int = 18, safe: bool = True):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query rỗng")

    # Try without license filter first (more results), then narrow if needed
    params = {
        "q": q,
        "page_size": min(limit, 20),
        "mature": "false" if safe else "true",
    }

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        try:
            r = await client.get(
                OPENVERSE_URL,
                params=params,
                headers={
                    "User-Agent": UA,
                    "Accept": "application/json",
                },
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Không kết nối được Openverse: {e}")

        if r.status_code == 401:
            raise HTTPException(status_code=502, detail="Openverse yêu cầu xác thực — thử lại sau")
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Openverse trả về {r.status_code}")

        try:
            data = r.json()
        except Exception:
            raise HTTPException(status_code=502, detail="Openverse trả về không phải JSON")

        results = data.get("results", [])
        items = []
        for it in results:
            img = it.get("url")
            if not img:
                continue
            thumb = it.get("thumbnail") or img
            items.append({
                "image": img,
                "thumbnail": thumb,
                "title": it.get("title", ""),
                "source": it.get("foreign_landing_url", ""),
                "url": it.get("foreign_landing_url", ""),
                "width": it.get("width"),
                "height": it.get("height"),
                "license": it.get("license", ""),
                "creator": it.get("creator", ""),
            })

        return {"query": q, "count": len(items), "results": items}
