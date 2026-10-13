import os
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://vicariat:changeme@localhost:5432/vicariat_test")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("STORAGE_LOCAL_PATH", "/tmp/vicariat_test_uploads")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
import app.models  # noqa: E402,F401
from app.main import app  # noqa: E402
from app.models.section import Section  # noqa: E402
from app.models.user import Role, User  # noqa: E402

engine = create_engine(settings.DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _clean_tables():
    """Vide toutes les tables entre chaque test pour une isolation complète."""
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from app.core.rate_limit import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture()
def client(db_session):
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def roles(db_session):
    admin_role = Role(name=Role.ADMIN, description="admin")
    section_role = Role(name=Role.SECTION, description="section")
    db_session.add_all([admin_role, section_role])
    db_session.commit()
    return {"ADMIN": admin_role, "SECTION": section_role}


@pytest.fixture()
def section_nda(db_session):
    section = Section(slug="nda", name="Notre-Dame de l'Annonciation", quartier="Nouveau Quartier")
    db_session.add(section)
    db_session.commit()
    return section


@pytest.fixture()
def section_stmarc(db_session):
    section = Section(slug="stmarc", name="Saint-Marc", quartier="des Toits Rouges")
    db_session.add(section)
    db_session.commit()
    return section


@pytest.fixture()
def doc_category(db_session):
    from app.models.document import DocumentCategory

    category = DocumentCategory(name="Rapport", is_system=True)
    db_session.add(category)
    db_session.commit()
    return category


# En-tête minimal d'un PDF valide : suffisant pour passer la vérification de
# signature binaire réelle du service de validation de fichiers.
MINIMAL_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

# Idem pour une image PNG minimale (seule la signature des 8 premiers octets
# est vérifiée par le service de validation, pas le contenu réel de l'image).
MINIMAL_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


def make_user(db_session, *, email=None, username=None, password, role, section=None, is_active=True, full_name="Test User"):
    if username is None:
        username = (email or "utilisateur").split("@")[0]
    user = User(
        id=uuid.uuid4(),
        username=username,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role_id=role.id,
        section_id=section.id if section else None,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_user(db_session, roles):
    return make_user(db_session, username="admin", email="admin@vicariat-annonciation.ci", password="AdminPass1", role=roles["ADMIN"])


@pytest.fixture()
def section_user_nda(db_session, roles, section_nda):
    return make_user(
        db_session,
        username="nda",
        email="nda@vicariat-annonciation.ci",
        password="SectionPass1",
        role=roles["SECTION"],
        section=section_nda,
    )


@pytest.fixture()
def section_user_stmarc(db_session, roles, section_stmarc):
    return make_user(
        db_session,
        username="stmarc",
        email="stmarc@vicariat-annonciation.ci",
        password="SectionPass1",
        role=roles["SECTION"],
        section=section_stmarc,
    )
