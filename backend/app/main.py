from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.actualites import router as actualites_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.bureau import router as bureau_router
from app.api.v1.courriers import router as courriers_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.documents import router as documents_router
from app.api.v1.effectifs import router as effectifs_router
from app.api.v1.gallery import router as gallery_router
from app.api.v1.mouvement import router as mouvement_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.programme import router as programme_router
from app.api.v1.public import router as public_router
from app.api.v1.section_bureau import router as section_bureau_router
from app.api.v1.sections import router as sections_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.core.rate_limit import limiter

app = FastAPI(
    title="Vicariat de l'Annonciation — API",
    description="API de la plateforme de gestion du Vicariat de l'Annonciation (CV-AV, Diocèse de Yopougon).",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(sections_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(audit_logs_router, prefix="/api/v1")
app.include_router(actualites_router, prefix="/api/v1")
app.include_router(programme_router, prefix="/api/v1")
app.include_router(gallery_router, prefix="/api/v1")
app.include_router(bureau_router, prefix="/api/v1")
app.include_router(effectifs_router, prefix="/api/v1")
app.include_router(mouvement_router, prefix="/api/v1")
app.include_router(section_bureau_router, prefix="/api/v1")
app.include_router(courriers_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["health"])
def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
