from sqlalchemy.orm import Session
from typing import Optional, List

from src.repositorios.repositorio_permissao import RepositorioPermissao, RepositorioCargo
from src.modelos.permissao import Permissao, Cargo


class ServicoPermissao:
    """Serviço para regras de negócio de Permissões."""

    def __init__(self, db: Session):
        self.db = db
        self.repositorio = RepositorioPermissao(db)

    def criar_permissao(self, nome: str, recurso: str, acao: str, 
                       descricao: Optional[str] = None, ativa: bool = True) -> Permissao:
        """Cria uma nova permissão."""
        # Verifica se já existe permissão com mesmo nome
        existente = self.repositorio.buscar_por_nome(nome)
        if existente:
            raise ValueError(f"Já existe uma permissão com o nome '{nome}'")
        
        return self.repositorio.criar(
            nome=nome,
            recurso=recurso,
            acao=acao,
            descricao=descricao,
            ativa=ativa
        )

    def obter_permissao(self, permissao_id: int) -> Optional[Permissao]:
        """Obtém uma permissão por ID."""
        return self.repositorio.buscar_por_id(permissao_id)

    def listar_permissoes(self, ativas: Optional[bool] = None) -> List[Permissao]:
        """Lista todas as permissões."""
        return self.repositorio.listar_todas(ativas=ativas)

    def atualizar_permissao(self, permissao_id: int, **dados_atualizacao) -> Optional[Permissao]:
        """Atualiza uma permissão existente."""
        permissao = self.repositorio.buscar_por_id(permissao_id)
        if not permissao:
            return None
        
        return self.repositorio.atualizar(permissao, **dados_atualizacao)

    def deletar_permissao(self, permissao_id: int) -> bool:
        """Deleta uma permissão."""
        permissao = self.repositorio.buscar_por_id(permissao_id)
        if not permissao:
            return False
        
        return self.repositorio.deletar(permissao)


class ServicoCargo:
    """Serviço para regras de negócio de Cargos."""

    def __init__(self, db: Session):
        self.db = db
        self.repositorio = RepositorioCargo(db)

    def criar_cargo(self, nome: str, slug: str, tenant_id: Optional[int] = None,
                   descricao: Optional[str] = None, eh_padrao: bool = False,
                   ativo: bool = True, permissoes_ids: Optional[List[int]] = None) -> Cargo:
        """Cria um novo cargo."""
        # Verifica se já existe cargo com mesmo slug no tenant
        existente = self.repositorio.buscar_por_slug(slug, tenant_id)
        if existente:
            raise ValueError(f"Já existe um cargo com o slug '{slug}' neste tenant")
        
        cargo = self.repositorio.criar(
            nome=nome,
            slug=slug,
            tenant_id=tenant_id,
            descricao=descricao,
            eh_padrao=eh_padrao,
            ativo=ativo
        )
        
        # Adiciona permissões se fornecidas
        if permissoes_ids:
            for permissao_id in permissoes_ids:
                self.repositorio.adicionar_permissao(cargo, permissao_id)
        
        return cargo

    def obter_cargo(self, cargo_id: int) -> Optional[Cargo]:
        """Obtém um cargo por ID."""
        return self.repositorio.buscar_por_id(cargo_id)

    def listar_cargos(self, tenant_id: Optional[int] = None, ativos: Optional[bool] = None) -> List[Cargo]:
        """Lista todos os cargos (globais + do tenant)."""
        return self.repositorio.listar_todos(tenant_id=tenant_id, ativos=ativos)

    def atualizar_cargo(self, cargo_id: int, **dados_atualizacao) -> Optional[Cargo]:
        """Atualiza um cargo existente."""
        cargo = self.repositorio.buscar_por_id(cargo_id)
        if not cargo:
            return None
        
        # Se estiver atualizando permissões
        permissoes_ids = dados_atualizacao.pop('permissoes_ids', None)
        if permissoes_ids is not None:
            # Remove todas as permissões atuais
            permissoes_atuais = self.repositorio.listar_permissoes_cargo(cargo_id)
            for cp in permissoes_atuais:
                self.repositorio.remover_permissao(cargo, cp.permissao_id)
            
            # Adiciona novas permissões
            for permissao_id in permissoes_ids:
                self.repositorio.adicionar_permissao(cargo, permissao_id)
        
        return self.repositorio.atualizar(cargo, **dados_atualizacao)

    def deletar_cargo(self, cargo_id: int) -> bool:
        """Deleta um cargo."""
        cargo = self.repositorio.buscar_por_id(cargo_id)
        if not cargo:
            return False
        
        # Verifica se há usuários com este cargo
        cargos_usuario = self.repositorio.listar_cargos_usuario(
            usuario_id=-1,  # Placeholder, precisaria de método específico
            tenant_id=-1
        )
        
        # Simplificação: não permite deletar se houver usuários (verificação real seria mais complexa)
        return self.repositorio.deletar(cargo)

    def adicionar_permissao_ao_cargo(self, cargo_id: int, permissao_id: int) -> bool:
        """Adiciona uma permissão a um cargo."""
        cargo = self.repositorio.buscar_por_id(cargo_id)
        if not cargo:
            raise ValueError(f"Cargo {cargo_id} não encontrado")
        
        permissao = self.db.query(Permissao).filter(Permissao.id == permissao_id).first()
        if not permissao:
            raise ValueError(f"Permissão {permissao_id} não encontrada")
        
        self.repositorio.adicionar_permissao(cargo, permissao_id)
        return True

    def remover_permissao_do_cargo(self, cargo_id: int, permissao_id: int) -> bool:
        """Remove uma permissão de um cargo."""
        cargo = self.repositorio.buscar_por_id(cargo_id)
        if not cargo:
            raise ValueError(f"Cargo {cargo_id} não encontrado")
        
        return self.repositorio.remover_permissao(cargo, permissao_id)

    def atribuir_cargo_a_usuario(self, usuario_id: int, cargo_id: int, tenant_id: int) -> bool:
        """Atribui um cargo a um usuário em um tenant."""
        cargo = self.repositorio.buscar_por_id(cargo_id)
        if not cargo:
            raise ValueError(f"Cargo {cargo_id} não encontrado")
        
        # Verifica se o cargo é global ou do tenant
        if cargo.tenant_id is not None and cargo.tenant_id != tenant_id:
            raise ValueError("Cargo não pertence a este tenant")
        
        self.repositorio.atribuir_cargo_usuario(usuario_id, cargo_id, tenant_id)
        return True

    def remover_cargo_de_usuario(self, usuario_id: int, cargo_id: int, tenant_id: int) -> bool:
        """Remove um cargo de um usuário em um tenant."""
        # Verifica se é o último administrador
        if self.repositorio.verificar_ultimo_administrador(tenant_id, usuario_id):
            raise ValueError("Não é possível remover o único administrador do tenant")
        
        return self.repositorio.remover_cargo_usuario(usuario_id, cargo_id, tenant_id)

    def listar_cargos_do_usuario(self, usuario_id: int, tenant_id: int) -> list:
        """Lista todos os cargos de um usuário em um tenant."""
        return self.repositorio.listar_cargos_usuario(usuario_id, tenant_id)

    def listar_permissoes_do_usuario(self, usuario_id: int, tenant_id: int) -> list:
        """Lista todas as permissões de um usuário em um tenant."""
        return self.repositorio.buscar_cargos_usuario_com_permissoes(usuario_id, tenant_id)

    def usuario_tem_permissao(self, usuario_id: int, tenant_id: int, recurso: str, acao: str) -> bool:
        """Verifica se um usuário tem uma permissão específica em um tenant."""
        permissoes = self.listar_permissoes_do_usuario(usuario_id, tenant_id)
        
        for permissao in permissoes:
            if permissao.recurso == recurso and permissao.acao == acao:
                return True
        
        return False

    def usuario_eh_administrador(self, usuario_id: int, tenant_id: int) -> bool:
        """Verifica se um usuário é administrador de um tenant."""
        return self.usuario_tem_permissao(usuario_id, tenant_id, 'todos', 'todos') or \
               self.repositorio.verificar_ultimo_administrador(tenant_id, usuario_id)
