# Agente Weap no WhatsApp: instalação

Um agente só atende os 5 números. Ele responde quem recebeu o disparo (ou quem veio do anúncio), entende o interesse, manda imagem ou vídeo do nicho quando faz sentido e marca a conversa de 30 minutos na agenda da Weap.

## O que tem nesta pasta

| Arquivo | Para que serve |
|---|---|
| `01-banco-de-dados.sql` | Cria as tabelas no Postgres. Pode rodar de novo sem perder dados. |
| `03 - Agente Weap WhatsApp.json` | O agente (workflow novo). |
| `02 - SDR Fabiano WEAP - v2 com banco.json` | O disparo de sempre, com 3 acréscimos: registra cada lead no banco, pula quem pediu para sair ou já está conversando e, se ligado, manda a mídia do nicho. |
| `04 - Importa planilha para o banco.json` | Passa para o banco quem JÁ recebeu mensagem, para o agente reconhecer essas pessoas quando responderem. |

## Como funciona, em 1 minuto

1. A pessoa responde no WhatsApp. A Evolution avisa o n8n.
2. O agente espera 20 segundos para juntar mensagens picadas ("oi" / "vi sim" / "como funciona?").
3. Ele lê a conversa toda (primeiro contato, recontato e respostas), as regras do nicho e os horários livres da agenda.
4. Ele responde pelo **mesmo número** que a pessoa escreveu.
5. Quando a pessoa escolhe um horário:
   - modo **sugerir** (padrão): o responsável recebe no WhatsApp um link "Confirmar". Ao clicar, o evento entra na agenda com Google Meet e o lead recebe a confirmação.
   - modo **automático**: o agente marca sozinho e manda o link do Meet.
6. O responsável recebe aviso de lead interessado, de horário escolhido e quando o agente passa a conversa para uma pessoa.

Regras que o agente segue:
- Nos números de prospecção, só responde quem está no banco (quem recebeu disparo). Amigos, família e clientes que escrevem no número não são respondidos.
- No número do tráfego pago, responde qualquer pessoa, com roteiro de atendimento.
- **Se o responsável digitar no celular numa conversa ativa, a IA para de responder aquele contato.** Para reativar, use o link que chega no aviso.
- Quem disser "não tenho interesse" ou "pare" nunca mais recebe disparo.
- Não fala preço. Leva para a conversa de 30 minutos.
- Segue as regras de cada conselho (OAB, CFP, CFO, CFM, CAU, CREA), conforme o nicho.

## Instalação, passo a passo

### 1. Banco de dados

> **Atenção ao copiar os comandos deste guia:** a palavra `sql` que aparece em cima de cada bloco de comando NÃO faz parte do comando. Copie só as linhas de baixo.

Dá para fazer tudo pelo próprio n8n, sem terminal. A ideia: criar um banco separado chamado `weap_sdr`, dentro do mesmo Postgres que o n8n já usa. Assim as tabelas do agente não se misturam com as do n8n.

**1.1 Descobrir os dados de acesso do Postgres**
1. Abra o Portainer e vá em **Stacks** > stack do **n8n** > aba **Editor**.
2. Procure estas variáveis e anote os valores:
   - `DB_POSTGRESDB_HOST`: normalmente `postgres`
   - `DB_POSTGRESDB_PORT`: normalmente `5432`
   - `DB_POSTGRESDB_DATABASE`: o banco do n8n, por exemplo `n8n_queue`
   - `DB_POSTGRESDB_USER`: normalmente `postgres`
   - `DB_POSTGRESDB_PASSWORD`: a senha
   (Se a senha não estiver ali, ela fica na stack do **postgres**, na variável `POSTGRES_PASSWORD`.)

**1.2 Criar a credencial no n8n**
1. No n8n: **Overview** > **Credentials** > **Create credential** > procure **Postgres**.
2. Preencha com o que você anotou:
   - Host: o valor de `DB_POSTGRESDB_HOST` (ex.: `postgres`)
   - Database: o banco do n8n (ex.: `n8n_queue`). Só por enquanto, no passo 1.4 você troca.
   - User e Password: os anotados
   - Port: `5432`
   - SSL: **Disable**
3. Dê o nome **Postgres Weap SDR** e clique em **Save**. Se aparecer "Connection tested successfully", está certo.

**1.3 Criar o banco `weap_sdr`**
1. Crie um workflow novo, em branco, chamado "Instalação banco SDR".
2. Adicione o node **Postgres** > ação **Execute a SQL query** e selecione a credencial **Postgres Weap SDR**.
3. No campo **Query**, escreva só isto:
   ```sql
   CREATE DATABASE weap_sdr;
   ```
4. Clique em **Execute step**. Deve dar sucesso, sem retorno.
   - Se der erro "already exists": o banco já existe, siga em frente.
   - Se der erro "cannot run inside a transaction block": abra **Options** no node, coloque **Query Batching** em **Single Query** e execute de novo.

**1.4 Apontar a credencial para o banco novo**
1. Volte em **Credentials** > **Postgres Weap SDR**.
2. Troque **Database** para `weap_sdr` e salve. O teste de conexão precisa passar de novo.

**1.5 Criar as tabelas**
1. No mesmo workflow "Instalação banco SDR", abra o node Postgres.
2. Apague o `CREATE DATABASE` do campo Query.
3. Abra o arquivo `01-banco-de-dados.sql` num editor de texto (Bloco de Notas serve), copie **tudo** (Ctrl+A, Ctrl+C) e cole no campo Query.
4. Clique em **Execute step**. Deve terminar sem erro. Pode rodar de novo sem problema, porque ele não apaga nada.
5. Para conferir, troque a query por `SELECT nicho FROM sdr_nichos;` e execute. Devem aparecer 9 nichos (advocacia, psicologia, odontologia...).

Guarde esse workflow. Ele serve para todos os comandos SQL deste guia: é só colar o comando no node e clicar em Execute step.

**1.6 Preencher a configuração**

Cole no node, troque os valores em MAIÚSCULAS e execute:
```sql
UPDATE sdr_config SET valor = 'https://URL-DA-SUA-EVOLUTION'          WHERE chave = 'evolution_url';
UPDATE sdr_config SET valor = 'https://URL-DO-SEU-N8N/webhook'        WHERE chave = 'webhook_base';
UPDATE sdr_config SET valor = 'NOME-DA-INSTANCIA-QUE-MANDA-OS-AVISOS' WHERE chave = 'instancia_avisos';
```
- `evolution_url`: o endereço da Evolution, sem barra no final (o mesmo `server_url` do node Dados_Evolution do disparo).
- `webhook_base`: o endereço do seu n8n + `/webhook`.
- `instancia_avisos`: o número (instância) que manda os avisos para os responsáveis. Use o número de Curitiba que você menos usa. Não use o número do próprio responsável, porque ninguém recebe aviso mandando mensagem para si mesmo.

**1.7 Cadastrar os 5 números**

Cole, troque pelos dados reais e execute. O nome em `instancia` precisa ser **igual** ao nome da instância na Evolution. `numero` é o número da instância. `responsavel_whatsapp` é o celular pessoal de quem recebe os avisos. A agenda você preenche no passo 2.
```sql
INSERT INTO sdr_instancias (instancia, numero, responsavel_nome, responsavel_whatsapp, tipo, cidade) VALUES
 ('NOME-INSTANCIA-FABIANO',   '5543XXXXXXXXX', 'Fabiano', '5543XXXXXXXXX', 'prospeccao', 'Londrina'),
 ('NOME-INSTANCIA-ALVARO',    '5543XXXXXXXXX', 'Álvaro',  '5543XXXXXXXXX', 'prospeccao', 'Londrina'),
 ('NOME-INSTANCIA-CURITIBA1', '5541XXXXXXXXX', 'Márcio',  '5541XXXXXXXXX', 'prospeccao', 'Curitiba'),
 ('NOME-INSTANCIA-CURITIBA2', '5541XXXXXXXXX', 'Márcio',  '5541XXXXXXXXX', 'prospeccao', 'Curitiba'),
 ('NOME-INSTANCIA-TRAFEGO',   '5541XXXXXXXXX', 'Márcio',  '5541XXXXXXXXX', 'trafego',    'Curitiba');
```
Para conferir: `SELECT instancia, responsavel_nome, tipo FROM sdr_instancias;`

### 2. Agenda
1. Na conta Google da Weap, crie a agenda **Weap Londrina** (e **Weap Curitiba**, se for usar).
2. Em Configurações da agenda > Integrar agenda, copie o **ID da agenda** (algo como `abc123@group.calendar.google.com`) e grave nos números, pelo workflow "Instalação banco SDR":
   ```sql
   UPDATE sdr_instancias SET agenda_id = 'ID-DA-AGENDA-WEAP-LONDRINA';
   ```
   (Sem `WHERE`, vale para os 5 números. Quando criar a Weap Curitiba, rode de novo só para eles, por exemplo `... WHERE cidade = 'Curitiba';`.)
3. Os horários de atendimento ficam em `horarios` (padrão: seg a sex, 9h às 18h, almoço 12h às 13h30, 30 minutos, mínimo de 3 horas de antecedência). Exemplo para mudar o Fabiano:
   ```sql
   UPDATE sdr_instancias
      SET horarios = '{"dias":[1,2,3,4,5],"inicio":"08:30","fim":"17:30","almoco":["12:00","13:00"],"duracao":30,"antecedencia_horas":4}'
    WHERE instancia = 'fabiano';
   ```
   (dias: 1 = segunda ... 7 = domingo)
4. Para a IA marcar sozinha: `UPDATE sdr_instancias SET modo_agenda = 'automatico' WHERE instancia = 'fabiano';`

### 3. Credenciais no n8n
Crie (ou reaproveite) estas credenciais, com estes nomes:
- **Postgres Weap SDR**: o banco do passo 1.
- **Evolution API**: tipo *Header Auth*, nome do header `apikey` e, como valor, a chave da Evolution. Assim a chave sai do workflow.
- **Google Agenda Weap**: tipo *Google Calendar OAuth2*, logada na conta da Weap. Passo a passo logo abaixo.

#### Credencial do Google Agenda, passo a passo
Você já tem um "app" no Google Cloud, porque a credencial do Google Sheets do disparo usa um. Dá para reaproveitar o mesmo.
1. **Ligar a API da agenda:** entre em console.cloud.google.com com a conta onde criou a credencial do Sheets e selecione o mesmo projeto, no topo da tela. Vá em **APIs e serviços** > **Biblioteca**, procure **Google Calendar API** e clique em **Ativar**.
2. **Pegar o Client ID e o Client Secret:** em **APIs e serviços** > **Credenciais**, abra o "ID do cliente OAuth" que o n8n já usa.
   - Confira se em **URIs de redirecionamento autorizados** está `https://n8n7.mercadonet.com.br/rest/oauth2-credential/callback`. Se não estiver, adicione e salve.
   - Copie o **ID do cliente**. O Google não mostra mais segredos antigos: se não tiver o segredo guardado, clique em **Adicionar chave secreta** e copie a nova (a antiga continua valendo para o Sheets).
3. **Liberar a conta da Weap:** em **APIs e serviços** > **Tela de consentimento OAuth** (ou **Google Auth Platform** > **Público-alvo**):
   - Se o app estiver em **Teste**, adicione o e-mail da conta da Weap em **Usuários de teste**.
   - Recomendado: clique em **Publicar app** (fica "Em produção"). Em modo Teste o Google derruba o login a cada 7 dias e o agente para de ver a agenda. Ao entrar, o Google vai mostrar o aviso "app não verificado": clique em **Avançado** > **Acessar**. É normal para app de uso interno.
4. **Criar no n8n:** **Credentials** > **Create credential** > **Google Calendar OAuth2 API**. Cole o **Client ID** e o **Client Secret**, dê o nome **Google Agenda Weap** e clique em **Sign in with Google**.
5. Entre com a **conta da Weap que tem a agenda Weap Londrina**, marque todas as permissões e confirme. Deve aparecer "Account connected".
6. **Testar:** no workflow "Instalação banco SDR", adicione um node **Google Calendar** > **Get many events**, escolha a credencial, selecione a agenda Weap Londrina na lista e execute. Se trouxer os eventos (ou vier vazio sem erro), está pronto.
- **OpenAi account**: a mesma do disparo.

### 4. Importar os workflows
1. Importe `03 - Agente Weap WhatsApp.json`. Abra cada node com credencial e selecione a credencial certa (o n8n pede isso ao importar).
2. **Ative** o workflow e copie a **URL de produção** do node "Recebe mensagem" (termina em `/webhook/weap-agente`).
3. Importe `04 - Importa planilha para o banco.json` e rode uma vez para **cada planilha já disparada**, colocando o nome da instância que disparou aquela planilha.
4. Troque o disparo atual pelo `02 - SDR Fabiano WEAP - v2 com banco.json` (um por número, como hoje). Nele, só os 4 nodes novos usam o banco: selecione a credencial **Postgres Weap SDR** em "Checa lead no banco" e "Registra lead no banco".

### 5. Webhook na Evolution (em cada um dos 5 números)
No Manager da Evolution, em cada instância > Webhook:
- **Enabled**: ligado
- **URL**: a URL de produção copiada no passo 4.2
- **Webhook by events**: desligado
- **Webhook base64**: desligado
- **Events**: marque só **MESSAGES_UPSERT**

### 6. Teste antes de soltar
1. Coloque seu número pessoal numa planilha de teste e rode o disparo, ou insira direto no banco:
   ```sql
   INSERT INTO sdr_leads (chave, telefone, instancia, nome_empresa, especialidades, nicho, status)
   VALUES (sdr_chave('41999999999'), '41999999999', 'fabiano', 'Empresa Teste', 'Advogado', 'advocacia', 'contatado');
   ```
2. Responda pelo seu celular: "vi sim, como funciona?". Em uns 30 segundos o agente responde.
3. Peça um horário, veja o aviso chegar no responsável e clique em Confirmar.
4. Veja o funil: `SELECT * FROM sdr_funil;`

## Imagens e vídeos

1. Suba o arquivo no bucket **weap-midia** do Cloudflare R2 (ou no site) e copie o link público.
2. Cadastre:
   ```sql
   INSERT INTO sdr_midias (nicho, tipo, url, descricao, legenda) VALUES
   ('advocacia', 'video', 'https://LINK-PUBLICO/case-advogado.mp4',
    'Vídeo de 20 s de um site que fizemos para um escritório de advocacia',
    'Esse é um dos trabalhos que fizemos para advogados');
   ```
   - `descricao` é o que a IA lê para decidir quando mandar. Seja claro.
   - Use `nicho = 'geral'` para mídia que serve para qualquer segmento.
   - Vídeo: mp4, até uns 30 segundos e 16 MB. Imagem: jpg ou png.
3. **No disparo** (primeiro contato ou recontato), a mídia vai junto só se as duas coisas estiverem ligadas:
   ```sql
   UPDATE sdr_config SET valor = 'sim' WHERE chave = 'midia_no_disparo';
   UPDATE sdr_midias SET usar_no_disparo = true WHERE id = 1;
   ```
   Recomendo deixar desligado no primeiro contato. Mídia de número desconhecido aumenta as denúncias de spam e o risco de bloqueio do número.

## Nichos novos

Os nichos ficam na tabela `sdr_nichos`. Para um nicho novo, basta uma linha:
```sql
INSERT INTO sdr_nichos (nicho, prioridade, palavras, regras, frentes) VALUES
('contabilidade', 40, '{contab,contador}',
 'Contadores seguem o Código de Ética do CFC: sem promessa de resultado, sem preço.',
 'site, Google Meu Negócio, conteúdo nas redes');
```
`palavras` são pedaços de texto procurados nas especialidades do Google Maps (minúsculo, sem acento).

## Comandos úteis

```sql
-- Funil por número, nicho e status
SELECT * FROM sdr_funil;

-- Leads que estão esperando o responsável
SELECT nome_empresa, instancia, status, resumo, 'https://wa.me/' || whatsapp AS conversa
  FROM sdr_leads WHERE status IN ('humano','agendamento_pendente') ORDER BY atualizado_em DESC;

-- Reativar a IA para um contato
UPDATE sdr_leads SET ia_pausada = false, status = 'respondeu' WHERE chave = sdr_chave('43999998888');

-- Desligar um número do agente
UPDATE sdr_instancias SET ativo = false WHERE instancia = 'alvaro';
```

## Limites desta versão

- Não ouve áudio: pede, com educação, para a pessoa escrever. Dá para incluir transcrição depois.
- Não conhece feriados: bloqueie o dia na agenda que ele não oferece o horário.
- Remarcar ou cancelar reunião passa para o responsável.
- O disparo v2 continua com a chave da Evolution no node "Dados_Evolution", como no original. Os nodes de envio do agente já usam a credencial.
