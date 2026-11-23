# Weap Leads CRM: instalação em leads.weap.com.br

No fim o **leads.weap.com.br** passa a abrir a tela nova (Python FastAPI + React), com:

- login;
- busca de leads com nota de 0 a 100 e os motivos;
- ficha da empresa com os sócios (o decisor);
- planilha do disparo;
- página dos clientes atuais.

Ela substitui a tela PHP antiga, no mesmo endereço e com o mesmo banco. O código PHP fica no repositório (pasta `leads/app`) só como referência e para desfazer.

Tempo: uns 20 minutos. A montagem das imagens leva de 5 a 10 minutos no servidor.

---

## 1. Mandar os arquivos novos

No **PowerShell do seu computador**, na pasta onde está o repositório `weap-leads` (no branch certo):

```
git pull
```

```
ssh root@2.29.100.74 "mkdir -p /opt/weap-leads/novos"
```

```
scp -r leads/crm leads/banco/05-nota-dos-leads.sql leads/docker-compose.yml leads/Caddyfile leads/.env.exemplo leads/importador/importar.sh root@2.29.100.74:/opt/weap-leads/novos/
```

## 2. No servidor

Entre com `ssh root@2.29.100.74` e rode um bloco por vez.

Primeiro, guarde uma cópia dos arquivos atuais:

```
cd /opt/weap-leads && mkdir -p backup-crm && cp docker-compose.yml Caddyfile importador/importar.sh backup-crm/
```

Depois, coloque os arquivos novos no lugar:

```
cd /opt/weap-leads && cp -r novos/crm . && cp novos/docker-compose.yml novos/Caddyfile novos/.env.exemplo . && cp novos/importar.sh importador/ && cp novos/05-nota-dos-leads.sql banco/
```

Crie a chave do CRM direto no `.env` (ela não aparece na tela):

```
cd /opt/weap-leads && echo "CRM_SECRET_KEY=$(openssl rand -hex 32)" >> .env
```

Abra o `.env`:

```
nano /opt/weap-leads/.env
```

Acrescente no fim o login do administrador, com o seu e-mail e uma senha que **só você sabe**:

```
CRM_ADMIN_EMAIL=seu@email
CRM_ADMIN_SENHA=uma-senha-forte
```

Salve com Ctrl+O, Enter, e saia com Ctrl+X.

Calcule o número de sócios de cada empresa e o perfil dos clientes. Leva de 5 a 15 minutos:

```
cd /opt/weap-leads && docker compose exec -T db psql -U leads -d leads -f - < banco/05-nota-dos-leads.sql
```

Monte e ligue o CRM:

```
cd /opt/weap-leads && docker compose up -d --build --remove-orphans
```

Confira:

```
cd /opt/weap-leads && docker compose ps && docker compose logs --tail 20 api
```

Abra **https://leads.weap.com.br** e entre com o e-mail e a senha do `.env`. O login antigo da tela PHP não vale mais.

## Se der errado

Para voltar para a tela PHP (o banco não é tocado):

```
cd /opt/weap-leads && cp backup-crm/docker-compose.yml backup-crm/Caddyfile . && cp backup-crm/importar.sh importador/ && docker compose up -d --build --remove-orphans
```

Nunca rode `docker compose down -v` nem `docker volume prune`: isso apaga o banco.

## Como a nota é calculada (0 a 100)

| Item | Pontos | Quando ganha |
| --- | --- | --- |
| Região | 25 | Mesma cidade de um cliente atual ou cidade da região de Londrina |
| Dono decide | 20 | De 1 a 3 sócios |
| Celular | 20 | Tem celular (WhatsApp) |
| Ramo | 15 | Mesma divisão de CNAE de um cliente da oferta escolhida |
| Porte | 10 | Mesmo porte dos clientes |
| E-mail | 5 | Tem e-mail |
| Idade | 5 | Dentro da faixa de idade dos clientes |

As cidades atendidas ficam em `CIDADES_ATENDIDAS` (padrão: Londrina, Cambé, Ibiporã, Arapongas, Rolândia, Apucarana).

## Atualização: MEI e capital social (20/11/2026)

O filtro de porte passa a ter MEI, Microempresa, Pequeno porte, Média e Grande, e entra o filtro de capital social (mínimo e máximo). O MEI vem do arquivo Simples.zip da Receita. A Receita junta média e grande em "Demais", então a tela separa pelo capital social: até R$ 10 milhões é média, acima é grande.

No servidor, depois de copiar `crm/`, `banco/06-simples-mei.sql` e `importador/` atualizados:

```
cd /opt/weap-leads && docker compose exec -T db psql -U leads -d leads -f - < banco/06-simples-mei.sql
```

```
cd /opt/weap-leads && docker compose build importador && docker compose run --rm --entrypoint /importador/importar-simples.sh importador
```

```
cd /opt/weap-leads && docker compose up -d --build api web
```

Daqui pra frente a importação mensal já traz o Simples junto.

## Atualização: Funil e perfis de usuário (fase 2a)

Entra a tela **Funil** (kanban) e o perfil de cada usuário (Administrador, Gestor ou Vendedor, com os números de WhatsApp dele). As tabelas novas são criadas sozinhas quando a API sobe.

No servidor, depois de copiar o `crm/` atualizado:

```
cd /opt/weap-leads && docker compose up -d --build api web
```

Depois, em **Admin**, edite cada usuário e escolha o perfil e os números. O vendedor vê só os leads dos números dele e os que forem passados para ele.

## Atualização: ficha do lead no Funil (fase 2b)

Clicar num card abre a ficha: etapa, valor, responsável e próxima ação, os dados da Receita, a conversa do WhatsApp (só leitura, lida do banco do agente quando a ficha abre), o resumo da IA, as notas e o histórico. A tabela de notas é criada sozinha quando a API sobe.

```
cd /opt/weap-leads && docker compose up -d --build api web
```

## Atualização: painel na tela inicial

A primeira tela passa a ser o **Painel**: fila do disparo, contatados, respostas, interessados, propostas, ganhos, clientes atuais, o funil por etapa, o disparo dos últimos 14 dias, os números por WhatsApp e os leads que precisam de atenção. O vendedor vê só os números dele. A consulta da base foi para o menu **Busca de leads** (`/busca`). No Funil, cada coluna abre com 20 cards e um botão **Carregar mais**. Não há migração.

```
cd /opt/weap-leads && docker compose up -d --build api web
```

## Atualização: busca rápida (nota guardada)

A busca não calcula mais a nota de todas as empresas a cada vez. A nota de cada oferta fica guardada na tabela `receita.notas` (cerca de 2 milhões de linhas e 0,5 GB de disco). A própria API cria e refaz essa tabela em segundo plano quando:
- a importação mensal termina;
- os clientes atuais mudam;
- as cidades atendidas mudam.

O cálculo leva alguns minutos. Enquanto ele roda, a busca usa a tabela anterior. Na primeira vez, quando ainda não existe tabela, a busca calcula a nota na hora, como antes. Não há migração.

```
cd /opt/weap-leads && docker compose up -d --build api
```

## Atualização: caixa de conversas (fase 3a e 3b)

Menu novo **Conversas**: as conversas do WhatsApp de todos os números, da mais recente para a mais antiga. Tem filtro por número, "Só não lidas" e busca por nome ou telefone. O vendedor vê só os números dele e os leads em que é o responsável. A lista se atualiza a cada 10 s e a conversa aberta a cada 5 s.

Quem responde pela caixa (ou pela ficha do card no Funil) manda a mensagem pelo mesmo número que conversa com o lead. A IA pausa para esse lead, igual a quando alguém escreve pelo celular. O botão "Devolver para a IA" faz ela voltar. Quem pediu para não receber mensagens não recebe resposta.

Para ligar, siga os passos abaixo, um bloco por vez.

1. No servidor do n8n, rode o SQL `n8n/atualizacao-caixa-conversas/1 - Rodar no banco.sql` no banco weap_sdr, como postgres. Ele deixa o usuário do CRM gravar a mensagem e pausar ou retomar a IA, e nada além disso.

2. No servidor do CRM, coloque no `.env` (a chave é a mesma que o n8n usa na Evolution, e não vai para o código nem para o chat):
```
EVOLUTION_URL=https://endereco-da-evolution
EVOLUTION_API_KEY=a-chave-da-evolution
```
Sem a URL, o CRM usa a `evolution_url` da tabela `sdr_config`. Sem a chave, a caixa funciona só para leitura.

3. Atualize a API (a migração 0004 cria a tabela de "lidas") e o site:
```
cd /opt/weap-leads && docker compose up -d --build api web
```
