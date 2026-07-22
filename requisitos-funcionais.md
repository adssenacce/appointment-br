# appointment-br — Requisitos Funcionais e Critérios de Aceite

Versão: 1.0 (validado, pronto para início do desenvolvimento)
Escopo: plataforma de agendamento white label, multi-tenant por subdomínio, com cobrança obrigatória via PIX antes da confirmação do agendamento.

> Este documento consolida as decisões de arquitetura e de negócio já validadas: multi-tenant por subdomínio, schema compartilhado com `tenant_id`, gateway de pagamento plugável (EFI Bank, Mercado Pago, etc.), conta obrigatória para clientes finais, disponibilidade recorrente, expiração lazy de cobrança PIX, conciliação manual para pagamentos tardios, reembolso manual, reagendamento com cobrança de diferença, webhooks de saída, auditoria e exclusão de dados pessoais (LGPD) — todos incluídos na primeira fase.

---

## 1. Tenants (contas white label)

### RF-01 — Criação de tenant
O sistema deve permitir criar um tenant com: nome fantasia, subdomínio único, e-mail de contato, e status (`active`, `suspended`).

**Critérios de aceite:**
- Não deve ser possível criar dois tenants com o mesmo subdomínio.
- Subdomínio deve seguir regex de hostname válido (letras minúsculas, números, hífen, sem começar/terminar com hífen).
- Ao criar, o tenant nasce com status `active` e sem gateway de pagamento configurado.

### RF-02 — Configuração de branding
O sistema deve permitir que um tenant configure: logo (URL), cor primária, cor secundária, nome exibido.

**Critérios de aceite:**
- Campos de branding são opcionais; valores default (tema neutro) são usados se não configurados.
- Alteração de branding não afeta agendamentos já existentes.

### RF-03 — Configuração de gateway de pagamento
O sistema deve permitir que um tenant escolha e configure um gateway de pagamento (ex: EFI Bank) com suas próprias credenciais.

**Critérios de aceite:**
- Credenciais de gateway são armazenadas de forma criptografada, nunca em texto plano.
- Um tenant sem gateway configurado não pode publicar tipos de evento pagos (ver RF-08).
- Trocar de gateway não afeta cobranças já criadas com o gateway anterior.

### RF-04 — Resolução de tenant por subdomínio
Toda requisição HTTP deve ser associada a um tenant a partir do subdomínio informado no header `Host`.

**Critérios de aceite:**
- Requisição para subdomínio inexistente retorna `404` com mensagem clara ("tenant não encontrado").
- Requisição para tenant com status `suspended` retorna `403`.
- O `tenant_id` resolvido fica disponível no contexto da requisição para todas as camadas (repositório, serviço, rota).

**Decisão validada:** isolamento por schema compartilhado, com `tenant_id` presente em toda tabela sensível a tenant. Todas as queries de repositório devem filtrar explicitamente por `tenant_id` (nunca confiar apenas no contexto de aplicação).

---

## 2. Usuários e papéis

### RF-05 — Papéis de usuário
O sistema deve suportar ao menos os seguintes papéis:
- `platform_admin` — administra todos os tenants (uso interno da plataforma).
- `tenant_admin` — administra um tenant específico (configura branding, gateway, eventos, disponibilidade).
- `staff` — atende agendamentos dentro de um tenant, sem acesso a configurações administrativas.
- `customer` — cliente final que realiza reservas (pode ou não exigir cadastro — ver RF-06).

**Critérios de aceite:**
- Um usuário pertence a exatamente um tenant, exceto `platform_admin`, que não pertence a nenhum tenant específico.
- Tentativa de acessar recurso fora do próprio tenant retorna `403`.
- Rotas administrativas (branding, gateway, eventos, disponibilidade) exigem papel `tenant_admin` ou `platform_admin`.

### RF-06 — Cadastro do cliente final
**Decisão validada:** o cliente final precisa criar conta com senha antes de realizar uma reserva.

**Critérios de aceite:**
- Cadastro exige nome, e-mail (único por tenant), senha e telefone.
- Login de cliente final é escopado ao tenant (mesmo e-mail pode existir em tenants diferentes como contas distintas).
- Reserva só pode ser criada por um `customer` autenticado (JWT), vinculado ao tenant do subdomínio acessado.
- Recuperação de senha (fluxo básico via e-mail) faz parte deste requisito.

---

## 3. Tipos de evento e disponibilidade

### RF-07 — CRUD de tipos de evento
Um `tenant_admin` deve poder criar tipos de evento com: nome, duração, descrição, preço (opcional) e moeda.

**Critérios de aceite:**
- Duração deve ser maior que zero.
- Se preço for `0` ou não informado, o evento é gratuito e **não** passa pelo fluxo de cobrança PIX.
- Se preço for maior que zero, o evento exige gateway de pagamento configurado no tenant (ver RF-03).

### RF-08 — Definição de disponibilidade
Um `tenant_admin` ou `staff` deve poder definir janelas de disponibilidade (dia da semana + hora início/fim, ou datas específicas).

**Critérios de aceite:**
- Não deve ser possível salvar uma janela com hora de início maior ou igual à hora de término.
- Disponibilidade respeita o timezone configurado no tenant ou no evento.

### RF-08a — Disponibilidade recorrente
**Decisão validada:** disponibilidade recorrente entra na primeira fase.

**Critérios de aceite:**
- `tenant_admin`/`staff` deve poder definir uma regra recorrente por dia da semana (ex: "toda segunda-feira, das 09h às 12h"), com data de início e, opcionalmente, data de término da recorrência.
- O sistema deve gerar/expandir os slots concretos a partir da regra recorrente (seja sob demanda ao consultar disponibilidade, seja via job de expansão — detalhamento técnico fica a critério da implementação).
- Uma exceção pontual (ex: feriado, folga) deve poder ser cadastrada para bloquear um dia específico sem alterar a regra recorrente geral.
- Alterar ou remover uma regra recorrente não deve cancelar reservas já `confirmed` em slots gerados anteriormente.

---

## 4. Reserva (booking) e pagamento PIX

### RF-09 — Criação de reserva
Um cliente final deve poder reservar um slot disponível de um tipo de evento.

**Critérios de aceite:**
- Slot deve estar dentro de uma janela de disponibilidade válida e não conflitar com outra reserva `confirmed` ou `pending_payment` não expirada.
- Se o evento é pago, a reserva nasce com status `pending_payment` e uma cobrança PIX é criada automaticamente (ver RF-10).
- Se o evento é gratuito, a reserva nasce diretamente com status `confirmed`.

### RF-10 — Geração de cobrança PIX
Ao criar uma reserva de evento pago, o sistema deve gerar uma cobrança PIX através do gateway configurado no tenant.

**Critérios de aceite:**
- Cobrança retorna QR Code, código copia-e-cola e prazo de expiração.
- Valor da cobrança é exatamente o preço do tipo de evento (sem cálculo adicional nesta fase, salvo taxas do próprio gateway).
- Falha na comunicação com o gateway não deve deixar a reserva "presa" — reserva deve ser marcada como `payment_failed` e o slot liberado.

### RF-11 — Expiração da cobrança e liberação do slot
**Decisão validada:** prazo padrão de 15 minutos, verificação lazy (sem job periódico nesta fase).

**Critérios de aceite:**
- Toda reserva `pending_payment` tem um campo `expires_at` calculado como `created_at + 15 minutos` no momento da criação.
- Não há job/cron rodando em background para expirar reservas nesta fase.
- A verificação de expiração acontece de forma lazy: ao consultar disponibilidade de um slot, ou ao tentar criar uma nova reserva para o mesmo slot, o sistema verifica se existe uma reserva `pending_payment` com `expires_at` no passado; se sim, ela é marcada como `expired` nesse momento e o slot é liberado para a nova tentativa.
- Consequência aceita: uma reserva expirada pode continuar aparecendo como `pending_payment` no banco até que alguém tente usar o mesmo slot ou consulte a própria reserva — isso é esperado e não é um bug.
- O endpoint de consulta de status da reserva (RF-13) também deve aplicar essa checagem lazy antes de responder, para não informar `pending_payment` desatualizado ao cliente final.

### RF-12 — Confirmação via webhook
O sistema deve expor um endpoint de webhook por gateway (`POST /api/v1/webhooks/payments/{gateway}`) para receber notificações de pagamento.

**Critérios de aceite:**
- Webhook valida a assinatura/origem da notificação conforme especificação do gateway (ex: EFI Bank).
- Ao confirmar pagamento, a reserva correspondente muda de `pending_payment` para `confirmed`.
- Webhooks duplicados (reenvio pelo gateway) não devem gerar efeitos colaterais duplicados (idempotência por `charge_id`).
- **Decisão validada:** webhook para reserva já `expired` **não** reconfirma automaticamente, mesmo que o slot ainda esteja livre. A reserva é marcada com status `payment_reconciliation_required` (ou equivalente) e o pagamento fica registrado vinculado a ela para que um `tenant_admin` decida manualmente (confirmar reserva, estornar, ou realocar o cliente para outro horário).
- O painel/endpoint administrativo deve listar reservas pendentes de conciliação manual, com dados do pagamento recebido, para facilitar a decisão do `tenant_admin`.

### RF-13 — Consulta de status de pagamento
O cliente final deve poder consultar o status da cobrança vinculada à sua reserva.

**Critérios de aceite:**
- Endpoint retorna status atualizado mesmo que o webhook ainda não tenha chegado (fallback: consulta ativa ao gateway).

---

## 5. Cancelamento, reagendamento e reembolso

### RF-14 — Cancelamento de reserva
Cliente final ou `staff`/`tenant_admin` deve poder cancelar uma reserva `confirmed` ou `pending_payment`.

**Critérios de aceite:**
- Cancelamento de reserva `pending_payment` apenas libera o slot (não há pagamento a estornar).
- Cancelamento de reserva `confirmed` (já paga) segue a política de reembolso do tenant — ver RF-15.

### RF-15 — Política de reembolso
**Decisão validada:** não há reembolso automático nesta fase; o processo de estorno é manual, feito fora do fluxo do sistema (ex: diretamente no painel do gateway de pagamento).

**Critérios de aceite:**
- Ao cancelar uma reserva `confirmed` (já paga), o sistema apenas registra o cancelamento e libera o slot; nenhuma chamada de estorno é feita ao gateway automaticamente.
- O sistema deve marcar a reserva cancelada com um indicador `refund_status = not_requested` (ou equivalente), permitindo que o `tenant_admin` atualize esse status manualmente depois de processar o estorno fora do sistema (ex: `refunded_manually`).
- A tela/endpoint de detalhes da reserva deve deixar claro para o `tenant_admin` que nenhum estorno automático ocorreu.

### RF-16 — Reagendamento
Cliente final deve poder reagendar uma reserva `confirmed` para outro slot disponível.

**Critérios de aceite:**
- Reagendamento não gera nova cobrança se o preço do evento for o mesmo do momento do pagamento original.
- **Decisão validada:** se o preço do evento aumentou desde o pagamento original, o sistema gera uma cobrança PIX complementar apenas pela diferença (novo preço − valor já pago), seguindo o mesmo fluxo de cobrança/expiração/webhook do RF-10 a RF-12.
- Se o preço do evento diminuiu, nenhuma cobrança adicional é gerada e nenhum reembolso automático da diferença ocorre nesta fase (ver RF-15 — reembolso é sempre manual).
- Enquanto a cobrança complementar estiver `pending_payment`, a reserva permanece com o slot **novo** já reservado; se essa cobrança complementar expirar sem pagamento, o reagendamento é revertido e a reserva volta ao slot e status anteriores.

---

## 6. Notificações e webhooks de saída

### RF-17 — Notificação por e-mail
O sistema deve enviar e-mail ao cliente final nos eventos: reserva criada (com cobrança PIX), pagamento confirmado, reserva cancelada, reserva reagendada.

**Critérios de aceite:**
- Falha no envio de e-mail não deve bloquear o fluxo principal (deve ser assíncrono/best-effort com retry).

### RF-18 — Webhooks de saída (integrações do tenant)
**Decisão validada:** entra nesta primeira fase.

**Critérios de aceite:**
- Um `tenant_admin` deve poder cadastrar uma ou mais URLs de webhook, cada uma associada a um conjunto de eventos que deseja receber (ex: `booking.created`, `booking.confirmed`, `booking.cancelled`, `booking.rescheduled`, `payment.received`).
- Cada disparo de webhook deve incluir um payload padronizado (tipo do evento, timestamp, dados do booking) e uma assinatura (ex: HMAC com um secret gerado por URL cadastrada), para que o tenant valide a autenticidade da chamada.
- Falha na entrega (timeout, erro 4xx/5xx do endpoint do tenant) deve acionar reenvio com backoff (ex: algumas tentativas espaçadas), sem bloquear o fluxo principal da reserva.
- Deve existir um registro (log) das últimas entregas de webhook por tenant, incluindo status de sucesso/falha, para fins de suporte.

---

## 7. Requisitos não funcionais

### RNF-01 — Segurança
- Credenciais de gateway de pagamento e segredos (JWT secret, client secrets) nunca em texto plano no banco ou logs.
- Todas as rotas administrativas exigem autenticação JWT + verificação de papel e tenant.

### RNF-02 — Auditoria
**Decisão validada:** log de auditoria é obrigatório nesta primeira fase.

**Critérios de aceite:**
- Toda ação administrativa relevante deve gerar um registro de auditoria contendo: `tenant_id`, usuário responsável, ação realizada, entidade afetada, timestamp e, quando aplicável, valores antes/depois.
- Ações que obrigatoriamente geram auditoria: criação/edição de tenant, alteração de branding, alteração de gateway de pagamento, criação/edição de tipo de evento (especialmente mudança de preço), confirmação manual de reserva em conciliação (RF-12), atualização de status de reembolso (RF-15), cancelamento de reserva por `staff`/`tenant_admin`.
- Registros de auditoria são imutáveis (não podem ser editados ou apagados pela aplicação) e devem ficar acessíveis por tenant, isolados de outros tenants.
- Nesta fase, um endpoint de consulta (somente leitura, filtrável por período/entidade/usuário) para `tenant_admin` é suficiente; um painel visual dedicado pode ficar para depois.

### RNF-03 — LGPD
Dados pessoais de clientes finais (nome, e-mail, telefone) devem ter tratamento compatível com a LGPD: finalidade declarada, possibilidade de exclusão sob solicitação.

**Decisão validada:** exclusão de dados pessoais sob solicitação entra nesta primeira fase.

**Critérios de aceite:**
- Cliente final deve poder solicitar a exclusão dos seus dados pessoais (via endpoint autenticado, ex: `DELETE /api/v1/customers/me`).
- A exclusão deve anonimizar dados pessoais (nome, e-mail, telefone) em reservas passadas, mantendo os registros financeiros/reservas em si para fins contábeis e de auditoria (RNF-02), porém sem dado identificável.
- Reservas `pending_payment` ou `confirmed` futuras impedem a exclusão imediata; o sistema deve informar ao cliente que é necessário cancelar reservas futuras antes de solicitar a exclusão (ou cancelar automaticamente como parte do processo — **a confirmar na especificação técnica**, mas o requisito de existir o mecanismo de exclusão é obrigatório nesta fase).
- A ação de exclusão gera um registro de auditoria (RNF-02), mesmo que o dado pessoal em si seja removido/anonimizado.

### RNF-04 — Performance e concorrência
- Duas requisições simultâneas para o mesmo slot não podem gerar duas reservas `confirmed`/`pending_payment` simultâneas (lock otimista ou constraint de unicidade no banco).

### RNF-05 — Observabilidade
- Logs estruturados para: criação de cobrança, recebimento de webhook, mudança de status de reserva.

---

## 8. Resumo das decisões validadas

| # | Decisão | Resolução |
|---|---|---|
| 1 | Isolamento de dados no banco | Schema compartilhado, com `tenant_id` em toda tabela sensível a tenant |
| 2 | Cadastro do cliente final | Conta com senha obrigatória (sem fluxo guest) |
| 3 | Disponibilidade recorrente | Entra na primeira fase, com suporte a exceções pontuais |
| 4 | Prazo de expiração da cobrança PIX | 15 minutos (fixo nesta fase) |
| 5 | Verificação de expiração | Lazy, sem job periódico |
| 6 | Pagamento tardio após expiração | Vai para conciliação manual (`tenant_admin` decide) |
| 7 | Política de reembolso | Sem reembolso automático; processo manual fora do sistema |
| 8 | Reagendamento com mudança de preço | Cobra a diferença via cobrança PIX complementar, se o preço aumentou |
| 9 | Webhooks de saída para o tenant | Entram na primeira fase, com assinatura HMAC e reenvio com backoff |
| 10 | Log de auditoria | Obrigatório nesta fase, para ações administrativas e financeiras |
| 11 | Exclusão de dados pessoais (LGPD) | Entra na primeira fase, via anonimização mantendo histórico financeiro |

---

## Próximos passos sugeridos

1. Iniciar o scaffolding do projeto (estrutura de pastas, modelos, migrations, middleware de tenant) com base nesta versão 1.0.
2. Implementar a interface `PaymentGateway` com uma implementação mock, já que este ambiente não tem acesso à internet para testar a API real da EFI Bank — a integração real deve ser validada localmente com credenciais de sandbox.
3. Priorizar a ordem sugerida de implementação: (1) tenants + auth + papéis, (2) eventos + disponibilidade (incluindo recorrência), (3) booking + PIX + expiração lazy, (4) webhooks de saída + auditoria, (5) exclusão de dados (LGPD).
