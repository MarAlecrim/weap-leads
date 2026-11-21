from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import User, UserCreate, UserUpdate


def _perfil_coerente(dados: dict[str, Any], atual: str | None = None) -> None:
    """O perfil "admin" e o is_superuser andam juntos."""
    if dados.get("perfil"):
        dados["is_superuser"] = dados["perfil"] == "admin"
    elif dados.get("is_superuser") is True:
        dados["perfil"] = "admin"
    elif dados.get("is_superuser") is False and atual == "admin":
        dados["perfil"] = "gestor"


def create_user(*, session: Session, user_create: UserCreate) -> User:
    dados = user_create.model_dump()
    if dados.get("is_superuser"):
        dados["perfil"] = "admin"
    elif dados.get("perfil") == "admin":
        dados["is_superuser"] = True
    dados["hashed_password"] = get_password_hash(user_create.password)
    db_obj = User.model_validate(dados)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    for campo in ("perfil", "numeros"):
        if campo in user_data and user_data[campo] is None:
            del user_data[campo]
    _perfil_coerente(user_data, db_user.perfil)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


# Dummy hash to use for timing attack prevention when user is not found
# This is an Argon2 hash of a random password, used to ensure constant-time comparison
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        # Prevent timing attacks by running password verification even when user doesn't exist
        # This ensures the response time is similar whether or not the email exists
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user
