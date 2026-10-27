import hashlib
import hmac
import secrets
from datetime import timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from .db import SessionLocal, LoginSession, User, now
from .config import settings

bearer = HTTPBearer(auto_error=False)

def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f'scrypt${salt}${digest}'

def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, expected = stored.split('$')
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def issue_session(db, user_id):
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=token_hash(token), user_id=user_id, expires_at=now()+timedelta(hours=settings.session_hours)))
    db.commit()
    return token

def get_db():
    with SessionLocal() as db:
        try:
            yield db
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(503, 'Database unavailable. Check MySQL and backend/.env.')

def current_user(auth: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if not auth:
        raise HTTPException(401, 'Please sign in.')
    session = db.get(LoginSession, token_hash(auth.credentials))
    if not session or session.expires_at <= now():
        raise HTTPException(401, 'Session expired. Please sign in again.')
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, 'Please sign in.')
    return user
