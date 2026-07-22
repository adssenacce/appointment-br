from sqlalchemy.orm import Session
from typing import Optional, List

from src.modelos.usuario import Usuario, TenantUsuario
from src.utilitarios.autenticacao import hash_senha


class RepositorioUsuario:
    """Repositório para operações de Usuário no banco de dados."""

    def __init__(self, sessao: Session):
        self.sessao = sessao

    def criar_usuario(self, nome: str, email: str, senha: str, 
                      administrador: bool = False) -> Usuario:
        """Cria um novo usuário no banco de dados."""
        senha_hash = hash_senha(senha)
        
        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=senha_hash,
            administrador=administrador
        )
        
        self.sessao.add(usuario)
        self.sessao.flush()  # Para obter o ID antes do commit
        
        return usuario

    def buscar_por_id(self, usuario_id: int) -> Optional[Usuario]:
        """Busca usuário por ID."""
        return self.sessao.query(Usuario).filter(Usuario.id == usuario_id).first()

    def buscar_por_email(self, email: str) -> Optional[Usuario]:
        """Busca usuário por email."""
        return self.sessao.query(Usuario).filter(Usuario.email == email).first()

    def listar_usuarios(self, ativo: Optional[bool] = None, 
                        limite: int = 100, deslocamento: int = 0) -> List[Usuario]:
        """Lista usuários com filtros opcionais."""
        consulta = self.sessao.query(Usuario)
        
        if ativo is not None:
            consulta = consulta.filter(Usuario.ativo == ativo)
        
        return consulta.offset(deslocamento).limit(limite).all()

    def atualizar_usuario(self, usuario: Usuario, 
                          nome: Optional[str] = None,
                          email: Optional[str] = None,
                          ativo: Optional[bool] = None,
                          administrador: Optional[bool] = None,
                          senha_hash: Optional[str] = None) -> Usuario:
        """Atualiza dados do usuário."""
        if nome is not None:
            usuario.nome = nome
        if email is not None:
            usuario.email = email
        if ativo is not None:
            usuario.ativo = ativo
        if administrador is not None:
            usuario.administrador = administrador
        if senha_hash is not None:
            usuario.senha_hash = senha_hash
        
        # A data_atualizacao é atualizada automaticamente pelo modelo
        self.sessao.flush()
        
        return usuario

    def deletar_usuario(self, usuario: Usuario) -> bool:
        """Deleta usuário do banco de dados."""
        self.sessao.delete(usuario)
        return True

    def vincular_usuario_tenant(self, usuario: Usuario, tenant_id: int, 
                                 administrador_tenant: bool = False) -> TenantUsuario:
        """Vincula usuário a um tenant."""
        from src.modelos.tenant import Tenant
        
        # Verifica se tenant existe
        tenant = self.sessao.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} não encontrado")
        
        # Verifica se já existe vínculo
        vinculo_existente = self.sessao.query(TenantUsuario).filter(
            TenantUsuario.usuario_id == usuario.id,
            TenantUsuario.tenant_id == tenant_id
        ).first()
        
        if vinculo_existente:
            raise ValueError(f"Usuário já está vinculado ao tenant {tenant_id}")
        
        vinculo = TenantUsuario(
            usuario_id=usuario.id,
            tenant_id=tenant_id,
            administrador_tenant=administrador_tenant
        )
        
        self.sessao.add(vinculo)
        self.sessao.flush()
        
        return vinculo

    def remover_vinculo_usuario_tenant(self, usuario: Usuario, tenant_id: int) -> bool:
        """Remove vínculo entre usuário e tenant."""
        vinculo = self.sessao.query(TenantUsuario).filter(
            TenantUsuario.usuario_id == usuario.id,
            TenantUsuario.tenant_id == tenant_id
        ).first()
        
        if vinculo:
            self.sessao.delete(vinculo)
            return True
        
        return False

    def buscar_tenants_do_usuario(self, usuario_id: int) -> List[TenantUsuario]:
        """Busca todos os tenants associados a um usuário."""
        return self.sessao.query(TenantUsuario).filter(
            TenantUsuario.usuario_id == usuario_id
        ).all()

    def buscar_usuario_no_tenant(self, usuario_id: int, tenant_id: int) -> Optional[TenantUsuario]:
        """Verifica se usuário pertence a um tenant específico."""
        return self.sessao.query(TenantUsuario).filter(
            TenantUsuario.usuario_id == usuario_id,
            TenantUsuario.tenant_id == tenant_id
        ).first()
