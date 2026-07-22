from sqlalchemy.orm import Session
from typing import Optional

from src.modelos.permissao import Permissao, Cargo, CargoPermissao, UsuarioCargoTenant


class RepositorioPermissao:
    """Repositório para operações de Permissão no banco de dados."""

    def __init__(self, db: Session):
        self.db = db

    def criar(self, nome: str, recurso: str, acao: str, descricao: Optional[str] = None, ativa: bool = True) -> Permissao:
        """Cria uma nova permissão."""
        permissao = Permissao(
            nome=nome,
            recurso=recurso,
            acao=acao,
            descricao=descricao,
            ativa=ativa
        )
        self.db.add(permissao)
        self.db.commit()
        self.db.refresh(permissao)
        return permissao

    def buscar_por_id(self, permissao_id: int) -> Optional[Permissao]:
        """Busca permissão por ID."""
        return self.db.query(Permissao).filter(Permissao.id == permissao_id).first()

    def buscar_por_nome(self, nome: str) -> Optional[Permissao]:
        """Busca permissão por nome."""
        return self.db.query(Permissao).filter(Permissao.nome == nome).first()

    def listar_todas(self, ativas: Optional[bool] = None) -> list[Permissao]:
        """Lista todas as permissões, opcionalmente filtrando por status."""
        consulta = self.db.query(Permissao)
        if ativas is not None:
            consulta = consulta.filter(Permissao.ativa == ativas)
        return consulta.order_by(Permissao.nome).all()

    def atualizar(self, permissao: Permissao, **dados_atualizacao) -> Permissao:
        """Atualiza uma permissão existente."""
        for campo, valor in dados_atualizacao.items():
            if hasattr(permissao, campo):
                setattr(permissao, campo, valor)
        self.db.commit()
        self.db.refresh(permissao)
        return permissao

    def deletar(self, permissao: Permissao) -> bool:
        """Deleta uma permissão."""
        self.db.delete(permissao)
        self.db.commit()
        return True

    def buscar_por_recurso_acao(self, recurso: str, acao: str) -> Optional[Permissao]:
        """Busca permissão por recurso e ação."""
        return self.db.query(Permissao).filter(
            Permissao.recurso == recurso,
            Permissao.acao == acao,
            Permissao.ativa == True
        ).first()


class RepositorioCargo:
    """Repositório para operações de Cargo no banco de dados."""

    def __init__(self, db: Session):
        self.db = db

    def criar(self, nome: str, slug: str, tenant_id: Optional[int] = None, 
              descricao: Optional[str] = None, eh_padrao: bool = False, ativo: bool = True) -> Cargo:
        """Cria um novo cargo."""
        cargo = Cargo(
            nome=nome,
            slug=slug,
            tenant_id=tenant_id,
            descricao=descricao,
            eh_padrao=eh_padrao,
            ativo=ativo
        )
        self.db.add(cargo)
        self.db.commit()
        self.db.refresh(cargo)
        return cargo

    def buscar_por_id(self, cargo_id: int) -> Optional[Cargo]:
        """Busca cargo por ID."""
        return self.db.query(Cargo).filter(Cargo.id == cargo_id).first()

    def buscar_por_slug(self, slug: str, tenant_id: Optional[int] = None) -> Optional[Cargo]:
        """Busca cargo por slug (considerando tenant)."""
        if tenant_id is None:
            return self.db.query(Cargo).filter(Cargo.slug == slug, Cargo.tenant_id.is_(None)).first()
        return self.db.query(Cargo).filter(
            Cargo.slug == slug,
            Cargo.tenant_id == tenant_id
        ).first()

    def listar_todos(self, tenant_id: Optional[int] = None, ativos: Optional[bool] = None) -> list[Cargo]:
        """Lista todos os cargos, opcionalmente filtrando por tenant e status."""
        consulta = self.db.query(Cargo)
        
        # Filtra por tenant (NULL = globais, ou específico)
        if tenant_id is not None:
            consulta = consulta.filter((Cargo.tenant_id == tenant_id) | (Cargo.tenant_id.is_(None)))
        
        if ativos is not None:
            consulta = consulta.filter(Cargo.ativo == ativos)
        
        return consulta.order_by(Cargo.nome).all()

    def atualizar(self, cargo: Cargo, **dados_atualizacao) -> Cargo:
        """Atualiza um cargo existente."""
        for campo, valor in dados_atualizacao.items():
            if hasattr(cargo, campo):
                setattr(cargo, campo, valor)
        self.db.commit()
        self.db.refresh(cargo)
        return cargo

    def deletar(self, cargo: Cargo) -> bool:
        """Deleta um cargo."""
        self.db.delete(cargo)
        self.db.commit()
        return True

    def adicionar_permissao(self, cargo: Cargo, permissao_id: int) -> CargoPermissao:
        """Adiciona uma permissão a um cargo."""
        # Verifica se já existe
        existente = self.db.query(CargoPermissao).filter(
            CargoPermissao.cargo_id == cargo.id,
            CargoPermissao.permissao_id == permissao_id
        ).first()
        
        if existente:
            return existente
        
        cargo_permissao = CargoPermissao(cargo_id=cargo.id, permissao_id=permissao_id)
        self.db.add(cargo_permissao)
        self.db.commit()
        self.db.refresh(cargo_permissao)
        return cargo_permissao

    def remover_permissao(self, cargo: Cargo, permissao_id: int) -> bool:
        """Remove uma permissão de um cargo."""
        cargo_permissao = self.db.query(CargoPermissao).filter(
            CargoPermissao.cargo_id == cargo.id,
            CargoPermissao.permissao_id == permissao_id
        ).first()
        
        if cargo_permissao:
            self.db.delete(cargo_permissao)
            self.db.commit()
            return True
        return False

    def listar_permissoes_cargo(self, cargo_id: int) -> list[CargoPermissao]:
        """Lista todas as permissões de um cargo."""
        return self.db.query(CargoPermissao).filter(CargoPermissao.cargo_id == cargo_id).all()

    def atribuir_cargo_usuario(self, usuario_id: int, cargo_id: int, tenant_id: int) -> UsuarioCargoTenant:
        """Atribui um cargo a um usuário em um tenant."""
        # Verifica se já existe
        existente = self.db.query(UsuarioCargoTenant).filter(
            UsuarioCargoTenant.usuario_id == usuario_id,
            UsuarioCargoTenant.cargo_id == cargo_id,
            UsuarioCargoTenant.tenant_id == tenant_id
        ).first()
        
        if existente:
            return existente
        
        usuario_cargo = UsuarioCargoTenant(
            usuario_id=usuario_id,
            cargo_id=cargo_id,
            tenant_id=tenant_id
        )
        self.db.add(usuario_cargo)
        self.db.commit()
        self.db.refresh(usuario_cargo)
        return usuario_cargo

    def remover_cargo_usuario(self, usuario_id: int, cargo_id: int, tenant_id: int) -> bool:
        """Remove um cargo de um usuário em um tenant."""
        usuario_cargo = self.db.query(UsuarioCargoTenant).filter(
            UsuarioCargoTenant.usuario_id == usuario_id,
            UsuarioCargoTenant.cargo_id == cargo_id,
            UsuarioCargoTenant.tenant_id == tenant_id
        ).first()
        
        if usuario_cargo:
            self.db.delete(usuario_cargo)
            self.db.commit()
            return True
        return False

    def listar_cargos_usuario(self, usuario_id: int, tenant_id: int) -> list[UsuarioCargoTenant]:
        """Lista todos os cargos de um usuário em um tenant."""
        return self.db.query(UsuarioCargoTenant).filter(
            UsuarioCargoTenant.usuario_id == usuario_id,
            UsuarioCargoTenant.tenant_id == tenant_id
        ).all()

    def buscar_cargos_usuario_com_permissoes(self, usuario_id: int, tenant_id: int) -> list[Permissao]:
        """Busca todas as permissões de um usuário em um tenant através dos seus cargos."""
        # Subquery para obter permissões dos cargos do usuário
        permissoes = self.db.query(Permissao).join(CargoPermissao).join(UsuarioCargoTenant).filter(
            UsuarioCargoTenant.usuario_id == usuario_id,
            UsuarioCargoTenant.tenant_id == tenant_id,
            Permissao.ativa == True
        ).distinct().all()
        
        return permissoes

    def verificar_ultimo_administrador(self, tenant_id: int, usuario_id: int) -> bool:
        """Verifica se o usuário é o único administrador do tenant."""
        # Busca cargo de administrador do tenant
        cargo_admin = self.db.query(Cargo).filter(
            Cargo.slug == 'administrador',
            (Cargo.tenant_id == tenant_id) | (Cargo.tenant_id.is_(None))
        ).first()
        
        if not cargo_admin:
            return False
        
        # Conta quantos usuários têm este cargo no tenant
        count = self.db.query(UsuarioCargoTenant).filter(
            UsuarioCargoTenant.cargo_id == cargo_admin.id,
            UsuarioCargoTenant.tenant_id == tenant_id
        ).count()
        
        return count == 1
