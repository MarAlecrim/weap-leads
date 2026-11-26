-- Números do Cesar (São Paulo). Rodar no weap_sdr DEPOIS do "1 - Rodar no banco.sql".
-- Troque NOME_DA_INSTANCIA_... pelo nome exato da instância na
--    Evolution (o mesmo que vai no Dados_Evolution do workflow de disparo desse número).
--    responsavel_whatsapp = celular PESSOAL do Cesar, que recebe os avisos de lead interessado.
--    O número 41 98513-4815 ainda não está conectado: deixe ativo = false até conectar.
INSERT INTO sdr_instancias (instancia, numero, responsavel_nome, responsavel_whatsapp, tipo, cidade, ufs, ativo) VALUES
  ('NOME_DA_INSTANCIA_1094', '5541985261094', 'Cesar', '5541997196127', 'prospeccao', 'São Paulo', '{SP}', true),
  ('NOME_DA_INSTANCIA_4815', '5541985134815', 'Cesar', '5541997196127', 'prospeccao', 'São Paulo', '{SP}', false)
ON CONFLICT (instancia) DO UPDATE SET
  numero = EXCLUDED.numero,
  responsavel_nome = EXCLUDED.responsavel_nome,
  responsavel_whatsapp = EXCLUDED.responsavel_whatsapp,
  cidade = EXCLUDED.cidade,
  ufs = EXCLUDED.ufs;

-- Quando o 4815 conectar:
-- UPDATE sdr_instancias SET ativo = true WHERE instancia = 'NOME_DA_INSTANCIA_4815';

-- Conferir:
SELECT instancia, numero, responsavel_nome, responsavel_whatsapp, ufs, ativo
  FROM sdr_instancias ORDER BY instancia;
