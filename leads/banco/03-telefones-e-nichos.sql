-- 20/11/2026: telefone da Receita vem com 8 dígitos (sem o 9 do celular).
-- Celular antigo começa com 6, 7, 8 ou 9: vira DDD + 9 + 8 dígitos. Lixo (00000000, sem DDD) vira vazio.
-- Pode rodar de novo sem problema.

CREATE OR REPLACE FUNCTION receita.normaliza_fone(t text) RETURNS text LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE
    WHEN t IS NULL OR t !~ '^[1-9][0-9][0-9]{8,9}$' OR substr(t, 3) ~ '^0+$' THEN NULL
    WHEN t ~ '^[1-9][0-9][6-9][0-9]{7}$' THEN left(t, 2) || '9' || substr(t, 3)
    ELSE t
  END
$$;

UPDATE receita.estabelecimentos
   SET telefone1 = receita.normaliza_fone(telefone1),
       telefone2 = receita.normaliza_fone(telefone2)
 WHERE telefone1 IS DISTINCT FROM receita.normaliza_fone(telefone1)
    OR telefone2 IS DISTINCT FROM receita.normaliza_fone(telefone2);

-- Se o 1º telefone é fixo e o 2º é celular, troca a ordem (o celular aparece primeiro)
UPDATE receita.estabelecimentos
   SET telefone1 = telefone2, telefone2 = telefone1
 WHERE NOT receita.celular(telefone1) AND receita.celular(telefone2);

-- Nichos novos (o nome é o que aparece na lista; edite à vontade)
INSERT INTO receita.nicho_cnaes (nicho, cnae, rotulo) VALUES
 ('salao de beleza', '9602501', 'Cabeleireiros, manicure e pedicure'),
 ('pet shop',        '4789004', 'Comércio de animais e artigos pet'),
 ('pet shop',        '9609208', 'Higiene e embelezamento de animais'),
 ('restaurante',     '5611201', 'Restaurantes'),
 ('restaurante',     '5611203', 'Lanchonetes'),
 ('restaurante',     '5611205', 'Bares'),
 ('restaurante',     '5620104', 'Comida preparada (delivery)'),
 ('escola e cursos', '8599604', 'Treinamento profissional'),
 ('escola e cursos', '8593700', 'Ensino de idiomas'),
 ('escola e cursos', '8599699', 'Outros cursos'),
 ('escola e cursos', '8512100', 'Educação infantil (pré-escola)'),
 ('escola e cursos', '8513900', 'Ensino fundamental'),
 ('autoescola',      '8599601', 'Autoescola'),
 ('moveis planejados','3101200', 'Fabricação de móveis'),
 ('materiais de construcao','4744099', 'Materiais de construção'),
 ('materiais de construcao','4744001', 'Ferragens'),
 ('energia solar',   '4321500', 'Instalação elétrica'),
 ('loja de roupas',  '4781400', 'Comércio de roupas'),
 ('farmacia',        '4771701', 'Farmácia'),
 ('hotel e pousada', '5510801', 'Hotéis'),
 ('hotel e pousada', '5590699', 'Pousadas e outros alojamentos'),
 ('saude',           '8630506', 'Vacinação'),
 ('nutricao',        '8650002', 'Nutrição'),
 ('fisioterapia',    '8650004', 'Fisioterapia'),
 ('otica',           '4774100', 'Ótica')
ON CONFLICT DO NOTHING;

VACUUM ANALYZE receita.estabelecimentos;

SELECT count(*) FILTER (WHERE receita.celular(telefone1) OR receita.celular(telefone2)) AS com_celular,
       count(*) AS total
  FROM receita.estabelecimentos;
