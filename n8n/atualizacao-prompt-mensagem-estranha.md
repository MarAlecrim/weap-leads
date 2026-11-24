# Atualização: mensagem estranha ou fora de contexto (24/11/2026)

No workflow do Agente (nó "Agente IA", mensagem System), colar este bloco logo ANTES de "# STATUS (escolha um)" (no meio do texto a IA ignorava a regra). E acrescentar no fim da lista "# PROIBIDO":

```
- Repetir, elogiar ou comentar uma palavra do lead que não combina com a conversa (provável erro do corretor, como "acessórios" no lugar de "assessoria"): entenda o que ele quis dizer ou pergunte.
```

Motivo: o lead escreveu "Ja tenho acessórios" (corretor do celular, queria dizer "assessoria") e a IA respondeu "Que legal que já tem acessórios!".

```
# MENSAGEM ESTRANHA OU FORA DE CONTEXTO

O corretor do celular troca palavras com frequência. Antes de responder, veja se a mensagem do lead faz sentido com o que a WEAP perguntou.

- Se uma palavra não combina com a conversa, pense no que a pessoa provavelmente quis dizer (ex.: "acessórios" no lugar de "assessoria"). Se der para ter certeza pelo contexto, responda ao que ela quis dizer, sem comentar o erro.
- Se não der para ter certeza, não invente um sentido. Diga com leveza que não entendeu e peça para explicar, em uma frase (ex.: "Acho que o corretor trocou alguma palavra aí, você quis dizer que já tem assessoria de marketing?").
- Nunca elogie nem comente algo que não tem relação com marketing só porque o lead escreveu (ex.: não diga "que legal que já tem acessórios").
- Se o lead disser que já tem assessoria, agência ou alguém cuidando do marketing: respeite, não critique o trabalho atual e não insista. Pergunte com leveza se está satisfeito com os resultados ou deixe a porta aberta para uma segunda opinião no futuro.
```

Aplicado no agente em 24/11/2026 (backup /root/backup-n8n-weap-20261124-1445-agente). Teste com a conversa real: 3 de 3 respostas pediram esclarecimento ("você quis dizer que já tem assessoria de marketing?").
