from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional

from src.configuracoes.definicoes import obter_configuracoes
from src.configuracoes.banco_dados import obter_sessao_db
from src.modelos.usuario import Usuario


configuracoes = obter_configuracoes()
seguranca_http = HTTPBearer(auto_error=False)


def hash_senha(senha: str) -> str:
    """Gera hash da senha usando bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), salt)
    return senha_hash.decode('utf-8')


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))


def gerar_token_acesso(dados: dict, minutos_expiracao: Optional[int] = None) -> str:
    """Gera token de acesso JWT."""
    tempo_expiracao = minutos_expiracao or configuracoes.MINUTAS_EXPIRACAO_TOKEN
    expiracao = datetime.utcnow() + timedelta(minutes=tempo_expiracao)

    dados_para_codificar = dados.copy()
    dados_para_codificar.update({
        "exp": expiracao,
        "iat": datetime.utcnow(),
        "tipo": "access"
    })

    token = jwt.encode(
        dados_para_codificar,
        configuracoes.CHAVE_SECRETA_JWT,
        algorithm=configuracoes.ALGORITMO_JWT
    )

    return token


def gerar_refresh_token(dados: dict, dias_expiracao: int = 7) -> str:
    """Gera refresh token JWT."""
    expiracao = datetime.utcnow() + timedelta(days=dias_expiracao)

    dados_para_codificar = dados.copy()
    dados_para_codificar.update({
        "exp": expiracao,
        "iat": datetime.utcnow(),
        "tipo": "refresh"
    })

    token = jwt.encode(
        dados_para_codificar,
        configuracoes.CHAVE_SECRETA_JWT,
        algorithm=configuracoes.ALGORITMO_JWT
    )

    return token


def decodificar_token(token: str, tipo_esperado: Optional[str] = None) -> dict:
    """Decodifica e valida token JWT."""
    try:
        payload = jwt.decode(
            token,
            configuracoes.CHAVE_SECRETA_JWT,
            algorithms=[configuracoes.ALGORITMO_JWT]
        )

        if tipo_esperado and payload.get("tipo") != tipo_esperado:
            raise jwt.InvalidTokenError(f"Tipo de token inválido. Esperado: {tipo_esperado}")

        return payload

    except jwt.ExpiredSignatureError:
        raise jwt.InvalidTokenError("Token expirado")
    except jwt.InvalidTokenError as erro:
        raise jwt.InvalidTokenError(f"Token inválido: {str(erro)}")


def validar_tokens(access_token: str, refresh_token: str) -> tuple[dict, dict]:
    """Valida ambos os tokens e retorna os payloads."""
    access_payload = decodificar_token(access_token, tipo_esperado="access")
    refresh_payload = decodificar_token(refresh_token, tipo_esperado="refresh")

    # Verifica se ambos pertencem ao mesmo usuário
    if access_payload.get("sub") != refresh_payload.get("sub"):
        raise jwt.InvalidTokenError("Tokens não correspondem ao mesmo usuário")

    return access_payload, refresh_payload


async def obter_usuario_atual(
    credenciais: HTTPAuthorizationCredentials = Depends(seguranca_http),
    db: Session = Depends(obter_sessao_db)
) -> Usuario:
    """
    Dependência do FastAPI para obter o usuário atual a partir do token JWT.
    
    Levanta HTTPException 401 se o token for inválido ou usuário não existir.
    """
    if credenciais is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais de autenticação não fornecidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credenciais.credentials
    
    try:
        payload = decodificar_token(token, tipo_esperado="access")
        usuario_id = payload.get("sub")
        
        if usuario_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: ID do usuário não encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        usuario = db.query(Usuario).filter(Usuario.id == int(usuario_id)).first()
        
        if usuario is None or not usuario.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado ou inativo",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return usuario
        
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
