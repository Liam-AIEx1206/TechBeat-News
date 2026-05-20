import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx

bearer = HTTPBearer(auto_error=False)

# NextAuth signs JWTs with NEXTAUTH_SECRET using HS256
NEXTAUTH_SECRET = os.getenv("NEXTAUTH_SECRET", "")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> dict:
    """Verify NextAuth JWT and return payload with email."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token thiếu")

    token = credentials.credentials
    if not NEXTAUTH_SECRET:
        raise HTTPException(status_code=500, detail="NEXTAUTH_SECRET chưa được set")

    try:
        payload = jwt.decode(
            token,
            NEXTAUTH_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        email: str = payload.get("email") or payload.get("sub", "")
        if not email:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
        return {"email": email, "name": payload.get("name"), "picture": payload.get("picture")}
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token không hợp lệ: {e}")


# Optional auth — không raise nếu không có token (cho backward compat)
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> Optional[dict]:
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
