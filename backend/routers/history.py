"""History router — extraction history."""
from fastapi import APIRouter, Depends, Request
from db.supabase import get_supabase
from middleware.auth import get_current_user
from typing import Optional

router = APIRouter(prefix="/history", tags=["history"])


def _get_user_id(email: str) -> str:
    sb = get_supabase()
    res = sb.table("users").select("id").eq("email", email).single().execute()
    return res.data["id"] if res.data else None


async def get_optional_user_email(request: Request) -> Optional[str]:
    # Try custom header
    email = request.headers.get("x-user-email")
    if email:
        return email
    
    # Try Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from jose import jwt
            import os
            secret = os.getenv("NEXTAUTH_SECRET", "")
            if secret:
                payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
                return payload.get("email") or payload.get("sub")
        except Exception:
            pass
    return None


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
async def list_local_history(request: Request):
    from routers.compositions import get_project_root
    import json

    project_root = get_project_root()
    email = await get_optional_user_email(request)
    if email:
        safe_email = email
        db_path = project_root / "history" / "users" / safe_email / "db.json"
    else:
        db_path = project_root / "history" / "db.json"

    if not db_path.exists():
        return {"history": []}

    try:
        data = json.loads(db_path.read_text(encoding="utf-8"))
        return {"history": data}
    except Exception as e:
        return {"history": [], "error": str(e)}


@router.delete("/local/{item_id}")
async def delete_local_history(item_id: str, request: Request):
    from routers.compositions import get_project_root
    import json

    project_root = get_project_root()
    email = await get_optional_user_email(request)
    if email:
        safe_email = email
        history_dir = project_root / "history" / "users" / safe_email
    else:
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
        if email:
            safe_email = email
            prefix = f"/static-history/users/{safe_email}/"
        else:
            prefix = "/static-history/"

        html_rel = item["html_url"].replace(prefix, "")
        video_rel = item["video_url"].replace(prefix, "")

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
