# Weap Leads CRM: instalação em crm.weap.com.br

No fim você terá o **crm.weap.com.br**, a tela nova (Python FastAPI + React), com:

- login;
- busca de leads com nota de 0 a 100 e os motivos;
- ficha da empresa com os sócios (o decisor);
- planilha do disparo;
- página dos clientes atuais.

O leads.weap.com.br antigo continua igual. Os dois usam o mesmo banco.

Tempo: uns 20 minutos. A montagem das imagens leva de 5 a 10 minutos no servidor.

---

## 1. DNS (no Cloudflare)

Crie um registro **A** com nome `crm`, apontando para `2.29.100.74`, com a nuvem **cinza** (DNS only).

## 2. Mandar os arquivos novos

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

## 3. No servidor

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
cd /opt/weap-leads && echo "DOMINIO_CRM=crm.weap.com.br" >> .env && echo "CRM_SECRET_KEY=$(openssl rand -hex 32)" >> .env
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
cd /opt/weap-leads && docker compose up -d --build
```

Confira:

```
cd /opt/weap-leads && docker compose ps && docker compose logs --tail 20 api
```

Abra **https://crm.weap.com.br**. O certificado HTTPS é emitido na primeira visita e pode levar até 1 minuto.

## Se der errado

Para voltar como estava (o banco não é tocado):

```
cd /opt/weap-leads && cp backup-crm/docker-compose.yml backup-crm/Caddyfile . && cp backup-crm/importar.sh importador/ && docker compose up -d --remove-orphans
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
