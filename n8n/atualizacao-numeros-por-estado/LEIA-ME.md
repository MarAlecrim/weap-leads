# Números por estado

Pedido do Márcio em 26/11/2026: em SP quem atende é o Cesar, com números só de SP, e o aviso de lead interessado vai para o celular dele.

## Como funciona

- O CRM grava o estado do lead na fila (`sdr_fila.uf`) quando ele é mandado para o disparo.
- Cada número pode ter uma lista de estados em `sdr_instancias.ufs` (ex.: `{SP}`).
  - Com lista, o número só pega leads desses estados.
  - Sem lista (NULL), o número pega leads dos estados que nenhum outro número reservou, e também os leads sem estado. Os números de hoje ficam assim e param de pegar SP assim que um número reservar SP.
- O responsável de cada número (`responsavel_nome`, `responsavel_whatsapp`) já decide quem recebe o aviso e com quem a IA diz que vai falar ("vou pedir para o Cesar, nosso especialista, te chamar").
- No CRM, o usuário do Cesar recebe os números dele em "Números", e assim só vê os leads desses números no funil.

## Onde aplicar

1. `1 - Rodar no banco.sql` no weap_sdr (antes de instalar o CRM novo, porque o CRM passa a gravar a coluna `uf`).
2. CRM: `docker compose up -d --build api web`.
3. Em cada workflow "02 - SDR ...", node "Pega lead da fila": trocar a Query pelo arquivo 2 e colocar o Query Parameter indicado no topo dele.
4. Quando os números do Cesar estiverem na Evolution: uma linha em `sdr_instancias` para cada um, com `ufs = '{SP}'` e o celular dele em `responsavel_whatsapp`. Os workflows dele são cópias do SDR do 7533, com o nome da instância trocado em "Dados_Evolution".

SP ainda precisa ser importado na base da Receita (RECEITA_UFS).
