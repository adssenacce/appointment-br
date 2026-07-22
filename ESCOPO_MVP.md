# appointment-br — Escopo do MVP

Versão: 1.0
Base: `REQUISITOS_FUNCIONAIS.md` v1.0

Princípio do MVP: **arquitetura multi-tenant completa desde o início, escopo funcional enxuto.** O que corta é feature de borda, nunca isolamento de tenant, segurança ou o fluxo central de pagamento.

---

## 1. Entra no MVP

### Tenants e auth
- CRUD de tenant (RF-01) + resolução por subdomínio (RF-04), com `tenant_id` em toda tabela sensível.
- Branding básico (RF-02): logo, cores, nome — sem editor visual, só campos via API.
- Papéis: `platform_admin`, `tenant_admin`, `staff`, `customer` (RF-05).
- Cadastro de cliente final com conta e senha (RF-06).
- 1 gateway de pagamento configurável por tenant (RF-03), via interface `PaymentGateway` já plugável — mas só **EFI Bank** implementado de fato.

### Eventos e disponibilidade
- CRUD de tipos de evento, com preço opcional (RF-07).
- Disponibilidade recorrente por dia da semana + exceções pontuais (RF-08a), conforme já decidido nos requisitos.

### Booking e pagamento PIX
- Criação de reserva com geração de cobrança PIX (RF-09, RF-10).
- Expiração lazy em 15 minutos (RF-11).
- Confirmação via webhook do gateway, com idempotência por `charge_id` (RF-12).
- Consulta de status de pagamento pelo cliente final (RF-13).
- Cancelamento de reserva (RF-14), com reembolso **manual** (RF-15 — sem chamada automática de estorno).
- Reagendamento simples: mesmo preço, sem gerar nova cobrança (parte do RF-16; a cobrança de diferença fica para a v2 — ver seção 2).

### Observabilidade e conformidade mínimas
- Log de auditoria básico (RNF-01/02): tabela de log + escrita nas ações administrativas e financeiras principais (criação de tenant, alteração de gateway, mudança de preço de evento, confirmação manual em conciliação, cancelamento por staff/admin). Sem painel dedicado — consulta via endpoint simples.
- Conciliação manual de pagamento tardio pós-expiração (RF-12): endpoint simples que lista essas reservas para o `tenant_admin` decidir.

---

## 2. Fica para depois da v1 (pós-MVP)

| Item | Motivo de adiar |
|---|---|
| 2º gateway de pagamento (Mercado Pago, etc.) | Interface já é plugável; adicionar depois não exige retrabalho de arquitetura |
| Webhooks de saída para o tenant (RF-18) | Não bloqueia o fluxo core de agendamento + pagamento |
| Reagendamento com cobrança de diferença (RF-16 completo) | Reagendamento simples (mesmo preço) já cobre o caso mais comum |
| Exclusão de dados pessoais / LGPD (RNF-03) | Poucas contas reais no início; mecanismo pode entrar assim que houver base de clientes maior |
| Painel administrativo visual (auditoria, conciliação, branding) | Endpoints simples já destravam o uso; UI dedicada vem depois do frontend React |
| Interface web em React | MVP roda via API + Swagger; frontend entra numa fase seguinte |

---

## 3. Critério de "pronto" do MVP

O MVP está pronto quando, para **um tenant real**, o fluxo completo funcionar de ponta a ponta:

1. Tenant é criado e configurado (branding + credenciais EFI Bank).
2. `tenant_admin` cria um tipo de evento pago e define disponibilidade (incluindo ao menos uma regra recorrente).
3. Um `customer` se cadastra, autentica e reserva um slot.
4. Cobrança PIX é gerada, paga (ambiente sandbox EFI) e confirmada via webhook.
5. Reserva aparece como `confirmed`.
6. Cliente cancela a reserva; sistema libera o slot e marca reembolso como pendente de ação manual.
7. Uma tentativa de reserva em slot com cobrança expirada (não paga em 15 min) libera o slot corretamente (checagem lazy).
8. Toda ação relevante do passo a passo acima aparece no log de auditoria.

---

## 4. Ordem sugerida de implementação

1. Tenants + auth + papéis (base de tudo).
2. Eventos + disponibilidade (incluindo recorrência).
3. Booking + integração EFI Bank (PIX) + expiração lazy + webhook de confirmação.
4. Cancelamento + conciliação manual + auditoria.
5. Ajustes finais e testes de ponta a ponta com o fluxo do critério de "pronto" (seção 3).
