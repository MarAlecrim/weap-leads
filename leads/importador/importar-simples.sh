#!/usr/bin/env bash
# Carrega só o arquivo Simples.zip (opção pelo Simples e pelo MEI) do mesmo mês da base já importada.
# Uso (no servidor): docker compose run --rm --entrypoint /importador/importar-simples.sh importador
# A importação mensal (importar.sh) já traz o Simples junto; este script é para a primeira carga.
set -euo pipefail
HOST="${RECEITA_HOST:-https://arquivos.receitafederal.gov.br}"
TOKEN="${RECEITA_TOKEN:-YggdBLfdninEJX9}"
DAV="$HOST/public.php/webdav"

MES="${1:-$(psql -XAtc "SELECT to_char(max(atualizado_em), 'YYYY-MM') FROM receita.estabelecimentos")}"
[ -n "$MES" ] || { echo "Base vazia: rode a importação completa"; exit 1; }
PASTA="${RECEITA_PASTA:-/tmp/receita}/simples-$MES"
mkdir -p "$PASTA"
echo "Simples/MEI do mês $MES"

if [ ! -s "$PASTA/Simples.zip" ]; then
  curl -fSL --retry 5 --retry-delay 20 -u "$TOKEN:" -o "$PASTA/Simples.zip.part" "$DAV/$MES/Simples.zip" \
  || curl -fSL --retry 5 --retry-delay 20 -o "$PASTA/Simples.zip.part" "$HOST/index.php/s/$TOKEN/download?path=%2F$MES&files=Simples.zip"
  mv "$PASTA/Simples.zip.part" "$PASTA/Simples.zip"
fi

# empresas que já estão na base (o filtro guarda só essas)
psql -XAtc "SELECT cnpj_basico FROM receita.empresas" > "$PASTA/basicos.txt"

psql -v ON_ERROR_STOP=1 <<SQL
CREATE TABLE IF NOT EXISTS receita.simples (cnpj_basico text PRIMARY KEY, simples boolean NOT NULL, mei boolean NOT NULL);
BEGIN;
TRUNCATE receita.simples;
\copy receita.simples from program 'python3 /importador/filtro.py simples $PASTA' with csv
COMMIT;
ANALYZE receita.simples;
SELECT count(*) AS empresas_no_arquivo, count(*) FILTER (WHERE simples) AS simples, count(*) FILTER (WHERE mei) AS mei FROM receita.simples;
SQL

rm -rf "$PASTA"
echo "Simples/MEI carregado."
