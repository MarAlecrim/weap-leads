#!/usr/bin/env bash
# Importação mensal da base CNPJ da Receita para o schema "receita".
# Uso: ./importar.sh [AAAA-MM]   (sem mês = o mais recente publicado)
# Roda dentro do container "importador" (docker compose run --rm importador). Conexão pelo PGHOST/PGUSER/PGPASSWORD/PGDATABASE.
set -euo pipefail
cd /importador
# A Receita publica numa pasta compartilhada (Nextcloud): https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9
HOST="${RECEITA_HOST:-https://arquivos.receitafederal.gov.br}"
TOKEN="${RECEITA_TOKEN:-YggdBLfdninEJX9}"
DAV="$HOST/public.php/webdav"
export RECEITA_UFS="${RECEITA_UFS:-PR}"

lista() {  # lista o conteúdo de uma pasta da Receita (vazio = raiz)
  curl -fsS -X PROPFIND -H "Depth: 1" -u "$TOKEN:" "$DAV/$1" | grep -oE '<d:href>[^<]*</d:href>' | sed -E 's#</?d:href>##g; s#.*/webdav/##; s#/$##'
}
baixa() {  # baixa um arquivo: $1 = mês, $2 = nome do zip, $3 = destino
  curl -fSL --retry 5 --retry-delay 20 -u "$TOKEN:" -o "$3" "$DAV/$1/$2" \
  || curl -fSL --retry 5 --retry-delay 20 -o "$3" "$HOST/index.php/s/$TOKEN/download?path=%2F$1&files=$2"
}

if [ -n "${1:-}" ]; then
  MES="$1"
else
  # o mês mais recente que já está completo (tem o último arquivo de sócios)
  MES=""
  MESES="$(lista "")"
  for m in $(echo "$MESES" | grep -oE '^20[0-9]{2}-[0-9]{2}$' | sort -r); do
    CONTEUDO="$(lista "$m")"
    if echo "$CONTEUDO" | grep -q 'Socios9.zip'; then MES="$m"; break; fi
    echo "Pasta $m ainda incompleta, tentando o mês anterior"
  done
  [ -n "$MES" ] || { echo "Não achei nenhum mês completo na Receita"; exit 1; }
fi
export RECEITA_MES="$MES"
PASTA="${RECEITA_PASTA:-/tmp/receita}/$MES"
mkdir -p "$PASTA"
echo "Base $MES, estados $RECEITA_UFS, pasta $PASTA"

ARQS="Cnaes Municipios Qualificacoes Naturezas"
for i in 0 1 2 3 4 5 6 7 8 9; do ARQS="$ARQS Estabelecimentos$i Empresas$i Socios$i"; done
for a in $ARQS; do
  [ -s "$PASTA/$a.zip" ] && continue
  [ "${RECEITA_SEM_DOWNLOAD:-}" = 1 ] && continue   # teste com arquivos já baixados
  echo "Baixando $a.zip"
  baixa "$MES" "$a.zip" "$PASTA/$a.zip.part"
  mv "$PASTA/$a.zip.part" "$PASTA/$a.zip"
done

F="python3 /importador/filtro.py"
psql -v ON_ERROR_STOP=1 <<SQL
BEGIN;
TRUNCATE receita.cnaes, receita.municipios, receita.qualificacoes, receita.naturezas,
         receita.estabelecimentos, receita.empresas, receita.socios RESTART IDENTITY;
\copy receita.cnaes from program '$F cnaes $PASTA' with csv
\copy receita.municipios from program '$F municipios $PASTA' with csv
\copy receita.qualificacoes from program '$F qualificacoes $PASTA' with csv
\copy receita.naturezas from program '$F naturezas $PASTA' with csv
\copy receita.estabelecimentos from program '$F estabelecimentos $PASTA' with csv
\copy receita.empresas from program '$F empresas $PASTA' with csv
\copy receita.socios (cnpj_basico, tipo, nome, qualificacao, data_entrada, faixa_etaria) from program '$F socios $PASTA' with csv
COMMIT;
ANALYZE receita.estabelecimentos; ANALYZE receita.empresas; ANALYZE receita.socios;
TRUNCATE receita.cidades;
INSERT INTO receita.cidades
  SELECT e.municipio, m.nome, e.uf, count(*) FROM receita.estabelecimentos e
  LEFT JOIN receita.municipios m ON m.codigo = e.municipio GROUP BY 1, 2, 3;
SELECT uf, count(*) AS empresas_ativas FROM receita.estabelecimentos GROUP BY uf;
SQL

# apaga os .zip depois da importação (economiza ~6 GB de disco)
rm -rf "$PASTA"
echo "Importação $MES concluída."
