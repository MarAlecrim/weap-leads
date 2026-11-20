-- Rodar no banco do AGENTE (weap_sdr, servidor do n8n), pelo node Postgres como antes.
-- Guarda de onde o lead veio e o nome do decisor. Pode rodar de novo sem problema.
ALTER TABLE sdr_leads ADD COLUMN IF NOT EXISTS cnpj text;
ALTER TABLE sdr_leads ADD COLUMN IF NOT EXISTS decisor text;

-- Usuário só de leitura para a tela leads.weap.com.br marcar quem já está no disparo.
-- Troque a senha abaixo antes de rodar e coloque a mesma no .env do leads01 (AGENTE_DB_PASSWORD).
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'leads_leitura') THEN
    CREATE ROLE leads_leitura LOGIN PASSWORD 'TROQUE_ESTA_SENHA';
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO leads_leitura;
GRANT SELECT ON sdr_leads TO leads_leitura;
