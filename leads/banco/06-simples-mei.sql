-- Simples Nacional e MEI (arquivo Simples.zip da Receita). Rodar uma vez; depois a carga é feita
-- pelo importador (importar-simples.sh na primeira vez, importar.sh todo mês).
CREATE TABLE IF NOT EXISTS receita.simples (
  cnpj_basico text PRIMARY KEY,
  simples     boolean NOT NULL,
  mei         boolean NOT NULL
);
-- filtro de capital social
CREATE INDEX IF NOT EXISTS emp_capital_idx ON receita.empresas (capital_social);
