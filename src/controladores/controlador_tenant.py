from fastapi import APIRouter, Depends, status, Query
from typing import Optional

from src.configuracoes.banco_dados import obter_sessao
from src.repositorios.repositorio_tenant import RepositorioTenant
from src.servicos.servico_tenant import ServicoTenant
from src.esquemas.tenant import TenantCriacao, TenantAtualizacao, TenantResposta


def obter_repositorio_tenant(sessao_generator=Depends(obter_sessao)):
    """Dependency para obter o repositório de tenant."""
    return RepositorioTenant(sessao=sessao_generator)


def obter_servico_tenant(
    repositorio: RepositorioTenant = Depends(obter_repositorio_tenant)
):
    """Dependency para obter o serviço de tenant."""
    return ServicoTenant(repositorio=repositorio)


router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post(
    "",
    response_model=TenantResposta,
    status_code=status.HTTP_201_CREATED,
    summary="Criar um novo tenant",
    description="Cria um novo tenant (organização) no sistema multi-tenant."
)
def criar_tenant(
    dados: TenantCriacao,
    servico: ServicoTenant = Depends(obter_servico_tenant)
):
    """Cria um novo tenant."""
    return servico.criar_tenant(dados=dados)


@router.get(
    "",
    response_model=list[TenantResposta],
    summary="Listar tenants",
    description="Lista todos os tenants cadastrados, com opção de filtrar por status."
)
def listar_tenants(
    ativo: Optional[bool] = Query(None, description="Filtrar por status (ativo/inativo)"),
    servico: ServicoTenant = Depends(obter_servico_tenant)
):
    """Lista todos os tenants."""
    return servico.listar_tenants(ativo=ativo)


@router.get(
    "/{tenant_id}",
    response_model=TenantResposta,
    summary="Buscar tenant por ID",
    description="Busca um tenant específico pelo seu ID."
)
def buscar_tenant(
    tenant_id: int,
    servico: ServicoTenant = Depends(obter_servico_tenant)
):
    """Busca um tenant pelo ID."""
    return servico.buscar_tenant(tenant_id=tenant_id)


@router.put(
    "/{tenant_id}",
    response_model=TenantResposta,
    summary="Atualizar tenant",
    description="Atualiza os dados de um tenant existente."
)
def atualizar_tenant(
    tenant_id: int,
    dados: TenantAtualizacao,
    servico: ServicoTenant = Depends(obter_servico_tenant)
):
    """Atualiza um tenant existente."""
    return servico.atualizar_tenant(tenant_id=tenant_id, dados=dados)


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_200_OK,
    summary="Deletar tenant",
    description="Remove um tenant do sistema."
)
def deletar_tenant(
    tenant_id: int,
    servico: ServicoTenant = Depends(obter_servico_tenant)
):
    """Deleta um tenant."""
    return servico.deletar_tenant(tenant_id=tenant_id)
