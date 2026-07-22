# appointment-br

Plataforma de agendamento **white label** em **FastAPI**, inspirada em plataformas como o Cal.com, com suporte a múltiplos clientes (tenants) via subdomínio e integração nativa de pagamentos via **PIX**, através de uma camada de gateway plugável (EFI Bank, Mercado Pago, entre outros).

## Visão geral

O `appointment-br` é uma API backend multi-tenant para agendamento de compromissos, desenvolvida com FastAPI.
Cada cliente (tenant) opera sua própria instância isolada, acessível por um subdomínio próprio (ex: `empresa.appointment-br.com`), com marca, cores e configurações independentes.

O projeto foi pensado para suportar fluxos como:

- Cadastro de tenants (contas white label) e seus respectivos usuários/perfis de atendimento.
- Personalização de marca por tenant (logo, cores, nome fantasia, domínio).
- Criação e gerenciamento de tipos de evento.
- Definição de horários disponíveis.
- Reserva de horários por clientes finais.
- Cobrança via PIX antes da confirmação do agendamento.
- Cancelamento, reagendamento e confirmação de agendamentos.
- Integrações com e-mail, webhook e notificações.

## Objetivos

- Fornecer uma base moderna e multi-tenant para um sistema de scheduling white label.
- Suportar cobrança via PIX de forma obrigatória para confirmar reservas.
- Manter os gateways de pagamento desacoplados do core da aplicação (arquitetura plugável).
- Separar regras de negócio, persistência, rotas e contexto de tenant de forma clara.
- Facilitar futuras integrações com frontend React, calendários externos e automações.
- Manter o projeto pronto para evolução com testes, autenticação e versionamento de API.

## Funcionalidades

- CRUD de tenants (contas white label) e configuração de marca/domínio.
- CRUD de usuários por tenant.
- CRUD de eventos/agendamentos.
- Gestão de disponibilidade.
- Reserva de slots com cobrança obrigatória via PIX.
- Camada de gateway de pagamento plugável (EFI Bank, Mercado Pago, etc.).
- Geração de cobrança PIX (QR Code e copia-e-cola).
- Webhook de confirmação de pagamento por gateway.
- Confirmação automática do agendamento após pagamento aprovado.
- Cancelamento e reagendamento (com regras de estorno/reembolso, quando aplicável).
- Autenticação com JWT, com contexto de tenant.
- Documentação automática com Swagger/OpenAPI.
- Estrutura preparada para webhooks e integrações adicionais.

## Tecnologias

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL (supabase)
- Alembic
- Uvicorn
- Docker
- Pytest
- Camada de integração PIX (EFI Bank SDK/API, adaptável a outros gateways)

## Arquitetura multi-tenant (white label)

O isolamento de tenants é feito por **subdomínio**, resolvido em nível de middleware:

- `empresa1.appointment-br.com` → tenant `empresa1`
- `empresa2.appointment-br.com` → tenant `empresa2`

Cada requisição passa por um middleware de resolução de tenant, que:

1. Identifica o subdomínio na requisição.
2. Resolve o `tenant_id` correspondente.
3. Injeta o contexto do tenant (marca, configurações, gateway de pagamento ativo) no restante da aplicação.

Cada tenant pode configurar:

- Nome fantasia, logo e cores (branding).
- Gateway de pagamento ativo e credenciais próprias.
- Regras de cancelamento/reembolso.
- Horários e disponibilidade específicos.

> Observação: a infraestrutura de DNS/wildcard subdomain (`*.appointment-br.com`) e certificado SSL wildcard deve ser configurada no provedor de hospedagem/proxy (ex: Nginx, Traefik, Cloudflare).

## Arquitetura de pagamentos (gateway plugável)

Os pagamentos via PIX são tratados por uma camada de abstração (`PaymentGateway`), permitindo múltiplos provedores sem acoplar o core da aplicação a um provedor específico.

```
app/services/payments/
├── base.py              # Interface abstrata PaymentGateway
├── efi_gateway.py        # Implementação EFI Bank
├── mercadopago_gateway.py # Implementação Mercado Pago (exemplo)
└── factory.py             # Seleciona o gateway conforme configuração do tenant
```

Interface mínima esperada por qualquer gateway:

- `create_charge(amount, booking_id, payer_data)` — gera cobrança PIX (QR Code / copia-e-cola).
- `get_charge_status(charge_id)` — consulta status da cobrança.
- `handle_webhook(payload)` — processa notificação de pagamento recebida do provedor.
- `refund(charge_id)` — solicita estorno, quando suportado.

Fluxo de cobrança:

1. Cliente final solicita uma reserva (`POST /api/v1/bookings`).
2. Sistema cria o agendamento com status `pending_payment`.
3. Sistema solicita ao gateway configurado a geração da cobrança PIX.
4. Cliente final paga via QR Code ou copia-e-cola.
5. Gateway notifica via webhook.
6. Sistema atualiza o status do agendamento para `confirmed` somente após confirmação do pagamento.

> Importante: o pagamento é **obrigatório** para confirmação do agendamento. Enquanto a cobrança não for paga, o agendamento permanece com status `pending_payment` e o slot pode ter uma janela de reserva temporária (a definir) antes de ser liberado novamente.

## Estrutura do projeto

```bash
appointment-br/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── routes/
│   │       └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── tenant_context.py
│   ├── middlewares/
│   │   └── tenant_resolver.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   │   └── payments/
│   │       ├── base.py
│   │       ├── efi_gateway.py
│   │       ├── mercadopago_gateway.py
│   │       └── factory.py
│   ├── repositories/
│   ├── utils/
│   └── main.py
├── alembic/
├── tests/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

Essa organização segue uma separação saudável entre rotas, modelos, serviços, contexto de tenant e integrações de pagamento, o que ajuda na escalabilidade do projeto [web:4][web:6].

## Requisitos

- Python 3.11 ou superior.
- PostgreSQL 14+.
- Poetry, pip ou uv para gerenciamento de dependências.
- Docker e Docker Compose, opcionais mas recomendados.
- Conta ativa em ao menos um gateway PIX (ex: EFI Bank) com credenciais de API/sandbox.
- Domínio próprio com suporte a subdomínio curinga (`*.appointment-br.com`), para ambientes de produção white label.

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/appointment-br.git
cd appointment-br
```

### 2. Crie o ambiente virtual

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

ou, se usar Poetry:

```bash
poetry install
```

### 4. Configure as variáveis de ambiente

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Exemplo de `.env`:

```env
APP_NAME=appointment-br
APP_ENV=development
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/appointment_br
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Multi-tenant / white label
BASE_DOMAIN=appointment-br.com
DEFAULT_TENANT=demo

# Gateway de pagamento padrão (pode ser sobrescrito por tenant)
DEFAULT_PAYMENT_GATEWAY=efi

# EFI Bank
EFI_CLIENT_ID=your-efi-client-id
EFI_CLIENT_SECRET=your-efi-client-secret
EFI_CERTIFICATE_PATH=./certs/efi-certificate.p12
EFI_PIX_KEY=your-efi-pix-key
EFI_SANDBOX=true

# Mercado Pago (exemplo de gateway alternativo)
MERCADOPAGO_ACCESS_TOKEN=your-mercadopago-token
```

## Execução local

```bash
uvicorn app.main:app --reload
```

Para simular subdomínios em ambiente local, adicione entradas no `/etc/hosts`, por exemplo:

```
127.0.0.1 demo.appointment-br.local
127.0.0.1 empresa1.appointment-br.local
```

A API ficará disponível em:

- `http://demo.appointment-br.local:8000`
- Documentação Swagger: `http://demo.appointment-br.local:8000/docs`
- Redoc: `http://demo.appointment-br.local:8000/redoc`

## Docker

### Subir a aplicação

```bash
docker compose up --build
```

### Parar os containers

```bash
docker compose down
```

Em produção, recomenda-se um proxy reverso (Nginx ou Traefik) na frente da aplicação para:

- Terminar SSL wildcard (`*.appointment-br.com`).
- Rotear todos os subdomínios para a mesma aplicação FastAPI.
- Repassar o header `Host` original para resolução de tenant.

## Endpoints principais

> Os caminhos abaixo podem ser adaptados conforme sua implementação.

- `POST /api/v1/auth/login` — autenticação.
- `POST /api/v1/tenants` — criação de tenant (conta white label).
- `PATCH /api/v1/tenants/{id}/branding` — atualização de marca (logo, cores, nome).
- `PATCH /api/v1/tenants/{id}/payment-gateway` — configuração do gateway de pagamento do tenant.
- `POST /api/v1/users` — criação de usuário.
- `GET /api/v1/users/{id}` — detalhes de usuário.
- `POST /api/v1/events` — criação de tipo de evento.
- `GET /api/v1/events` — listagem de eventos.
- `POST /api/v1/availability` — definição de disponibilidade.
- `POST /api/v1/bookings` — criação de agendamento (gera cobrança PIX).
- `GET /api/v1/bookings/{id}/payment` — consulta status da cobrança PIX vinculada.
- `POST /api/v1/webhooks/payments/{gateway}` — recebimento de notificações de pagamento.
- `PATCH /api/v1/bookings/{id}/cancel` — cancelamento.
- `PATCH /api/v1/bookings/{id}/reschedule` — reagendamento.

## Exemplo de uso

### Criar um agendamento (gera cobrança PIX)

```http
POST /api/v1/bookings
Host: empresa1.appointment-br.com
Content-Type: application/json
Authorization: Bearer <token>
```

```json
{
  "event_type_id": 1,
  "customer_name": "João Silva",
  "customer_email": "joao@email.com",
  "start_time": "2026-07-22T14:00:00",
  "timezone": "America/Sao_Paulo"
}
```

### Resposta esperada

```json
{
  "id": 42,
  "status": "pending_payment",
  "start_time": "2026-07-22T14:00:00",
  "end_time": "2026-07-22T14:30:00",
  "payment": {
    "gateway": "efi",
    "charge_id": "abc123",
    "amount": 5000,
    "currency": "BRL",
    "pix_copy_paste": "00020126...",
    "qr_code_url": "https://.../qrcode.png",
    "expires_at": "2026-07-22T13:45:00"
  }
}
```

### Após confirmação do pagamento (via webhook)

```json
{
  "id": 42,
  "status": "confirmed",
  "start_time": "2026-07-22T14:00:00",
  "end_time": "2026-07-22T14:30:00",
  "payment": {
    "gateway": "efi",
    "charge_id": "abc123",
    "status": "paid",
    "paid_at": "2026-07-22T13:40:12"
  }
}
```

## Banco de dados

O projeto pode usar PostgreSQL com migrations via Alembic.
As entidades principais normalmente incluem:

- Tenant
- User
- EventType
- Availability
- Booking
- Payment
- PaymentGatewayConfig
- Notification
- Webhook

## Testes

Executar testes com Pytest:

```bash
pytest
```

Se desejar cobertura com relatório:

```bash
pytest --cov=app
```

Recomenda-se manter testes específicos para:

- Resolução de tenant por subdomínio.
- Cada implementação de `PaymentGateway` (com mocks das APIs externas).
- Fluxo completo de booking → cobrança → webhook → confirmação.

## Roadmap

- [ ] Autenticação completa com JWT (com contexto de tenant).
- [ ] Middleware de resolução de tenant por subdomínio.
- [ ] Camada de gateway de pagamento plugável (interface `PaymentGateway`).
- [ ] Integração com EFI Bank (PIX).
- [ ] Integração com gateways adicionais (ex: Mercado Pago).
- [ ] Webhooks de confirmação de pagamento por gateway.
- [ ] Expiração automática de cobranças PIX não pagas e liberação do slot.
- [ ] Painel de configuração de branding por tenant.
- [ ] Integração com Google Calendar.
- [ ] Notificações por e-mail.
- [ ] Interface web em React (customizável por tenant).
- [ ] Painel administrativo (por tenant e/ou global).
- [ ] Disponibilidade recorrente.
- [ ] Links públicos de agendamento por tenant.

## Contribuição

1. Faça um fork do repositório.
2. Crie uma branch para sua feature.
3. Implemente a melhoria.
4. Adicione testes quando possível.
5. Envie um pull request.

## Licença

Distribuído sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.
## Créditos

Projeto inspirado em experiências modernas de agendamento, com foco em produtividade, automação, white label e pagamentos via PIX.
