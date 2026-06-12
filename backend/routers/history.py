"""History router — extraction history."""
from fastapi import APIRouter, Depends, Request
from db.supabase import get_supabase
from middleware.auth import get_current_user
from typing import Optional

router = APIRouter(prefix="/history", tags=["history"])

ADMIN_EMAIL = "cuongld@xgamevn.com"


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

        html_url = item.get("html_url")
        video_url = item.get("video_url")
        log_url = item.get("log_url")

        if html_url:
            html_rel = html_url.replace(prefix, "")
            html_file = history_dir / html_rel
            if html_file.exists():
                html_file.unlink()

        if video_url:
            video_rel = video_url.replace(prefix, "")
            video_file = history_dir / video_rel
            if video_file.exists():
                video_file.unlink()
                
        if log_url:
            log_rel = log_url.replace(prefix, "")
            log_file = history_dir / log_rel
            if log_file.exists():
                log_file.unlink()

        # Filter item from list
        new_list = [x for x in history_list if x["id"] != item_id]
        db_path.write_text(json.dumps(new_list, indent=2, ensure_ascii=False), encoding="utf-8")

        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/admin/users")
async def list_admin_users(request: Request):
    from routers.compositions import get_project_root
    import json
    import os
    import datetime

    # 1. Enforce admin permission
    email = await get_optional_user_email(request)
    if email != ADMIN_EMAIL:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden: Admin access only")

    project_root = get_project_root()
    users_dir = project_root / "history" / "users"
    if not users_dir.exists():
        return {"users": []}

    users_list = []
    # 2. Scan users directory
    for p in users_dir.iterdir():
        if p.is_dir():
            user_email = p.name
            
            if "@" not in user_email:
                continue

            # Read creation time of the folder
            try:
                stat_info = p.stat()
                created_at = datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat()
            except Exception:
                created_at = datetime.datetime.now().isoformat()

            db_path = p / "db.json"
            history = []
            stats = {"total": 0, "success": 0, "failed": 0}
            last_active = created_at

            if db_path.exists():
                try:
                    history = json.loads(db_path.read_text(encoding="utf-8"))
                    stats["total"] = len(history)
                    stats["failed"] = sum(1 for item in history if item.get("status") == "failed")
                    stats["success"] = stats["total"] - stats["failed"]
                    if history:
                        latest_time = None
                        for item in history:
                            c_time = item.get("created_at")
                            if c_time:
                                if not latest_time or c_time > latest_time:
                                    latest_time = c_time
                        if latest_time:
                            last_active = latest_time
                except Exception as e:
                    print(f"[list_admin_users ERROR] Failed to parse db.json for {user_email}: {e}")

            users_list.append({
                "email": user_email,
                "created_at": created_at,
                "last_active": last_active,
                "stats": stats,
                "history": history
            })

    # Sort users by last_active descending (most recently active at the top)
    users_list.sort(key=lambda u: u["last_active"], reverse=True)

    return {"users": users_list}


@router.delete("/admin/users/{user_email}/items/{item_id}")
async def delete_admin_user_history_item(user_email: str, item_id: str, request: Request):
    from routers.compositions import get_project_root
    import json
    import re
    from fastapi import HTTPException

    # 1. Enforce admin permission
    email = await get_optional_user_email(request)
    if email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access only")

    # 2. Validate user_email format using regex to prevent path traversal
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(email_regex, user_email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    project_root = get_project_root()
    history_dir = project_root / "history" / "users" / user_email
    db_path = history_dir / "db.json"

    if not db_path.exists():
        raise HTTPException(status_code=404, detail="User history database not found")

    try:
        history_list = json.loads(db_path.read_text(encoding="utf-8"))
        item = next((x for x in history_list if x["id"] == item_id), None)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Delete files if they exist
        prefix = f"/static-history/users/{user_email}/"
        html_url = item.get("html_url")
        video_url = item.get("video_url")
        log_url = item.get("log_url")

        if html_url:
            html_rel = html_url.replace(prefix, "")
            if ".." not in html_rel:
                html_file = history_dir / html_rel
                if html_file.exists():
                    html_file.unlink()

        if video_url:
            video_rel = video_url.replace(prefix, "")
            if ".." not in video_rel:
                video_file = history_dir / video_rel
                if video_file.exists():
                    video_file.unlink()
                    
        if log_url:
            log_rel = log_url.replace(prefix, "")
            if ".." not in log_rel:
                log_file = history_dir / log_rel
                if log_file.exists():
                    log_file.unlink()

        # Filter item from list
        new_list = [x for x in history_list if x["id"] != item_id]
        db_path.write_text(json.dumps(new_list, indent=2, ensure_ascii=False), encoding="utf-8")

        return {"success": True}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

