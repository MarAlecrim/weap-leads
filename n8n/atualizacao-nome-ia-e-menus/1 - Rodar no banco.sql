-- Nome com que a IA se apresenta (no disparo e na conversa). O especialista continua em responsavel_nome.
ALTER TABLE sdr_instancias ADD COLUMN IF NOT EXISTS nome_ia text NOT NULL DEFAULT 'Cláudio';

-- Conferir:
SELECT instancia, nome_ia, responsavel_nome, ativo FROM sdr_instancias ORDER BY instancia;
