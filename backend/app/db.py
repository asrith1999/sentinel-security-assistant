from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass

engine = create_engine(settings.database_url, pool_pre_ping=True,
    connect_args={'check_same_thread': False} if settings.database_url.startswith('sqlite') else {'connect_timeout': 5})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class LoginSession(Base):
    __tablename__ = 'login_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

class Investigation(Base):
    __tablename__ = 'investigations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(150))
    source: Mapped[str] = mapped_column(String(150))
    logs: Mapped[str] = mapped_column(Text().with_variant(MEDIUMTEXT(), 'mysql'))
    result: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default='open')
    ai_summary: Mapped[str] = mapped_column(Text().with_variant(MEDIUMTEXT(), 'mysql'), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Chat(Base):
    __tablename__ = 'chats'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text().with_variant(MEDIUMTEXT(), 'mysql'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
