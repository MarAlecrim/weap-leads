# Plano: leads, score e CRM da Weap

Documento vivo (com comentários): https://claude.ai/artifact/CFAYmeSnwGc2GuLzDSaJd8

## Resumo

O leads.weap.com.br vira o mini CRM da Weap: dá nota aos leads aprendendo com quem já fechou, controla o funil de cada lead e, no fim, junta os 5 números de WhatsApp numa caixa única.

## Machine learning em três degraus

1. **Semelhança com quem fechou (lookalike):** CNPJs dos clientes atuais (painel de hospedagem) cruzados com a Receita; nota por grupo de CNAE, porte, idade, capital, cidade e MEI.
2. **Pesos ajustados pelo funil:** cada resposta, interesse, reunião e fechamento vira exemplo. Primeiro alvo: "vai responder com interesse".
3. **Modelo treinado:** com ~300 respostas e ~30 fechamentos, regressão logística ou gradient boosting em Python, retreinado todo mês. A tela mostra os motivos da nota.

Decisor por regra: 1 sócio = ele; vários = sócio-administrador; senão "confirmar na conversa".

## Stack

CRM novo em Python FastAPI (backend) + React (frontend), a partir do modelo do leads-filter-fullstack, em `leads/crm/`. Ele substitui a tela PHP no mesmo endereço leads.weap.com.br (decisão do Gab, 20/11/2026: uma interface só).

## Fases

0. Fechar o que está no ar (Gab).
1. Ligar weap_sdr pela rede interna, importar Simples/MEI (feito em 20/11: filtro MEI/ME/EPP/média/grande + capital social), cadastrar clientes atuais, nota de semelhança por oferta.
2. Mini CRM (Novo, No disparo, Respondeu, Interessado, Reunião, Proposta, Fechado, Perdido; responsável; notas; próxima ação) e "Mandar para o disparo" (checa WhatsApp na Evolution, fila única com rodízio dos 5 números).
3. Caixa única do WhatsApp: fila "Precisa de você", resumo e intenção por IA, responder pela tela.
4. Modelo de ML.
5. CRM completo (referência: DeskCom).

## Atendimento por estado (26/11/2026)

Cada número de WhatsApp pode ficar com um ou mais estados (`sdr_instancias.ufs`). Número com estados só dispara para leads desses estados; número sem estados dispara para os demais. Estado exclusivo não vaza para outro atendente, nem com o número desligado. O aviso de lead interessado vai para o celular do responsável pelo número.

Primeiro caso: São Paulo com o Cesar, números 41 98526-1094 (conectado) e 41 98513-4815 (a conectar), avisos no celular dele. A busca tem filtro por estado. Importação da Receita: RS antes de SP.

Instalação: `n8n/atualizacao-atendimento-por-estado/LEIA-ME.md`.

