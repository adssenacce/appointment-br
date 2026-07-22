from pydantic_settings import BaseSettings
from functools import lru_cache


class Configuracoes(BaseSettings):
    """Configurações da aplicação."""

    URL_BANCO_DADOS: str = "postgresql://usuario_admin:senha_segura_123@localhost:5432/db_tenants"
    CHAVE_SECRETA_JWT: str = "sua_chave_secreta_muito_segura_aqui_mude_em_producao"
    ALGORITMO_JWT: str = "HS256"
    MINUTAS_EXPIRACAO_TOKEN: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def obter_configuracoes() -> Configuracoes:
    """Retorna as configurações em cache."""
    return Configuracoes()
