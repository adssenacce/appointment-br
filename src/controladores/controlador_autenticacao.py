from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from jwt import InvalidTokenError

from src.configuracoes.banco_dados import obter_sessao
from src.esquemas.usuario import (
    UsuarioCriacao,
    UsuarioResposta,
    UsuarioAtualizacao,
    LoginRequisicao,
    TokenResposta,
    RefreshTokenRequisicao,
    UsuarioComTenantsResposta
)
from src.servicos.servico_autenticacao import ServicoAutenticacao, ServicoUsuario
from src.utilitarios.autenticacao import decodificar_token

router = APIRouter(prefix="/api/v1", tags=["Autenticação e Usuários"])

# Configuração do OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


def _obter_servico_autenticacao(sessao: Session = Depends(obter_sessao)) -> ServicoAutenticacao:
    """Dependency para obter serviço de autenticação."""
    return ServicoAutenticacao(sessao)


def _obter_servico_usuario(sessao: Session = Depends(obter_sessao)) -> ServicoUsuario:
    """Dependency para obter serviço de usuário."""
    return ServicoUsuario(sessao)


async def obter_usuario_atual(
    token: str = Depends(oauth2_scheme),
    servico_autenticacao: ServicoAutenticacao = Depends(_obter_servico_autenticacao)
):
    """Dependency para obter usuário atual a partir do token JWT."""
    try:
        usuario = servico_autenticacao.obter_usuario_por_token(token)
        return usuario
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(erro),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/registro", response_model=dict, summary="Registrar novo usuário")
async def registrar_usuario(
    dados: UsuarioCriacao,
    servico_autenticacao: ServicoAutenticacao = Depends(_obter_servico_autenticacao)
):
    """
    Registra um novo usuário no sistema.
    
    - **nome**: Nome do usuário
    - **email**: Email único
    - **senha**: Senha (mínimo 6 caracteres)
    - **administrador**: Se é administrador global (opcional)
    
    Retorna o usuário criado + tokens JWT.
    """
    try:
        usuario, tokens = servico_autenticacao.registrar_usuario(dados)
        return {
            "usuario": UsuarioResposta.model_validate(usuario),
            **tokens
        }
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.post("/login", response_model=TokenResposta, summary="Login de usuário")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    servico_autenticacao: ServicoAutenticacao = Depends(_obter_servico_autenticacao)
):
    """
    Autentica usuário e retorna tokens JWT.
    
    Usa OAuth2 password flow (username=email, password=senha).
    """
    try:
        usuario, tokens = servico_autenticacao.autenticar_usuario(
            email=form_data.username,
            senha=form_data.password
        )
        return TokenResposta(**tokens)
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(erro),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=TokenResposta, summary="Renovar tokens")
async def renovar_token(
    dados: RefreshTokenRequisicao,
    servico_autenticacao: ServicoAutenticacao = Depends(_obter_servico_autenticacao)
):
    """
    Renova os tokens usando refresh token.
    
    O access token resultante terá nova expiração.
    """
    try:
        tokens = servico_autenticacao.renovar_tokens(dados.refresh_token)
        return TokenResposta(**tokens)
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(erro),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UsuarioComTenantsResposta, summary="Obter usuário atual")
async def obter_meu_usuario(
    usuario_atual = Depends(obter_usuario_atual),
    servico_usuario: ServicoUsuario = Depends(_obter_servico_usuario)
):
    """
    Obtém informações do usuário autenticado.
    
    Requer token JWT válido no header Authorization.
    """
    tenants_vinculos = servico_usuario.buscar_tenants_do_usuario(usuario_atual.id)
    
    tenants_lista = [
        {
            "tenant_id": vinculo.tenant_id,
            "administrador_tenant": vinculo.administrador_tenant,
            "data_vinculo": vinculo.data_vinculo
        }
        for vinculo in tenants_vinculos
    ]
    
    return UsuarioComTenantsResposta(
        id=usuario_atual.id,
        nome=usuario_atual.nome,
        email=usuario_atual.email,
        ativo=usuario_atual.ativo,
        administrador=usuario_atual.administrador,
        data_criacao=usuario_atual.data_criacao,
        data_atualizacao=usuario_atual.data_atualizacao,
        tenants=tenants_lista
    )


@router.post("/logout", summary="Logout (client-side)")
async def logout():
    """
    Logout do usuário.
    
    Como usamos JWT stateless, o logout é feito apenas no client-side
    (removendo o token do armazenamento local). Este endpoint existe
    apenas para documentação e possíveis logs futuros.
    """
    return {"mensagem": "Logout realizado. Remova o token do seu client."}


# ==================== CRUD de Usuários ====================

@router.get("/usuarios", response_model=List[UsuarioResposta], summary="Listar usuários")
async def listar_usuarios(
    ativo: bool = None,
    limite: int = 100,
    deslocamento: int = 0,
    usuario_atual = Depends(obter_usuario_atual),
    servico_usuario: ServicoUsuario = Depends(_obter_servico_usuario)
):
    """
    Lista todos os usuários com filtros opcionais.
    
    Requer autenticação. Apenas administradores globais podem listar todos.
    """
    # Verifica se é administrador global
    if not usuario_atual.administrador:
        # Usuários não-admin podem ver apenas a si mesmos
        if usuario_atual.ativo == ativo or ativo is None:
            return [UsuarioResposta.model_validate(usuario_atual)]
        return []
    
    return servico_usuario.listar_usuarios(ativo=ativo, limite=limite, deslocamento=deslocamento)


@router.get("/usuarios/{usuario_id}", response_model=UsuarioResposta, summary="Buscar usuário por ID")
async def buscar_usuario(
    usuario_id: int,
    usuario_atual = Depends(obter_usuario_atual),
    servico_usuario: ServicoUsuario = Depends(_obter_servico_usuario)
):
    """
    Busca um usuário específico por ID.
    
    Requer autenticação. Usuários só podem ver seus próprios dados
    ou outros usuários se forem administradores.
    """
    if usuario_id != usuario_atual.id and not usuario_atual.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem ver outros usuários."
        )
    
    usuario = servico_usuario.buscar_usuario(usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário {usuario_id} não encontrado"
        )
    
    return UsuarioResposta.model_validate(usuario)


@router.put("/usuarios/{usuario_id}", response_model=UsuarioResposta, summary="Atualizar usuário")
async def atualizar_usuario(
    usuario_id: int,
    dados: UsuarioAtualizacao,
    usuario_atual = Depends(obter_usuario_atual),
    servico_usuario: ServicoUsuario = Depends(_obter_servico_usuario)
):
    """
    Atualiza dados de um usuário.
    
    Usuários podem atualizar seus próprios dados.
    Administradores podem atualizar qualquer usuário.
    """
    if usuario_id != usuario_atual.id and not usuario_atual.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem editar outros usuários."
        )
    
    # Impede que usuário comum altere seu próprio status de administrador
    if not usuario_atual.administrador and dados.administrador is not None:
        dados.administrador = None
    
    try:
        usuario = servico_usuario.atualizar_usuario(usuario_id, dados)
        return UsuarioResposta.model_validate(usuario)
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.delete("/usuarios/{usuario_id}", summary="Deletar usuário")
async def deletar_usuario(
    usuario_id: int,
    usuario_atual = Depends(obter_usuario_atual),
    servico_usuario: ServicoUsuario = Depends(_obter_servico_usuario)
):
    """
    Deleta um usuário do sistema.
    
    Requer ser administrador global.
    Usuário não pode deletar a si mesmo.
    """
    if not usuario_atual.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem deletar usuários."
        )
    
    if usuario_id == usuario_atual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário não pode deletar a si mesmo"
        )
    
    try:
        servico_usuario.deletar_usuario(usuario_id)
        return {"mensagem": f"Usuário {usuario_id} deletado com sucesso"}
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(erro)
        )
