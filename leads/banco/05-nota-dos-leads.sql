-- Fase 1: base da nota dos leads (semelhança com os clientes atuais).
-- Rodar uma vez depois do 04. A importação mensal recalcula n_socios sozinha.

-- Quantos sócios cada empresa tem (o "dono decide" da nota). Leva alguns minutos no PR inteiro.
ALTER TABLE receita.empresas ADD COLUMN IF NOT EXISTS n_socios smallint;
UPDATE receita.empresas emp
   SET n_socios = s.qtd
  FROM (SELECT cnpj_basico, least(count(*), 32767)::smallint AS qtd FROM receita.socios GROUP BY cnpj_basico) s
 WHERE s.cnpj_basico = emp.cnpj_basico;
UPDATE receita.empresas SET n_socios = 0 WHERE n_socios IS NULL;

-- Perfil de quem compra cada oferta, tirado dos clientes atuais achados na Receita.
-- oferta 'geral' = todos os clientes.
CREATE OR REPLACE VIEW receita.perfil_oferta AS
WITH c AS (
  SELECT unnest(cw.ofertas || '{geral}'::text[]) AS oferta, e.municipio, left(e.cnae_principal, 2) AS divisao,
         emp.porte, extract(year FROM age(current_date, e.data_abertura))::int AS anos
    FROM receita.clientes_weap cw
    JOIN receita.estabelecimentos e ON e.cnpj = cw.cnpj
    JOIN receita.empresas emp ON emp.cnpj_basico = e.cnpj_basico
)
SELECT oferta,
       count(*)                          AS clientes,
       array_agg(DISTINCT municipio)     AS municipios,
       array_agg(DISTINCT divisao)       AS divisoes,
       array_agg(DISTINCT porte)         AS portes,
       min(anos)                         AS anos_min,
       max(anos)                         AS anos_max
  FROM c GROUP BY oferta;

VACUUM (PARALLEL 0, ANALYZE) receita.empresas;

SELECT oferta, clientes, cardinality(municipios) AS cidades, cardinality(divisoes) AS ramos, portes, anos_min, anos_max
  FROM receita.perfil_oferta ORDER BY clientes DESC;
