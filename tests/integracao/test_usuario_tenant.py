"""Testes de integração para o módulo de Usuários por Tenant."""

import pytest
import os

# Configurar banco de dados de teste antes de importar a aplicação
os.environ["DATABASE_URL"] = "sqlite:///./teste_banco.db"

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.principal import aplicacao
from src.configuracoes.banco_dados import criar_tabelas, obter_sessao, engine, get_engine, Base
from src.modelos.tenant import Tenant
from src.modelos.usuario import Usuario, TenantUsuario
from src.utilitarios.autenticacao import hash_senha


@pytest.fixture(scope="function")
def setup_banco_dados():
    """Configura o banco de dados para os testes."""
    # Recria as tabelas
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Limpa o banco após cada teste
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sessao_db(setup_banco_dados):
    """Cria uma sessão de banco de dados para os testes."""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    sessao = SessionLocal()
    yield sessao
    sessao.close()


@pytest.fixture
def cliente():
    """Cria um cliente de teste."""
    return TestClient(aplicacao)


@pytest.fixture
def tenant_exemplo(setup_banco_dados, sessao_db):
    """Cria um tenant de exemplo."""
    tenant = Tenant(nome="Empresa Teste", slug="empresa-teste")
    sessao_db.add(tenant)
    sessao_db.commit()
    sessao_db.refresh(tenant)
    return tenant


@pytest.fixture
def usuario_admin_global(setup_banco_dados, sessao_db):
    """Cria um usuário administrador global."""
    usuario = Usuario(
        nome="Admin Global",
        email="admin@sistema.com",
        senha_hash=hash_senha("senha123"),
        administrador=True,
        ativo=True
    )
    sessao_db.add(usuario)
    sessao_db.commit()
    sessao_db.refresh(usuario)
    return usuario


@pytest.fixture
def usuario_comum(setup_banco_dados, sessao_db):
    """Cria um usuário comum."""
    usuario = Usuario(
        nome="Usuário Comum",
        email="usuario@exemplo.com",
        senha_hash=hash_senha("senha123"),
        administrador=False,
        ativo=True
    )
    sessao_db.add(usuario)
    sessao_db.commit()
    sessao_db.refresh(usuario)
    return usuario


@pytest.fixture
def usuario_admin_tenant(setup_banco_dados, sessao_db, tenant_exemplo):
    """Cria um usuário e o vincula como administrador ao tenant."""
    usuario = Usuario(
        nome="Admin do Tenant",
        email="admin@tenant.com",
        senha_hash=hash_senha("senha123"),
        administrador=False,
        ativo=True
    )
    sessao_db.add(usuario)
    sessao_db.commit()
    sessao_db.refresh(usuario)
    
    # Vincula ao tenant como administrador
    vinculo = TenantUsuario(
        usuario_id=usuario.id,
        tenant_id=tenant_exemplo.id,
        administrador_tenant=True
    )
    sessao_db.add(vinculo)
    sessao_db.commit()
    
    return usuario


@pytest.fixture
def usuario_vinculado_tenant(setup_banco_dados, sessao_db, tenant_exemplo):
    """Cria um usuário e o vincula ao tenant (não admin)."""
    usuario = Usuario(
        nome="Usuário do Tenant",
        email="user@tenant.com",
        senha_hash=hash_senha("senha123"),
        administrador=False,
        ativo=True
    )
    sessao_db.add(usuario)
    sessao_db.commit()
    sessao_db.refresh(usuario)
    
    # Vincula ao tenant
    vinculo = TenantUsuario(
        usuario_id=usuario.id,
        tenant_id=tenant_exemplo.id,
        administrador_tenant=False
    )
    sessao_db.add(vinculo)
    sessao_db.commit()
    
    return usuario


@pytest.fixture
def token_acesso(cliente, usuario_admin_global):
    """Obtém um token de acesso para o administrador global."""
    resposta = cliente.post(
        "/api/v1/login",
        data={"username": usuario_admin_global.email, "password": "senha123"}
    )
    return resposta.json()["access_token"]


@pytest.fixture
def token_admin_tenant(cliente, usuario_admin_tenant):
    """Obtém um token de acesso para o admin do tenant."""
    resposta = cliente.post(
        "/api/v1/login",
        data={"username": usuario_admin_tenant.email, "password": "senha123"}
    )
    return resposta.json()["access_token"]


@pytest.fixture
def token_usuario_comum(cliente, usuario_vinculado_tenant):
    """Obtém um token de acesso para o usuário comum do tenant."""
    resposta = cliente.post(
        "/api/v1/login",
        data={"username": usuario_vinculado_tenant.email, "password": "senha123"}
    )
    return resposta.json()["access_token"]


# ==================== TESTES PARA LISTAR USUÁRIOS DO TENANT ====================

def test_listar_usuarios_tenant_admin_global(
    cliente, tenant_exemplo, usuario_admin_tenant, 
    usuario_vinculado_tenant, token_acesso
):
    """Testa listar usuários do tenant como admin global."""
    resposta = cliente.get(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios",
        headers={"Authorization": f"Bearer {token_acesso}"}
    )
    
    assert resposta.status_code == 200
    dados = resposta.json()
    assert len(dados) >= 1  # Pelo menos o admin do tenant


def test_listar_usuarios_tenant_admin_tenant(
    cliente, tenant_exemplo, usuario_vinculado_tenant, token_admin_tenant
):
    """Testa listar usuários do tenant como admin do tenant."""
    resposta = cliente.get(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios",
        headers={"Authorization": f"Bearer {token_admin_tenant}"}
    )
    
    assert resposta.status_code == 200
    dados = resposta.json()
    # Admin do tenant deve conseguir ver todos os usuários do tenant
    assert len(dados) >= 1


def test_listar_usuarios_tenant_usuario_comum(
    cliente, tenant_exemplo, token_usuario_comum
):
    """Testa que usuário comum só vê a si mesmo."""
    resposta = cliente.get(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios",
        headers={"Authorization": f"Bearer {token_usuario_comum}"}
    )
    
    assert resposta.status_code == 200
    dados = resposta.json()
    # Usuário comum só deve ver a si mesmo
    assert len(dados) == 1
    assert dados[0]["email"] == "user@tenant.com"


def test_listar_usuarios_tenant_sem_autenticacao(cliente, tenant_exemplo):
    """Testa que não é possível listar usuários sem autenticação."""
    resposta = cliente.get(f"/api/v1/tenants/{tenant_exemplo.id}/usuarios")
    
    assert resposta.status_code == 401


def test_listar_usuarios_tenant_nao_pertence(cliente, tenant_exemplo, usuario_comum, token_acesso):
    """Testa que usuário de outro tenant não pode listar usuários."""
    # Cria token para usuário que não pertence ao tenant
    resposta_login = cliente.post(
        "/api/v1/login",
        data={"username": usuario_comum.email, "password": "senha123"}
    )
    token = resposta_login.json()["access_token"]
    
    resposta = cliente.get(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert resposta.status_code == 403


# ==================== TESTES PARA ADICIONAR USUÁRIO AO TENANT ====================

def test_adicionar_usuario_a_tenant_admin_global(
    cliente, tenant_exemplo, usuario_comum, token_acesso
):
    """Testa adicionar usuário a tenant como admin global."""
    resposta = cliente.post(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_comum.id}",
        headers={"Authorization": f"Bearer {token_acesso}"},
        json={"tenant_id": tenant_exemplo.id, "administrador_tenant": False}
    )
    
    assert resposta.status_code == 200
    dados = resposta.json()
    assert "adicionado ao tenant" in dados["mensagem"]


def test_adicionar_usuario_a_tenant_admin_tenant(
    cliente, tenant_exemplo, usuario_comum, token_admin_tenant
):
    """Testa adicionar usuário a tenant como admin do tenant."""
    resposta = cliente.post(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_comum.id}",
        headers={"Authorization": f"Bearer {token_admin_tenant}"},
        json={"tenant_id": tenant_exemplo.id, "administrador_tenant": False}
    )
    
    assert resposta.status_code == 200


def test_adicionar_usuario_a_tenant_usuario_comum(
    cliente, tenant_exemplo, usuario_comum, token_usuario_comum
):
    """Testa que usuário comum não pode adicionar usuários ao tenant."""
    # Cria outro usuário para tentar adicionar
    resposta_registro = cliente.post(
        "/api/v1/registro",
        json={
            "nome": "Novo Usuário",
            "email": "novo@exemplo.com",
            "senha": "senha123"
        }
    )
    novo_usuario_id = resposta_registro.json()["usuario"]["id"]
    
    resposta = cliente.post(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{novo_usuario_id}",
        headers={"Authorization": f"Bearer {token_usuario_comum}"},
        json={"tenant_id": tenant_exemplo.id, "administrador_tenant": False}
    )
    
    assert resposta.status_code == 403


def test_adicionar_usuario_inexistente_a_tenant(
    cliente, tenant_exemplo, token_acesso
):
    """Testa adicionar usuário inexistente a tenant."""
    resposta = cliente.post(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/99999",
        headers={"Authorization": f"Bearer {token_acesso}"},
        json={"tenant_id": tenant_exemplo.id, "administrador_tenant": False}
    )
    
    assert resposta.status_code == 404


def test_adicionar_usuario_ja_vinculado(
    cliente, tenant_exemplo, usuario_admin_tenant, token_acesso
):
    """Testa adicionar usuário já vinculado ao tenant."""
    resposta = cliente.post(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_admin_tenant.id}",
        headers={"Authorization": f"Bearer {token_acesso}"},
        json={"tenant_id": tenant_exemplo.id, "administrador_tenant": False}
    )
    
    assert resposta.status_code == 400
    assert "já está vinculado" in resposta.json()["detail"]


# ==================== TESTES PARA REMOVER USUÁRIO DO TENANT ====================

def test_remover_usuario_de_tenant_admin_global(
    cliente, tenant_exemplo, usuario_vinculado_tenant, token_acesso
):
    """Testa remover usuário de tenant como admin global."""
    resposta = cliente.delete(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_vinculado_tenant.id}",
        headers={"Authorization": f"Bearer {token_acesso}"}
    )
    
    assert resposta.status_code == 200
    assert "removido do tenant" in resposta.json()["mensagem"]


def test_remover_usuario_de_tenant_admin_tenant(
    cliente, tenant_exemplo, usuario_vinculado_tenant, token_admin_tenant
):
    """Testa remover usuário de tenant como admin do tenant."""
    resposta = cliente.delete(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_vinculado_tenant.id}",
        headers={"Authorization": f"Bearer {token_admin_tenant}"}
    )
    
    assert resposta.status_code == 200


def test_remover_ultimo_administrador_tenant(
    cliente, tenant_exemplo, usuario_admin_tenant, token_acesso
):
    """Testa que não é possível remover o último administrador do tenant."""
    resposta = cliente.delete(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_admin_tenant.id}",
        headers={"Authorization": f"Bearer {token_acesso}"}
    )
    
    assert resposta.status_code == 400
    assert "último administrador" in resposta.json()["detail"]


def test_usuario_remover_a_si_mesmo(
    cliente, tenant_exemplo, usuario_admin_tenant, token_admin_tenant
):
    """Testa que usuário não pode remover a si mesmo do tenant."""
    resposta = cliente.delete(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_admin_tenant.id}",
        headers={"Authorization": f"Bearer {token_admin_tenant}"}
    )
    
    assert resposta.status_code == 400
    assert "remover a si mesmo" in resposta.json()["detail"]


# ==================== TESTES PARA ATUALIZAR PERMISSÕES ====================

def test_atualizar_permissoes_usuario_admin_global(
    cliente, tenant_exemplo, usuario_vinculado_tenant, token_acesso
):
    """Testa atualizar permissões de usuário como admin global."""
    resposta = cliente.put(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_vinculado_tenant.id}/permissoes",
        headers={"Authorization": f"Bearer {token_acesso}"},
        json={"tenant_id": tenant_exemplo.id, "administrador_tenant": True}
    )
    
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["administrador_tenant"] == True


def test_atualizar_permissoes_usuario_admin_tenant(
    cliente, tenant_exemplo, usuario_vinculado_tenant, token_admin_tenant
):
    """Testa atualizar permissões de usuário como admin do tenant."""
    resposta = cliente.put(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_vinculado_tenant.id}/permissoes",
        headers={"Authorization": f"Bearer {token_admin_tenant}"},
        json={"tenant_id": tenant_exemplo.id, "administrador_tenant": True}
    )
    
    assert resposta.status_code == 200


def test_remover_ultimo_administrador_via_permissoes(
    cliente, tenant_exemplo, usuario_admin_tenant, token_acesso
):
    """Testa que não é possível remover status de admin do último administrador."""
    resposta = cliente.put(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_admin_tenant.id}/permissoes",
        headers={"Authorization": f"Bearer {token_acesso}"},
        json={"tenant_id": tenant_exemplo.id, "administrador_tenant": False}
    )
    
    assert resposta.status_code == 400
    assert "último administrador" in resposta.json()["detail"]


# ==================== TESTES PARA BUSCAR USUÁRIO NO TENANT ====================

def test_buscar_usuario_no_tenant(
    cliente, tenant_exemplo, usuario_admin_tenant, token_admin_tenant
):
    """Testa buscar um usuário específico no tenant."""
    resposta = cliente.get(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_admin_tenant.id}",
        headers={"Authorization": f"Bearer {token_admin_tenant}"}
    )
    
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["id"] == usuario_admin_tenant.id
    assert len(dados["tenants"]) > 0


def test_buscar_usuario_nao_vinculado(
    cliente, tenant_exemplo, usuario_comum, token_admin_tenant
):
    """Testa buscar usuário que não está vinculado ao tenant."""
    resposta = cliente.get(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios/{usuario_comum.id}",
        headers={"Authorization": f"Bearer {token_admin_tenant}"}
    )
    
    assert resposta.status_code == 404


def test_filtrar_usuarios_por_status(
    cliente, tenant_exemplo, usuario_admin_tenant, token_admin_tenant, sessao_db
):
    """Testa filtrar usuários por status ativo/inativo."""
    # Cria outro usuário para o tenant
    from src.modelos.usuario import Usuario, TenantUsuario
    from src.utilitarios.autenticacao import hash_senha
    
    outro_usuario = Usuario(
        nome="Outro Usuário",
        email="outro@tenant.com",
        senha_hash=hash_senha("senha123"),
        administrador=False,
        ativo=True
    )
    sessao_db.add(outro_usuario)
    sessao_db.commit()
    
    vinculo = TenantUsuario(
        usuario_id=outro_usuario.id,
        tenant_id=tenant_exemplo.id,
        administrador_tenant=False
    )
    sessao_db.add(vinculo)
    sessao_db.commit()
    
    # Desativa o outro usuário
    outro_usuario.ativo = False
    sessao_db.commit()
    
    # Filtra por ativos
    resposta = cliente.get(
        f"/api/v1/tenants/{tenant_exemplo.id}/usuarios?ativo=true",
        headers={"Authorization": f"Bearer {token_admin_tenant}"}
    )
    
    assert resposta.status_code == 200
    dados = resposta.json()
    # Não deve retornar usuários inativos
    for usuario in dados:
        assert usuario["ativo"] == True
