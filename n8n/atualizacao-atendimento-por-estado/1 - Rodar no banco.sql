-- Atendimento por estado. Rodar uma vez no banco weap_sdr, como administrador.
-- Pode rodar de novo sem problema (só cria o que falta).

-- 1) Quais estados cada número atende.
--    Vazio (NULL) = número geral: atende os leads dos estados que NÃO são exclusivos de algum número.
--    Preenchido (ex.: '{SP}') = só atende leads desses estados, e esses estados ficam só com ele.
ALTER TABLE sdr_instancias ADD COLUMN IF NOT EXISTS ufs text[];

-- 2) Estado do lead na fila do disparo (o CRM passa a gravar). Leads antigos ficam sem estado
--    e saem pelos números gerais, como hoje.
ALTER TABLE sdr_fila ADD COLUMN IF NOT EXISTS uf text;
CREATE INDEX IF NOT EXISTS sdr_fila_uf_idx ON sdr_fila (status, uf, nota DESC, id);

-- 3) Regra: este número pode pegar um lead deste estado?
--    Número que não está em sdr_instancias conta como geral.
--    Estado exclusivo continua exclusivo mesmo com o número desligado (ativo = false):
--    os leads esperam na fila em vez de ir para outro atendente.
CREATE OR REPLACE FUNCTION sdr_atende_uf(p_instancia text, p_uf text) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT coalesce(
    -- número com estados próprios: só os dele (lead sem estado não vai para ele)
    (SELECT coalesce(p_uf = ANY(i.ufs), false)
       FROM sdr_instancias i
      WHERE i.instancia = p_instancia AND coalesce(cardinality(i.ufs), 0) > 0),
    -- número geral: tudo, menos os estados exclusivos de outro número
    p_uf IS NULL OR NOT EXISTS (
      SELECT 1 FROM sdr_instancias o
       WHERE o.instancia <> p_instancia AND p_uf = ANY(o.ufs)))
$$;

-- Conferir:
SELECT instancia, numero, responsavel_nome, responsavel_whatsapp, ufs, ativo
  FROM sdr_instancias ORDER BY instancia;
