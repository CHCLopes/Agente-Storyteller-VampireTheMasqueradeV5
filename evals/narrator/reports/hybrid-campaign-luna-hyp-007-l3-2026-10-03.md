# HYP-007-L3 — resultado, diagnóstico e correção local

Lote `06e9e661-7e97-49d3-b0ba-7b60987fc8f3`, executado em 03/10/2026
(04/10 01:27 UTC), Luna low, prompt/estado v2. Limite autorizado de 17
chamadas e teto estimado adicional USD 0,15; parada na primeira reprovação.

## Resultado preservado

**Uma chamada, zero turnos completos**; parada por
`campaign_source_policy_failed` em CAMP-EVAL-01/R-01. Resposta estruturada e
proveniência OpenAI/Luna presentes: a autenticação funcionou nesta execução.
Sem retry, fallback ou segundo lote. A trava L3 existe e o gate live foi
fechado. Registros/summary originais não foram reescritos.

SHA-256 verificado contra summary:
`c8d2fd355e0c7bb50b2adfdf8a8c588df17e909e9fe59c46ca5aa5b47f505d82`.
O manifesto estava válido antes da correção local. Corpo registrado: 9.290
bytes; geração 5.372 ms; turno inteiro 5.538 ms. Uma chamada não mede
distribuição de latência ou experiência da campanha completa.

Custo final **estimado USD 0,0007078**, a partir de 2.285 tokens de entrada
e 209 tokens de saída reportados. Fórmula: `(2285×0,20 + 209×1,20)/1.000.000`.
Recalculado pelo reporter local, coincide com summary. Não é cobrança
confirmada. Diagnóstico, correção e preparação seguinte fizeram zero chamadas
externas adicionais, custo de inferência USD 0.

## Evidência narrativa e diagnóstico

Resposta retida tem 80 palavras em `n` e 85 com `q`, dentro da faixa 30–150.
Realized effects coincidem com a preparação; o guard lexical da campanha
considera R-01 realizado. Texto identifica a bancada baixa no Arquivo,
superfície seca na Galeria e fala direta de Mara; não descreve retirada.

A reprodução local de validação com preparação sintética equivalente mostrou:

```
scene_player_agency_violation
field=narrative; rule=undeclared_player_action
subject=ambiguous_pronoun; clause_index=5; unauthorized_concepts=[interact]
```

Na cláusula "Ela aponta discretamente para a passagem, mas não toca no
objeto", o perfil da campanha passava `npc_aliases=()` à política, mesmo
com Mara no roster canônico. O pronome não encontrava a antecedente conhecida.
A falha no repasse do contexto gera falso positivo de atribuição; não é prova
de que o modelo executou uma ação do jogador nessa cláusula. O motivo
detalhado foi obtido por reprodução, não estava retido no summary original.

Correção mínima: `api/campaign_source_profile.py` agora combina
`source.canonical_scene.npcs_present` com aliases explícitos ao invocar a
política. Não são nomes enviados pelo modelo e o detector genérico não foi
relaxado ou modificado. Colisão com alias de jogador, pronome sem antecedente
e ações de jogador reconhecidas continuam recusadas.

O texto exato L3 passa localmente após esse repasse. Um teste usa adaptador
falso em sessão sintética nova e verifica commit/reconstrução/replay únicos,
informação `safe_surface`, registro ainda em `bench` e uma só chamada fake.
Isso não promove o turno live rejeitado a aprovado, nem é replay da cápsula
live original: timestamps/DB temporária original não estão retidos.

## Verificação e limitações

- Baseline da regressão retida: teste positivo falhou antes da correção.
- **410 testes aprovados** em campanha, runners e regressões de agência/NPC.
- **7 testes específicos aprovados**, incluindo o teste de integração
  acrescentado depois da seleção maior. As contagens se sobrepõem.
- **10 testes aprovados** na seleção final de atribuição NPC (7) e preparação
  L4 (3), repetida após a última edição do teste de autorização. Avisos de
  cache pytest sem permissão de escrita e depreciação multipart, sem falha de
  teste; nenhuma alteração oportunista. Parser PowerShell e manifesto
  prospectivo conferidos, verificações de whitespace sem erros.
- Manifestos históricos L2/L3 conservam seus hashes: o runtime corrigido
  diverge de L3 e esse runner histórico o recusa. Testes L3 posteriores usam
  manifesto temporário exclusivo, com contraprova do gate histórico fechado.
- Suíte integral não repetida; as falhas históricas Windows/schema continuam
  separadas. Nenhum `.env`, segredo ou chave foi consultado na análise.

A resposta de Mara sugere manter tudo estável e apresenta risco de manipular
o registro sem cuidado. Esse foco não demonstra a urgência do resgate ou
progressão positiva e merece julgamento narrativo; o núcleo causal atribui
o risco à água. Pode ser avaliado como intenção da personagem ou orientação
inadequada, não como nova regra canônica automaticamente aprovada. Nenhuma
trajetória ou desfecho foi observado neste lote. R-05/posição depois do resgate
e consistência de comprimento em vários turnos continuam sem evidência live.

Uma contraprova de verbos de retirada expôs limitação lexical preexistente,
registrada separadamente em
[observação de agência](../../../plan/observation-campaign-agency-vocabulary-1.md).
Não declarar proteção semântica irrestrita. A correção atual trata somente o
repasse dos NPCs canônicos; a descoberta não foi incorporada como nova frente.

Conclusão técnica: **L3 inconclusivo para admissão por falso positivo de
atribuição NPC; nenhum candidato elegível neste lote, nenhum narrador admitido**.
Aceitação narrativa/produto continua humana. CAMP-24/TASK-013 permanecem abertos.

## Próximo lote prospectivo preparado, ainda bloqueado para gasto

HYP-007-L4 isolado, mesmo prompt v2/estado/alvo/schedule, 17 chamadas no máximo,
768 tokens por chamada, deadline 60 s, corpo até 20.000 bytes, sem retry/fallback,
mesma parada na primeira reprovação. Única correção de comportamento em relação
a L3: fornecer NPCs canônicos à política de atribuição. Gate próprio com
21 arquivos congelados (incluindo o detector genérico), orçamento **proposto**
adicional USD 0,15; ambos os flags live/paid permanecem false.

Runner/preflight/lançador próprios `*_hybrid_campaign_luna_l4_*` estão prontos,
mas não há inferência ou janela de credencial aberta para L4. Três testes
comprovam preflight sem despacho, 17 turnos fake e bloqueio de produção sem
autorização. Não usar as 16 chamadas não executadas de L3 como novo lote.
Preflight CLI final: 17 turnos planejados, zero chamadas, maior corpo
13.043 bytes. Conferência final do manifesto: 21 hashes válidos, ambos os
flags false e nenhuma trava/claim L4 de produção criada. SHA-256 dos registros
L3 reconferido e idêntico após as correções/documentação.
Após aprovação específica, ativar gate L4 e abrir entrada segura de chave.

Configuração recomendada: **gpt-5.6-sol / high**, para avaliar diagnóstico,
limites narrativos e autorização de novo gasto. Ação humana: aceitar ou
contestar a conclusão delimitada L3 e autorizar ou alterar L4/orçamento.
Operação de chave depois: **Sol low**. Nenhum default ou narrador é admitido
pela aprovação de orçamento ou pela correção offline.

## Aprovação e prontidão posteriores

O usuário respondeu "Aprovado. Continue" à proposta delimitada acima: conclusão
L3 aceita e HYP-007-L4 autorizado até 17 chamadas, teto estimado adicional
USD 0,15. Só os flags de autorização e notas do gate L4 mudaram; hashes,
prompt, parâmetros e critérios preservados. Nenhuma admissão por esse aceite.
Três testes de preparação passaram após ativação, manifesto de 21 arquivos
válido, parser PowerShell válido; preflight CLI de 17 turnos/zero chamadas,
maior corpo 13.043 bytes. A janela externa foi aberta e o sinal próprio
`eval-results/preflights/hybrid-campaign-luna-l4-ready.json` confirmou fase
`awaiting_secure_credential`, zero chamadas. Próxima dependência: entrada
protegida da chave. Depois verificar novo lote/custo e encerrar o gate live.
