# Weap Leads

Prospecção própria da Weap: base de empresas da Receita Federal, nota de cada lead, mini CRM e o disparo/agente de WhatsApp no n8n.

No ar em **https://leads.weap.com.br** (tela PHP) e, a partir da fase 1, **https://crm.weap.com.br** (CRM novo em FastAPI + React). Servidor Hetzner "crm", pasta `/opt/weap-leads`.

## Pastas

| Pasta | O que tem |
| --- | --- |
| `leads/` | Tela de busca antiga (PHP 8.3 + Postgres 16 + Caddy em docker compose) e o importador mensal da Receita |
| `leads/crm/` | CRM novo: `backend/` (FastAPI, SQLModel, Alembic) e `frontend/` (React, TanStack, shadcn). Guia: `docs/instalacao-crm.md` |
| `n8n/` | Workflows do disparo e do agente de WhatsApp (banco `weap_sdr`) e as atualizações para colar nos nodes |
| `docs/` | Guias de instalação, plano e prévias das telas |

## Plano

Fases (detalhe em `docs/plano.md`):

0. Fechar o que está no ar (zip novo, SQL 03, cron mensal, disparo sem repetir)
1. Ligar o banco do agente, importar Simples/MEI e dar nota por semelhança com os clientes atuais
2. Mini CRM (funil, responsável, notas) e disparo lendo do banco, sem planilha
3. Caixa única dos 5 números de WhatsApp, com fila manual, resumo e intenção
4. Modelo de machine learning treinado com o funil
5. CRM completo

## Regras

- Senhas e chaves (banco, Evolution, OpenAI) ficam só no `.env` do servidor ou nas credenciais do n8n. Nos JSON do n8n, a chave aparece como `COLOQUE_A_CHAVE_NO_N8N`.
- Nunca rodar `docker volume prune` nem `docker compose down -v` no servidor: apaga o banco.
- CPF dos sócios não é guardado.
