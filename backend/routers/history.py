"""History router — extraction history."""
from fastapi import APIRouter, Depends
from db.supabase import get_supabase
from middleware.auth import get_current_user

router = APIRouter(prefix="/history", tags=["history"])


def _get_user_id(email: str) -> str:
    sb = get_supabase()
    res = sb.table("users").select("id").eq("email", email).single().execute()
    return res.data["id"] if res.data else None


@router.get("")
async def list_history(user: dict = Depends(get_current_user)):
    sb = get_supabase()
    user_id = _get_user_id(user["email"])
    if not user_id:
        return {"extractions": []}
    res = sb.table("extractions") \
        .select("id,source_url,source_type,title,text_preview,created_at,project_id") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(50) \
        .execute()
    return {"extractions": res.data or []}


@router.get("/local")
async def list_local_history():
    from routers.compositions import get_project_root
    import json

    project_root = get_project_root()
    db_path = project_root / "history" / "db.json"

    if not db_path.exists():
        return {"history": []}

    try:
        data = json.loads(db_path.read_text(encoding="utf-8"))
        return {"history": data}
    except Exception as e:
        return {"history": [], "error": str(e)}


@router.delete("/local/{item_id}")
async def delete_local_history(item_id: str):
    from routers.compositions import get_project_root
    import json

    project_root = get_project_root()
    history_dir = project_root / "history"
    db_path = history_dir / "db.json"

    if not db_path.exists():
        return {"success": False, "message": "History db not found"}

    try:
        history_list = json.loads(db_path.read_text(encoding="utf-8"))
        # Find item
        item = next((x for x in history_list if x["id"] == item_id), None)
        if not item:
            return {"success": False, "message": "Item not found"}

        # Delete files if they exist
        # html_url is like "/static-history/htmls/html_TIMESTAMP.html"
        # video_url is like "/static-history/videos/video_TIMESTAMP.mp4"
        html_rel = item["html_url"].replace("/static-history/", "")
        video_rel = item["video_url"].replace("/static-history/", "")

        html_file = history_dir / html_rel
        video_file = history_dir / video_rel

        if html_file.exists():
            html_file.unlink()
        if video_file.exists():
            video_file.unlink()

        # Filter item from list
        new_list = [x for x in history_list if x["id"] != item_id]
        db_path.write_text(json.dumps(new_list, indent=2, ensure_ascii=False), encoding="utf-8")

        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}
