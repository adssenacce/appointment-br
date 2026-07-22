from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.configuracoes.banco_dados import criar_tabelas
from src.controladores.controlador_tenant import router as tenant_router


def criar_aplicacao() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""
    
    aplicacao = FastAPI(
        title="Sistema Multi-Tenant",
        description="API para gerenciamento de sistema multi-tenant com autenticação JWT e controle de acesso baseado em papéis.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Configurar CORS
    aplicacao.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Em produção, especifique os domínios permitidos
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Criar tabelas do banco de dados
    criar_tabelas()

    # Incluir routers
    aplicacao.include_router(tenant_router, prefix="/api/v1")

    @aplicacao.get("/", tags=["Root"])
    def root():
        """Endpoint raiz da API."""
        return {"mensagem": "Bem-vindo à API Multi-Tenant", "docs": "/docs"}

    @aplicacao.get("/health", tags=["Health"])
    def health_check():
        """Verifica se a API está saudável."""
        return {"status": "healthy"}

    return aplicacao


aplicacao = criar_aplicacao()
