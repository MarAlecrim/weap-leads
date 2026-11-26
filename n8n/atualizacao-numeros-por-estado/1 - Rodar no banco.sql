-- Números por estado (26/11/2026).
-- sdr_fila.uf: estado do lead (o CRM grava ao mandar para o disparo).
-- sdr_instancias.ufs: estados que o número atende. NULL = qualquer estado que nenhum outro número reservou.
ALTER TABLE sdr_fila ADD COLUMN IF NOT EXISTS uf text;
ALTER TABLE sdr_instancias ADD COLUMN IF NOT EXISTS ufs text[];

-- Leads que já estavam na fila vieram todos do Paraná (a base só tinha PR até 26/11).
UPDATE sdr_fila SET uf = 'PR' WHERE uf IS NULL AND origem = 'receita';

-- Exemplo, quando os números do Cesar estiverem na Evolution (troque pelos nomes reais):
-- INSERT INTO sdr_instancias (instancia, numero, responsavel_nome, responsavel_whatsapp, tipo, cidade, ufs)
-- VALUES ('Weap-Cesar-XXXX', '55119XXXXXXXX', 'Cesar', '<celular do Cesar com 55>', 'prospeccao', 'São Paulo', '{SP}');

-- Conferir:
SELECT instancia, responsavel_nome, ufs, ativo FROM sdr_instancias ORDER BY instancia;
SELECT uf, status, count(*) FROM sdr_fila GROUP BY 1, 2 ORDER BY 1, 2;
