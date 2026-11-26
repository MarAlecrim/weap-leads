-- Números escolhidos por lista de disparo. Rodar uma vez no banco weap_sdr, como administrador,
-- DEPOIS do n8n/atualizacao-atendimento-por-estado/1 - Rodar no banco.sql. Pode rodar de novo.

-- Números que podem disparar para este lead, escolhidos no CRM ("Mandar para o disparo").
-- Vazio (NULL) = automático, pela regra de estados (sdr_atende_uf).
ALTER TABLE sdr_fila ADD COLUMN IF NOT EXISTS instancias text[];

-- Regra completa: este número pode pegar este lead da fila?
-- Se a lista escolheu números, só eles (mesmo fora dos estados de cada um: a escolha manda).
-- Se não escolheu, vale a regra de estados.
CREATE OR REPLACE FUNCTION sdr_pode_pegar(p_instancia text, p_uf text, p_instancias text[]) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT CASE
    WHEN coalesce(cardinality(p_instancias), 0) > 0 THEN p_instancia = ANY(p_instancias)
    ELSE coalesce(sdr_atende_uf(p_instancia, p_uf), false)
  END
$$;
