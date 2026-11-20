# Weap Leads: instalação no servidor leads01

O que você vai ter no fim: o endereço **leads.weap.com.br** com login, busca por nicho, cidade, bairro, porte e tempo de empresa, a ficha de cada empresa com os sócios (o decisor) e o botão que baixa a planilha **no mesmo formato da planilha do disparo**. A base da Receita se atualiza sozinha todo mês.

Tempo: uns 30 minutos de instalação, mais 1 a 2 horas de importação, que rodam sozinhas.

---

## 1. Antes de começar (no painel da Hetzner e no Cloudflare)

1. Servidor **leads01** criado (CX23, Ubuntu 24.04), ligado na rede `weap-interna`.
2. No Cloudflare, registro **A** `leads` apontando para o IP público do leads01, com a nuvem **cinza** (DNS only).
3. **Firewall do leads01:** no painel da Hetzner, Firewalls → Create Firewall → nome `leads01`. Regras de entrada: TCP 22, TCP 80 e TCP 443, vindas de qualquer IP. Em "Apply to", escolha o leads01.

## 2. Mandar os arquivos para o servidor

No seu computador, baixe o arquivo **weap-leads.zip** (está junto deste guia). Abra o **PowerShell** na pasta onde ele está e rode, trocando `IP_DO_LEADS01`:

```
scp weap-leads.zip root@IP_DO_LEADS01:/opt/
```

## 3. Instalar

Entre no servidor pelo PowerShell (não pelo console do navegador da Hetzner, que troca os símbolos):

```
ssh root@IP_DO_LEADS01
```

Rode um bloco por vez:

```
apt-get update && apt-get install -y unzip
curl -fsSL https://get.docker.com | sh
```

```
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

```
cd /opt && unzip weap-leads.zip && cd /opt/weap-leads
cp .env.exemplo .env
openssl rand -base64 24
```

O último comando mostra uma senha aleatória. Abra o `.env`:

```
nano .env
```

Cole a senha no lugar de `TROQUE_POR_UMA_SENHA_LONGA`. Deixe a parte do banco do agente vazia por enquanto. Salve com **Ctrl+O**, Enter, e saia com **Ctrl+X**. Essa senha fica só no servidor: não precisa mandar para ninguém.

Suba tudo:

```
docker compose up -d --build
docker compose ps
```

Os 3 serviços (db, app e caddy) devem aparecer como "running". O certificado do HTTPS sai sozinho em 1 ou 2 minutos.

## 4. Criar os logins

Um por pessoa, com senha de pelo menos 8 caracteres:

```
docker compose exec app php /app/criar-usuario.php gab SENHA_DO_GAB
docker compose exec app php /app/criar-usuario.php fabiano SENHA_DO_FABIANO
docker compose exec app php /app/criar-usuario.php alvaro SENHA_DO_ALVARO
```

Rodar de novo com o mesmo nome troca a senha.

## 5. Primeira importação da Receita

```
nohup docker compose --profile importar run --rm importador > /opt/importacao.log 2>&1 &
tail -f /opt/importacao.log
```

Ele baixa uns 6 GB da Receita, filtra só as empresas **ativas de PR e SP** e grava no banco. Leva de 1 a 2 horas. Pode fechar o terminal: ele continua rodando. Para acompanhar depois, entre de novo e rode `tail -f /opt/importacao.log` (Ctrl+C só para de olhar, não para a importação).

Terminou quando aparecer **"Importação AAAA-MM concluída."** com a contagem por estado.

Para trocar os estados, mude `RECEITA_UFS` no `.env` (por exemplo `PR,SP,SC`) e rode a importação de novo.

## 6. Atualização automática todo mês

```
crontab -e
```

Se ele perguntar o editor, escolha **1** (nano). Vá até o fim do arquivo e cole:

```
0 3 20 * * cd /opt/weap-leads && docker compose --profile importar run --rm importador > /opt/importacao.log 2>&1
```

Salve (Ctrl+O, Enter, Ctrl+X). Todo dia 20, às 3h da manhã, ele pega a base mais nova da Receita.

## 7. Usar

1. Abra **https://leads.weap.com.br** e entre.
2. Escolha o nicho e a cidade e clique em **Buscar**. "Tem celular (WhatsApp)" já vem marcado, porque telefone fixo não serve para o disparo.
3. Clique no nome da empresa para ver a ficha com os sócios e o link para procurar o sócio no LinkedIn.
4. Marque as empresas (ou nenhuma, para pegar todas) e clique em **Baixar planilha**.
5. No Google Planilhas: Arquivo → Importar → Fazer upload → escolha o arquivo → **Criar nova planilha**.
6. No workflow de disparo do número que vai usar, troque a planilha nos dois nodes do Google Sheets e refaça o mapeamento da coluna `telefone`, como você já fez antes.

A planilha vem com as mesmas colunas de hoje (`nome_empresa`, `telefone`, `endereco`, `website`, `rating`, `reviews`, `especialidades`, `mensagem`, `disparo`), mais três no fim: `decisor`, `email` e `cnpj`.

**Teste primeiro com 2 ou 3 linhas.** A Receita não traz site, nota nem avaliações, então essas colunas vêm vazias. O prompt já sabe lidar com isso (não cita nota e não diz que viu o site), mas vale confirmar que o node de scraper do site não dá erro com o `website` vazio.

---

## Próximo passo (comigo)

- **Ligar no banco do agente:** a tela passa a marcar "já no disparo" e a esconder quem já foi contatado. Isso usa a rede interna e o arquivo `banco/02-ajuste-banco-agente.sql`, e eu te guio.
- **Disparo lendo direto do banco**, sem planilha no meio, com o nome do decisor na mensagem.
- **Cruzar com o Google Maps** para trazer nota, avaliações e site.

## Se algo der errado

- Ver o que aconteceu na tela: `cd /opt/weap-leads && docker compose logs --tail=50 app`
- HTTPS não sai: confira se o DNS do `leads` está com a nuvem **cinza** e aponta para o IP certo, e rode `docker compose logs --tail=50 caddy`.
- Reiniciar tudo: `cd /opt/weap-leads && docker compose restart`
- Nunca rode `docker volume prune` nem `docker compose down -v`: isso apaga o banco.
