-- =====================================================================
-- Caixa de conversas do CRM: o CRM passa a gravar a resposta de quem
-- escreve pela caixa (autor 'humano') e a pausar/retomar a IA do lead.
-- Rodar uma vez no banco weap_sdr, como dono das tabelas (postgres).
-- Só dá ao usuário do CRM (leads_crm) o mínimo: inserir mensagem e mexer
-- em 4 colunas de sdr_leads. Ele continua sem apagar nada.
-- =====================================================================

GRANT INSERT ON sdr_mensagens TO leads_crm;
GRANT USAGE ON SEQUENCE sdr_mensagens_id_seq TO leads_crm;
GRANT UPDATE (ia_pausada, status, ultimo_contato_em, atualizado_em) ON sdr_leads TO leads_crm;

-- conferência: deve mostrar INSERT em sdr_mensagens e UPDATE nas 4 colunas
SELECT table_name, privilege_type FROM information_schema.role_table_grants
 WHERE grantee = 'leads_crm' AND table_name IN ('sdr_mensagens', 'sdr_leads');
SELECT column_name, privilege_type FROM information_schema.column_privileges
 WHERE grantee = 'leads_crm' AND table_name = 'sdr_leads' AND privilege_type = 'UPDATE';
