-- Clientes atuais da Weap: base do "lookalike" (nota por semelhança com quem fechou).
-- Fonte: painel de hospedagem (CNPJ) + cobranças do Asaas, 20/11/2026.
-- Fora: Cesar Pires (não foi venda) e cobranças do próprio Márcio.
-- Ofertas: site, hospedagem, redes, sdr, simplestv, blog, sistema, manutencao.
-- Rodar quantas vezes quiser: esvazia e preenche a tabela de novo.

CREATE TABLE IF NOT EXISTS receita.clientes_weap (
  nome         text NOT NULL,
  cnpj         text,              -- 14 dígitos; NULL = procurar pela razão social
  busca_nome   text,              -- trecho da razão social p/ achar o CNPJ
  ofertas      text[] NOT NULL,
  valor_cents  int,               -- valor de referência (mensal ou da venda)
  ativo        boolean NOT NULL DEFAULT true
);
TRUNCATE receita.clientes_weap;

INSERT INTO receita.clientes_weap (nome, cnpj, busca_nome, ofertas, valor_cents, ativo) VALUES
 ('Frigorífico Origem',        '05342368000151', NULL, '{site,hospedagem}',            39970, true),
 ('Saúde Pinhais SPE',         '48430801000113', NULL, '{site,hospedagem}',            51516, true),
 ('Garage 03 (Diego Lemos)',   '61342519000142', NULL, '{site,hospedagem,redes}',      75000, true),
 ('Omniclin',                  '34501631000106', NULL, '{site,hospedagem}',            51516, false),
 ('Menina Chic Store',         '23196057000103', NULL, '{site,hospedagem}',             NULL, false),
 ('Soupex',                    '81183394000162', NULL, '{site,hospedagem}',            39880, true),
 ('AC Sul Comercial',          '13064801000162', NULL, '{site,hospedagem}',            68400, true),
 ('Karatê Shubu-do',           '10345865000143', NULL, '{site,hospedagem}',            37494, true),
 ('Igreja Trinity',            '51113749000186', NULL, '{site,hospedagem,manutencao}', 106033, true),
 ('Agência Papai Noel',        '41529091000134', NULL, '{site,hospedagem}',             2990, false),
 ('Recarga (E.s.l. Vendas)',   '51300414000177', NULL, '{site,hospedagem}',            10655, false),
 ('Abs Logística',             '00092446000193', NULL, '{site,hospedagem}',            39468, true),
 ('GoldenIT',                  '03441246000197', NULL, '{site,hospedagem,manutencao}', 20800, true),
 ('PCA Consultoria',           NULL, 'PCA CONSULTORIA E CORRETAGEM',   '{sdr}',                 30000, true),
 ('Soreluz',                   NULL, 'SORELUZ LOCACAO DE GUINDASTES',  '{manutencao}',          37500, true),
 ('R J dos Santos Imobiliária',NULL, 'R J DOS SANTOS IMOBILIARIA',     '{simplestv}',          110000, true),
 ('Sodivel',                   NULL, 'SODIVEL HIDRAULICA',             '{sistema,simplestv}',   36000, true),
 ('EOS Advogados',             NULL, 'EOS SERVICOS DE ASSESSORIA',     '{blog}',                25000, true);

-- Acha o CNPJ (matriz) de quem só tem o nome.
UPDATE receita.clientes_weap c
   SET cnpj = (SELECT e.cnpj
                 FROM receita.empresas emp
                 JOIN receita.estabelecimentos e ON e.cnpj_basico = emp.cnpj_basico
                WHERE emp.razao_social ILIKE c.busca_nome || '%'
                ORDER BY e.matriz DESC NULLS LAST LIMIT 1)
 WHERE c.cnpj IS NULL;

-- Perfil de cada cliente na Receita (só aparece quem está na base importada: hoje só PR).
CREATE OR REPLACE VIEW receita.perfil_clientes AS
SELECT c.nome, c.ofertas, c.ativo, c.cnpj,
       e.cnae_principal, cn.descricao AS cnae_descricao,
       emp.porte, emp.capital_social,
       extract(year FROM age(current_date, e.data_abertura))::int AS anos,
       m.nome AS cidade, e.uf, e.bairro,
       (SELECT count(*) FROM receita.socios s WHERE s.cnpj_basico = e.cnpj_basico) AS socios,
       (e.cnpj IS NOT NULL) AS achou_na_receita
  FROM receita.clientes_weap c
  LEFT JOIN receita.estabelecimentos e ON e.cnpj = c.cnpj
  LEFT JOIN receita.empresas emp ON emp.cnpj_basico = e.cnpj_basico
  LEFT JOIN receita.cnaes cn ON cn.codigo = e.cnae_principal
  LEFT JOIN receita.municipios m ON m.codigo = e.municipio;

SELECT nome, achou_na_receita AS achou, cnae_principal, left(cnae_descricao, 40) AS atividade,
       porte, capital_social, anos, cidade, uf, socios
  FROM receita.perfil_clientes ORDER BY achou_na_receita DESC, nome;
