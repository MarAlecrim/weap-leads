# Atendimento por estado

Cada número de WhatsApp pode ficar com um ou mais estados. Exemplo: São Paulo só sai pelos números do Cesar, e os avisos de lead interessado desses números vão para o celular dele.

## Regra

- Número com estados (`sdr_instancias.ufs`, ex.: `{SP}`): só pega leads desses estados.
- Número sem estados (o padrão, como os de hoje): pega os leads de qualquer estado que não seja exclusivo de alguém, e os leads antigos da fila, que não têm estado.
- Estado exclusivo continua exclusivo mesmo com o número desligado: os leads esperam na fila em vez de ir para outro atendente.
- O aviso de lead interessado vai para o `responsavel_whatsapp` do número que fez o disparo. Isso já funcionava assim; basta cadastrar o número do Cesar com o celular dele.

## Ordem de instalação

1. **Banco** (weap_sdr): rodar `1 - Rodar no banco.sql`. Pode rodar de novo sem problema. Nada muda no disparo até o passo 3.
2. **CRM**: fazer o deploy da versão nova. A partir daí, o "Mandar para o disparo" grava o estado de cada lead na fila. Se o CRM subir antes do passo 1, ele continua funcionando e só não grava o estado.
3. **n8n**: em **cada** workflow "02 - SDR WEAP", trocar a query do node "Pega lead da fila" pela de `2 - Pega lead da fila - Query.txt` e preencher o Query Parameters com o nome da instância daquele workflow (o mesmo do Dados_Evolution). Workflow sem o parâmetro dá erro na query; por isso, trocar todos de uma vez.
4. **Números do Cesar**: trocar os nomes das instâncias em `3 - Cadastrar numeros do Cesar.sql` e rodar no weap_sdr. Copiar um workflow "02 - SDR WEAP" para cada número dele, com o Dados_Evolution e o Query Parameters apontando para a instância dele.
5. **Usuário do Cesar no CRM**: em Admin, criar o usuário e marcar os números dele. Assim ele vê no funil só os leads desses números.

## Conferir

```sql
-- quem atende o quê
SELECT instancia, responsavel_nome, responsavel_whatsapp, ufs, ativo FROM sdr_instancias ORDER BY instancia;
-- fila por estado
SELECT coalesce(uf, '(sem estado)') AS uf, status, count(*) FROM sdr_fila GROUP BY 1, 2 ORDER BY 1, 2;
```

## Para desfazer

Voltar a query antiga do "Pega lead da fila" (`n8n/atualizacao-fila-do-crm/2 - Pega lead da fila - Query.txt`). As colunas novas podem ficar no banco sem atrapalhar.
