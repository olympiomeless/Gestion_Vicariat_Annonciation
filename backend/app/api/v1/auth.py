from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, get_current_user_full
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "vicariat_refresh_token"


def _set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
    from app.core.config import settings

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/api/v1/auth",
    )


def _user_out(user) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
        section_id=user.section_id,
        section_slug=user.section.slug if user.section else None,
        is_active=user.is_active,
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
def login(request: Request, response: Response, payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = auth_service.authenticate(db, username=payload.username, password=payload.password, ip=get_client_ip(request))
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    access_token, raw_refresh, expires_in = auth_service.issue_tokens(
        db, user=user, ip=get_client_ip(request), user_agent=request.headers.get("user-agent")
    )
    _set_refresh_cookie(response, raw_refresh)
    return LoginResponse(access_token=access_token, expires_in=expires_in, user=_user_out(user))


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    vicariat_refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    if not vicariat_refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Aucune session active.")
    try:
        user, access_token, new_refresh, expires_in = auth_service.rotate_refresh_token(
            db,
            raw_refresh_token=vicariat_refresh_token,
            ip=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except auth_service.AuthError as exc:
        response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    _set_refresh_cookie(response, new_refresh)
    return LoginResponse(access_token=access_token, expires_in=expires_in, user=_user_out(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    vicariat_refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    if vicariat_refresh_token:
        auth_service.revoke_refresh_token(db, raw_refresh_token=vicariat_refresh_token)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")
    return None


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user_full)):
    return _user_out(user)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    token = auth_service.request_password_reset(db, email=payload.email)
    response_body = {"message": "Si un compte existe avec cette adresse, un lien de réinitialisation a été envoyé."}
    if token is not None and _is_dev():
        # Uniquement en développement (pas d'envoi e-mail configuré) : renvoyer
        # le jeton pour pouvoir tester le flux complet. Ne JAMAIS faire ça en
        # production (le token doit uniquement partir par e-mail).
        response_body["dev_reset_token"] = token
    return response_body


def _is_dev() -> bool:
    from app.core.config import settings

    return settings.ENVIRONMENT == "development"


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        auth_service.reset_password(db, raw_token=payload.token, new_password=payload.new_password)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return None


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db), user=Depends(get_current_user_full)):
    try:
        auth_service.change_password(db, user=user, current_password=payload.current_password, new_password=payload.new_password)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return None
