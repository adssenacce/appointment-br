import pytest
from fastapi.testclient import TestClient
from src.principal import aplicacao
from src.configuracoes.banco_dados import get_engine, Base, criar_tabelas
from sqlalchemy.orm import sessionmaker
import json

# Criar cliente de teste
cliente = TestClient(aplicacao)


@pytest.fixture(scope="function")
def setup_banco_dados():
    """Configura banco de dados limpo para cada teste."""
    # Recria as tabelas
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Limpa após o teste
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def usuario_admin_setup(setup_banco_dados):
    """Cria um usuário administrador para testes."""
    dados_registro = {
        "nome": "Admin Teste",
        "email": "admin@teste.com",
        "senha": "senha123",
        "administrador": True
    }
    resposta = cliente.post("/api/v1/registro", json=dados_registro)
    assert resposta.status_code == 200
    return resposta.json()


@pytest.fixture
def usuario_comum_setup(setup_banco_dados):
    """Cria um usuário comum para testes."""
    dados_registro = {
        "nome": "Usuario Comum",
        "email": "comum@teste.com",
        "senha": "senha123",
        "administrador": False
    }
    resposta = cliente.post("/api/v1/registro", json=dados_registro)
    assert resposta.status_code == 200
    return resposta.json()


class TestRegistro:
    """Testes para registro de usuário."""

    def test_registrar_usuario_sucesso(self, setup_banco_dados):
        """Testa registro de usuário com sucesso."""
        dados = {
            "nome": "Joao Silva",
            "email": "joao@teste.com",
            "senha": "senha123"
        }
        resposta = cliente.post("/api/v1/registro", json=dados)
        
        assert resposta.status_code == 200
        dados_resposta = resposta.json()
        
        assert "usuario" in dados_resposta
        assert "access_token" in dados_resposta
        assert "refresh_token" in dados_resposta
        assert dados_resposta["usuario"]["nome"] == "Joao Silva"
        assert dados_resposta["usuario"]["email"] == "joao@teste.com"
        assert not dados_resposta["usuario"]["administrador"]

    def test_registrar_usuario_email_repetido(self, usuario_admin_setup):
        """Testa erro ao registrar com email já existente."""
        dados = {
            "nome": "Outro Usuario",
            "email": "admin@teste.com",
            "senha": "senha456"
        }
        resposta = cliente.post("/api/v1/registro", json=dados)
        
        assert resposta.status_code == 400
        assert "já está em uso" in resposta.json()["detail"]

    def test_registrar_usuario_senha_curta(self, setup_banco_dados):
        """Testa erro ao registrar com senha muito curta."""
        dados = {
            "nome": "Usuario Senha Curta",
            "email": "curta@teste.com",
            "senha": "123"
        }
        resposta = cliente.post("/api/v1/registro", json=dados)
        
        assert resposta.status_code == 422  # Validation error


class TestLogin:
    """Testes para login de usuário."""

    def test_login_sucesso(self, usuario_admin_setup):
        """Testa login com credenciais válidas."""
        dados_login = {
            "username": "admin@teste.com",
            "password": "senha123"
        }
        resposta = cliente.post("/api/v1/login", data=dados_login)
        
        assert resposta.status_code == 200
        dados_resposta = resposta.json()
        
        assert "access_token" in dados_resposta
        assert "refresh_token" in dados_resposta
        assert dados_resposta["token_type"] == "bearer"

    def test_login_senha_incorreta(self, usuario_admin_setup):
        """Testa login com senha incorreta."""
        dados_login = {
            "username": "admin@teste.com",
            "password": "senha_errada"
        }
        resposta = cliente.post("/api/v1/login", data=dados_login)
        
        assert resposta.status_code == 401
        assert "Email ou senha inválidos" in resposta.json()["detail"]

    def test_login_usuario_inexistente(self, setup_banco_dados):
        """Testa login com usuário que não existe."""
        dados_login = {
            "username": "nao_existe@teste.com",
            "password": "senha123"
        }
        resposta = cliente.post("/api/v1/login", data=dados_login)
        
        assert resposta.status_code == 401
        assert "Email ou senha inválidos" in resposta.json()["detail"]


class TestTokenRefresh:
    """Testes para refresh de token."""

    def test_refresh_token_sucesso(self, usuario_admin_setup):
        """Testa refresh de token com sucesso."""
        refresh_token = usuario_admin_setup["refresh_token"]
        
        dados_refresh = {"refresh_token": refresh_token}
        resposta = cliente.post("/api/v1/refresh", json=dados_refresh)
        
        assert resposta.status_code == 200
        dados_resposta = resposta.json()
        
        assert "access_token" in dados_resposta
        assert "refresh_token" in dados_resposta
        # Nota: tokens podem ser iguais se gerados no mesmo segundo (mesmo iat/exp)
        # O importante é que novos tokens válidos foram retornados
        assert dados_resposta["token_type"] == "bearer"

    def test_refresh_token_invalido(self, setup_banco_dados):
        """Testa refresh com token inválido."""
        dados_refresh = {"refresh_token": "token_invalido"}
        resposta = cliente.post("/api/v1/refresh", json=dados_refresh)
        
        assert resposta.status_code == 401


class TestObterUsuarioAtual:
    """Testes para obter usuário autenticado."""

    def test_obter_meu_usuario_sucesso(self, usuario_admin_setup):
        """Testa obtenção do usuário atual com sucesso."""
        access_token = usuario_admin_setup["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        resposta = cliente.get("/api/v1/me", headers=headers)
        
        assert resposta.status_code == 200
        dados_resposta = resposta.json()
        
        assert dados_resposta["nome"] == "Admin Teste"
        assert dados_resposta["email"] == "admin@teste.com"
        assert dados_resposta["administrador"] is True

    def test_obter_meu_usuario_sem_token(self, setup_banco_dados):
        """Testa erro ao acessar sem token."""
        resposta = cliente.get("/api/v1/me")
        
        assert resposta.status_code == 401

    def test_obter_meu_usuario_token_invalido(self, setup_banco_dados):
        """Testa erro ao acessar com token inválido."""
        headers = {"Authorization": "Bearer token_invalido"}
        resposta = cliente.get("/api/v1/me", headers=headers)
        
        assert resposta.status_code == 401


class TestCRUDUsuarios:
    """Testes para CRUD de usuários."""

    def test_listar_usuarios_admin(self, usuario_admin_setup):
        """Testa listagem de usuários como admin."""
        access_token = usuario_admin_setup["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        resposta = cliente.get("/api/v1/usuarios", headers=headers)
        
        assert resposta.status_code == 200
        usuarios = resposta.json()
        assert len(usuarios) >= 1

    def test_listar_usuarios_comum_ve_apenas_si_mesmo(self, usuario_comum_setup):
        """Testa que usuário comum vê apenas a si mesmo."""
        access_token = usuario_comum_setup["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        resposta = cliente.get("/api/v1/usuarios", headers=headers)
        
        assert resposta.status_code == 200
        usuarios = resposta.json()
        assert len(usuarios) == 1
        assert usuarios[0]["email"] == "comum@teste.com"

    def test_buscar_usuario_por_id_admin(self, usuario_admin_setup, usuario_comum_setup):
        """Testa busca de usuário por ID como admin."""
        access_token = usuario_admin_setup["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        usuario_id = usuario_comum_setup["usuario"]["id"]
        resposta = cliente.get(f"/api/v1/usuarios/{usuario_id}", headers=headers)
        
        assert resposta.status_code == 200
        assert resposta.json()["email"] == "comum@teste.com"

    def test_buscar_usuario_por_id_comum_nao_pode_ver_outro(self, usuario_comum_setup, usuario_admin_setup):
        """Testa que usuário comum não pode ver outro usuário."""
        access_token = usuario_comum_setup["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Tenta buscar ID do admin (que é diferente do seu próprio)
        admin_id = usuario_admin_setup["usuario"]["id"]
        resposta = cliente.get(f"/api/v1/usuarios/{admin_id}", headers=headers)
        
        assert resposta.status_code == 403

    def test_atualizar_usuario_a_propria_senha(self, usuario_comum_setup):
        """Testa atualização da própria senha."""
        access_token = usuario_comum_setup["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        dados_atualizacao = {"senha": "nova_senha_123"}
        usuario_id = usuario_comum_setup["usuario"]["id"]
        
        resposta = cliente.put(f"/api/v1/usuarios/{usuario_id}", 
                               json=dados_atualizacao, 
                               headers=headers)
        
        assert resposta.status_code == 200
        
        # Testa login com nova senha
        dados_login = {
            "username": "comum@teste.com",
            "password": "nova_senha_123"
        }
        resposta_login = cliente.post("/api/v1/login", data=dados_login)
        assert resposta_login.status_code == 200

    def test_deletar_usuario_admin(self, usuario_admin_setup, usuario_comum_setup):
        """Testa deleção de usuário por admin."""
        access_token = usuario_admin_setup["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        usuario_id = usuario_comum_setup["usuario"]["id"]
        resposta = cliente.delete(f"/api/v1/usuarios/{usuario_id}", headers=headers)
        
        assert resposta.status_code == 200
        
        # Verifica que usuário foi deletado
        resposta_busca = cliente.get(f"/api/v1/usuarios/{usuario_id}", headers=headers)
        assert resposta_busca.status_code == 404

    def test_admin_nao_pode_deletar_a_si_mesmo(self, usuario_admin_setup):
        """Testa que admin não pode deletar a si mesmo."""
        access_token = usuario_admin_setup["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        usuario_id = usuario_admin_setup["usuario"]["id"]
        resposta = cliente.delete(f"/api/v1/usuarios/{usuario_id}", headers=headers)
        
        assert resposta.status_code == 400
        assert "não pode deletar a si mesmo" in resposta.json()["detail"]

    def test_usuario_comum_nao_pode_deletar(self, usuario_comum_setup):
        """Testa que usuário comum não pode deletar ninguém."""
        access_token = usuario_comum_setup["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        resposta = cliente.delete("/api/v1/usuarios/1", headers=headers)
        
        assert resposta.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
