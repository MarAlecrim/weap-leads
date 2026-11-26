# Tela de números no Admin

Em **Admin**, abaixo dos usuários, aparece **Números de WhatsApp**: cada instância da Evolution com número, responsável, celular de aviso (quem recebe o aviso de lead interessado), estados que atende e se está ligada. Dá para editar e cadastrar números novos. Apagar continua só pelo banco.

Só administrador vê e muda. A mudança vale no próximo lead que o número tirar da fila. O nome do responsável também aparece na conversa da IA com o lead ("o Márcio já vai falar com você").

## Ordem de instalação

1. **Banco** (weap_sdr): rodar `1 - Rodar no banco.sql`. Ele só dá ao usuário do CRM (`leads_crm`) permissão para cadastrar e mudar essas colunas.
2. **CRM**: deploy da versão nova (`docker compose up -d --build api web`). Antes do passo 1, a tela abre, mas salvar avisa que falta o SQL.

Cadastrar um número aqui não cria o workflow de disparo dele no n8n: continue copiando um workflow "02 - SDR WEAP" para cada número novo.
