"""Projects router — CRUD for user video projects."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import json

from db.supabase import get_supabase
from middleware.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_user_id(email: str) -> str:
    sb = get_supabase()
    res = sb.table("users").select("id").eq("email", email).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="User không tồn tại")
    return res.data["id"]


@router.get("")
async def list_projects(user: dict = Depends(get_current_user)):
    sb = get_supabase()
    user_id = _get_user_id(user["email"])
    res = sb.table("projects") \
        .select("id,title,status,video_url,html_url,duration,created_at,updated_at") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .execute()
    return {"projects": res.data or []}


@router.get("/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    user_id = _get_user_id(user["email"])
    res = sb.table("projects") \
        .select("*") \
        .eq("id", project_id) \
        .eq("user_id", user_id) \
        .single() \
        .execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    return res.data


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    user_id = _get_user_id(user["email"])
    sb.table("projects").delete().eq("id", project_id).eq("user_id", user_id).execute()
    return {"deleted": True}
