# Weap Leads

Prospecção da Weap: base CNPJ da Receita (só ativas, UFs em RECEITA_UFS), tela PHP em leads.weap.com.br, workflows n8n do disparo/agente (Postgres weap_sdr).

- Plano e fases: `docs/plano.md`. Mudança de regra de negócio passa pelo plano antes do código.
- `leads/`: PHP 8.3 puro + Postgres 16 + Caddy (docker compose). Importador Python em `leads/importador` (perfil "importar").
- Receita: Nextcloud https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9 (WebDAV public.php/webdav, user = token). CSV latin-1, `;`, sem cabeçalho. Celular vem com 8 dígitos (normalizar).
- Nunca colocar senha do banco, chave da Evolution ou da OpenAI no código, nos JSON do n8n ou no chat.
- Nunca `docker volume prune` / `docker compose down -v` no servidor.
- O Gab instala por SSH no servidor: comandos um por bloco, sem ambiguidade de onde rodar (PowerShell local x servidor).
