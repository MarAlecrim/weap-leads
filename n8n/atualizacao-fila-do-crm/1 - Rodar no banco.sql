-- Fila do disparo alimentada pelo CRM (leads.weap.com.br). Rodar no banco weap_sdr, como administrador.
-- O CRM só consegue INSERIR nesta tabela (e ler o resto). Quem tira da fila é o workflow de disparo.

CREATE TABLE IF NOT EXISTS sdr_fila (
  id             bigserial PRIMARY KEY,
  chave          text NOT NULL UNIQUE,              -- sdr_chave(telefone): um lead entra uma vez só
  telefone       text NOT NULL,                     -- 55 + DDD + número + @s.whatsapp.net (igual à planilha)
  nome_empresa   text,
  endereco       text,
  cidade         text,
  website        text,
  especialidades text,                              -- atividade (CNAE) da Receita
  decisor        text,
  email          text,
  cnpj           text,
  nota           int NOT NULL DEFAULT 0,            -- nota do CRM (0 a 100): a fila sai da maior para a menor
  origem         text NOT NULL DEFAULT 'receita',
  criado_por     text,
  criado_em      timestamptz NOT NULL DEFAULT now(),
  status         text NOT NULL DEFAULT 'novo' CHECK (status IN ('novo','pegando','enviado','pulado','erro')),
  tentativas     int NOT NULL DEFAULT 0,
  instancia      text,
  pego_em        timestamptz,
  enviado_em     timestamptz,
  motivo         text,
  mensagem       text
);
CREATE INDEX IF NOT EXISTS sdr_fila_proximo_idx ON sdr_fila (status, nota DESC, id);

-- Usuário do CRM: lê tudo e só insere na fila (a senha é definida no servidor, fora deste arquivo)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'leads_crm') THEN
    CREATE ROLE leads_crm NOLOGIN;
  END IF;
END $$;
GRANT CONNECT ON DATABASE weap_sdr TO leads_crm;
GRANT USAGE ON SCHEMA public TO leads_crm;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO leads_crm;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO leads_crm;
GRANT INSERT ON sdr_fila TO leads_crm;
GRANT USAGE ON SEQUENCE sdr_fila_id_seq TO leads_crm;
