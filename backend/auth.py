import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel, EmailStr
from core import db, P, new_id, now, client_ip, audit

router = APIRouter(prefix="/api/auth")
ALG = "HS256"


def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p, h):
    return bcrypt.checkpw(p.encode(), h.encode())


def token(uid, email, kind, delta):
    return jwt.encode({"sub": uid, "email": email, "type": kind, "exp": datetime.now(timezone.utc) + delta}, os.environ["JWT_SECRET"], algorithm=ALG)


def set_cookies(resp, uid, email):
    resp.set_cookie("access_token", token(uid, email, "access", timedelta(minutes=60)), httponly=True, secure=True, samesite="none", max_age=3600, path="/")
    resp.set_cookie("refresh_token", token(uid, email, "refresh", timedelta(days=7)), httponly=True, secure=True, samesite="none", max_age=604800, path="/")


async def get_admin(request: Request):
    t = request.cookies.get("access_token")
    if not t and request.headers.get("Authorization", "").startswith("Bearer "):
        t = request.headers["Authorization"][7:]
    if not t:
        raise HTTPException(401, "Not authenticated")
    try:
        pl = jwt.decode(t, os.environ["JWT_SECRET"], algorithms=[ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if pl.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    u = await db.users.find_one({"id": pl["sub"]}, {"_id": 0, "password_hash": 0})
    if not u or u.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return u


class Login(BaseModel):
    email: EmailStr
    password: str


class PwChange(BaseModel):
    current_password: str
    new_password: str


@router.post("/login")
async def login(body: Login, request: Request, response: Response):
    email = body.email.lower()
    ident = f"email:{email}"
    att = await db.login_attempts.find_one({"identifier": ident})
    if att and att.get("count", 0) >= 5 and att.get("locked_until", "") > now():
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    u = await db.users.find_one({"email": email})
    if not u or not verify_password(body.password, u["password_hash"]):
        cnt = (att or {}).get("count", 0) + 1
        await db.login_attempts.update_one({"identifier": ident}, {"$set": {"count": cnt, "locked_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}}, upsert=True)
        await audit("admin", "auth.login_failed", "admin", {"ip": client_ip(request)}, "anonymous")
        raise HTTPException(401, "Invalid email or password")
    await db.login_attempts.delete_one({"identifier": ident})
    set_cookies(response, u["id"], email)
    await audit("admin", "auth.login", "admin", {}, email)
    return {"id": u["id"], "email": email, "name": u.get("name"), "role": u["role"]}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")
    return {"ok": True}


@router.get("/me")
async def me(u=Depends(get_admin)):
    return u


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    t = request.cookies.get("refresh_token")
    try:
        pl = jwt.decode(t or "", os.environ["JWT_SECRET"], algorithms=[ALG])
        assert pl.get("type") == "refresh"
    except (jwt.InvalidTokenError, AssertionError):
        raise HTTPException(401, "Invalid refresh token")
    u = await db.users.find_one({"id": pl["sub"]}, P)
    if not u:
        raise HTTPException(401, "User not found")
    set_cookies(response, u["id"], u["email"])
    return {"ok": True}


@router.post("/change-password")
async def change_pw(body: PwChange, u=Depends(get_admin)):
    full = await db.users.find_one({"id": u["id"]})
    if not verify_password(body.current_password, full["password_hash"]):
        raise HTTPException(400, "Current password is incorrect")
    if len(body.new_password) < 12:
        raise HTTPException(422, "New password must be at least 12 characters")
    await db.users.update_one({"id": u["id"]}, {"$set": {"password_hash": hash_password(body.new_password)}})
    await audit("admin", "auth.password_changed", "admin", {}, u["email"])
    return {"ok": True}


async def seed_admin():
    email = os.environ["ADMIN_EMAIL"].lower()
    if not await db.users.find_one({"email": email}):
        await db.users.insert_one({"id": new_id("usr-"), "email": email, "password_hash": hash_password(os.environ["ADMIN_PASSWORD"]), "name": "Seun Olawepo", "role": "admin", "created_at": now()})
