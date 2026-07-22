from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from contextlib import contextmanager

from src.configuracoes.definicoes import obter_configuracoes

configuracoes = obter_configuracoes()

# Usar SQLite para desenvolvimento se PostgreSQL não estiver disponível
URL_BANCO_DADOS = "sqlite:///./tenants.db"  # SQLite para desenvolvimento
# URL_BANCO_DADOS = configuracoes.URL_BANCO_DADOS  # PostgreSQL para produção

engine = None
Base = declarative_base()


def get_engine():
    """Obtém ou cria o engine do banco de dados."""
    global engine
    if engine is None:
        engine = create_engine(
            URL_BANCO_DADOS,
            connect_args={"check_same_thread": False} if "sqlite" in URL_BANCO_DADOS else {},
            echo=False,
        )
    return engine


from contextlib import contextmanager


@contextmanager
def gerenciar_sessao():
    """Gera uma sessão de banco de dados para uso direto."""
    from sqlalchemy.orm import sessionmaker
    
    eng = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    sessao = SessionLocal()
    try:
        yield sessao
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    finally:
        sessao.close()


async def obter_sessao():
    """Dependency do FastAPI para obter sessão de banco de dados."""
    with gerenciar_sessao() as sessao:
        yield sessao


def criar_tabelas():
    """Cria todas as tabelas no banco de dados."""
    Base.metadata.create_all(bind=get_engine())
