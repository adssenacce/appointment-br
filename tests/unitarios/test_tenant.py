import pytest
import os

# Configurar banco de dados de teste antes de importar a aplicação
os.environ["DATABASE_URL"] = "sqlite:///./teste_banco.db"

from fastapi.testclient import TestClient
from src.principal import aplicacao
from src.configuracoes.banco_dados import get_engine, Base

client = TestClient(aplicacao)


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


@pytest.fixture(autouse=True)
def limpar_banco_dados(setup_banco_dados):
    """Limpa o banco de dados antes de cada teste automaticamente."""
    yield


class TestCriarTenant:
    """Testes para criação de tenant."""

    def test_criar_tenant_sucesso(self):
        """Testa criação de tenant com sucesso."""
        dados = {
            "nome": "Empresa Teste",
            "slug": "empresa-teste"
        }
        resposta = client.post("/api/v1/tenants", json=dados)
        
        assert resposta.status_code == 201
        dados_resposta = resposta.json()
        assert dados_resposta["nome"] == "Empresa Teste"
        assert dados_resposta["slug"] == "empresa-teste"
        assert dados_resposta["ativo"] is True
        assert "id" in dados_resposta
        assert "data_criacao" in dados_resposta

    def test_criar_tenant_slug_duplicado(self):
        """Testa criação de tenant com slug duplicado."""
        # Primeiro cria um tenant
        dados_primeiro = {
            "nome": "Empresa Primeira",
            "slug": "empresa-teste"
        }
        resposta_primeira = client.post("/api/v1/tenants", json=dados_primeiro)
        assert resposta_primeira.status_code == 201
        
        # Tenta criar outro com mesmo slug
        dados = {
            "nome": "Empresa Duplicada",
            "slug": "empresa-teste"
        }
        resposta = client.post("/api/v1/tenants", json=dados)
        
        assert resposta.status_code == 400
        assert "slug" in resposta.json()["detail"].lower()


class TestListarTenants:
    """Testes para listagem de tenants."""

    def test_listar_todos_tenants(self):
        """Testa listagem de todos os tenants."""
        # Cria um tenant primeiro
        dados_criacao = {
            "nome": "Empresa Listagem",
            "slug": "empresa-listagem"
        }
        resposta_criacao = client.post("/api/v1/tenants", json=dados_criacao)
        assert resposta_criacao.status_code == 201
        
        resposta = client.get("/api/v1/tenants")
        
        assert resposta.status_code == 200
        dados = resposta.json()
        assert isinstance(dados, list)
        assert len(dados) >= 1  # Pelo menos o tenant criado anteriormente

    def test_listar_tenants_ativos(self):
        """Testa filtragem de tenants ativos."""
        resposta = client.get("/api/v1/tenants?ativo=true")
        
        assert resposta.status_code == 200
        dados = resposta.json()
        assert isinstance(dados, list)
        for tenant in dados:
            assert tenant["ativo"] is True


class TestBuscarTenant:
    """Testes para busca de tenant por ID."""

    def test_buscar_tenant_existente(self):
        """Testa busca de tenant existente."""
        # Primeiro cria um tenant
        dados_criacao = {
            "nome": "Empresa Busca",
            "slug": "empresa-busca"
        }
        resposta_criacao = client.post("/api/v1/tenants", json=dados_criacao)
        tenant_id = resposta_criacao.json()["id"]
        
        # Busca o tenant
        resposta = client.get(f"/api/v1/tenants/{tenant_id}")
        
        assert resposta.status_code == 200
        dados = resposta.json()
        assert dados["id"] == tenant_id
        assert dados["nome"] == "Empresa Busca"

    def test_buscar_tenant_inexistente(self):
        """Testa busca de tenant inexistente."""
        resposta = client.get("/api/v1/tenants/99999")
        
        assert resposta.status_code == 404


class TestAtualizarTenant:
    """Testes para atualização de tenant."""

    def test_atualizar_tenant_nome(self):
        """Testa atualização do nome do tenant."""
        # Cria um tenant
        dados_criacao = {
            "nome": "Empresa Atualizacao",
            "slug": "empresa-atualizacao"
        }
        resposta_criacao = client.post("/api/v1/tenants", json=dados_criacao)
        tenant_id = resposta_criacao.json()["id"]
        
        # Atualiza o tenant
        dados_atualizacao = {"nome": "Empresa Atualizada"}
        resposta = client.put(f"/api/v1/tenants/{tenant_id}", json=dados_atualizacao)
        
        assert resposta.status_code == 200
        dados = resposta.json()
        assert dados["nome"] == "Empresa Atualizada"
        assert dados["slug"] == "empresa-atualizacao"  # Slug não mudou

    def test_atualizar_tenant_inexistente(self):
        """Testa atualização de tenant inexistente."""
        dados_atualizacao = {"nome": "Empresa Inexistente"}
        resposta = client.put("/api/v1/tenants/99999", json=dados_atualizacao)
        
        assert resposta.status_code == 404


class TestDeletarTenant:
    """Testes para deleção de tenant."""

    def test_deletar_tenant_existente(self):
        """Testa deleção de tenant existente."""
        # Cria um tenant
        dados_criacao = {
            "nome": "Empresa Deletar",
            "slug": "empresa-deletar"
        }
        resposta_criacao = client.post("/api/v1/tenants", json=dados_criacao)
        tenant_id = resposta_criacao.json()["id"]
        
        # Deleta o tenant
        resposta = client.delete(f"/api/v1/tenants/{tenant_id}")
        
        assert resposta.status_code == 200
        assert "mensagem" in resposta.json()
        
        # Verifica que o tenant foi deletado
        resposta_busca = client.get(f"/api/v1/tenants/{tenant_id}")
        assert resposta_busca.status_code == 404

    def test_deletar_tenant_inexistente(self):
        """Testa deleção de tenant inexistente."""
        resposta = client.delete("/api/v1/tenants/99999")
        
        assert resposta.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
