-- =====================================================================
-- Weap SDR - banco do agente de WhatsApp (Postgres)
-- Rodar uma vez no Postgres do n8n (ou num banco separado).
-- Pode rodar de novo sem perder dados (usa IF NOT EXISTS / ON CONFLICT).
-- =====================================================================

-- ---------- Configuração geral ----------
CREATE TABLE IF NOT EXISTS sdr_config (
  chave text PRIMARY KEY,
  valor text,
  descricao text
);

INSERT INTO sdr_config (chave, valor, descricao) VALUES
 ('evolution_url',     'https://SUA-EVOLUTION.com.br', 'URL da Evolution API, sem barra no final'),
 ('instancia_avisos',  'PREENCHER',                    'Instância (número) que manda os avisos para os responsáveis'),
 ('webhook_base',      'https://SEU-N8N.com.br/webhook','URL pública dos webhooks do n8n, sem barra no final'),
 ('midia_no_disparo',  'nao',                          'sim = manda a mídia do nicho junto do 1º contato/recontato'),
 ('espera_especialista_min', '10',                     'Minutos que a IA espera o especialista chamar o lead antes de reassumir e oferecer horários')
ON CONFLICT (chave) DO NOTHING;

-- ---------- Números (instâncias da Evolution) ----------
-- tipo: 'prospeccao' = só responde quem está na tabela de leads (quem recebeu disparo)
--       'trafego'    = responde qualquer pessoa (lead que veio do anúncio)
-- modo_agenda: 'sugerir' = IA propõe horário e o responsável confirma por um link
--              'automatico' = IA marca sozinha na agenda
CREATE TABLE IF NOT EXISTS sdr_instancias (
  instancia            text PRIMARY KEY,
  numero               text,          -- número de WhatsApp desta instância (55 + DDD + número)
  responsavel_nome     text NOT NULL,
  responsavel_whatsapp text NOT NULL,
  tipo                 text NOT NULL DEFAULT 'prospeccao' CHECK (tipo IN ('prospeccao','trafego')),
  cidade               text,
  agenda_id            text,
  modo_agenda          text NOT NULL DEFAULT 'sugerir' CHECK (modo_agenda IN ('sugerir','automatico')),
  horarios             jsonb NOT NULL DEFAULT '{"dias":[1,2,3,4,5],"inicio":"09:00","fim":"18:00","almoco":["12:00","13:30"],"duracao":30,"antecedencia_horas":3}',
  ativo                boolean NOT NULL DEFAULT true
);

ALTER TABLE sdr_instancias ADD COLUMN IF NOT EXISTS numero text;

-- EXEMPLO (troque pelos nomes reais das instâncias na Evolution e pelos números reais):
-- responsavel_whatsapp = celular PESSOAL de quem recebe os avisos (não pode ser o número da própria instância)
-- INSERT INTO sdr_instancias (instancia, numero, responsavel_nome, responsavel_whatsapp, tipo, cidade, agenda_id) VALUES
--  ('fabiano',  '5543900000001', 'Fabiano', '5543999990000', 'prospeccao', 'Londrina', 'ID_DA_AGENDA_WEAP_LONDRINA@group.calendar.google.com'),
--  ('alvaro',   '5543900000002', 'Álvaro',  '5543999990001', 'prospeccao', 'Londrina', 'ID_DA_AGENDA_WEAP_LONDRINA@group.calendar.google.com'),
--  ('curitiba1','5541900000003', 'Márcio',  '5541999990002', 'prospeccao', 'Curitiba', 'ID_DA_AGENDA_WEAP_CURITIBA@group.calendar.google.com'),
--  ('curitiba2','5541900000004', 'Márcio',  '5541999990002', 'prospeccao', 'Curitiba', 'ID_DA_AGENDA_WEAP_CURITIBA@group.calendar.google.com'),
--  ('trafego',  '5541900000005', 'Márcio',  '5541999990002', 'trafego',    'Curitiba', 'ID_DA_AGENDA_WEAP_CURITIBA@group.calendar.google.com');

-- ---------- Nichos ----------
-- palavras: pedaços de texto procurados (sem acento e minúsculo) nas especialidades do Google Maps
CREATE TABLE IF NOT EXISTS sdr_nichos (
  nicho      text PRIMARY KEY,
  prioridade int  NOT NULL DEFAULT 100,
  palavras   text[] NOT NULL DEFAULT '{}',
  regras     text,
  frentes    text
);

INSERT INTO sdr_nichos (nicho, prioridade, palavras, regras, frentes) VALUES
 ('advocacia', 10, '{advogad,advocacia,juridic,direito}',
  'Advogados seguem o Código de Ética da OAB e o Provimento 205/2021: publicidade só informativa, sem captação de clientela, sem promessa de resultado, sem citar valores e sem mercantilização. Nunca sugira anúncio que "capte clientes" ou fale em "vender mais"; fale em ser encontrado, transmitir autoridade e informar.',
  'site institucional, conteúdo informativo nas redes, Google Meu Negócio'),
 ('psicologia', 20, '{psicolog,psicoterap,terapia,terapeut,psicanal}',
  'Psicólogos seguem o Código de Ética do CFP e a Resolução CFP 3/2022 (publicidade): sem promessa de cura ou resultado, sem depoimentos de pacientes, sem sensacionalismo. Tom acolhedor e discreto.',
  'site, conteúdo educativo nas redes, Google Meu Negócio'),
 ('odontologia', 20, '{dentist,odonto,ortodont,implant}',
  'Dentistas seguem as regras do CFO (Resolução CFO 196/2019): sem antes e depois sem as regras do conselho, sem preço ou promoção, sem promessa de resultado. Toda comunicação precisa do nome e CRO do responsável técnico.',
  'site, gestão de redes, Google Meu Negócio, tráfego pago'),
 ('saude', 30, '{medic,clinica,fisioterap,nutricion,fonoaud,saude,estetic,dermat,pediatr}',
  'Profissionais de saúde seguem seus conselhos (CFM, CREFITO, CFN etc.): sem promessa de resultado, sem preço ou promoção, sem sensacionalismo, sem depoimentos de pacientes quando o conselho proíbe.',
  'site, gestão de redes, Google Meu Negócio'),
 ('arquitetura', 40, '{arquitet,interiores,paisag}',
  'Arquitetos seguem o Código de Ética do CAU: sem preço vil, sem promessa de resultado; portfólio de projetos é bem-vindo.',
  'site com portfólio, gestão de redes, manual de marca'),
 ('engenharia', 40, '{engenh,topograf,projeto estrutural,laudo}',
  'Engenheiros seguem o Código de Ética do CREA/Confea: comunicação técnica, sem promessa de resultado.',
  'site institucional, Google Meu Negócio, manual de marca'),
 ('construcao', 50, '{construtora,construcao,reforma,incorporad,empreiteir,obra}',
  'Sem promessa de prazo ou preço. Fotos de obras entregues ajudam a passar confiança.',
  'site com obras, tráfego pago, gestão de redes'),
 ('oficina', 50, '{oficina,mecanic,auto center,autocenter,funilaria,auto eletric}',
  'Sem promessa de preço. Confiança e transparência são o ponto central do segmento.',
  'site, Google Meu Negócio, tráfego pago'),
 ('geral', 999, '{}', 'Sem promessa de resultado, sem preço.',
  'site, gestão de redes, tráfego pago, manual de marca')
ON CONFLICT (nicho) DO NOTHING;

-- ---------- Mídias (imagens e vídeos por nicho) ----------
-- url: link público (ex.: bucket R2 weap-midia). Vídeos até ~30 s e 16 MB, mp4.
CREATE TABLE IF NOT EXISTS sdr_midias (
  id               serial PRIMARY KEY,
  nicho            text NOT NULL DEFAULT 'geral',
  tipo             text NOT NULL CHECK (tipo IN ('image','video')),
  url              text NOT NULL,
  descricao        text NOT NULL,   -- a IA lê isto para decidir quando mandar
  legenda          text,            -- texto que vai junto da mídia (opcional)
  usar_no_disparo  boolean NOT NULL DEFAULT false,
  ativo            boolean NOT NULL DEFAULT true
);

-- EXEMPLO:
-- INSERT INTO sdr_midias (nicho, tipo, url, descricao, legenda) VALUES
--  ('oficina', 'video', 'https://midia.weap.com.br/cases/garage03.mp4',
--   'Vídeo curto do case Garage 03 (site + Instagram de uma oficina)', 'Esse é um dos trabalhos que fizemos para uma oficina 🙂');

-- ---------- Leads ----------
CREATE TABLE IF NOT EXISTS sdr_leads (
  id                  bigserial PRIMARY KEY,
  chave               text UNIQUE NOT NULL,   -- 55 + DDD + 8 últimos dígitos (resolve o 9º dígito)
  telefone            text,                   -- como veio da planilha
  whatsapp            text,                   -- número exato que o WhatsApp usa (vem da 1ª resposta)
  instancia           text,                   -- número da Weap que conversa com o lead
  nome_empresa        text,
  nome_contato        text,
  especialidades      text,
  nicho               text NOT NULL DEFAULT 'geral',
  origem              text NOT NULL DEFAULT 'prospeccao',
  planilha            text,
  status              text NOT NULL DEFAULT 'contatado',
  primeira_mensagem   text,
  ultima_mensagem_enviada text,
  contatos_enviados   int  NOT NULL DEFAULT 0,
  resumo              text,
  ia_pausada          boolean NOT NULL DEFAULT false,
  opt_out             boolean NOT NULL DEFAULT false,
  horario_proposto    timestamptz,
  token               text,
  evento_id           text,
  link_reuniao        text,
  ultimo_contato_em   timestamptz,
  ultima_resposta_em  timestamptz,
  criado_em           timestamptz NOT NULL DEFAULT now(),
  atualizado_em       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sdr_leads_status ON sdr_leads (status);
ALTER TABLE sdr_leads ADD COLUMN IF NOT EXISTS chamado_em timestamptz;  -- quando o lead aceitou falar com o especialista agora

-- ---------- Mensagens (histórico da conversa = memória do agente) ----------
CREATE TABLE IF NOT EXISTS sdr_mensagens (
  id         bigserial PRIMARY KEY,
  lead_id    bigint REFERENCES sdr_leads(id) ON DELETE CASCADE,
  instancia  text,
  direcao    text NOT NULL CHECK (direcao IN ('in','out')),
  autor      text NOT NULL CHECK (autor IN ('lead','ia','disparo','humano')),
  texto      text,
  msg_id     text,
  criado_em  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sdr_mensagens_lead ON sdr_mensagens (lead_id, id);
CREATE INDEX IF NOT EXISTS sdr_mensagens_msgid ON sdr_mensagens (msg_id);

-- ---------- Funções ----------
-- Chave do telefone: 55 + DDD + 8 últimos dígitos. Assim "43 99999-8888" e "554399998888" batem.
CREATE OR REPLACE FUNCTION sdr_chave(t text) RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE
    WHEN d IS NULL OR length(d) < 10 THEN NULL
    ELSE '55' || substr(d, 1, 2) || right(d, 8)
  END
  FROM (
    SELECT CASE WHEN length(x) >= 12 AND left(x, 2) = '55' THEN substr(x, 3) ELSE ltrim(x, '0') END AS d
    FROM (SELECT regexp_replace(coalesce(t, ''), '\D', '', 'g') AS x) a
  ) b
$$;

-- Descobre o nicho pelas especialidades do Google Maps
CREATE OR REPLACE FUNCTION sdr_nicho(esp text) RETURNS text LANGUAGE sql STABLE AS $$
  SELECT coalesce((
    SELECT n.nicho FROM sdr_nichos n
    WHERE EXISTS (
      SELECT 1 FROM unnest(n.palavras) p
      WHERE translate(lower(coalesce(esp, '')), 'áàâãäéèêëíìîïóòôõöúùûüç', 'aaaaaeeeeiiiiooooouuuuc') LIKE '%' || p || '%'
    )
    ORDER BY n.prioridade LIMIT 1
  ), 'geral')
$$;

-- Status que significam "já está conversando": o disparo não manda recontato para eles
CREATE OR REPLACE FUNCTION sdr_em_conversa(s text) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
  SELECT s IN ('respondeu','interessado','agendamento_pendente','agendado','humano','sem_interesse','bot')
$$;

-- Números da própria Weap (instâncias e responsáveis): o agente nunca trata esses números como lead
CREATE OR REPLACE FUNCTION sdr_interno(t text) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM sdr_instancias i
     WHERE sdr_chave(i.numero) = sdr_chave(t) OR sdr_chave(i.responsavel_whatsapp) = sdr_chave(t)
  )
$$;

-- ---------- Visão do funil (para olhar no dia a dia) ----------
CREATE OR REPLACE VIEW sdr_funil AS
SELECT l.instancia, l.nicho, l.status, count(*) AS leads
FROM sdr_leads l GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;
