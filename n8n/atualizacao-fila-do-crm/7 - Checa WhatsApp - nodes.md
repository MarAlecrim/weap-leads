# Checagem de WhatsApp antes do envio

O CRM grava o celular com o 9 (13 dígitos), mas muitos números estão no WhatsApp sem o 9. Se o endereço completo vier errado, a Evolution recusa o envio com erro 400. Por isso, antes de enviar, o workflow pergunta à Evolution o endereço certo.

A checagem fica entre o **Merge** e o **Loop Over Items**. Ela não pode ir antes, porque o Dados_Evolution só existe depois do Filter e do Merge.

```
Merge → Verifica WhatsApp → Tem WhatsApp?
           sim → Atualiza telefone na fila → Loop Over Items (segue igual)
           não → Motivo sem WhatsApp → Marca pulado na fila
```

## Verifica WhatsApp (HTTP Request, POST)

- URL: `={{ $('Dados_Evolution').first().json.server_url }}/chat/whatsappNumbers/{{ $('Dados_Evolution').first().json.instancia }}`
- Header `apikey`: `={{ $('Dados_Evolution').first().json.api_key }}`. A chave vem do Dados_Evolution e não fica escrita no node.
- Body JSON: `={{ JSON.stringify({ numbers: [ String($('Pega lead da fila').first().json.telefone || '').split('@')[0] ] }) }}`

## Tem WhatsApp? (If)

Condição booleana verdadeira: `={{ $json.exists === true && !!$json.jid }}`

## Atualiza telefone na fila (Postgres, Execute Query, credencial do weap_sdr)

```sql
UPDATE sdr_fila SET telefone = $2 WHERE id = $1::bigint
RETURNING id AS fila_id, nome_empresa, telefone, endereco, cidade,
          coalesce(website,'') AS website, '' AS rating, '' AS reviews,
          especialidades, '' AS mensagem, '' AS disparo, origem;
```

Query Parameters: `={{ [ $('Pega lead da fila').first().json.fila_id, $json.jid ] }}`

O node devolve o lead no mesmo formato do "Pega lead da fila", agora com o endereço correto. Daí em diante, todo `$('Loop Over Items').json.telefone` usa esse endereço.

## Motivo sem WhatsApp (Set)

`motivo = 'sem WhatsApp'`, seguindo para o **Marca pulado na fila**, que já existe.
