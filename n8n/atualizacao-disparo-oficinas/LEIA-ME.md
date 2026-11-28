# Disparo de oficinas com o case Garage 03 (número 41 98861-0859)

O número **Weap-0859** (zap7) prospecta só oficinas mecânicas, oferecendo site e gestão do Instagram, e mostra o case **Garage 03** (garage03.com.br + @garage_03_autocenter).

## O que já está pronto

- **n8n:** workflow `02 - SDR WEAP - 0859 - Oficinas` (id `k5IW9rhrXs2F9mK9`), criado **desligado**. Cópia do 6258 com:
  - prompt novo, só para oficinas: 2 mensagens curtas (gancho + prova Garage 03 + uma pergunta de sim/não), recontato de 1 mensagem (`prompt-disparo-oficinas.md`);
  - **imagem do case no 1º contato**, logo depois das 2 mensagens (não depende do `sdr_config.midia_no_disparo`, que continua valendo para os outros números);
  - grava no histórico que a imagem foi enviada, para o agente não repetir;
  - lead registrado com nicho `oficina` (o agente usa as regras de oficina e pode mandar o vídeo);
  - **só pega leads das levas em que o 0859 foi marcado** no "Mandar para o disparo" do CRM (nunca pega a fila geral);
  - checagem de conexão (Redis `weap:disparo:conexao:Weap-0859`), horário 7:32 às 18:47, de 15 em 15 min, dias úteis.
- **Monitor de conexão** (`00 - Monitor de conexão dos disparos`): o Weap-0859 foi acrescentado na lista.
- **Mídias** (este PR): `leads/crm/frontend/public/midia/garage03-case.jpg` (1080x1350) e `garage03-case.mp4` (16 s, 720x1280). Depois do deploy do CRM ficam em `https://leads.weap.com.br/midia/...`. Fontes da peça em `peca/`.

## O que falta (em ordem)

1. **Deploy do CRM** (servidor do CRM 37.60.227.24, para as mídias ficarem no ar): copiar os dois arquivos de `leads/crm/frontend/public/midia/` para `/opt/weap-leads/crm/frontend/public/midia/` e, no servidor:
   ```
   cd /opt/weap-leads && docker compose up -d --build web
   ```
   Conferir: `https://leads.weap.com.br/midia/garage03-case.jpg` abre a imagem.
2. **SQL** no banco `weap_sdr` (servidor do n8n): `01-midias-e-nicho-oficina.sql`.
3. **Chave da instância:** no n8n, abrir o workflow `02 - SDR WEAP - 0859 - Oficinas`, node **Dados_Evolution**, colar a chave da instância Weap-0859 no campo `api_key` (no lugar de `COLE_AQUI_A_CHAVE_DA_INSTANCIA`).
4. **Webhook da Evolution** na instância Weap-0859 apontando para o agente (URL de produção do webhook `weap-agente`, só MESSAGES_UPSERT), igual aos outros números. Sem isso o agente não responde quem responder o disparo.
5. **CRM, Admin → Números de WhatsApp:** conferir que o Weap-0859 está ativo, com responsável e celular de aviso. O nome que a IA usa vem de `sdr_instancias.nome_ia` (padrão Cláudio).
6. **Mandar leads:** na busca, filtrar o nicho de oficinas (e o estado), "Mandar para o disparo" marcando **só o 0859**.
7. **Ligar** o workflow no n8n.

## Teste antes de soltar

Mande uma leva com um lead só, com o seu número, marcando o 0859. Ligue o workflow e espere o próximo horário (ou rode manualmente): chegam 2 mensagens e a imagem. Responda "como funciona?" e veja o agente responder (ele pode mandar o vídeo).

Mídia de número novo aumenta o risco de denúncia de spam. Se o 0859 começar a cair, desligue a imagem do 1º contato com:
```sql
UPDATE sdr_midias SET usar_no_disparo = false WHERE url = 'https://leads.weap.com.br/midia/garage03-case.jpg';
```
