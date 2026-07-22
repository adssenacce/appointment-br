from sqlalchemy.orm import Session
from typing import Optional, Tuple, List
from jwt import InvalidTokenError

from src.modelos.usuario import Usuario, TenantUsuario
from src.repositorios.repositorio_usuario import RepositorioUsuario
from src.utilitarios.autenticacao import (
    hash_senha,
    verificar_senha,
    gerar_token_acesso,
    gerar_refresh_token,
    decodificar_token
)
from src.esquemas.usuario import UsuarioCriacao, UsuarioAtualizacao


class ServicoAutenticacao:
    """Serviço para operações de autenticação."""

    def __init__(self, sessao: Session):
        self.sessao = sessao
        self.repositorio = RepositorioUsuario(sessao)

    def registrar_usuario(self, dados: UsuarioCriacao) -> Tuple[Usuario, dict]:
        """Registra um novo usuário e retorna usuário + tokens."""
        # Verifica se email já existe
        usuario_existente = self.repositorio.buscar_por_email(dados.email)
        if usuario_existente:
            raise ValueError(f"Email {dados.email} já está em uso")

        # Cria usuário
        usuario = self.repositorio.criar_usuario(
            nome=dados.nome,
            email=dados.email,
            senha=dados.senha,
            administrador=dados.administrador
        )

        # Gera tokens
        tokens = self._gerar_tokens_usuario(usuario)

        return usuario, tokens

    def autenticar_usuario(self, email: str, senha: str) -> Tuple[Usuario, dict]:
        """Autentica usuário e retorna usuário + tokens."""
        # Busca usuário por email
        usuario = self.repositorio.buscar_por_email(email)
        if not usuario:
            raise ValueError("Email ou senha inválidos")

        # Verifica se usuário está ativo
        if not usuario.ativo:
            raise ValueError("Usuário inativo")

        # Verifica senha
        if not verificar_senha(senha, usuario.senha_hash):
            raise ValueError("Email ou senha inválidos")

        # Gera tokens
        tokens = self._gerar_tokens_usuario(usuario)

        return usuario, tokens

    def _gerar_tokens_usuario(self, usuario: Usuario) -> dict:
        """Gera access token e refresh token para o usuário."""
        dados_token = {
            "sub": str(usuario.id),
            "email": usuario.email,
            "nome": usuario.nome
        }

        access_token = gerar_token_acesso(dados_token)
        refresh_token = gerar_refresh_token(dados_token)

        # Calcula tempo de expiração em segundos
        from datetime import datetime, timedelta
        from src.configuracoes.definicoes import obter_configuracoes
        configuracoes = obter_configuracoes()
        expiracao_segundos = configuracoes.MINUTAS_EXPIRACAO_TOKEN * 60

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expiracao_segundos
        }

    def renovar_tokens(self, refresh_token: str) -> dict:
        """Renova tokens usando refresh token."""
        try:
            payload = decodificar_token(refresh_token, tipo_esperado="refresh")
        except InvalidTokenError as erro:
            raise ValueError(f"Refresh token inválido: {str(erro)}")

        usuario_id = int(payload.get("sub"))
        usuario = self.repositorio.buscar_por_id(usuario_id)

        if not usuario or not usuario.ativo:
            raise ValueError("Usuário não encontrado ou inativo")

        # Gera novos tokens
        return self._gerar_tokens_usuario(usuario)

    def obter_usuario_por_id(self, usuario_id: int) -> Optional[Usuario]:
        """Busca usuário por ID."""
        return self.repositorio.buscar_por_id(usuario_id)

    def obter_usuario_por_token(self, token: str) -> Usuario:
        """Obtém usuário a partir do token de acesso."""
        try:
            payload = decodificar_token(token, tipo_esperado="access")
        except InvalidTokenError as erro:
            raise ValueError(f"Token inválido: {str(erro)}")

        usuario_id = int(payload.get("sub"))
        usuario = self.repositorio.buscar_por_id(usuario_id)

        if not usuario:
            raise ValueError("Usuário não encontrado")

        if not usuario.ativo:
            raise ValueError("Usuário inativo")

        return usuario


class ServicoUsuario:
    """Serviço para operações de Usuário (CRUD)."""

    def __init__(self, sessao: Session):
        self.sessao = sessao
        self.repositorio = RepositorioUsuario(sessao)

    def criar_usuario(self, dados: UsuarioCriacao) -> Usuario:
        """Cria um novo usuário."""
        # Verifica se email já existe
        usuario_existente = self.repositorio.buscar_por_email(dados.email)
        if usuario_existente:
            raise ValueError(f"Email {dados.email} já está em uso")

        return self.repositorio.criar_usuario(
            nome=dados.nome,
            email=dados.email,
            senha=dados.senha,
            administrador=dados.administrador
        )

    def buscar_usuario(self, usuario_id: int) -> Optional[Usuario]:
        """Busca usuário por ID."""
        return self.repositorio.buscar_por_id(usuario_id)

    def listar_usuarios(self, ativo: Optional[bool] = None, 
                        limite: int = 100, deslocamento: int = 0) -> List[Usuario]:
        """Lista usuários com filtros."""
        return self.repositorio.listar_usuarios(ativo=ativo, limite=limite, deslocamento=deslocamento)

    def atualizar_usuario(self, usuario_id: int, dados: UsuarioAtualizacao) -> Usuario:
        """Atualiza usuário."""
        usuario = self.repositorio.buscar_por_id(usuario_id)
        if not usuario:
            raise ValueError(f"Usuário {usuario_id} não encontrado")

        senha_hash = None
        if dados.senha:
            senha_hash = hash_senha(dados.senha)

        return self.repositorio.atualizar_usuario(
            usuario=usuario,
            nome=dados.nome,
            email=dados.email,
            ativo=dados.ativo,
            administrador=dados.administrador,
            senha_hash=senha_hash
        )

    def deletar_usuario(self, usuario_id: int) -> bool:
        """Deleta usuário."""
        usuario = self.repositorio.buscar_por_id(usuario_id)
        if not usuario:
            raise ValueError(f"Usuário {usuario_id} não encontrado")

        return self.repositorio.deletar_usuario(usuario)

    def vincular_usuario_tenant(self, usuario_id: int, tenant_id: int, 
                                 administrador_tenant: bool = False) -> TenantUsuario:
        """Vincula usuário a tenant."""
        usuario = self.repositorio.buscar_por_id(usuario_id)
        if not usuario:
            raise ValueError(f"Usuário {usuario_id} não encontrado")

        return self.repositorio.vincular_usuario_tenant(
            usuario=usuario,
            tenant_id=tenant_id,
            administrador_tenant=administrador_tenant
        )

    def remover_vinculo_tenant(self, usuario_id: int, tenant_id: int) -> bool:
        """Remove vínculo entre usuário e tenant."""
        usuario = self.repositorio.buscar_por_id(usuario_id)
        if not usuario:
            raise ValueError(f"Usuário {usuario_id} não encontrado")

        return self.repositorio.remover_vinculo_usuario_tenant(usuario, tenant_id)

    def buscar_tenants_do_usuario(self, usuario_id: int) -> List[TenantUsuario]:
        """Busca tenants do usuário."""
        return self.repositorio.buscar_tenants_do_usuario(usuario_id)
