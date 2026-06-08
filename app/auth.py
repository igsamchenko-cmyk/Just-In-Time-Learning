from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User


oauth = OAuth()


def google_oauth_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


if google_oauth_configured():
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def get_or_create_user_from_google(db: Session, profile: dict) -> User:
    email = profile.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google profile does not include email")

    user = db.scalar(select(User).where(User.email == email))
    if user:
        user.google_id = profile.get("sub") or user.google_id
        user.name = profile.get("name") or user.name
        user.avatar_url = profile.get("picture") or user.avatar_url
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=email,
        name=profile.get("name") or email,
        google_id=profile.get("sub"),
        avatar_url=profile.get("picture"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_demo_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == "demo@example.com"))
    if user:
        return user

    user = User(
        email="demo@example.com",
        name="Демо користувач",
        google_id="demo-google-user",
        avatar_url=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)
