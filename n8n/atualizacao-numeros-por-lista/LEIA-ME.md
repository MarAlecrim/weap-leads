# Escolher os números de cada lista de disparo

No CRM, a janela **Mandar para o disparo** ganha a parte **Quem dispara**:

- **Automático** (padrão): cada número pega os leads dos estados dele, como no atendimento por estado.
- **Só estes números**: a leva só sai pelos números marcados, mesmo que estejam fora dos estados deles. Se o filtro da busca tem um estado, a janela já sugere os números desse estado. Número desligado pode ser marcado: os leads esperam até ele ligar.

Lead que já estava na fila não muda: a escolha vale para os que entram agora.

## Ordem de instalação

1. **Banco** (weap_sdr): rodar `1 - Rodar no banco.sql`, depois do `atualizacao-atendimento-por-estado/1 - Rodar no banco.sql`. Pode rodar de novo.
2. **CRM**: deploy da versão nova (`docker compose up -d --build api web`). Se o CRM subir antes do passo 1, o automático continua funcionando e a escolha de números avisa que o banco ainda não aceita.
3. **n8n**: em **cada** workflow de disparo, trocar a query do node "Pega lead da fila" pela de `2 - Pega lead da fila - Query.txt`, com o nome da instância daquele workflow no Query Parameters. Ela substitui a query do atendimento por estado.

## Conferir

```sql
SELECT coalesce(array_to_string(instancias, ', '), '(automático)') AS numeros, coalesce(uf, '-') AS uf, status, count(*)
  FROM sdr_fila GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;
```

## Para desfazer

Voltar a query anterior do "Pega lead da fila". A coluna nova pode ficar no banco.
