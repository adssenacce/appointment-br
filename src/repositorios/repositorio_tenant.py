from sqlalchemy.orm import Session
from typing import Optional, List

from src.modelos.tenant import Tenant


class RepositorioTenant:
    """Repositório para operações de Tenant no banco de dados."""

    def __init__(self, sessao: Session):
        self.sessao = sessao

    def criar(self, nome: str, slug: str) -> Tenant:
        """Cria um novo tenant."""
        tenant = Tenant(nome=nome, slug=slug)
        self.sessao.add(tenant)
        self.sessao.commit()
        self.sessao.refresh(tenant)
        return tenant

    def buscar_por_id(self, tenant_id: int) -> Optional[Tenant]:
        """Busca um tenant pelo ID."""
        return self.sessao.query(Tenant).filter(Tenant.id == tenant_id).first()

    def buscar_por_slug(self, slug: str) -> Optional[Tenant]:
        """Busca um tenant pelo slug."""
        return self.sessao.query(Tenant).filter(Tenant.slug == slug).first()

    def listar_todos(self, ativo: Optional[bool] = None) -> List[Tenant]:
        """Lista todos os tenants, opcionalmente filtrando por status."""
        consulta = self.sessao.query(Tenant)
        if ativo is not None:
            consulta = consulta.filter(Tenant.ativo == ativo)
        return consulta.order_by(Tenant.nome).all()

    def atualizar(self, tenant: Tenant, **dados_atualizacao) -> Tenant:
        """Atualiza um tenant existente."""
        for chave, valor in dados_atualizacao.items():
            setattr(tenant, chave, valor)
        self.sessao.commit()
        self.sessao.refresh(tenant)
        return tenant

    def deletar(self, tenant: Tenant) -> bool:
        """Deleta um tenant."""
        self.sessao.delete(tenant)
        self.sessao.commit()
        return True

    def existe_slug(self, slug: str, excluir_id: Optional[int] = None) -> bool:
        """Verifica se um slug já existe."""
        consulta = self.sessao.query(Tenant).filter(Tenant.slug == slug)
        if excluir_id:
            consulta = consulta.filter(Tenant.id != excluir_id)
        return consulta.first() is not None
