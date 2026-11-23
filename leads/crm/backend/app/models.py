import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import EmailStr
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    # admin (vê e configura tudo), gestor (vê tudo) ou vendedor (só os seus leads)
    perfil: str = Field(default="vendedor", max_length=20)
    # instâncias da Evolution (números de WhatsApp) deste usuário, ex. "Weap-Fabiano-7187"
    numeros: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String), nullable=False, server_default="{}"),
    )


PERFIS = {"admin": "Administrador", "gestor": "Gestor", "vendedor": "Vendedor"}


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore[assignment]
    password: str | None = Field(default=None, min_length=8, max_length=128)
    perfil: str | None = Field(default=None, max_length=20)  # type: ignore[assignment]
    numeros: list[str] | None = None  # type: ignore[assignment]


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True)),
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


def _quando() -> Any:
    return Field(default=None, sa_column=Column(DateTime(timezone=True)))


# ---------- Funil (kanban) ----------
class Negocio(SQLModel, table=True):
    """Um card do funil: um lead do disparo (chave = 55 + DDD + 8 últimos dígitos, como no banco do agente)."""

    __tablename__ = "crm_negocio"

    id: int | None = Field(default=None, primary_key=True)
    chave: str = Field(max_length=20, unique=True, index=True)
    telefone: str | None = Field(default=None, max_length=40)
    nome: str = Field(default="", max_length=255)
    cnpj: str | None = Field(default=None, max_length=14)
    cidade: str | None = Field(default=None, max_length=120)
    origem: str = Field(default="google_maps", max_length=20)
    nota: int | None = None
    instancia: str | None = Field(default=None, max_length=120, index=True)
    etapa: str = Field(default="fila", max_length=20, index=True)
    etapa_desde: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    movido_manual: bool = False
    status_agente: str | None = Field(default=None, max_length=40)
    ia_pausada: bool = False
    valor_cents: int | None = None
    servico: str | None = Field(default=None, max_length=40)
    responsavel_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    perdido_motivo: str | None = Field(default=None, max_length=120)
    proxima_acao: str | None = Field(default=None, max_length=255)
    proxima_acao_em: datetime | None = _quando()
    ultimo_contato_em: datetime | None = _quando()
    ultima_resposta_em: datetime | None = _quando()
    criado_em: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    atualizado_em: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class NegocioHistorico(SQLModel, table=True):
    """Cada mudança de etapa: de onde, para onde, quem (nome da pessoa ou "agente") e quando."""

    __tablename__ = "crm_negocio_historico"

    id: int | None = Field(default=None, primary_key=True)
    negocio_id: int = Field(
        sa_column=Column(
            ForeignKey("crm_negocio.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    de: str | None = Field(default=None, max_length=20)
    para: str = Field(max_length=20)
    autor: str = Field(max_length=255)
    criado_em: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class NegocioNota(SQLModel, table=True):
    """Nota livre num card, com o nome de quem escreveu."""

    __tablename__ = "crm_negocio_nota"

    id: int | None = Field(default=None, primary_key=True)
    negocio_id: int = Field(
        sa_column=Column(
            ForeignKey("crm_negocio.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    autor: str = Field(max_length=255)
    texto: str = Field(max_length=4000)
    criado_em: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
