import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser, get_client_ip, require_admin
from app.core.database import get_db
from app.core.security import hash_password
from app.models.section import Section
from app.models.user import Role, User
from app.schemas.user import AdminResetPasswordRequest, UserAdminOut, UserCreate, UserUpdate
from app.services.audit_service import log_action
from app.services.auth_service import revoke_all_sessions_for_user
from app.services.notification_service import notify
from app.models.notification import NotificationType

router = APIRouter(prefix="/users", tags=["users"])


def _actor_label(db: Session, current: CurrentUser) -> str:
    user = db.get(User, current.id)
    return user.username if user else str(current.id)


def _user_out(user: User) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
        section_id=user.section_id,
        section_name=user.section.name if user.section else None,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def _resolve_role_and_section(db: Session, *, role_name: str, section_id: uuid.UUID | None) -> tuple[Role, Section | None]:
    role = db.query(Role).filter(Role.name == role_name).first()
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Rôle inconnu : {role_name}.")

    section = None
    if role.name == Role.SECTION:
        if section_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un utilisateur de rôle SECTION doit être rattaché à une section.",
            )
        section = db.get(Section, section_id)
        if section is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section introuvable.")
    return role, section


@router.get("", response_model=list[UserAdminOut])
def list_users(db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)):
    users = db.query(User).options(joinedload(User.role), joinedload(User.section)).order_by(User.created_at.desc()).all()
    return [_user_out(u) for u in users]


@router.post("", response_model=UserAdminOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    username = payload.username.lower().strip()
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un compte existe déjà avec cet identifiant.")

    email = payload.email.lower().strip() if payload.email else None
    if email and db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un compte existe déjà avec cet e-mail.")

    role, section = _resolve_role_and_section(db, role_name=payload.role, section_id=payload.section_id)

    user = User(
        username=username,
        email=email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_id=role.id,
        section_id=section.id if section else None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    notify(
        db,
        user_id=user.id,
        type=NotificationType.NEW_ACCOUNT,
        message=f"Un compte {role.name} vient d'être créé pour vous par le Bureau du Vicariat.",
    )
    log_action(
        db,
        user_id=current.id,
        user_label=_actor_label(db, current),
        action="USER_CREATED",
        resource_type="user",
        resource_id=str(user.id),
        resource_label=user.username,
        ip_address=get_client_ip(request),
    )
    return _user_out(user)


@router.put("/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")

    if payload.role is not None or payload.section_id is not None:
        new_role_name = payload.role or user.role.name
        new_section_id = payload.section_id if payload.section_id is not None else user.section_id
        role, section = _resolve_role_and_section(db, role_name=new_role_name, section_id=new_section_id)
        user.role_id = role.id
        user.section_id = section.id if section else None

    if payload.full_name is not None:
        user.full_name = payload.full_name

    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(
        db,
        user_id=current.id,
        user_label=_actor_label(db, current),
        action="USER_UPDATED",
        resource_type="user",
        resource_id=str(user.id),
        resource_label=user.username,
        ip_address=get_client_ip(request),
    )
    return _user_out(user)


@router.post("/{user_id}/deactivate", response_model=UserAdminOut)
def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    if user.id == current.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vous ne pouvez pas désactiver votre propre compte.")

    user.is_active = False
    db.add(user)
    db.commit()
    revoke_all_sessions_for_user(db, user_id=user.id)

    log_action(
        db,
        user_id=current.id,
        user_label=_actor_label(db, current),
        action="USER_DEACTIVATED",
        resource_type="user",
        resource_id=str(user.id),
        resource_label=user.username,
        ip_address=get_client_ip(request),
    )
    db.refresh(user)
    return _user_out(user)


@router.post("/{user_id}/reactivate", response_model=UserAdminOut)
def reactivate_user(
    user_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")

    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(
        db,
        user_id=current.id,
        user_label=_actor_label(db, current),
        action="USER_REACTIVATED",
        resource_type="user",
        resource_id=str(user.id),
        resource_label=user.username,
        ip_address=get_client_ip(request),
    )
    return _user_out(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    if user.id == current.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vous ne pouvez pas supprimer votre propre compte.")

    label = user.username
    db.delete(user)
    try:
        db.commit()
    except IntegrityError:
        # L'utilisateur est l'auteur de documents / actualités / activités /
        # photos existants : on ne perd jamais ce contenu ni son historique
        # d'auteur. La suppression définitive n'est possible que pour un
        # compte qui n'a jamais rien publié ; sinon, il faut le désactiver.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Ce compte a créé des contenus (documents, actualités, activités ou photos) : "
                "il ne peut pas être supprimé définitivement afin de ne pas perdre ces données. "
                "Désactivez-le à la place."
            ),
        )

    log_action(
        db,
        user_id=current.id,
        user_label=_actor_label(db, current),
        action="USER_DELETED",
        resource_type="user",
        resource_id=str(user_id),
        resource_label=label,
        ip_address=get_client_ip(request),
    )
    return None


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def admin_reset_password(
    user_id: uuid.UUID,
    payload: AdminResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")

    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    db.commit()
    revoke_all_sessions_for_user(db, user_id=user.id)

    log_action(
        db,
        user_id=current.id,
        user_label=_actor_label(db, current),
        action="USER_PASSWORD_RESET_BY_ADMIN",
        resource_type="user",
        resource_id=str(user.id),
        resource_label=user.username,
        ip_address=get_client_ip(request),
    )
    return None
