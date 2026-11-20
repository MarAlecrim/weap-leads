-- Feriados: o disparo não manda mensagem nesses dias (o agente continua respondendo quem chamar).
-- Rodar uma vez no banco weap_sdr (node Postgres do n8n). Pode rodar de novo sem problema.
-- Lista única para todos os números: nacionais + Curitiba + Londrina + vésperas de Natal e Ano Novo.
-- Para incluir um dia: INSERT INTO sdr_feriados VALUES ('2027-07-26', 'Motivo');

CREATE TABLE IF NOT EXISTS sdr_feriados (
  data  date PRIMARY KEY,
  nome  text NOT NULL
);

INSERT INTO sdr_feriados (data, nome) VALUES
 ('2026-01-01','Confraternização Universal'),
 ('2026-02-16','Carnaval'),
 ('2026-02-17','Carnaval'),
 ('2026-04-03','Sexta-feira Santa'),
 ('2026-04-21','Tiradentes'),
 ('2026-05-01','Dia do Trabalho'),
 ('2026-06-04','Corpus Christi'),
 ('2026-09-07','Independência'),
 ('2026-09-08','Nossa Senhora da Luz (Curitiba)'),
 ('2026-10-12','Nossa Senhora Aparecida'),
 ('2026-11-02','Finados'),
 ('2026-11-15','Proclamação da República'),
 ('2026-11-20','Consciência Negra'),
 ('2026-12-10','Aniversário de Londrina'),
 ('2026-12-24','Véspera de Natal'),
 ('2026-12-25','Natal'),
 ('2026-12-31','Véspera de Ano Novo'),
 ('2027-01-01','Confraternização Universal'),
 ('2027-02-08','Carnaval'),
 ('2027-02-09','Carnaval'),
 ('2027-03-26','Sexta-feira Santa'),
 ('2027-04-21','Tiradentes'),
 ('2027-05-01','Dia do Trabalho'),
 ('2027-05-27','Corpus Christi'),
 ('2027-09-07','Independência'),
 ('2027-09-08','Nossa Senhora da Luz (Curitiba)'),
 ('2027-10-12','Nossa Senhora Aparecida'),
 ('2027-11-02','Finados'),
 ('2027-11-15','Proclamação da República'),
 ('2027-11-20','Consciência Negra'),
 ('2027-12-10','Aniversário de Londrina'),
 ('2027-12-24','Véspera de Natal'),
 ('2027-12-25','Natal'),
 ('2027-12-31','Véspera de Ano Novo')
ON CONFLICT (data) DO NOTHING;

-- Nome do feriado de hoje (horário de Brasília), ou NULL em dia normal.
CREATE OR REPLACE FUNCTION sdr_feriado_hoje() RETURNS text LANGUAGE sql STABLE AS $$
  SELECT nome FROM sdr_feriados WHERE data = (now() AT TIME ZONE 'America/Sao_Paulo')::date
$$;

SELECT count(*) AS feriados_cadastrados, sdr_feriado_hoje() AS hoje FROM sdr_feriados;
