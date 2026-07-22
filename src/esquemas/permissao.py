from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PermissaoBase(BaseModel):
    """Esquema base para Permissão."""

    nome: str = Field(..., min_length=1, max_length=100, description="Nome da permissão")
    descricao: Optional[str] = Field(None, max_length=255, description="Descrição da permissão")
    recurso: str = Field(..., min_length=1, max_length=100, description="Recurso (ex: 'usuarios', 'tenants')")
    acao: str = Field(..., min_length=1, max_length=50, description="Ação (ex: 'criar', 'ler', 'atualizar', 'deletar')")
    ativa: bool = True


class PermissaoCriacao(PermissaoBase):
    """Esquema para criação de permissão."""

    pass


class PermissaoAtualizacao(BaseModel):
    """Esquema para atualização de permissão."""

    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    ativa: Optional[bool] = None


class PermissaoResposta(PermissaoBase):
    """Esquema de resposta da permissão."""

    id: int
    data_criacao: datetime
    data_atualizacao: datetime

    class Config:
        from_attributes = True


class CargoBase(BaseModel):
    """Esquema base para Cargo."""

    nome: str = Field(..., min_length=1, max_length=100, description="Nome do cargo")
    slug: str = Field(..., min_length=1, max_length=50, description="Slug do cargo (ex: 'admin', 'usuario')")
    descricao: Optional[str] = Field(None, max_length=255, description="Descrição do cargo")
    eh_padrao: bool = False
    ativo: bool = True


class CargoCriacao(CargoBase):
    """Esquema para criação de cargo."""

    tenant_id: Optional[int] = Field(None, description="ID do tenant (NULL = cargo global)")
    permissoes_ids: list[int] = Field(default_factory=list, description="IDs das permissões do cargo")


class CargoAtualizacao(BaseModel):
    """Esquema para atualização de cargo."""

    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    eh_padrao: Optional[bool] = None
    ativo: Optional[bool] = None
    permissoes_ids: Optional[list[int]] = None


class CargoResposta(CargoBase):
    """Esquema de resposta do cargo."""

    id: int
    tenant_id: Optional[int] = None
    data_criacao: datetime
    data_atualizacao: datetime
    permissoes: list[PermissaoResposta] = []

    class Config:
        from_attributes = True


class UsuarioCargoVinculo(BaseModel):
    """Esquema para vincular usuário a cargo em um tenant."""

    usuario_id: int
    cargo_id: int
    tenant_id: int


class CargoUsuarioResposta(CargoBase):
    """Esquema de resposta do cargo com informações do tenant."""

    id: int
    tenant_id: Optional[int] = None
    tenant_nome: Optional[str] = None
    data_vinculo: datetime

    class Config:
        from_attributes = True
