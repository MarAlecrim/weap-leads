-- Disparo de oficinas (número 41 98861-0859) com o case Garage 03.
-- Rodar no banco weap_sdr (servidor do n8n). Pode rodar mais de uma vez.

BEGIN;

-- 1) Mídias do case Garage 03 (arquivos servidos pelo CRM em leads.weap.com.br/midia/)
--    A imagem vai junto do 1º contato do disparo de oficinas (usar_no_disparo = true).
--    O vídeo fica para o agente mandar quando o lead quiser ver mais.
INSERT INTO sdr_midias (nicho, tipo, url, descricao, legenda, usar_no_disparo)
SELECT 'oficina', 'image', 'https://leads.weap.com.br/midia/garage03-case.jpg',
       'Imagem do case Garage 03: o site (garage03.com.br) e o Instagram (@garage_03_autocenter) que a WEAP fez para uma oficina mecânica de Curitiba.',
       'Garage 03, oficina de Curitiba: site e Instagram feitos pela WEAP.',
       true
 WHERE NOT EXISTS (SELECT 1 FROM sdr_midias WHERE url = 'https://leads.weap.com.br/midia/garage03-case.jpg');

INSERT INTO sdr_midias (nicho, tipo, url, descricao, legenda, usar_no_disparo)
SELECT 'oficina', 'video', 'https://leads.weap.com.br/midia/garage03-case.mp4',
       'Vídeo de 16 segundos mostrando por dentro o site e o Instagram da Garage 03 rolando no celular. Mande quando a pessoa quiser ver mais, perguntar como funciona ou como ficaria para a oficina dela.',
       'O site e o Instagram da Garage 03 por dentro.',
       false
 WHERE NOT EXISTS (SELECT 1 FROM sdr_midias WHERE url = 'https://leads.weap.com.br/midia/garage03-case.mp4');

-- 2) Regras do nicho oficina: é isto que o agente "03 - Agente Weap WhatsApp" lê
--    ao responder um lead de oficina (não muda nada para os outros nichos).
UPDATE sdr_nichos
   SET regras = 'Oficinas mecânicas, auto centers e funilarias. Sem promessa de preço ou de resultado. '
             || 'Confiança e orçamento claro são o centro do segmento. '
             || 'Use como exemplo o case Garage 03: oficina de Curitiba (Boqueirão), desde 2003; a WEAP fez o site garage03.com.br '
             || '(serviços, promoções com preço claro, passo a passo do atendimento e agendamento pelo WhatsApp) e cuida do Instagram '
             || '@garage_03_autocenter (posts de serviço com preço, dicas e vídeos do dono na oficina). '
             || 'Nunca invente números de resultado da Garage 03 (clientes, vendas, seguidores). '
             || 'Seja objetivo: respostas curtas, uma pergunta por vez, fale a língua do dono da oficina (cliente, carro, orçamento, agenda) '
             || 'e, com interesse, leve para conversar com o especialista.',
       frentes = 'site com agendamento pelo WhatsApp, gestão do Instagram (posts de serviço, preço e dicas), Google Meu Negócio'
 WHERE nicho = 'oficina';

COMMIT;

-- Conferir:
-- SELECT id, nicho, tipo, url, usar_no_disparo, ativo FROM sdr_midias WHERE nicho = 'oficina';
-- SELECT instancia, numero, responsavel_nome, nome_ia, ufs, ativo FROM sdr_instancias WHERE numero LIKE '%88610859%';
