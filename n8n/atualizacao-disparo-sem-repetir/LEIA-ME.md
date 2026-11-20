# Disparo sem repetir (planilha compartilhada entre os 5 números)

**Por que repetiu:** os 5 workflows foram duplicados do 7533 e ficaram com o mesmo horário (`1/15 7-19 * * 1-5`). Todos rodam no mesmo minuto, leem a planilha ao mesmo tempo e pegam a mesma primeira linha vazia. O "sim" só é gravado depois do envio (IA + site + espera), então os 5 mandam para o mesmo contato.

Faça os 3 ajustes em **cada um dos 5** workflows de disparo. Desative antes e ative depois.

## 1. Horário diferente para cada número (node "Schedule Trigger")

Troque a expressão Cron, deixando 3 minutos entre um número e outro:

| Número | Cron |
|---|---|
| Weap-7533 | `1/15 7-19 * * 1-5` (já está) |
| Agente-Site-Weap-8220 | `4/15 7-19 * * 1-5` |
| WEAP-9172 | `7/15 7-19 * * 1-5` |
| Weap-Alvaro-6060 | `10/15 7-19 * * 1-5` |
| Weap-Fabiano-7187 | `13/15 7-19 * * 1-5` |

Cada número continua mandando 1 mensagem a cada 15 minutos, só que em minutos diferentes.

## 2. Query nova no node "Checa lead no banco"

Cole a Query do arquivo `../atualizacao-disparo-automatico/1 - Checa lead no banco - Query e Query Parameters.txt` (versão de 19/11, noite). O Query Parameters não muda.

Ela faz o recontato sair **do mesmo número que mandou a 1ª mensagem**. Os outros números deixam a linha para ele. Se esse número ficar 2 dias sem disparar (workflow desligado), qualquer número pode mandar, para a fila não travar.

## 3. Um node novo entre "Pular lead?" e "Marca como pulado na planilha"

Sem ele, o número que não é o dono marcaria a linha como pulada e o recontato nunca sairia.

1. Clique na seta que liga a saída **true** do "Pular lead?" ao "Marca como pulado na planilha" e apague (lixeira).
2. Na saída **true** do "Pular lead?", clique no **+** e adicione um node **If**. Nome: `É de outro número?`
3. Condição: em **value 1**, modo Expression, cole `{{ $json.deixar_para_dono }}`. Tipo **Boolean**, operação **is true**.
4. Ligue a saída **false** desse If ao "Marca como pulado na planilha".
5. A saída **true** fica sem nada: a linha continua vazia e o dono pega no horário dele.

Fica assim:

```
Pular lead? ── true ──► É de outro número? ── true ──► (nada)
     │                          └── false ─► Marca como pulado na planilha
     └── false ─► Volta dados do lead ...
```
