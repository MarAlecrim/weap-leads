# Disparo pela fila do CRM

O botão "Mandar para o disparo" do CRM (leads.weap.com.br) põe os leads na tabela `sdr_fila` do banco do agente (weap_sdr). Os workflows de disparo deixam de ler a planilha do Google e passam a tirar um lead por vez dessa fila, da nota mais alta para a mais baixa. Os números não pegam o mesmo lead (`FOR UPDATE SKIP LOCKED`).

## Banco

Rodar `1 - Rodar no banco.sql` uma vez no weap_sdr. Ele cria a fila e o usuário `leads_crm`, que só pode ler e inserir na fila. A senha desse usuário é criada no servidor e nunca vai para o código.

## Troca de nodes em cada workflow "02 - SDR WEAP"

| Node antigo | Node novo (Postgres, Execute Query) | Arquivo |
| --- | --- | --- |
| Get row(s) in sheet | Pega lead da fila | `2 - Pega lead da fila - Query.txt` |
| Atualiza planilha para sim | Marca enviado na fila | `3 - Marca enviado na fila - Query.txt` |
| Marca como pulado na planilha | Marca pulado na fila | `4 - Marca pulado na fila - Query.txt` |
| Message a model (System) | mesmo node, texto novo | `5 - Message a model - prompt System.txt` |
| Message a model (User) | mesmo node, texto novo | `6 - Message a model - mensagem User.txt` |
| (novo, entre Merge e Loop Over Items) | Verifica WhatsApp, Tem WhatsApp?, Atualiza telefone na fila | `7 - Checa WhatsApp - nodes.md` |

O node novo devolve os mesmos campos da planilha (nome_empresa, telefone, website, especialidades…), mais `origem`, `cidade` e `fila_id`. O resto do fluxo continua igual.

## Texto da mensagem

Os leads da Receita não vieram do Google Maps. O campo Origem muda o texto: com `receita`, a mensagem não fala em Google Maps, Receita, CNPJ, cadastro nem no nome do sócio.

## Celular com ou sem o 9

O WhatsApp registra muitos celulares sem o 9. Antes de cada envio, o workflow pergunta à Evolution o endereço exato (arquivo 7). Quem não tem WhatsApp vira `pulado` com o motivo "sem WhatsApp".

## Falhas

Se a execução cair no meio, o lead fica como `pegando`. Depois de 30 minutos ele volta para a fila, no máximo 2 vezes.

Em feriado o "Pular lead?" manda o lead para "Marca pulado na fila", que o devolve para a fila (`novo`) sem gastar tentativa. Ele sai no próximo dia útil.

## Para desfazer

Reimportar o backup do workflow (feito antes da troca) no servidor do n8n. A fila não atrapalha nada se ficar no banco.
