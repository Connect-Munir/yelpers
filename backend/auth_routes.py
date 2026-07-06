"""Authentication and admin endpoints, mounted under /api."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    user_public,
    verify_password,
)
from .database import get_db
from .models import ROLE_ADMIN, ROLE_USER, VALID_ROLES, Business, User

router = APIRouter(prefix="/api", tags=["auth"])


# --- schemas --------------------------------------------------------------- #
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RoleUpdate(BaseModel):
    role: str


class ActiveUpdate(BaseModel):
    is_active: bool


# --- auth ------------------------------------------------------------------ #
@router.post("/auth/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)) -> dict:
    if not req.name or len(req.name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Public signups are always plain users — admins are promoted explicitly.
    user = User(
        name=req.name.strip(),
        email=req.email,
        hashed_password=hash_password(req.password),
        role=ROLE_USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": create_access_token(user), "user": user_public(user)}


@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    return {"token": create_access_token(user), "user": user_public(user)}


@router.post("/auth/logout")
def logout() -> dict:
    """Stateless JWT — the client just discards the token."""
    return {"message": "Logged out successfully"}


@router.get("/auth/me")
def me(current: User = Depends(get_current_user)) -> dict:
    return user_public(current)


# --- admin (role == 'admin' required) -------------------------------------- #
@router.get("/admin/users")
def admin_list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    search: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    q = db.query(User)
    if search:
        like = f"%{search}%"
        q = q.filter((User.name.like(like)) | (User.email.like(like)))
    total = q.count()
    rows = q.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [user_public(u) for u in rows]}


@router.get("/admin/users/{user_id}")
def admin_get_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = user_public(user)
    # Optional lead count; tolerant if businesses has no user link.
    try:
        data["business_count"] = db.query(Business).filter(
            Business.user_id == user.id  # type: ignore[attr-defined]
        ).count()
    except Exception:  # noqa: BLE001
        data["business_count"] = None
    return data


@router.patch("/admin/users/{user_id}/role")
def admin_set_role(
    user_id: int,
    body: RoleUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of {sorted(VALID_ROLES)}")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and body.role != ROLE_ADMIN:
        raise HTTPException(status_code=400, detail="You cannot remove your own admin role")
    user.role = body.role
    db.commit()
    db.refresh(user)
    return user_public(user)


@router.patch("/admin/users/{user_id}/active")
def admin_set_active(
    user_id: int,
    body: ActiveUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and not body.is_active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return user_public(user)


@router.delete("/admin/users/{user_id}", status_code=204)
def admin_delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    db.delete(user)
    db.commit()
