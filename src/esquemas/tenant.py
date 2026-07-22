from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TenantBase(BaseModel):
    """Esquema base para Tenant."""

    nome: str = Field(..., min_length=3, max_length=100, description="Nome do tenant")
    slug: str = Field(..., min_length=3, max_length=50, description="Slug único do tenant")


class TenantCriacao(TenantBase):
    """Esquema para criação de Tenant."""

    pass


class TenantAtualizacao(BaseModel):
    """Esquema para atualização de Tenant."""

    nome: Optional[str] = Field(None, min_length=3, max_length=100)
    slug: Optional[str] = Field(None, min_length=3, max_length=50)
    ativo: Optional[bool] = None


class TenantResposta(TenantBase):
    """Esquema de resposta para Tenant."""

    id: int
    ativo: bool
    data_criacao: datetime
    data_atualizacao: Optional[datetime] = None

    class Config:
        from_attributes = True
