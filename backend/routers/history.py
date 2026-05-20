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
