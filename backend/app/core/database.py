"""Connexion SQLAlchemy et fournisseur de session pour les dépendances FastAPI."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dépendance FastAPI : une session DB par requête, toujours fermée."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
