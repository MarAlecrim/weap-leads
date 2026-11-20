# Disparo não envia em feriado

Em feriado, os 5 disparos não mandam nada e não marcam nada na planilha. A linha fica esperando o próximo dia útil. O agente continua respondendo quem chamar.

**Antes:** esta mudança usa o If "É de outro número?" da pasta `atualizacao-disparo-sem-repetir`. Se ele ainda não foi colocado em algum número, coloque primeiro. Sem ele, o lead seria marcado como "pulado" na planilha.

1. Rode `1 - Rodar no banco.sql` uma vez, num node Postgres do n8n (banco weap_sdr). No fim aparecem 34 feriados cadastrados (2026 e 2027).
2. Em cada um dos 5 disparos, no node **Checa lead no banco**, troque o campo "Query" pelo conteúdo de `2 - Checa lead no banco - Query.txt`. O "Query Parameters" continua igual. Salve.

A lista é a mesma para todos os números: feriados nacionais, Carnaval, Corpus Christi, 8/9 (Curitiba), 10/12 (Londrina) e as vésperas de Natal e Ano Novo. Para incluir outro dia:

```
INSERT INTO sdr_feriados VALUES ('2027-07-26', 'Motivo');
```
