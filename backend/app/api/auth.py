"""Auth: login / register (demo user)."""
import base64
import json
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.db.session import get_conn

router = APIRouter()


def _issue_token(user_id: str) -> str:
    payload = json.dumps({"sub": user_id, "exp": int(time.time()) + 24 * 3600})
    b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    return f"demo.{b64}.token"


class LoginBody(BaseModel):
    email: str
    password: str


class RegisterBody(BaseModel):
    email: str
    password: str
    display_name: str | None = None


@router.post("/login")
def login(body: LoginBody) -> dict:
    if not body.email or not body.password:
        raise HTTPException(status_code=401, detail={"code": "invalid_credentials", "message": "Invalid credentials"})
    settings = get_settings()
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT id, email, display_name FROM users WHERE id = ?",
            (settings.demo_user_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail={"code": "invalid_credentials", "message": "Invalid credentials"})
        user = dict(row)
        return {
            "access_token": _issue_token(user["id"]),
            "token_type": "bearer",
            "profile": {"id": user["id"], "email": user["email"], "display_name": user["display_name"]},
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.post("/register")
def register(body: RegisterBody) -> dict:
    settings = get_settings()
    conn = get_conn()
    try:
        cur = conn.execute("SELECT id, email, display_name FROM users WHERE id = ?", (settings.demo_user_id,))
        row = cur.fetchone()
        if row:
            user = dict(row)
            return {
                "access_token": _issue_token(user["id"]),
                "token_type": "bearer",
                "profile": {"id": user["id"], "email": user["email"], "display_name": user["display_name"]},
            }
        display = (body.display_name or body.email or "User").strip() or "User"
        conn.execute(
            "INSERT INTO users (id, email, display_name) VALUES (?, ?, ?)",
            (settings.demo_user_id, body.email or settings.demo_email, display),
        )
        conn.commit()
        return {
            "access_token": _issue_token(settings.demo_user_id),
            "token_type": "bearer",
            "profile": {"id": settings.demo_user_id, "email": body.email or settings.demo_email, "display_name": display},
        }
    finally:
        conn.close()
