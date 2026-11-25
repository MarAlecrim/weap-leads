# IA se apresenta como Cláudio e não responde menu de robô

Pedido do Márcio em 25/11/2026, depois da conversa com um escritório de contabilidade (lead do 7533):

- O primeiro retorno do lead foi um menu automático ("1 - ..., 0 - Não sei o departamento"), e a IA respondeu como se uma pessoa tivesse escrito.
- A IA se apresentou como "Márcio" e depois disse "vou pedir para o Márcio te chamar".

## O que muda

1. **Nome da IA.** A IA se apresenta como **Cláudio**, da equipe da WEAP, tanto no disparo quanto na conversa. O especialista, que é o `responsavel_nome` da instância (Márcio, Fabiano, Álvaro), só entra quando há interesse ("vou pedir para o Márcio, nosso especialista, te chamar"). O nome fica na coluna nova `sdr_instancias.nome_ia`, com padrão "Cláudio", e pode ser diferente em cada número.
2. **Robô de menu.** O prompt passa a dizer que lista numerada de opções é sempre sistema, e que avisos como "não entendi a sua resposta" e "atendimento transferido" também são. Além disso, o node "Valida decisão" confere isso sozinho, sem depender da IA: se todas as mensagens novas forem menu ou aviso do sistema, a IA não responde (`automatica`) e espera uma pessoa escrever.
3. **Conversas antigas.** Quem já recebeu mensagem assinada pelo especialista não recebe "Cláudio" do nada: a IA não se reapresenta, e se precisar diz que é da equipe que trabalha com ele.

Se perguntarem direto se é robô ou IA, a regra de dizer a verdade continua.

## Onde aplicar

1. `1 - Rodar no banco.sql` no weap_sdr.
2. Workflow "03 - Agente Weap WhatsApp": nodes "Prepara prompt", "Valida decisão" e o prompt System do "Agente IA", iguais ao `n8n/03 - Agente Weap WhatsApp.json` deste repositório.
3. Em cada workflow de disparo ("02 - SDR ..."), no node "Checa lead no banco", trocar só este trecho da Query:

   de
   `(SELECT responsavel_nome FROM sdr_instancias WHERE instancia = $2) AS responsavel`

   para
   `(SELECT coalesce(nome_ia, responsavel_nome) FROM sdr_instancias WHERE instancia = $2) AS responsavel`

   O campo "Quem escreve" do prompt passa a ser "Cláudio". O texto do prompt não muda.

Backup dos workflows antes. Para desfazer, basta reimportar o backup. A coluna nova pode ficar no banco.
