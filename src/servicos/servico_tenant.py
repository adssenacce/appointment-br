from fastapi import HTTPException, status

from src.repositorios.repositorio_tenant import RepositorioTenant
from src.esquemas.tenant import TenantCriacao, TenantAtualizacao, TenantResposta


class ServicoTenant:
    """Serviço para regras de negócio de Tenant."""

    def __init__(self, repositorio: RepositorioTenant):
        self.repositorio = repositorio

    def criar_tenant(self, dados: TenantCriacao) -> TenantResposta:
        """Cria um novo tenant."""
        if self.repositorio.buscar_por_slug(dados.slug):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um tenant com o slug '{dados.slug}'"
            )

        tenant = self.repositorio.criar(nome=dados.nome, slug=dados.slug)
        return TenantResposta.model_validate(tenant)

    def buscar_tenant(self, tenant_id: int) -> TenantResposta:
        """Busca um tenant pelo ID."""
        tenant = self.repositorio.buscar_por_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant com ID {tenant_id} não encontrado"
            )
        return TenantResposta.model_validate(tenant)

    def listar_tenants(self, ativo: bool = None) -> list[TenantResposta]:
        """Lista todos os tenants."""
        tenants = self.repositorio.listar_todos(ativo=ativo)
        return [TenantResposta.model_validate(t) for t in tenants]

    def atualizar_tenant(self, tenant_id: int, dados: TenantAtualizacao) -> TenantResposta:
        """Atualiza um tenant existente."""
        tenant = self.repositorio.buscar_por_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant com ID {tenant_id} não encontrado"
            )

        if dados.slug and self.repositorio.existe_slug(dados.slug, excluir_id=tenant_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um tenant com o slug '{dados.slug}'"
            )

        dados_atualizacao = {k: v for k, v in dados.model_dump().items() if v is not None}
        tenant = self.repositorio.atualizar(tenant, **dados_atualizacao)
        return TenantResposta.model_validate(tenant)

    def deletar_tenant(self, tenant_id: int) -> dict:
        """Deleta um tenant."""
        tenant = self.repositorio.buscar_por_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant com ID {tenant_id} não encontrado"
            )

        self.repositorio.deletar(tenant)
        return {"mensagem": f"Tenant '{tenant.nome}' deletado com sucesso"}
