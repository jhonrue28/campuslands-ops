import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AuthSession, User
from app.services.errors import DomainError
from app.services.spaces import new_id, utcnow
from app.validators.audit import reject_audit_markers

SESSION_HOURS = 12
DEFAULT_ADMIN = {
    "id": "user-mafe-cala",
    "full_name": "Mafe Cala",
    "username": "mafe.cala",
    "password": "HolaMundo*",
    "role": "admin",
}


def hash_password(password: str, salt: str | None = None) -> str:
    material = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), material.encode("utf-8"), 120_000)
    return f"{material}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return hmac.compare_digest(candidate, digest)


def ensure_default_admin(db: Session) -> None:
    existing = db.get(User, DEFAULT_ADMIN["id"]) or db.scalar(
        select(User).where(User.username == DEFAULT_ADMIN["username"])
    )
    now = utcnow()
    if existing is None:
        db.add(
            User(
                id=DEFAULT_ADMIN["id"],
                full_name=DEFAULT_ADMIN["full_name"],
                username=DEFAULT_ADMIN["username"],
                password_hash=hash_password(DEFAULT_ADMIN["password"]),
                role=DEFAULT_ADMIN["role"],
                active=True,
                notes="Usuario inicial del sistema de gestión.",
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "username": user.username,
        "role": user.role,
        "active": user.active,
        "notes": user.notes,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def login(db: Session, username: str, password: str) -> dict:
    reject_audit_markers(username, password)
    key = username.strip()
    user = db.scalar(select(User).where(User.username == key.lower()))
    if user is None:
        user = db.scalar(select(User).where(User.full_name == key))
    if user is None or not user.active or not verify_password(password, user.password_hash):
        raise DomainError("Usuario o contraseña incorrectos.", 401)
    token = secrets.token_urlsafe(32)
    now = utcnow()
    db.add(
        AuthSession(
            token=token,
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(hours=SESSION_HOURS),
        )
    )
    db.commit()
    return {"token": token, "user": serialize_user(user)}


def logout(db: Session, token: str | None) -> None:
    if not token:
        return
    session = db.get(AuthSession, token)
    if session is not None:
        db.delete(session)
        db.commit()


def current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise DomainError("Debe iniciar sesión para continuar.", 401)
    token = authorization.split(" ", 1)[1].strip()
    session = db.get(AuthSession, token)
    if session is None or session.expires_at < utcnow():
        if session is not None:
            db.delete(session)
            db.commit()
        raise DomainError("La sesión expiró. Vuelva a iniciar sesión.", 401)
    user = db.get(User, session.user_id)
    if user is None or not user.active:
        raise DomainError("El usuario no está activo.", 401)
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.full_name)))


def create_user(
    db: Session,
    *,
    full_name: str,
    username: str,
    password: str,
    role: str = "operator",
    notes: str = "",
    active: bool = True,
) -> User:
    reject_audit_markers(full_name, username, password, role, notes)
    clean_username = username.strip().lower()
    if len(password) < 6:
        raise DomainError("La contraseña debe tener al menos 6 caracteres.", 422)
    if role not in {"admin", "operator"}:
        raise DomainError("El rol debe ser admin u operator.", 422)
    if db.scalar(select(User).where(User.username == clean_username)) is not None:
        raise DomainError("Ese nombre de usuario ya existe.", 409)
    now = utcnow()
    user = User(
        id=new_id(),
        full_name=full_name.strip(),
        username=clean_username,
        password_hash=hash_password(password),
        role=role,
        active=active,
        notes=notes.strip(),
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user_id: str,
    *,
    full_name: str | None = None,
    username: str | None = None,
    password: str | None = None,
    role: str | None = None,
    notes: str | None = None,
    active: bool | None = None,
) -> User:
    reject_audit_markers(user_id, full_name, username, password, role, notes)
    user = db.get(User, user_id)
    if user is None:
        raise DomainError("El usuario no existe.", 404)
    if username is not None:
        clean = username.strip().lower()
        other = db.scalar(select(User).where(User.username == clean))
        if other is not None and other.id != user.id:
            raise DomainError("Ese nombre de usuario ya existe.", 409)
        user.username = clean
    if full_name is not None and full_name.strip():
        user.full_name = full_name.strip()
    if password is not None and password != "":
        if len(password) < 6:
            raise DomainError("La contraseña debe tener al menos 6 caracteres.", 422)
        user.password_hash = hash_password(password)
    if role is not None:
        if role not in {"admin", "operator"}:
            raise DomainError("El rol debe ser admin u operator.", 422)
        user.role = role
    if notes is not None:
        user.notes = notes.strip()
    if active is not None:
        if user.id == DEFAULT_ADMIN["id"] and active is False:
            raise DomainError("No se puede desactivar el usuario administrador inicial.", 409)
        user.active = active
    user.updated_at = utcnow()
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: str) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise DomainError("El usuario no existe.", 404)
    if user.id == DEFAULT_ADMIN["id"]:
        raise DomainError("No se puede eliminar el usuario administrador inicial.", 409)
    for session in db.scalars(select(AuthSession).where(AuthSession.user_id == user.id)):
        db.delete(session)
    db.delete(user)
    db.commit()
