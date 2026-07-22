# 📘 Manual de Testes - Sistema Multi-Tenant SaaS

Este documento descreve como executar os testes do projeto, desde a verificação unitária automática até a validação manual de fluxos completos via interface Swagger e scripts dedicados.

---

## 📋 Pré-requisitos

Antes de iniciar qualquer teste, certifique-se de que:

1.  **Python 3.9+** está instalado.
2.  As dependências estão instaladas:
    ```bash
    pip install -r requirements.txt
    ```
3.  O banco de dados está configurado (SQLite para dev ou PostgreSQL via Docker).
4.  A API está rodando localmente:
    ```bash
    uvicorn src.principal:aplicacao --reload
    ```
    *A API estará disponível em `http://localhost:8000`.*

---

## 1️⃣ Testes Automatizados (Unitários e Integração)

Esta é a primeira linha de defesa. Estes testes validam a lógica de negócio, regras de segurança e integridade dos dados.

### Como Executar

Execute todos os testes com o seguinte comando no terminal:

```bash
python -m pytest tests/ -v
```

### O que é testado?

*   **RF-01 (Tenants):** Criação, listagem, atualização, exclusão e validação de slug único.
*   **RF-02 (Autenticação):** Registro, login (JWT), refresh token, logout e proteção de rotas.
*   **RF-03 (Usuários):** Vinculação a tenants, listagem filtrada e regra crítica do "último administrador".
*   **RF-04 (Permissões):** Criação de cargos, atribuição de permissões e validação de acesso (RBAC).
*   **RF-05 (Dashboard):** Recuperação de métricas e validação de escopo de dados (global vs. tenant).

### Critério de Sucesso
*   Todos os testes devem passar (**100% green**).
*   Nenhum erro de `AssertionError` ou exceções não tratadas.
*   Cobertura de código adequada (verificado visualmente nos logs do `pytest`).

---

## 2️⃣ Script de Fluxo Completo (E2E)

Existe um script Python dedicado (`scripts/testar_fluxo_completo.py`) que simula um usuário real navegando pelo sistema, criando dados e validando respostas em sequência.

### Preparação

Certifique-se de ter a biblioteca `requests` instalada (já incluída em `requirements.txt`):
```bash
pip install requests
```

### Como Executar

Com a API rodando (`uvicorn ...`), execute em outro terminal:

```bash
python scripts/testar_fluxo_completo.py
```

### O que o script faz?

Ele executa sequencialmente:
1.  **Criação de Tenant:** Gera um novo ambiente isolado.
2.  **Registro de Admin:** Cria o primeiro usuário mestre desse tenant.
3.  **Login:** Obtém token JWT válido.
4.  **Gestão de Usuários:** Cria um usuário comum vinculado ao tenant.
5.  **Validação de Segurança:** Tenta operações restritas para garantir que as regras de "último admin" funcionam.
6.  **Dashboard:** Consome as métricas geradas.
7.  **Logout:** Encerra a sessão corretamente.

### Interpretação do Resultado

*   **✅ SUCESSO:** O script imprime mensagens verdes e finaliza com código de saída `0`.
*   **❌ FALHA:** O script imprime mensagens vermelhas indicando em qual passo a integração falhou e termina com código `1`.

---

## 3️⃣ Testes Manuais via Swagger UI

Para exploração interativa, debugging ou demonstração, utilize a documentação automática gerada pelo FastAPI.

### Acesso

Com a API rodando, abra no navegador:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Roteiro de Teste Manual Sugerido

Siga esta ordem para validar a coerência do sistema:

#### Passo 1: Criar Tenant (RF-01)
1.  Expanda o endpoint `POST /api/v1/tenants`.
2.  Clique em **"Try it out"**.
3.  Preencha o JSON:
    ```json
    {
      "nome": "Minha Empresa",
      "slug": "minha-empresa"
    }
    ```
4.  Execute e copie o `id` do tenant retornado.

#### Passo 2: Registrar Usuário Admin (RF-02/RF-03)
1.  Expanda `POST /api/v1/auth/registrar`.
2.  Preencha com os dados do admin, usando o `tenant_id` copiado anteriormente.
    ```json
    {
      "nome": "Admin Principal",
      "email": "admin@minhaempresa.com",
      "senha": "Senha123!",
      "tenant_id": "<COLE_O_ID_AQUI>",
      "cargo_nome": "Administrador"
    }
    ```
3.  Execute.

#### Passo 3: Obter Token (RF-02)
1.  Expanda `POST /api/v1/auth/login`.
2.  Use as credenciais criadas no passo anterior.
3.  Execute e copie o `access_token` da resposta.

#### Passo 4: Autorizar Sessão
1.  Clique no botão **"Authorize"** no topo da página Swagger.
2.  Cole o token no formato: `Bearer <SEU_TOKEN_AQUI>`.
3.  Clique em **Authorize** e feche o modal.
    *Agora todos os endpoints protegidos terão acesso automático.*

#### Passo 5: Validar Dashboard (RF-05)
1.  Expanda `GET /api/v1/dashboard/tenants/{tenant_id}/metricas`.
2.  Insira o ID do tenant.
3.  Execute. Você deve ver um JSON com contagens de usuários, status do tenant, etc.

#### Passo 6: Testar Regra de Negócio (RF-03/RF-04)
1.  Tente deletar o usuário admin que você acabou de criar através do endpoint `DELETE /api/v1/tenants/{tenant_id}/usuarios/{usuario_id}`.
2.  **Resultado Esperado:** Erro **400 Bad Request** com mensagem informando que não é possível remover o último administrador.

---

## 🐛 Solução de Problemas Comuns

| Problema | Causa Provável | Solução |
| :--- | :--- | :--- |
| **Erro de Conexão (Connection Refused)** | API não está rodando. | Execute `uvicorn src.principal:aplicacao --reload`. |
| **Testes Falhando com "Table not found"** | Banco de dados sujo ou migrations pendentes. | Delete o arquivo `app.db` (se SQLite) e rode os testes novamente (eles recriam as tabelas). |
| **Erro 401 Unauthorized** | Token expirado ou não enviado. | Renove o login e atualize o token no Swagger ou variável do script. |
| **Erro 403 Forbidden** | Usuário sem permissão para a ação. | Verifique se o usuário possui o cargo adequado (ex: Administrador). |
| **Script E2E falha no início** | Porta 8000 ocupada ou DB travado. | Verifique logs da API e reinicie o servidor. |

---

## ✅ Critérios de Aceite para "Pronto"

Um módulo ou versão é considerada estável quando:
1.  ✅ Todos os testes automatizados (`pytest`) passam sem falhas.
2.  ✅ O script de fluxo completo (`testar_fluxo_completo.py`) executa do início ao fim com sucesso.
3.  ✅ Os testes manuais no Swagger confirmam as regras de negócio (especialmente as de segurança).
4.  ✅ Não há erros críticos nos logs da aplicação durante os testes.
