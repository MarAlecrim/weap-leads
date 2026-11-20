-- Base CNPJ da Receita Federal (dados abertos) para busca de leads
-- Roda no banco próprio do servidor leads01 (criado sozinho na 1ª subida do Docker).
-- Pode rodar de novo sem problema.

CREATE SCHEMA IF NOT EXISTS receita;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Tabelas de apoio (códigos -> descrição)
CREATE TABLE IF NOT EXISTS receita.cnaes          (codigo text PRIMARY KEY, descricao text);
CREATE TABLE IF NOT EXISTS receita.municipios     (codigo text PRIMARY KEY, nome text);
CREATE TABLE IF NOT EXISTS receita.qualificacoes  (codigo text PRIMARY KEY, descricao text);
CREATE TABLE IF NOT EXISTS receita.naturezas      (codigo text PRIMARY KEY, descricao text);

-- Empresa (dados comuns à matriz e às filiais)
CREATE TABLE IF NOT EXISTS receita.empresas (
  cnpj_basico       text PRIMARY KEY,
  razao_social      text,
  natureza_juridica text,
  capital_social    numeric,
  porte             text   -- 00 não informado, 01 micro, 03 pequeno porte, 05 demais
);

-- Opção pelo Simples Nacional e pelo MEI (arquivo Simples.zip da Receita)
CREATE TABLE IF NOT EXISTS receita.simples (
  cnpj_basico text PRIMARY KEY,
  simples     boolean NOT NULL,
  mei         boolean NOT NULL
);

-- Estabelecimento (cada CNPJ completo). Só entram ATIVOS dos estados escolhidos.
CREATE TABLE IF NOT EXISTS receita.estabelecimentos (
  cnpj            text PRIMARY KEY,           -- 14 dígitos
  cnpj_basico     text NOT NULL,
  matriz          boolean,
  nome_fantasia   text,
  data_abertura   date,
  cnae_principal  text,
  cnaes_secundarios text[],
  logradouro      text,
  numero          text,
  complemento     text,
  bairro          text,
  cep             text,
  uf              text,
  municipio       text,                        -- código Receita
  telefone1       text,                        -- DDD + número
  telefone2       text,
  email           text,
  atualizado_em   date                         -- mês da base importada
);
CREATE INDEX IF NOT EXISTS est_basico_idx  ON receita.estabelecimentos (cnpj_basico);
CREATE INDEX IF NOT EXISTS est_busca_idx   ON receita.estabelecimentos (uf, municipio, cnae_principal);
CREATE INDEX IF NOT EXISTS est_cnae2_idx   ON receita.estabelecimentos USING gin (cnaes_secundarios);
CREATE INDEX IF NOT EXISTS est_bairro_idx  ON receita.estabelecimentos USING gin (bairro gin_trgm_ops);
CREATE INDEX IF NOT EXISTS est_fantasia_idx ON receita.estabelecimentos USING gin (nome_fantasia gin_trgm_ops);

-- Sócios (o decisor). CPF vem mascarado pela própria Receita e NÃO é guardado.
CREATE TABLE IF NOT EXISTS receita.socios (
  id              bigserial PRIMARY KEY,
  cnpj_basico     text NOT NULL,
  tipo            text,      -- 1 pessoa jurídica, 2 pessoa física, 3 estrangeiro
  nome            text,
  qualificacao    text,      -- código (49 = sócio-administrador, 05 = administrador...)
  data_entrada    date,
  faixa_etaria    text
);
CREATE INDEX IF NOT EXISTS socios_basico_idx ON receita.socios (cnpj_basico);

-- Mapa nicho -> CNAEs (prefixo). Edite à vontade; o nicho é o mesmo de sdr_nichos.
CREATE TABLE IF NOT EXISTS receita.nicho_cnaes (
  nicho  text NOT NULL,
  cnae   text NOT NULL,       -- 7 dígitos, ou prefixo (ex.: '8630')
  rotulo text,
  PRIMARY KEY (nicho, cnae)
);
INSERT INTO receita.nicho_cnaes (nicho, cnae, rotulo) VALUES
 ('advocacia',   '6911701', 'Serviços advocatícios'),
 ('psicologia',  '8650003', 'Psicologia e psicanálise'),
 ('odontologia', '8630504', 'Atividade odontológica'),
 ('saude',       '8630503', 'Clínica médica ambulatorial (consultas)'),
 ('saude',       '8630501', 'Clínica ambulatorial com cirurgia'),
 ('saude',       '8630502', 'Clínica ambulatorial com exames'),
 ('saude',       '8650002', 'Nutrição'),
 ('saude',       '8650004', 'Fisioterapia'),
 ('saude',       '8650006', 'Fonoaudiologia'),
 ('saude',       '8650001', 'Enfermagem'),
 ('saude',       '8690901', 'Práticas integrativas'),
 ('arquitetura', '7111100', 'Serviços de arquitetura'),
 ('engenharia',  '7112000', 'Serviços de engenharia'),
 ('construcao',  '4120400', 'Construção de edifícios'),
 ('construcao',  '4330404', 'Pintura de edificações'),
 ('construcao',  '4330499', 'Acabamentos em construção'),
 ('construcao',  '4399199', 'Serviços especializados para construção'),
 ('oficina',     '4520001', 'Mecânica de veículos'),
 ('oficina',     '4520005', 'Lavagem e lubrificação'),
 ('oficina',     '4520002', 'Lanternagem e pintura'),
 ('contabilidade','6920601', 'Contabilidade'),
 ('estetica',    '9602502', 'Estética e beleza'),
 ('imobiliaria', '6821801', 'Corretagem de imóveis'),
 ('veterinaria', '7500100', 'Veterinária'),
 ('academia',    '9313100', 'Academias')
ON CONFLICT DO NOTHING;

-- Cidades que existem na base importada (atualizada no fim de cada importação)
CREATE TABLE IF NOT EXISTS receita.cidades (
  municipio text PRIMARY KEY, nome text, uf text, empresas int
);

-- Usuários da tela leads.weap.com.br (crie com: docker compose exec app php /app/criar-usuario.php nome senha)
CREATE TABLE IF NOT EXISTS public.app_usuarios (
  usuario    text PRIMARY KEY,
  senha_hash text NOT NULL,
  criado_em  timestamptz NOT NULL DEFAULT now()
);

-- Telefone com cara de celular (DDD + 9 + 8 dígitos): é o que tem chance de ter WhatsApp
CREATE OR REPLACE FUNCTION receita.celular(t text) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
  SELECT coalesce(t, '') ~ '^[1-9][0-9]9[0-9]{8}$'
$$;
CREATE INDEX IF NOT EXISTS est_cel_idx ON receita.estabelecimentos ((receita.celular(telefone1) OR receita.celular(telefone2)));
