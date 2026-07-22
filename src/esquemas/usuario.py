from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UsuarioBase(BaseModel):
    """Esquema base para Usuário."""

    nome: str = Field(..., min_length=1, max_length=100, description="Nome do usuário")
    email: EmailStr = Field(..., description="Email do usuário")
    ativo: bool = True
    administrador: bool = False


class UsuarioCriacao(UsuarioBase):
    """Esquema para criação de usuário."""

    senha: str = Field(..., min_length=6, max_length=255, description="Senha do usuário (mínimo 6 caracteres)")


class UsuarioAtualizacao(BaseModel):
    """Esquema para atualização de usuário."""

    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    ativo: Optional[bool] = None
    administrador: Optional[bool] = None
    senha: Optional[str] = Field(None, min_length=6, max_length=255)


class UsuarioResposta(UsuarioBase):
    """Esquema de resposta do usuário (sem senha)."""

    id: int
    data_criacao: datetime
    data_atualizacao: datetime

    class Config:
        from_attributes = True


class LoginRequisicao(BaseModel):
    """Esquema para requisição de login."""

    email: EmailStr = Field(..., description="Email do usuário")
    senha: str = Field(..., description="Senha do usuário")


class TokenResposta(BaseModel):
    """Esquema de resposta do token JWT."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequisicao(BaseModel):
    """Esquema para requisição de refresh token."""

    refresh_token: str


class TenantUsuarioVinculo(BaseModel):
    """Esquema para vincular usuário a tenant."""

    tenant_id: int
    administrador_tenant: bool = False


class UsuarioComTenantsResposta(UsuarioResposta):
    """Esquema de resposta do usuário com tenants associados."""

    tenants: list[dict] = []

    class Config:
        from_attributes = True
