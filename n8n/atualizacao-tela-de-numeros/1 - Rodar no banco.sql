-- Tela "Números de WhatsApp" no Admin do CRM. Rodar uma vez no banco weap_sdr, como administrador,
-- depois do n8n/atualizacao-atendimento-por-estado/1 - Rodar no banco.sql. Pode rodar de novo.
-- Deixa o usuário do CRM (leads_crm) cadastrar números e mudar estados, responsável, celular de
-- aviso e ligado/desligado. Ele continua sem poder apagar números nem mexer nas outras colunas
-- (agenda, horários, nome da IA).

GRANT UPDATE (numero, responsavel_nome, responsavel_whatsapp, cidade, ufs, ativo)
   ON sdr_instancias TO leads_crm;
GRANT INSERT (instancia, numero, responsavel_nome, responsavel_whatsapp, tipo, cidade, ufs, ativo)
   ON sdr_instancias TO leads_crm;
