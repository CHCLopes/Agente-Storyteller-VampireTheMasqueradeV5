# Retomada limpa — Agente Storyteller

Continue o trabalho existente neste projeto. Confirme os fatos nos arquivos antes
de agir e carregue apenas o contexto necessário ao próximo passo.

## Checkpoint vigente — promoção GitHub autorizada em 18/10/2026

O usuário autorizou consolidar a evolução do worktree na branch principal do
repositório `CHCLopes/Agente-Storyteller-VampireTheMasqueradeV5`. Preservar
`master`, seu histórico e o checkout original. Rota: commit da evolução,
publicação da branch de implementação, criação de `main` a partir da `master`
remota, integração por PR e mudança de default apenas após merge verificado.
Sem force-push, exclusão de branches, leitura de `.env*` ou novo gasto de LLM.
Login GitHub verificado; commit/push/PR/merge ainda pendentes neste checkpoint.
Plano, evidências e limitações: `docs/repository-promotion.md`. Consultar também
o estado remoto ao retomar: este registro não afirma que a promoção terminou.
O MVP continua aberto; nenhum narrador/default está admitido. A autorização
Git não aceita L4, não libera L5 e não modifica o backlog de produto.

## Checkpoint anterior — auditoria de segurança em 16/10/2026

O usuário pediu auditoria pela skill global e correção dos achados. Foram
confirmadas e corrigidas duas causas: SEC-001, fronteira Host/Origin ausente no
app padrão e bootstrap do ensaio HTTP; SEC-002, consolidação do jogador elegendo
fontes privadas e podendo suceder cadeia privada. A nova barreira ASGI não é
login: preserva o operador local único, loopback e automação nativa confiável.
A consolidação filtra public/player e recusa cadeia anterior privada sem a
expor ou modificar. Sem migração, dependência nova, Git write ou inferência.
Sete regressões falharam antes; depois passaram 196 testes backend focados,
mais 56 de transações/retomada/memória e 24 frontend. Não é suíte integral verde.
Inventariados 20 handlers explícitos, quatro rotas automáticas e mount estático;
scan mascarado de 1.063 arquivos e 182 blobs/27 commits, sem `.env*` ou saves.
Relatório e fontes: `docs/security-audit/README.md`; PDF de 11 páginas gerado e
rasterizado, revisão visual de layout concluída. Nenhuma issue publicada.
Não foi confirmada credencial exposta nos arquivos/histórico examinados; scan
heurístico e exclusões não provam ausência universal. JWT legado sem consumidor
é informativo e ficou intacto. Quatro espaços finais preexistentes em main
foram observados na checagem de whitespace e preservados, sem limpeza lateral.

Reconciliação factual da avaliação suspensa: HYP-007-L4 terminou em 03/10 com
duas chamadas, um turno completo e parada R-05 por política; custo estimado
USD 0,0014972. Gate live fechado. Reprodução local atribuiu o estado do objeto
"Ele permanece intacto" a espera ambígua; instrução prospectiva de sujeito
explícito no prompt v3 foi preparada em L5, sem alterar detector ou gates.
L4 continua sem aceite narrativo e nenhum narrador admitido. L5 não foi aprovado
nem executado. A correção de segurança do ensaio offline invalida os hashes de
preparação anteriores que incluam esse arquivo; não atualizar manifestos live
históricos. Ao retomar, refazer preflight/congelamento prospectivo antes de
qualquer execução, sem pedir chave ou presumir novo orçamento nesta auditoria.

## Contexto anterior — campanha B opt-in verificada offline; experiência pendente

Em 29/09/2026, o usuário aprovou explicitamente PROG-ROUTE-B: planejar a
progressão e a campanha híbrida mínima antes de retomar a admissão do narrador.
Também determinou Luna low como referência prioritária desta etapa, com melhorias
compartilhadas pelos demais modelos potencialmente utilizáveis. Isso aprova a
ordem de trabalho e a prioridade de avaliação, não admite Luna, não escolhe um
default e não reabre lotes encerrados ou gastos. HYP-006 permanece encerrado com
rejeição narrativa aceita; nenhum narrador está admitido.

Plano atual: `plan/architecture-hybrid-campaign-progression-1.md`. A inspeção
documentou uma diferença de composição: o ensaio manual Luna herda
`narrative-source-progress-v1` no caminho B restrito; os beats catalogados de Mara
estão no caminho padrão. O perfil B atual não é uma campanha com consequências
genéricas. Essa diferença impede atribuir o problema somente ao modelo; não
desfaz o julgamento do ensaio nem demonstra que a integração proposta o resolverá.

DEC-PROG-001 (recorte) e DEC-PROG-002 (extensão opt-in B) foram aprovadas
explicitamente em 29/09/2026. Foram preparados
`spec/spec-architecture-hybrid-campaign-progression.md` e
`evals/narrator/hybrid_campaign_progression_protocol_v1.md`: estados, fronteiras,
nove consequências candidatas, oito trajetórias e nove contraprovas.
TASK-001–008 do plano documentam preparação concluída. Em 29/09, o usuário
escolheu a opção A e mandou continuar. TASK-009–011 registram o ritmo de três
esperas e o núcleo puro em `api/campaign_progression_service.py` e
`api/campaign_progression_catalog.py`, com 435 testes focados/regressão aprovados
(58 do núcleo/catálogo de cena). Um rascunho canônico offline separado em
`api/campaign_source_preparation.py` vincula ação, recibo, efeito e delta à
operação. Três asserções de schema 3 em testes B antigos foram atualizadas para
o schema 4 já vigente, sem migração. Em seguida TASK-012 integrou origem,
cápsula P/K, histórico/fonte, executor H, commit transacional, reconexão e
retomadas explícitas numa rota B nova, sem torná-la default e sem DDL. O delta
é preparado antes de H e só vira estado canônico no commit admitido; nenhuma
falha H grava progressão parcial nem repete RNG. Os 8 percursos autorados e 9
contraprovas do protocolo foram exercitados offline. TASK-013 tem ensaio HTTP
local separado com adaptador falso e prosa autorada; **não é um teste Luna** nem
aceitação da experiência. [Evidência e limites](evals/narrator/reports/hybrid-campaign-source-offline-2026-09-29.md).
Após correções do desbloqueio do campo e da recuperação de sessão sintética
vencida, o usuário confirmou que envio e nova sessão funcionaram, que houve
progressão e resposta pertinente de Mara, e que a microcena atingiu seu
objetivo de teste. UX não foi medida; a fala autorada de Mara pareceu curta,
impessoal e relatada em vez de encenada. A preferência futura por diálogo
direto está em `plan/observation-npc-direct-dialogue-1.md`, separada dos gates
aprovados. Isso não é aceite integral de CAMP-EVAL-01–08, CAMP-24, Luna ou
TASK-013; nenhum narrador/default foi admitido.
Em seguida, o usuário confirmou que as conclusões CAMP-EVAL-02–04 do ensaio
autorado foram executadas como esperado. O aceite desses desfechos não mede UX,
não cobre todos os percursos 05–08 e não admite Luna. Em 30/09, confirmou que
01 já havia sido executado, que 05 preservou o registro como esperado e que
recusa, orientação e salvamento de 08 fizeram sentido na sequência solicitada
com recarga. A avaliação de UX apontou a mediação impessoal de Mara como perda
de interação e imersão; o usuário prefere NPC em fala direta e role-play.
Essa preferência está documentada separadamente, sem reescrever a prosa
autorada, alterar gates retroativamente ou admitir narrador/default.
O desenho prospectivo da avaliação da campanha por Luna low está em
`evals/narrator/reports/hybrid-campaign-luna-prospective-gate-2026-09-29.md`:
com preflight keyless de 17 turnos, maior corpo HTTP sintético de 12.049 bytes e
 runner/launcher simulados e manifesto de hashes congelado. Em 30/09, o usuário
 autorizou explicitamente toda a proposta HYP-007, inclusive até 17 chamadas
 e teto estimado USD 0,15. Os dois flags do gate foram ativados; ainda não
 houve inserção de chave, gasto ou lote live. Uma falha de custo sem registro
 e o caminho de módulos do lançador foram corrigidos. Preflight keyless:
 17 turnos, zero chamadas, corpo máximo 12.049 bytes; 12 testes focados passaram.
 HYP-007-L1 foi iniciado em 30/09 e parou na primeira requisição com HTTP 400;
 custo final indisponível por falta de uso reportado, sem turno concluído ou
 evidência narrativa. O schema strict não listava `protocol` em `required`,
 causa plausível corrigida localmente; 13 testes focados e preflight keyless
 passaram. O gate live voltou a false para impedir outro lote silencioso.
 [Relatório L1](evals/narrator/reports/hybrid-campaign-luna-hyp-007-l1-2026-09-30.md).
 A admissão continua dependente de avaliação própria; não reutilizar HYP-006.
CAMP-06 foi respondida pelo recorte;
formato/culminação/save têm respostas parciais. Luna low permanece prioritário.

Separadamente, o usuário autorizou reduzir a espera e mostrar custo em todo teste
Luna. Foi implementado o protocolo de ensaio Luna v2: zero cooldown artificial na
UI e no controle, mantendo deadline de 60 s, serialização, quatro chamadas e
768 tokens por chamada. Groq mantém seu intervalo. Os dois lançadores Luna agora
mostram custo estimado ou indisponível no encerramento; nenhum dado ausente vira
zero. Preflight sem chave exibiu custo USD 0, sem inferência. Verificação:
224 testes backend distintos, 211 frontend, TypeScript/build e parser PowerShell.
Relatório: `evals/narrator/reports/luna-latency-cost-preparation-2026-09-29.md`.
Nenhum novo gasto, chamada, narrador/default admitido ou lote histórico alterado.

Em 03/10/2026, o usuário aprovou HYP-007-L2 com até 17 novas chamadas e
teto estimado adicional USD 0,15. O gate L2 está ativo, com manifesto de
hashes e trava atômica de lote único; 14 testes focados, parse PowerShell e
preflight keyless de 17 turnos/zero chamadas passaram. O maior corpo foi
12.019 bytes. Nenhuma chave foi consultada nem houve gasto em L2.
[Prontidão L2](evals/narrator/reports/hybrid-campaign-luna-hyp-007-l2-preflight-2026-10-03.md).
O usuário inseriu a chave com segurança e HYP-007-L2 executou duas chamadas
em 03/10. R-01 foi admitida com fala direta de Mara; R-05 falhou no gate de
política por texto abaixo do mínimo de 30 palavras. A origem do registro no
segundo texto divergiu do roteiro autorado, mas sua posição exata não estava
codificada no pacote canônico: há também lacuna de contexto do ensaio.
O lote parou, sem desfecho ou admissão de
narrador. Custo estimado USD 0,0012318, não cobrança confirmada; L1 tinha
custo indisponível e permanece separado. O gate live L2 voltou a false.
[Resultado L2](evals/narrator/reports/hybrid-campaign-luna-hyp-007-l2-2026-10-03.md).
Em 03/10, o usuário aprovou a opção A de posição em
`plan/observation-campaign-record-location-1.md`. Implementada e verificada
offline: novas sessões `record-at-risk.v2` / `campaign-progression.v2`, posição
`bench` inicial e `dry_surface` apenas após resgate admitido R-05/R-06. R-07
recupera informação sem deslocar objeto; local do jogador não é alterado.
Leitura/reconstrução/retomada v1 preservam formato e hashes sem migração.
101 testes focados passaram, incluindo preflight do prompt prospectivo v2:
17 turnos falsos, zero chamadas externas, maior corpo 13.043 bytes. Regressão
ampliada: 1.612 aprovados e uma falha Windows já documentada de sidecars SQLite;
não declarar suíte integral verde. Evidência em
`evals/narrator/reports/campaign-record-location-v2-2026-10-03.md`.
Em seguida, o usuário aprovou HYP-007-L3 com "Aprovado. Continue": até 17
chamadas Luna low e teto estimado adicional USD 0,15. Runner, preflight e
lançador L3 próprios preparados com prompt v2, manifesto de 20 arquivos e
trava de lote único; 35 testes focados, parse PowerShell e preflight CLI
passaram (17 turnos simulados, zero chamadas, máximo 13.043 bytes). O gate L3
foi ativado para aquela execução. Relatório de prontidão:
`evals/narrator/reports/hybrid-campaign-luna-hyp-007-l3-preflight-2026-10-03.md`.
PowerShell externo pronto, confirmado pelo sinal local de fase
`awaiting_secure_credential` (zero chamadas) em
`eval-results/preflights/hybrid-campaign-luna-l3-ready.json`.
Após a entrada segura da chave, L3 realizou uma chamada e parou em R-01 por
`campaign_source_policy_failed`: zero turnos completos, custo final estimado
USD 0,0007078 (2.285 tokens de entrada e 209 de saída), sem cobrança confirmada.
Autenticação/proveniência funcionaram. A reprodução local mostrou falso positivo
de atribuição: o perfil não repassava Mara do roster canônico ao detector de
agência, que tratava "Ela ... não toca no objeto" como sujeito ambíguo.
TASK-015 corrigiu somente esse repasse; o texto exato passa localmente, sem
reescrever os registros live ou admitir o turno retroativamente. 410 testes
de campanha/atribuição passaram; sete específicos incluem integração fake e
replay único. Dez testes finais (contagens sobrepostas) cobrem atribuição e
preparação L4. L3 ficou fechado, com hashes históricos preservados.
Conclusão técnica proposta: L3 inconclusivo por falso positivo NPC, nenhum
narrador admitido. CAMP-24/TASK-013 seguem abertos. Evidência:
`evals/narrator/reports/hybrid-campaign-luna-hyp-007-l3-2026-10-03.md`.
HYP-007-L4 está preparado offline: mesmo prompt v2 e parâmetros, até 17
chamadas, teto adicional proposto USD 0,15, sem retry/fallback, manifesto próprio
de 21 arquivos. Preflight: zero chamadas e corpo máximo 13.043 bytes; ambos os
flags live/paid estão false. Próxima dependência: aceite delimitado do resultado
L3 e autorização específica de novo gasto L4, não outra decisão de posição.
Não solicitar chave nem executar L4 antes disso. L2 fica fechado e intacto.
Essa dependência foi atendida em seguida com "Aprovado. Continue": conclusão
delimitada L3 aceita e HYP-007-L4 autorizado até 17 chamadas, teto estimado
adicional USD 0,15. Somente os flags L4 foram ativados, sem mudar hashes,
prompt, critérios ou parâmetros. A próxima dependência operacional é entrada
segura da chave no PowerShell externo L4; não pedir orçamento novamente.
Verificação pós-aprovação: três testes de preparação passaram, parser
PowerShell válido, 21 hashes válidos e preflight CLI com zero chamadas,
17 turnos e máximo 13.043 bytes. PowerShell externo aberto e confirmado
pronto pelo sinal `eval-results/preflights/hybrid-campaign-luna-l4-ready.json`,
fase `awaiting_secure_credential`, zero chamadas. Acompanhar os artefatos L4
depois da inserção; fechar gate ao encerrar e apresentar custo/análise antes
do julgamento narrativo. Não ler a chave nem o ambiente do processo.
A limitação lexical de retirada está registrada separadamente em
`plan/observation-campaign-agency-vocabulary-1.md`, sem implementação ou
prioridade automática; não declarar proteção semântica irrestrita.
Não reaproveitar autorizações ou artefatos L1/L2. O protocolo
e o runner estão preparados offline; a avaliação causal da prosa autorada
foi realizada, mas a crítica de UX sobre Mara e a aceitação integral do MVP
continuam separadas. O ritmo A está escolhido: primeira espera avisa,
segunda molha, terceira perde. R-08 conserva o dano de falha da proposta
original. Não pedir novamente A nem DEC-PROG-001/002; não iniciar live por
arrasto e não admitir narrador/default automaticamente.
As instruções antigas de selecionar narrador primeiro, começar a pauta somente
após sua admissão ou ativar HYP-006 estão superadas. Os blocos datados abaixo
preservam histórico; esta seção e o próximo passo ao final regem a continuação.

### Histórico de fechamento e avaliações anteriores

Em 22/09/2026, a auditoria de fechamento de pausa/retomada foi concluída no
worktree `b008`, branch `codex/planejamento-agente-storyteller-v5`, sem acessar
`.env`, segredo ou credencial. Após receber o relatório técnico, o usuário
respondeu “Prossiga” em 22/09/2026. Essa resposta aceitou `TASK-032` e `TASK-033`;
`TASK-034` promoveu o plano para `Completed`. `TASK-041` está
`N/A por DEC-003-B`; não há probe sintético.

Foram corrigidos e provados: gate persistido antes de todo dispatch real, segunda
consulta imediatamente antes do RNG, H4 sem fallback de capacidade que permita
commit, cápsula com hash verificado, recuperação de lease após restart, retomada
somente H6 sem novo RNG, vínculo auditável com a operação original, replay
idempotente, bloqueio de novas ações/rolagens, rascunho editável e CAS concorrente.
Dez claims simultâneos em conexões distintas produziram exatamente um vencedor.

A matriz backend focada final aprovou 163 testes; o frontend aprovou 249 testes,
lint afetado e build. A suíte backend ampla executou até o fim: 8.408 aprovados,
333 ignorados, 285 falhas e 61 erros. O erro-raiz observável permanece nos
experimentos históricos congelados do Narrador (`Final actor schema differs` e
fingerprints derivados), já registrado neste documento; esses artefatos não foram
regravados por arrasto. O lint frontend completo também conserva problemas
preexistentes fora do recorte em `useCharacterState.ts` e
`useInitializationLog.ts`.

Fonte de evidência e procedimento humano aceito:
`evals/narrator/reports/narrator-pause-resume-technical-audit-2026-09-22.md` e
`.json`. Nenhum candidato, default, provedor, custo, fallback ou `CAP-001` foi
promovido. Naquele checkpoint, o próximo item era escolher e admitir o Narrador;
essa ordem foi posteriormente alterada por PROG-ROUTE-B. O parecer daquele ciclo em
`evals/narrator/reports/source-model-choice-status-2026-09-12.md` recomenda não
repetir o comparativo sem hipótese nova: nenhum candidato está qualificado e a
necessidade de código/inferência adicional permanece zero até decisão humana.
O gate reproduzível, com opções e limites de autorização, está em
`evals/narrator/reports/narrator-admission-gate-2026-09-22.md` e `.json`.
Opção recomendada: A, não admitir candidato agora e definir uma hipótese
prospectiva distinta antes de qualquer nova chamada.

Em 22/09/2026, o usuário escolheu a opção A. Nenhum candidato foi admitido e
nenhum default foi criado. O brief prospectivo recomendado foi preparado, sem
chamadas, em
`evals/narrator/reports/narrator-prospective-admission-hypothesis-2026-09-22.md`
e `.json`. Ele propõe testar um contrato de progressão fundamentada contra as
falhas compartilhadas de progressão fraca e estado inventado. Esse era o gate
anterior, fechado pela aceitação registrada no parágrafo seguinte.

Ainda em 22/09/2026, o usuário respondeu `Aprovo HYP-001`. Foram preparados
offline o protocolo, oito casos, extensão de prompt, oito templates sem alvo,
matriz de adulterações, verificador e testes. A regressão relacionada aprovou
421 testes na reconciliação mais recente. O preparador offline continua
target-neutral e registra zero chamada, nenhuma credencial e nenhum alvo.
Evidência:
`evals/narrator/reports/grounded-progression-contract-preparation-2026-09-22.md`
e `.json`. O gate humano separado para alvos, parâmetros, ordem, máximo de
chamadas, parada e execução opt-in foi fechado pela decisão registrada abaixo.
O gate concreto está em
`evals/narrator/reports/grounded-progression-live-gate-2026-09-22.md` e `.json`.
A opção recomendada é `L1`: Qwen e GPT-OSS nos alvos históricos exatos, máximo
de 16 chamadas, sem retry/fallback/gasto pago e com parada fail-closed. O gate
registrava zero chamada e aguardava a decisão descrita no parágrafo seguinte.

Em 22/09/2026, o usuário respondeu `Aprovo LIVE-HYP-001-L1. credencial
pendente`. A credencial foi depois inserida por entrada mascarada no terminal
observável; apenas a confirmação não sensível foi verificada. O lote único L1,
`c03cff72-817f-4881-a864-8a5848011c0a`, executou os 16 slots congelados entre
23:23:58Z e 23:38:59Z. Foram 16 chamadas concluídas, zero falha, zero skip, zero
retry/reparo/fallback e nenhuma troca de alvo. O verificador causal passou no
terminal e foi repetido offline com o mesmo preflight SHA-256
`d2c647a04435413e2395b858fe436e82bad44f415744076d68ffa2ec584dd348`.
A credencial foi removida do ambiente do terminal ao final e não foi lida,
impressa, copiada nem persistida pelo agente.

A revisão semântica independente, vinculada byte a byte às narrativas do
`records.jsonl`, foi executada pelo verificador congelado. Qwen passou 2/8 casos
e GPT-OSS passou 5/8; ambos falharam gates obrigatórios, portanto nenhum candidato
é elegível, nenhum narrador foi admitido e nenhum default foi criado. O Qwen teve
cinco narrativas sem pontuação terminal, uma resposta com 29 palavras e falhas de
estado/progressão; o GPT-OSS avançou a água sem transição, atribuiu aproximação ao
jogador e inventou tipos de instrumentos e uma reação ambiental. Evidência:
`evals/narrator/reports/grounded-progression-live-observation-c03cff72-2026-09-25.md`
e `.json`, com fichas completas em `evals/narrator/reviews/`.

O launcher operacional foi fechado após o lote sem repetir chamadas: ausência de
credencial agora retorna o código fail-closed 3, antes da criação de lote ou rede.
Passaram 32 testes focados (18 contrato, 12 runner, 2 launcher), parse PowerShell
sem erros e contraprova sem credencial com exit 3. A matriz relacionada de 421
testes permanece como a regressão ampla mais recente; não foi repetida porque a
única correção posterior foi o código de saída local do launcher.

Em 25/09/2026, o usuário respondeu `Aceito HYP-001-L1: nenhum candidato
elegível; nenhum narrador admitido.` O aceite fecha a classificação semântica e
o resultado formal de HYP-001; não aprova HYP-002, novo alvo, custo, provedor,
default ou campanha híbrida. Uma verificação não sensível em novo terminal
observável confirmou que a variável de processo dedicada do Groq está ausente.
Nenhuma chamada de autenticação foi tentada sem credencial.

Depois, a credencial foi inserida por entrada mascarada em terminal observável.
Uma única sonda sintética `groq-auth-once-v1`, separada de qualquer bateria,
retornou `success: true` para Groq oficial e `qwen/qwen3.8-27b`, sem categoria de
erro ou status HTTP de falha. A sonda teve deadline de 30 segundos, teto de 128
tokens, zero retry/fallback e não expôs nem persistiu a chave. Ela comprova apenas
autenticação e alcance naquele instante. Evidência:
`evals/narrator/reports/groq-authentication-check-2026-09-25.md` e `.json`.

A proposta prospectiva HYP-002 foi preparada offline em
`evals/narrator/reports/narrator-prospective-admission-hypothesis-002-2026-09-25.md`
e `.json`. A opção recomendada `HYP-002-L1` testa somente o GPT-OSS 120B exato,
reasoning low, contra oito casos sintéticos novos e isomórficos, mudando apenas
o contrato para um plano de renderização de mundo fechado. O máximo proposto é
oito chamadas, sem retry, reparo, fallback ou troca de alvo. Nenhuma chamada
HYP-002 foi feita e a autorização humana permanece pendente.

Em 25/09/2026, o usuário respondeu `Aprovo HYP-002-L2`, escolhendo a alternativa
comparativa com GPT-OSS 120B low e Qwen 3.8 27B none, oito casos novos por alvo e
máximo de 16 chamadas. Foram preparados corpus, protocolo, extensão de prompt,
fixtures de adulteração, preparador/verificador, runner e launcher isolados de
HYP-001. Passaram 34 testes próprios e 66 testes combinados HYP-001 + HYP-002.
O preflight keyless confirmou 16 slots, `provider_calls: 0`,
`credential_inspected: false` e hash canônico
`dd11ec02df78d5bc01b2c7a57df0fdaeade2f51a48aa95875a03eb6bc3a9a8db`.
O parse PowerShell teve zero erro e o launcher sem credencial encerrou com exit 3
antes da rede. Evidência:
`evals/narrator/reports/closed-world-render-live-readiness-2026-09-25.md` e
`.json`. Nenhuma chamada HYP-002 foi realizada até este ponto.

Em 25/09/2026, o lote único HYP-002-L2
`4f13b856-6bf8-4eab-8639-188fc32b05b3` executou os 16 slots congelados entre
01:05:45Z e 01:20:46Z de 26/09 UTC: 16 chamadas concluídas, zero falha, skip,
retry, reparo, fallback, troca de alvo ou repetição. O verificador causal passou
com `LIVE_EXIT=0` e `VERIFY_EXIT=0`, e a credencial foi removida do ambiente do
terminal ao final. A revisão independente comparou as 16 narrativas byte a byte
com `records.jsonl`, sem divergências. Qwen e GPT-OSS passaram 0/8 cada; ambos
falharam o gate fechado de afirmações não listadas, e houve falhas adicionais de
orçamento, unidade obrigatória, continuidade ou próxima escolha. Portanto nenhum
candidato é elegível, nenhum narrador foi admitido e nenhum default foi criado.
O resultado foi posteriormente aceito pelo usuário. Evidência:
`evals/narrator/reports/closed-world-render-live-observation-4f13b856-2026-09-25.md`
e `.json`.

Em 25/09/2026, o usuário respondeu `Aceito HYP-002-L2: nenhum candidato
elegível; nenhum narrador admitido.` O aceite encerra HYP-002 e confirma a
classificação sem promover modelo, provedor, default, custo, `CAP-001` ou campanha
híbrida. A escolha e admissão do Narrador do MVP permanece o próximo bloqueio.

Em 26/09/2026, foi registrada a resposta `Aprovo NARRATOR-ROUTE-A`. Após a
pesquisa oficial, o usuário determinou: `No momento, o uso de provedores pagos
está fora de questão. Faça novos testes no Gemini Flash gratuito`. Isso escolhe
`gemini-3.8-flash` na API direta Google Gemini Free Tier, orçamento US$ 0,00 e
somente dados sintéticos. O Free Tier pode usar entradas e respostas para melhorar
produtos; campanha, dados pessoais e lore privado continuam proibidos.

A preparação offline HYP-003-GEMINI-FREE-L1 foi concluída: oito fixtures novas,
schema nativo `n`/`q`, thinking `low`, 768 tokens por resposta, intervalo mínimo
de 60 segundos, zero retry/reparo/fallback e target efetivo obrigatório. O runner
exige confirmação explícita de projeto Free Tier sem billing antes da chave,
reserva cada chamada antes do dispatch, remove a chave em `finally` e não altera
o runtime padrão. Passaram 36 testes focados, parse PowerShell e preflight sem
credencial. Arquivos: `scripts/evaluate_gemini_free_closed_world_live.py`,
`scripts/run_gemini_free_closed_world_live.ps1` e
`evals/narrator/gemini_free_closed_world_contract_v1.json`. A prontidão está em
`evals/narrator/reports/gemini-free-hypothesis-003-readiness-2026-09-26.md` e
`.json`.

O lote L1 `d56a55b2-e01f-4436-8c97-68dcaebffef2` confirmou o Free Tier e fez
exatamente uma chamada. A API recusou o primeiro request com HTTP 400 antes de
qualquer narrativa; os outros sete slots foram pulados, sem retry, reparo ou
fallback. O verificador de integridade passou antes de qualquer alteração local.
A investigação contra a referência REST oficial identificou a causa no adaptador:
`responseFormat.text.mimeType` recebeu a string legada `application/json`, mas o
novo campo exige o enum `APPLICATION_JSON`. `store: false` foi confirmado como
válido e preservado. O lote falho permanece imutável e não fornece evidência
semântica. Evidência:
`evals/narrator/reports/gemini-free-hypothesis-003-l1-transport-observation-2026-09-26.md`
e `.json`.

A correção mínima foi aplicada ao adaptador e coberta por regressão. O protocolo
prospectivo agora se identifica como HYP-003-GEMINI-FREE-L2/live-v2, para não
reutilizar nem disfarçar o lote L1. Passaram novamente 36 testes focados, o parse
PowerShell tem zero erro e o preflight keyless encerra com exit 0. A prontidão L2
está em `evals/narrator/reports/gemini-free-hypothesis-003-l2-readiness-2026-09-26.md`
e `.json`. A credencial Free Tier é a única dependência humana técnica. Nenhum
narrador/default/CAP-001 foi admitido.

O lote L2 `d64fd149-7f9e-499d-8566-e72207833114` fez três chamadas Free Tier.
As duas primeiras concluíram e passaram individualmente a revisão semântica; a
terceira recebeu HTTP 503 `provider_unavailable`. O protocolo encerrou sem retry
e pulou os cinco slots restantes. O verificador passou no launcher e novamente
offline; a credencial foi removida. Como seis casos ficaram sem resposta, o gate
integral não foi satisfeito: resultado inconclusivo, candidato inelegível, nenhum
narrador/default admitido. Evidência:
`evals/narrator/reports/gemini-free-hypothesis-003-l2-observation-d64fd149-2026-09-26.md`
e `.json`; revisão parcial em
`evals/narrator/reviews/gemini-free-closed-world-d64fd149-partial-codex.json`.
A classificação permaneceu pendente até a decisão explícita registrada no
parágrafo seguinte; L2 não pode ser retomado ou repetido.

Em 26/09/2026, o usuário respondeu `Aceito HYP-003-L2 inconclusivo. Aprovo
HYP-003-L3 integral.` A classificação L2 foi aceita e o novo desenho preserva o
conjunto integral dos mesmos oito casos para comparabilidade. L3 terá identidade,
UUID e preflight próprios; não agrega respostas L2, não retoma slots anteriores e
mantém máximo de oito chamadas Free Tier, zero retry/reparo/fallback, corpus
sintético, target direto e gates semânticos inalterados. Nenhum narrador/default
foi admitido por essa aprovação.

A preparação offline L3 foi concluída. Os dois prompts do launcher agora usam
entrada mascarada, inclusive a confirmação `FREE`, evitando que uma chave colada
no primeiro campo reapareça no terminal. Passaram 37 testes focados, 51 na
regressão relacionada, parse PowerShell e preflight keyless. A prontidão está em
`evals/narrator/reports/gemini-free-hypothesis-003-l3-integral-readiness-2026-09-26.md`
e `.json`. Nenhuma chamada ou autenticação L3 foi feita; a entrada humana da chave
Free Tier é a única dependência técnica restante.

O lote integral L3 `0164d8e2-1c2f-448a-b8db-8a8f744d4466` fez duas chamadas.
A primeira concluiu e passou a revisão semântica; a segunda recebeu HTTP 503
`provider_unavailable`, encerrando o lote e pulando os seis slots seguintes. O
verificador passou no launcher e novamente offline; a credencial foi removida.
Como sete casos ficaram sem resposta, o L3 é inconclusivo e o candidato continua
inelegível. Evidência:
`evals/narrator/reports/gemini-free-hypothesis-003-l3-integral-observation-0164d8e2-2026-09-26.md`
e `.json`; revisão parcial em
`evals/narrator/reviews/gemini-free-closed-world-0164d8e2-partial-codex.json`.

A referência oficial distingue HTTP 503 (sobrecarga/indisponibilidade temporária)
de HTTP 429 (limite/quota) e recomenda retry com backoff. O protocolo L3 proibia
retry; não alterar essa regra por arrasto. Um eventual L4 precisa de decisão
explícita sobre retry estritamente de transporte sem resposta, com limite,
backoff, registro de todas as tentativas e proibição de selecionar narrativas.
Nenhum narrador/default/CAP-001 foi admitido.

Em 26/09/2026, o usuário respondeu `Aceito HYP-003-L3 inconclusivo. Aprovo
HYP-003-L4 integral com retry estrito de transporte`. A classificação L3 foi
aceita. O L4 mantém os oito casos como lote autônomo e permite até dois retries
somente para HTTP 408, 429 ou 5xx sem resposta, na fase `connect`, com backoff
60/180 s, jitter determinístico de 0–15 s e teto global de 16 tentativas. Cada
tentativa é persistida; retry narrativo, reparo, fallback, seleção de melhor saída
e agregação L2/L3 permanecem proibidos.

A preparação offline L4 foi concluída. Passaram 47 testes focados, 61 testes na
regressão relacionada, parse PowerShell e preflight keyless. Contraprovas cobrem
esgotamento por caso/global, erro não elegível, saída inválida, adulteração causal
e eco de credencial. A prontidão está em
`evals/narrator/reports/gemini-free-hypothesis-003-l4-transport-retry-readiness-2026-09-26.md`
e `.json`. No encerramento dessa preparação, nenhuma autenticação ou chamada L4
havia sido feita e a entrada humana da chave Free Tier era a única dependência
técnica restante.

O lote L4 `0a23913a-470e-4f64-9168-c635d9ffff99` fez três chamadas no primeiro
caso. Todas receberam HTTP 503 `provider_unavailable` na fase `connect`, sem
resposta parcial. Os retries estritos aplicaram delays determinísticos de 64 e
186 segundos; a terceira falha encerrou o caso por `per_case_retry_limit` e os
sete casos seguintes foram pulados. Não houve retry narrativo, reparo, fallback,
troca de alvo, seleção de melhor saída ou agregação com L2/L3. O verificador
passou no launcher e novamente offline, e a credencial foi removida. Como nenhum
caso produziu resposta, o L4 é inconclusivo e o candidato continua inelegível;
nenhum narrador ou default foi admitido. Evidência:
`evals/narrator/reports/gemini-free-hypothesis-003-l4-transport-retry-observation-0a23913a-2026-09-26.md`
e `.json`. Naquele ponto, a classificação aguardava aceite humano; nenhum L5
estava autorizado.

Em 26/09/2026, o usuário respondeu `Aceito HYP-003-L4 inconclusivo: nenhum
candidato elegível; nenhum narrador admitido.` O aceite encerra formalmente L4
sem promover Gemini, narrador ou default. Na mesma mensagem, o usuário solicitou
uma nova execução dos testes com Qwen e GPT-OSS para confirmar a incerteza dos
dois modelos antes de buscar alternativas.

A nova bateria foi registrada como
`HYP-004-QWEN-GPT-OSS-REPLICATION-L1`, uma replicação independente do HYP-002-L2.
Ela conserva os mesmos oito casos por modelo, alvos, prompts, temperatura,
raciocínio, pacing e gates, com máximo de 16 chamadas, zero retry/reparo/fallback,
somente fixtures sintéticas e gasto pago não autorizado. Resultados HYP-002 e
HYP-004 serão comparados caso a caso, mas não agregados para admissão nem usados
como seleção de melhor saída.

A preparação offline HYP-004 foi concluída: 17 testes focados e 85 testes na
regressão relacionada passaram, o parse PowerShell teve zero erro, o preflight
keyless confirmou zero chamada e credencial não inspecionada, e a ausência da
variável dedicada encerra antes de criar lote. O HYP-002 histórico foi novamente
verificado com exit 0 após a implementação. Prontidão:
`evals/narrator/reports/closed-world-render-replication-readiness-2026-09-26.md`
e `.json`. Naquele ponto, nenhuma chamada ou autenticação HYP-004 havia sido
feita; a entrada mascarada da chave Groq era a única dependência humana técnica.

O HYP-004 foi executado no lote
`dfd7febc-9e64-4ff6-b81c-c6c40cfd2aa0`: as 16 chamadas foram concluídas sem
falha, skip, retry, reparo, fallback ou troca de alvo; o verificador de artefatos
passou e a credencial foi removida. A revisão semântica independente encontrou
Qwen em 2/8, contra 0/8 no HYP-002, e GPT-OSS novamente em 0/8. Assim, Qwen
demonstrou variabilidade entre amostras mas continua inelegível; GPT-OSS mostrou
falha consistente nas duas execuções observadas. Os lotes não foram agregados,
nenhuma melhor saída foi selecionada e nenhum narrador ou default foi admitido.
Evidência:
`evals/narrator/reports/closed-world-render-replication-observation-dfd7febc-2026-09-26.md`
e `.json`. O fechamento técnico estava concluído e aguardava somente o aceite
humano da classificação HYP-004.

Em 26/09/2026, o usuário respondeu `Aceito HYP-004: Qwen variável e inelegível;
GPT-OSS consistentemente inelegível`. O aceite encerra formalmente HYP-004 sem
admitir narrador ou default. Na mesma mensagem, o usuário autorizou avaliar
modelos chineses com API grátis e, por último, a API do Luna em esforço baixo.

A pesquisa em fontes oficiais selecionou SiliconFlow para a nova hipótese
`HYP-005-SILICONFLOW-FREE-CHINESE-L1`, com três alvos gratuitos exatos:
`XingChenAGI/Xing4.0-29B`, `Qwen/Qwen3.5-4B` e
`THUDM/GLM-4-9B-0414`. O lote mantém os oito casos fechados por alvo, máximo de
24 chamadas, zero retry/reparo/fallback/troca, dados sintéticos, limiar 8/8 por
candidato, sem agregação ou best-of. A preparação offline passou 44 testes
focados, parse PowerShell, preflight keyless e bloqueio antes de criar lote sem
credencial. Evidência:
`evals/narrator/reports/siliconflow-free-chinese-readiness-2026-09-26.md` e
`.json`.

O Luna oficial (`gpt-5.6-luna`) suporta esforço baixo, mas a API é paga, com
preço oficial observado de USD 0,20 por milhão de tokens de entrada e USD 1,20
por milhão de tokens de saída. A solicitação de avaliar Luna não será executada
até o usuário reconhecer explicitamente esse custo e autorizar um teto; isso
preserva a decisão anterior de não usar provedores pagos. Nenhuma chave OpenAI,
chamada Luna ou gasto foi realizado.

A preparação offline do Luna também foi concluída como
`HYP-006-OPENAI-LUNA-LOW-L1`: alvo e esforço exatos, oito casos, máximo de oito
chamadas e 6.144 tokens de saída, zero retry/reparo/fallback/troca, limiar 8/8 e
sem agregação. O runner recusa `--live` antes de chave ou diretório enquanto os
gates `live_inference_authorized` e `paid_spend_authorized` estiverem fechados; o
launcher também exige teto de conta de USD 0,05 e confirmação mascarada literal.
Passaram 48 testes focados e o parse PowerShell. Evidência:
`evals/narrator/reports/openai-luna-low-readiness-2026-09-26.md` e `.json`.
O transporte foi reconciliado com a documentação oficial e agora usa
`POST /v1/responses`, `reasoning.effort: low`, `store: false` e JSON Schema. Um
transporte simulado comprovou corpo, parsing, proveniência e uso reportado sem
chamada externa. Permanecem fechados apenas os gates humanos de custo, teto de
conta e credencial.

Depois, o usuário informou que a plataforma chinesa SiliconFlow não permitia
cadastro estrangeiro e que o Alibaba não entregava o SMS de verificação. Nenhuma
tentativa de contornar cadastro ou verificação foi feita. O usuário abriu e
autenticou uma conta na plataforma global OpenRouter, pediu que o catálogo fosse
avaliado, solicitou incluir modelos não chineses que atendessem aos mesmos
critérios e respondeu `Continue`.

A hipótese vigente passou a ser `HYP-005-OPENROUTER-FREE-L1`, substituindo a
execução SiliconFlow ainda não iniciada. Ela congela três slugs gratuitos com
JSON Schema documentado: `nvidia/nemotron-3-super-120b-a12b:free` e
`liquid/lfm-2.5-2.6b:free`, ambos não chineses, e
`deepseek/deepseek-v4-flash-0731:free`, chinês. Qwen não foi repetido; Gemma,
Inkling, Nemotron Omni/Lightning gratuito e GLM sem schema estrito comprovado
ficaram fora. `openrouter/free` foi excluído por selecionar modelo dinamicamente.

A preparação offline foi concluída com oito casos por candidato e máximo de 24
chamadas. O corpo usa slug único, `provider.allow_fallbacks: false`,
`provider.require_parameters: true` e JSON Schema estrito. Cada resposta precisa
reportar custo exatamente zero `OPENROUTER_CREDITS`; custo ausente, inválido ou
positivo encerra o lote. Continuam proibidos retry, reparo, troca de alvo,
best-of, agregação e dados reais. Passaram 80 testes focados, incluindo o
adaptador OpenRouter e isolamento de rede, além de preflight keyless, bloqueio sem
chave e parse PowerShell. Nenhuma autenticação ou chamada OpenRouter
foi realizada. Evidência:
`evals/narrator/reports/openrouter-free-narrators-readiness-2026-09-26.md` e
`.json`.

Em 26/09/2026, a chave foi inserida por entrada mascarada no terminal observável
e removida do ambiente do processo ao final. O lote único
`cbdad0ac-216c-4b40-baef-3b73c9ae1621` fez 15 chamadas: uma concluída, 14 falhas
operacionais e nove skips. A verificação offline dos artefatos passou. Nemotron
teve sete truncamentos; a rota `:free` exata do DeepSeek retornou 404/modelo
indisponível; o Liquid concluiu somente `favorable-shutter-result` e truncou os
outros seis casos tentados. Não houve retry, reparo, troca de alvo, fallback ou
custo positivo reportado.

A revisão independente do único texto concluído preservou a transição mecânica e
a próxima escolha, mas identificou alegações não listadas sobre eco, frio, sala,
luz, poeira e reação ambiental. Como `unlisted_render_claim` é fatal, o caso não
passa. Os 23 registros incompletos não foram pontuados semanticamente. Evidência:
`evals/narrator/reports/openrouter-free-narrators-observation-cbdad0ac-2026-09-27.md`
e `evals/narrator/reviews/openrouter-free-narrators-cbdad0ac-partial-codex.json`.
Em 27/09/2026, o usuário aceitou formalmente a classificação: Nemotron
inconclusivo por truncamento, Liquid inelegível, DeepSeek inconclusivo por rota
gratuita indisponível; nenhum candidato elegível e nenhum narrador admitido. O
mesmo ato aprovou `HYP-005-L2-B`, alterando somente `max_output_tokens` de 768
para 2048, com máximo de 24 chamadas gratuitas e preservação dos demais gates.

L2-B foi preparado offline sem alterar o runner L1 congelado. Runner, launcher,
gate e testes próprios estão prontos. O preflight registra zero chamada, nenhuma
inspeção de credencial, teto agregado de 49.152 tokens e SHA-256
`bdb6969a598932d1f4bf9c4acbb744a97130b5bc3d0c03e4de4437c07c5f35fc`.
Passaram 104 testes focados finais e o parser PowerShell encontrou zero erro.
Evidência:
`evals/narrator/reports/openrouter-free-narrators-l2-readiness-2026-09-27.md`
e `.json`.

Ainda em 27/09/2026, L2-B foi executado em terminal externo observável. O lote
`47f0c07f-ed8a-49b1-a9a6-4b760e7c4ffd` fez duas chamadas: o primeiro caso do
Nemotron concluiu com rota verificada e custo reportado zero; a segunda chamada
falhou por `provider_unavailable/openrouter_provider_overloaded`. O fail-closed
global preservado produziu 22 skips causais. Não houve retry, reparo, fallback,
troca de alvo ou custo positivo. A reconstrução offline dos artefatos passou.

O aumento de 768 para 2048 permitiu que `hold-silent-bell`, truncado em L1,
concluísse em L2-B. Isso sustenta o teto anterior como barreira de observação
somente para esse caso, sem provar qualidade. A revisão independente preservou
as cinco unidades autorizadas e a ação declarada, mas marcou a afirmação de que
o silêncio envolve sino e pedra como alegação ambiental não listada. O único
caso concluído falhou o gate semântico fatal. Evidência:
`evals/narrator/reports/openrouter-free-narrators-l2-observation-47f0c07f-2026-09-27.md`
e `.json`, com ficha em
`evals/narrator/reviews/openrouter-free-narrators-l2-47f0c07f-partial-codex.json`.
Classificação proposta: Nemotron inelegível; Liquid e DeepSeek inconclusivos e
inelegíveis neste lote; nenhum candidato elegível e nenhum narrador admitido.
Após adicionar o construtor byte-vinculado e a contraprova dos hashes, a matriz
focada final aprovou 107 testes; os JSONs foram reabertos e a revisão regenerada
coincidiu byte a byte com o artefato versionado.

Em 27/09/2026, o usuário aceitou a classificação L2-B: Nemotron inelegível;
Liquid e DeepSeek inconclusivos e inelegíveis no lote; nenhum candidato elegível
e nenhum narrador admitido. No mesmo ato aprovou `HYP-005-L3-B`, permitindo no
máximo um retry estrito da mesma requisição somente para
`provider_unavailable/openrouter_provider_overloaded`, com teto teórico de 48
chamadas gratuitas e execução somente em nova janela diária gratuita.

L3-B foi preparado offline de forma aditiva. O retry conserva objeto de
requisição, invocation ID, deadline, corpo e alvo; outros erros não repetem, a
segunda falha é terminal e cancelamento no pacing é persistido sem contar chamada.
O launcher exige nova janela e custo zero por entrada mascarada, não consulta
`.env` e remove a credencial do processo em `finally`. Passaram 14 testes próprios,
43 na regressão combinada L1/L2/L3, revisores, runner-base e isolamento de rede;
o parser PowerShell encontrou zero erro e o preflight keyless registrou zero
chamada e nenhuma inspeção de credencial. Evidência:
`evals/narrator/reports/openrouter-free-narrators-l3-readiness-2026-09-27.md`
e `.json`. Nenhuma execução L3, autenticação, admissão ou mudança de default foi
realizada. A próxima ação é executar uma única bateria em nova janela diária.

Ainda em 27/09/2026, enquanto a nova janela gratuita não estava disponível, o
usuário solicitou preparar um switch para Luna e depois revogou temporariamente
a decisão “provedores pagos fora de questão” para permitir testes, reservando-se
o direito de restaurá-la. A revogação abre a classe de provedor para avaliação,
mas não autoriza gasto ilimitado, não muda o default e não admite narrador.

O switch `NARRATOR-EVAL-SWITCH-OPENROUTER-L3-TO-LUNA-LOW-V1` foi preparado como
transição apenas entre filas de avaliação. Ele preserva OpenRouter L3 pendente e
aponta para o HYP-006 existente: `gpt-5.6-luna`, esforço `low`, oito casos
sintéticos, máximo de oito chamadas, 768 tokens por resposta, zero retry,
reparo, fallback, agregação ou best-of. O preparador não possui modo live e
valida que os gates pagos permanecem fechados. A documentação oficial atual
confirma Responses API, Structured Outputs, esforço low, ausência de Free Tier e
preços Standard curtos de USD 0,20/M input e USD 1,20/M output.

Passaram 4 testes próprios e 22 na regressão combinada com Luna, runner-base e
isolamento de rede. O preflight registrou zero chamada, nenhuma inspeção de
credencial, nenhum default alterado e nenhum narrador admitido. Evidência:
`evals/narrator/reports/narrator-evaluation-switch-to-luna-readiness-2026-09-27.md`
e `.json`. Antes de execução, ainda é obrigatória autorização explícita do lote
pago delimitado e confirmação humana de limite de conta de USD 0,05.

Em 28/09/2026, a ativação delimitada do HYP-006 foi concluída. O usuário já
havia autorizado temporariamente provedores pagos para realizar os testes,
adicionou USD 5,00 de crédito com recarga automática desativada e confirmou a
gravação de um hard limit mensal de USD 0,05. A interface da organização mostrou
`$0.00 / $0.05` e informou que novas requisições começam a falhar ao atingir o
limite, ressalvando que o enforcement não é instantâneo e pode haver pequena
ultrapassagem. Os gates `live_inference_authorized` e `paid_spend_authorized`
foram abertos somente para HYP-006: `gpt-5.6-luna`, esforço `low`, oito casos
sintéticos, máximo de oito chamadas e 6.144 tokens de saída, zero retry, reparo,
fallback, troca de alvo, agregação ou best-of. Default e admissão continuam
fechados. A única pendência operacional é entrada temporária e mascarada da
credencial no launcher; ela não pode ser lida, exibida ou persistida pelo agente.

Ainda em 28/09/2026, o lote único HYP-006
`c875289b-e3f0-4907-8301-2408781a96ce` foi executado com a credencial inserida
por prompt mascarado e removida do ambiente ao final. Foram exatamente oito
chamadas a `gpt-5.6-luna` com esforço `low`: oito concluídas, zero falha e zero
skip, sem retry, reparo, fallback ou troca de alvo. A verificação offline dos
artefatos passou e confirmou a rota reportada nos oito casos. A API reportou
9.762 tokens de entrada e 1.473 de saída; pelos preços congelados, o custo
calculado é aproximadamente USD 0,00372, sem alegar leitura da cobrança real.

A revisão semântica independente byte-vinculada aprovou os oito casos: zero
alegação não listada, atribuição de agência, vazamento de segredo ou expansão
mecânica, com preservação da próxima escolha. O candidato ficou, naquele lote,
`eligible_for_final_human_narrative_acceptance`, mas nenhum narrador foi
admitido e nenhum default mudou. Os gates pagos foram fechados novamente após o
lote para impedir repetição acidental. Evidência:
`evals/narrator/reports/openai-luna-low-observation-c875289b-2026-09-28.md`,
`.json` e `evals/narrator/reviews/openai-luna-low-c875289b-codex.json`.

Na observação manual posterior, a sessão isolada
`413d4983-ea8a-488c-8687-e31f5c4ac13f` concluiu três chamadas e foi encerrada
pelo operador antes da quarta. O usuário percebeu ausência de progressão real e
sensação de momento em loop. Os turnos confirmam variação ambiental superficial
e nenhuma resposta de Mara a duas perguntas diretas consecutivas. O recorte fixo
explica a ausência de mudança de local ou elenco, mas não o silêncio do NPC. O
ensaio manual, portanto, falhou em demonstrar progressão dramática e
responsividade do NPC. Isso não é promovido por inferência a reprovação universal
do modelo nem desfaz os resultados técnicos do lote de oito casos; a classificação
humana final ainda estava pendente nesse momento e foi fechada abaixo. Nenhum narrador foi admitido e os
gates pagos estão fechados. Evidência:
`evals/narrator/reports/openai-luna-manual-observation-413d4983-2026-09-28.md`
e `.json`.

Em 28/09/2026, o usuário aceitou a classificação final literal: `Aceito HYP-006:
Luna tecnicamente seguro, mas narrativamente inelegível por progressão
insuficiente e baixa responsividade do NPC; nenhum narrador admitido.` HYP-006
está encerrado, nenhum default foi criado e novas chamadas pagas permanecem sem
autorização. O usuário também confirmou que o problema de progressão tem grande
impacto no MVP e deve ser resolvido. Naquele momento não decidiu sua posição na
lista de tarefas; a ordenação foi aprovada em 29/09 por PROG-ROUTE-B. O item foi preservado em
`plan/issue-mvp-narrative-progression-1.md` como bloqueador da aceitação integral,
inicialmente com ordenação pendente. A aprovação posterior autoriza planejamento,
não uma solução específica, novo lote, implementação ou inferência.

Limite preservado do piloto: o gate assume um único operador/conta configurada
por runtime e enforcement persistido por sessão. Coordenação multi-conta/global
entre campanhas exige decisão e migração próprias; não é requisito admitido deste
MVP local.

## Histórico anterior — piloto semântico de Mara ativo no caminho padrão

Ainda em 16/09, `DEC-001` a `DEC-005` foram aprovadas conjuntamente. Foram
implementados `api/catalog_models.py`, `api/catalog_service.py`, a matriz de 66
entradas e o manifesto sidecar. Os seis serviços consumidores usam o registro
validado preservando suas APIs. Passaram 6 testes próprios, 39 focados e, na
regressão ampliada, 200 testes. Uma falha fora do incremento exige uma frase
literal antiga no SYSTEM; nenhum prompt foi modificado e a falha não foi corrigida
por arrasto.

TASK-005 a TASK-014 estão concluídas. A fonte editorial informada pelo usuário é a
compilação privada `Organizando Regras de Vampiro para IA`, no caderno NotebookLM
de 25/04/2026. O manifesto registra título, URL, edição declarada e fundamento de
uso interno. A compilação não identifica páginas dos manuais nem comprova licença
sobre publicações subjacentes; esses limites continuam explícitos e não devem ser
preenchidos por inferência. Os oito poderes possuem metadados tipados, com `null`
nos campos que a fonte não permitiu identificar.

O usuário também designou seis PDFs locais como arquivos-base. O inventário com
hash e papel de autoridade está em `data/catalogs/catalog_manifest.json`: livro-base
e Quickstart V5 são referências mecânicas; a 3ª edição é apenas legado explícito;
os dois documentos de projeto orientam arquitetura/histórico; a aventura Aldi
Sanguine é material de cenário. A presença no inventário não autoriza redistribuição
nem substitui mapeamento de cada alegação para página específica.

Em 16/09, a frente seguinte escolhida pelo usuário foi a arquitetura dos
catálogos determinísticos. A Fase 0 começou sem editar conteúdo V5. Preflight,
inventário dos sete catálogos e baseline da topologia de chamadas estão
concluídos: TASK-001, TASK-002 e TASK-004. Quatro testes offline passaram; a
primeira seleção de pytest apenas referenciou um nome de teste inexistente e não
executou casos. Relatório:
`evals/narrator/reports/deterministic-catalogs-phase0-2026-09-16.md`.

O brief de `DEC-001` a `DEC-005` está em
`plan/decisions-deterministic-context-catalogs-2026-09-16.md`. TASK-003 permanece
aberta até decisão humana. Nenhuma fase dependente foi iniciada e nenhum catálogo,
contrato, provedor, modelo ou limite de chamadas foi alterado.

Ainda em 16/09, a contraprova ao vivo após reinício concluiu o incremento Mara.
Na cena confirmada `Galeria` com `Mara`, a ação única
`Mara, quem é a fundadora deste lugar?` executou `H6.direct_scene`, selecionou
`mara.founder` e declarou `mara.responds.without_founder_identity`. Mara reteve
nome e rosto, chamou a fundadora apenas de “A Primeira”, ofereceu uma pista
acionável e deixou a próxima escolha ao jogador. A operação
`mara-founder-929e1015-50b8-4e50-976c-8402d0d9c1fb` foi persistida uma vez com
hash `e47058814d828082a7eec70eabcfff75a46e6d1271ac1cd10f25a7adf6b680cf`.
Uma tentativa anterior na mesma sessão foi inválida porque a preparação da cena
falhou e permaneceu em Elysium; ela não conta como evidência semântica. Relatório:
`evals/narrator/reports/mara-founder-live-recheck-2026-09-16.md`. TASK-025 está
concluída. Isto não aprova modelo padrão, campanha, runtime ou CAP-001.

Ainda em 16/09, uma segunda ação na mesma sessão isolada expôs um desvio de rota:
`Mara, quem é a fundadora deste lugar?` foi classificada como lore e executada por
`h4.answer_lore_query`, sem H6, beat ou fatos. H4 inventou lore de Brujah e uma
obrigação interna do jogador. O turno sintético histórico permanece confirmado e
inalterado: operação `mara-founder-1e44c905-2a77-470e-a1f2-9e22f71d63c0`, hash
`5c79bea14cbc16115810063b1ded9740c062f48d97e54b17e55e09432f721874`.

A correção prospectiva passa NPCs presentes à triagem e classifica pergunta
explicitamente dirigida a um deles como diálogo antes de H0. Nome ausente e lore
geral conservam a rota anterior. O teste integrado agora produz `mara.founder` e
`mara.responds.without_founder_identity`, sem chamar H0/H4. Passaram 165 testes.
Relatório: `evals/narrator/reports/npc-dialogue-routing-founder-2026-09-16.md`.
O servidor manual atual foi iniciado antes da correção; reiniciá-lo é a única
dependência para a contraprova ao vivo. Não repetir no processo antigo.

Em 16/09/2026, a primeira observação ao vivo do catálogo mínimo no jogo completo
foi concluída. Em Galeria com Mara, a ação `Mara, me fale sobre este lugar.`
selecionou deterministicamente `mara.place_history` e realizou
`mara.answers.place_context`. Qwen/Groq produziu resposta cautelosa, pista parcial,
ajuda condicional e pergunta final acionável, preservando agência, NPC, local e o
limite da identidade da fundadora. O turno foi confirmado uma vez, sem rolagem,
retry ou fallback: operação `mara-live-45423af4-892f-4962-b75d-840d720c71f3`,
hash `e453bc64a4bd20876d0b0301e64f10403298a9943634714f1250d3e59e52a42e`.

O catálogo só forneceu opção, efeito e nove chaves de orientação; gesto, diálogo,
metáfora, atmosfera e gancho foram autoria do modelo. O detalhe sensorial de
`pólvora` não estava na cena inicial: foi admitido como cor não contraditória e
não virou fato separado. A amostra demonstra ativação estreita e autoria útil,
mas não escolhe modelo, valida a campanha inteira, aprova runtime ou CAP-001.
Relatório: `evals/narrator/reports/scene-direction-live-mara-2026-09-16.md`.

Antes da chamada, o diagnóstico seguro foi estendido para erros de agência: o
attempt pode preservar apenas campo, regra, classes e conceitos fechados, nunca
o texto rejeitado ou nomes livres. Passaram 53 testes focados e 213 testes do
pipeline transacional/WebSocket. O servidor foi reiniciado após a correção.

Em 14/09/2026 o usuário aprovou DEC-RES-001 a DEC-RES-005 e mandou prosseguir.
As fases 0, 1, 2 e 3 de `plan/architecture-scene-resolution-1.md` foram concluídas:
especificação, exemplos, núcleo puro, adaptadores, ponte opt-in para H6 e validação
beat/proposta, commit atômico e replay idempotente do recibo. O caminho padrão permanece inalterado e o plano está `In progress`.
Não existe nova rolagem, catálogo canônico, ativação de produto ou escolha de modelo.

Verificação final ampliada: 273 testes aprovados, zero falhas e uma advertência
preexistente. O corpus offline autorado passou 4/4 casos nos gates de causalidade,
agência, atribuição, progressão e não contradição. Relatórios em
`evals/narrator/reports/scene-resolution-core-2026-09-15.md/json` e
`evals/narrator/reports/scene-resolution-offline-2026-09-15.md/json`.

TASK-016 a TASK-019 estão encerradas. O usuário aprovou explicitamente a ativação
em 15/09/2026. A inspeção do caminho padrão mostrou que não existe fonte canônica
de `SceneConsequenceOption`: somente fixtures fornecem opções hoje. A ponte não
foi ligada às cegas, pois isso recusaria turnos reais ou exigiria fabricar
consequências genéricas no orquestrador. O próximo passo depende de escolher a
fonte autoritativa: catálogo por cena/campanha, templates globais ou composição
ordenada dos dois.

O usuário definiu em seguida que o catálogo deve ser mínimo e composto por
palavras-chave: núcleo de personalidade, reações condicionadas por tópicos,
objetivos estáveis e locais, capacidades, limites e caminhos para ajudar,
dificultar ou complicar. H6 conserva fala, gestos, atmosfera, ritmo e realização
concreta. Essa direção foi implementada no piloto de Mara. `effect_keys` vinculam
o mínimo causal; `guidance_keys` orientam sem exigir repetição; `e` declara os
efeitos realizados. A aleatoriedade interna continua adiada.

O caminho padrão agora anexa beat apenas a diálogo explicitamente dirigido a Mara
em Arquivo/Galeria e tópico catalogado. Cenas sem cobertura mantêm o fluxo anterior.
O teste de ponta a ponta com adaptador falso confirmou commit do recibo sem frase
pronta. Regressão ampliada: 352 testes aprovados, zero falhas e uma advertência
preexistente. Relatório:
`evals/narrator/reports/scene-direction-keyword-pilot-2026-09-15.md`.

Em 16/09/2026, o comparativo ao vivo de diálogo
`e6827c97-1af2-4849-9ca8-251aa8c1e3cc` encerrou com 10 chamadas HTTP 200 e
schema/rota válidos, seis commits e duas chamadas dependentes puladas. Qwen teve
saídas truncadas e pergunta final retrospectiva; GPT-OSS foi mais completo, mas
inventou uma chegada anterior no Arquivo. Um falso positivo adicional foi
comprovado na condição `se você observar ... verá`. O gate foi corrigido
prospectivamente para condições de observação e perguntas completas de
preferência feitas por NPC, sem liberar citações incompletas, afirmações ou ações
posteriores. Passaram 654 testes focados, e a reprodução das quatro recusas mudou
somente o caso condicional legítimo para aceito. Relatório:
`evals/narrator/reports/source-dialogue-comparison-e6827c97-2026-09-16.md`.
O lote permanece encerrado, não escolhe modelo padrão e não aprova CAP-001.

O lote `095e7efd-081b-474f-b5ed-179658373ec2` encerrou `finished/1` em
13/09/2026. O verificador oficial passou e confirmou os artefatos sem alterá-los:
oito HTTP200/stop, oito schemas e rotas válidos, seis commits, quatro skips e
nenhuma parada global. Cada candidato teve quatro chamadas e três commits.

Qwen concluiu os três turnos da Oficina e teve o primeiro turno do Arquivo
recusado corretamente por 167 palavras para o teto de 150. GPT-OSS concluiu os três
turnos do Arquivo; sua primeira proposta da Oficina foi recusada por agência,
mas o diagnóstico offline mostrou falso positivo em “dependendo do que você
procura”. Os turnos dependentes não foram enviados, conforme o protocolo.
Assim, nenhum candidato possui os seis turnos confirmados exigidos e nenhum está
qualificado ou aprovado como default. Não repetir o lote para forçar vencedor.

A revisão narrativa principal leu os oito textos gerados. Qwen avançou bem na
Oficina, mas sua espera desenvolveu pouco um elemento anterior. GPT-OSS deu uma
orientação clara no Arquivo, porém seu terceiro turno declarou que nada mudou e
repetiu a oferta de ajuda, caracterizando estagnação. Uma segunda leitura por
modelo diferente, independente dos geradores, coincidiu nos oito vetores e gates.
Ela não foi cega nem organizacionalmente independente porque o contexto da tarefa
já continha identidades e conclusão principal; esse limite está registrado.

Correção prospectiva do falso positivo concluída, sem reclassificar o lote: o
gate agora distingue o interesse condicional terminal de uma busca executada e
continua recusando objeto de busca ou ação posterior. A rodada final combinada
teve 525 testes distintos aprovados. Core atual SHA
`30e7635f124698f7e44e52cb586b2470aebfb6415ee2d1f92372991a907e4aa4`.
Nenhuma nova inferência foi realizada durante o diagnóstico ou a correção.

O usuário retomou em 12/09/2026 e reiterou autonomia: prosseguir até existir uma
intervenção estritamente humana. A chave inserida de forma protegida funcionou nas quatro chamadas do lote
291b3960; isso não comprova quota ou disponibilidade futura. Não ler `.env`, histórico, outra janela ou conteúdo de chave.
Somente a execução concreta por mecanismo protegido pode usar a credencial.

A composição técnica B foi concluída com fixture autorada, sem inferência real:
introdução e orientação das formas aceitas, recusa segura, continuação confirmada,
consulta, reconexão e rolagem independente. Na mesma montagem, texto e identidade
permanecem. Reload perde a cópia local do histórico/input e recupera só o último n/q
confirmado após conexão explícita. O painel é de cena/ação, não uma ficha completa.

O fechamento ASGI duplicado da pausa foi reproduzido e corrigido, com 29 testes
aprovados. O lançador sintético também foi corrigido: Ctrl+C tratado não é reaplicado
após shutdown; stopped exige encerramento sem pendências/falhas do lifespan. Foram
aprovados 33 casos distintos em etapas, com contraprovas e reproduções preservadas.
O delta de rolagem foi revalidado; orientação REQ-006 acrescentou um caso acessível.
Lint e TypeScript finais passaram. Não somar reexecuções como novos casos distintos.

Fixture d249b3fc-f045-4438-97d2-4d3da9e462a9: dois turnos confirmados, consultas,
reconexão e reload sem mutação; lifecycle failed revelou a falha do lançador e
permanece histórico. Fixture final d8abaa85-5c57-40ee-aa4e-041d95513806: uma recusa
com P failed e zero K/H/turnos, depois um diálogo confirmado. Banco idêntico após
consultas/reconexão e shutdown, com um turno e nenhuma pendência. Lifecycle stopped;
a ferramenta retornou 1 ao interromper PowerShell, sem medição separada do exit Python.
Vite exit 0, listeners técnicos ausentes, abas fechadas e viewport restaurado.

Provas: `evals/narrator/reports/source-local-resume-2026-09-12.md` e `.json`;
checkpoint `eval-results/checkpoints/source-local-resume-20260912/manifest.json`.
As 75 cópias da pausa, 53 do comparativo e seis brutos originais conservaram os hashes.
Nenhuma falha histórica foi reclassificada. Os bancos sintéticos são preservados,
não reutilizados para novas observações.

O comparativo 61b83a2f segue encerrado: sete HTTP 200, quatro commits, três recusas,
cinco skips; nenhum candidato qualificado. Modelo/default/campanha/CAP-001 não
aprovados. Correção prospectiva de agência tem 1.097 testes em evidência separada.

O diagnóstico de orçamento 291b3960-55a5-4fdc-a9f4-31d9cfa695f7 está ENCERRADO:
finished/1 em12/09/2026 15:29:12UTC, quatro HTTP200/stop, quatro schemas/rotas válidos,
duas admissões e duas recusas de agência, zero skips. Totais de palavras77/78/104/122,
todos no gate; margem B em2/2, mas A também no gate em2/2. Hipótese não discriminada;
não adotar variante B nem aumentar limites. Uso reportado4962entrada/598saída.
Auditoria íntegra, intervalos>=60s, sem sobreposição/timeout ou nova inferência.

Revisão narrativa principal/independente: C1B responde mais diretamente, mas pouco;
C2 avança modestamente e ambos afirmam que a porta continua aberta/entreaberta sem
esse estado na fonte. Agência C1 foi reproduzida offline: o harness omitiu
npc_aliases; com Bela explicitamente confiável os mesmos textos passam.22contraprovas
exploratórias conservaram ações/emoções/perguntas indevidas recusadas. O fluxo B
configurado e o comparador já repassam aliases, conforme inspeção estática.
Nenhum núcleo, evaluator fechado, prompt ou resultado histórico foi alterado.

Provas: `evals/narrator/reports/source-word-budget-observation-291b3960-2026-09-12.md/json`.
Checkpoint de observação com41cópias e anexo de diagnóstico com10cópias verificados.
A matriz `evals/narrator/reports/source-model-choice-status-2026-09-12.md` distingue
validação técnica, qualidade e produto; nenhum candidato qualificado/default/CAP001.

A ligação interativa Groq foi CONCLUÍDA em preparação offline: novo runner e
launcher, callback de admissão antes de token/deadline e entrada visual própria.
47 casos de handler; 66 de runner e 81 de UI reconciliados em etapas; launcher
55 na suíte final; lint/TypeScript/build aprovados. Preflight conjunto0/45inputs,
sem chave/DB/listener. Vite real isolado encerrado por stdin/exit0/porta liberada;
navegador mostrou entrada desconectada, sem ligar backend. Ctrl+C real do backend
e inferência interativa ainda não exercitados. Nenhum modelo/default/CAP001 aprovado.

Provas: evals/narrator/reports/source-player-interactive-preparation-2026-09-12.md/json;
checkpoint eval-results/checkpoints/source-player-interactive-preparation-20260912/manifest.json,
152 cópias verificadas. Os artefatos anteriores continuam íntegros.

O usuário executou a sessão6486b938-4667-418d-8bc0-57b913c104b7. Encerrada
stopped/0 sem força, admission_unavailable, calls_started0; zero P/K/H, attempts,
turnos e eventos. Nenhum records.jsonl. O texto informado depois foi “Mara, me
fale sobre este lugar”; não foi recuperado do banco. A contraprova mostrou que
essa fala crua não corresponde à gramática existente. O status original não
guardou um subtipo de admissão; não inventar atribuição retroativa mais precisa.

Correção CONCLUÍDA: controles Conversar com Mara/Aguardar. A fala literal é
composta no envelope já aceito; espera exige confirmação explícita. Rascunho bruto
local conserva texto incompatível e mostra erro antes de ID/envio. Modos/query/
reconexão conservam o rascunho; nova ação explícita limpa. Default/parser/reducer/
hook/runner/launcher/prompt/RNG inalterados.51 casos UI reconciliados em etapas,
2 backend simulados, lint/TypeScript/build aprovados. Preflight final a8d9edb2,
exit0/45inputs, sem chave/banco/listener/HTTP. Revisão independente sem pendência.

Provas: evals/narrator/reports/source-player-dialogue-correction-2026-09-12.md/json.
Checkpoints source-player-interactive-observation-6486b938-20260912 e
source-player-dialogue-correction-20260912. Preparação anterior152cópias e
observação58cópias preservadas. Nenhuma inferência nova durante a correção.

A sessão49fffca2-3d4e-4e6c-9dba-ed813c86d985 está ENCERRADA. Quatro HTTP200/stop,
quatro turnos e12 attempts concluídos; quatro eventos de declaração, sem memória
derivada. Launcher/backend stopped/exit0, sem força, reason budget_completed.
Uso reportado9.264 entrada/750 saída. Gaps1076,326/120,835/111,685s e deadlines
respeitados. Portas e PID ausentes. DB/WAL/SHM preservados; WAL não vazio exigiu
consulta de cópia íntegra, sem immutable. Checkpoint de observação com66 cópias,
manifest b4e3a5da047d42bc9bf9fc586dac63f4c673c3bd832390a80534076889042366.

Resultado narrativo: Mara não responde em quatro iniciativas; q1/q2 pressupõem
uma resposta ausente. O terceiro turno avança espacialmente, mas antecipa o
caminhar do jogador a partir de fala; reconhecer a intenção coloquial do convite.
Improvisação ambiental é permitida e não foi tratada como erro. Fontes e aliases
corretos; gates permitem fala de NPC. Ênfase ambiental do SYSTEM é hipótese de
incentivo à evasão, sem demonstração causal. Relatório final:
evals/narrator/reports/source-player-interactive-observation-49fffca2-2026-09-12.md/json.
A nota parcial de um turno e todos os brutos continuam históricos, sem alteração.

Preparação offline do diagnóstico independente de resposta de NPC CONCLUÍDA.
Novo SYSTEM/corpus/protocolo próprios, consumidor e launcher protegidos, sem
alterar núcleo, gates, UI, runner interativo, prompt antigo ou comparador.
78 casos distintos do consumidor e 73 do launcher aprovados em etapas;
151 distintos, sem contar reexecuções como casos novos. Revisão independente
concluída. Preflight final 3abaa31f-d8f9-45f0-ad86-ddc1adf6d9c5, exit 0,
preflight_only_completed, sem chave/rede/DB/diretório de inferência.
SHA 28393e5906af7a1358f409937c8530ca0af137a278898f9c933e71e2606fe26a.
Provas: evals/narrator/reports/source-dialogue-response-preparation-2026-09-12.md/json;
checkpoint eval-results/checkpoints/source-dialogue-response-preparation-20260912/manifest.json.

O usuário executou o lote 81cb2b57-adbe-4b21-a0dd-e16da56f6df1: ENCERRADO,
finished/0 e completed/0, três HTTP200/stop/accepted, sem skips. Auditoria
65/65 e CLI verificador aprovados, brutos preservados. Uso 4.729/481/5.210
tokens entrada/saída/total. Espera inicial60,881507s; gaps60,831661/61,077821s;
deadlines respeitados. Nenhuma chamada extra ou aprovação de produto.

Revisão narrativa: resposta mínima “É um acervo”; recusa reconhecível mas
recuperação parcial “Aqui não é um lugar para perguntas”; espera molha papel
e desenvolve fonte. Agência e q coerentes nos três. Improvisação permitida,
sem comparação causal com49. Não confundir três casos independentes com
conversa continuada. Relatório final:
evals/narrator/reports/source-dialogue-response-observation-81cb2b57-2026-09-12.md/json.
Checkpoint de observação com 41 cópias, SHA 5827173504c4538ffd5d644c6605b66707712cf2fcf5cb9bd8bd95d0efdfd4e9.

Preparação da continuidade de diálogo CONCLUÍDA offline. Consumidor novo
scripts/evaluate_source_dialogue_continuity.py e launcher
scripts/run_groq_source_dialogue_continuity.ps1, sobre APIs B existentes;
nenhuma alteração de núcleo/helpers/variantes históricas/UI/default.
33 casos distintos do consumidor e 60 do launcher aprovados em etapas,
com revisão independente e preflight final 9b21955c-3d46-4c76-a453-8d703a7f5891, exit 0,
33 entradas. Provas em:
evals/narrator/reports/source-dialogue-continuity-preparation-2026-09-12.md/json.
Checkpoint com 97 cópias, SHA ebe2721a72838aaaaf2be744aadb39a0af9914dfa4f99878183a88e3ffd1ce50.

O usuário executou 87e187bb-61e7-4949-9574-4aea19f23c9f: ENCERRADO,
finished/1. Dois HTTP200/stop, schema/rota2/2, P2/K2/H2; um commit, seis attempts,
um evento. T1 e preparação têm replay confirmado sem nova produção; T2 foi
recusado por scene_player_agency_violation e não tem envelope. Auditoria
70/70 e CLI de integridade aprovados; oito brutos preservados.
Fonte USER2 é exatamente o n1 commitado; q fica separado. Uso3574/320/3894.
Intervalos>=60s e deadlines respeitados. Não repetir nem reaplicar a sessão.

Narrativa: Mara responde sobre intenções e esclarece marcas/ausências em T2;
há continuidade temática, ainda abstrata. T2 é proposta recusada, não segundo
turno confirmado. Revisão semântica não encontra ação imposta ao jogador.
Diagnóstico offline reproduziu falso positivo: voce objeto de observando é
tratado como sujeito de esperando (Mara) e permanece (explicação).
Relatório evals/narrator/reports/source-dialogue-continuity-observation-87e187bb-2026-09-12.md/json.
Checkpoint com 69 cópias, SHA 14ec252d78315976047649c765a21825545ca6bdc2c3eaf44e575be42d307fe0; as 97 da preparação intactas.

Correção LOCAL de atribuição concluída: core898c7e9134acee08c711196f2ee4230ddf968f767da87d30047a8e6f7aa93953.
Dois helpers ajustados e três privados novos; demais definições AST preservadas.
Caso n/q87 integral admitido sem declarar espera pelo jogador. Pronome exige
antecedente local comprovado fora da fala; decisão por verbo conserva outros
matches. Fronteiras ambíguas e ações reais do jogador continuam recusadas.

426 testes distintos aprovados:30 novos+63 regressões focais+331 compartilhados
+2 integrações. Dois commits em SQLite novo, n1 como fonte integral, q separado,
ficha/relações intactas e replay reaberto sem produção/RNG/mutação. Revisão
independente concluída. Não houve nova inferência; o lote87 segue recusado.
Provas evals/narrator/reports/source-dialogue-observer-correction-2026-09-12.md/json;
checkpoint source-dialogue-observer-correction-20260912, SHA6379c44e32b3c052a6f5addef65669b75f96238f5550c50db7d97e38e4d1e002.
Os oito brutos e69+97 cópias históricas conservaram hashes. O freeze antigo
representa o core anterior: não substituir seus resultados pelo código corrigido.

Preparação da comparação com diálogo CONCLUÍDA offline. Novo consumidor
scripts/evaluate_source_dialogue_comparison.py e launcher
scripts/run_groq_source_dialogue_comparison.ps1; corpus/protocolo próprios,
SYSTEM dialogue-v1 existente e mesmas cenas/ordem/rubrica de elegibilidade de61b83.
Não importa respostas ou bancos históricos. A pergunta agora cobre as duas
configurações sob o diálogo que81/87 observaram parcialmente com Qwen.

107 casos distintos aprovados em etapas, com revisão independente. Falhas
de auditoria encontradas em timeout sem HTTP e cancelamento após commit foram
corrigidas localmente, sem alterar o runtime; vermelhos preservados. Preflight
nativo 2b399092-bd38-42b9-839a-5a3919908950 exit0/preflight_only_completed, sem chave/HTTP/banco/live dir,
SHA65b51c6042f39b396945f01c97b9947c3ae701aed38e4f84f1abfebdf0375096. Relatório:
evals/narrator/reports/source-dialogue-comparison-preparation-2026-09-12.md/json.
Checkpoint com98 cópias, SHA59a899b352456dc47f36c7cdc7da70f866f26c6508b0de8f3b511ce0f4b03e3b;68+69+97 anteriores intactas.

Revisão e reconciliação concluídas; relatório e checkpoint final fecham a
comparação sem candidato. Não repetir este lote, reaplicar propostas recusadas ou
afrouxar teto/gates. Modelo default, campanha e CAP-001 continuam sem aprovação.

Próximo passo único: fase 3 do plano, integrando beat admitido ao commit atômico e
à recuperação idempotente, ainda sem ativar o caminho padrão. Preservar a ponte
opt-in, não criar catálogo por arrasto e não abrir nova rodada de modelo.

Dois limites existentes dos gates foram registrados, sem correção por arrasto:
heurística lexical pode ler movimento dentro de fala entre aspas; NPC novo apenas
em prosa pode passar por roster estruturado fixo. Os critérios narrativos cobrem
essas condições; não alegar garantias automáticas que o código não oferece.
O protocolo novo foi corrigido para distinguir schema extra de NPC novo na prosa.
Modelo/default/CAP-001 permanecem sem aprovação. Não repetir lotes antigos.

Trabalhar no b008, branch `codex/planejamento-agente-storyteller-v5`, HEAD 5e563824.
Checkout original master limpo; preservar as 39 alterações rastreadas preexistentes
e o trabalho não rastreado. Sem commit/push/merge. Autonomia técnica contínua não
promove aprovação de produto; não pedir nova confirmação por incremento reversível.
As pautas futuras e a criação da ficha por último permanecem na ordem abaixo.

## Estado técnico preservado — projeções públicas B concluídas

Em10/09/2026 o usuário aprovou o roteiro de planejamento da campanha híbrida,
relatou satisfação com o uso teste apesar de problemas pontuais e pediu continuar
do ponto anterior ao teste com interface. Origem e leitores internos da direção B
CONCLUÍDOS no perfil de cena conhecida: campanha somente nova, origem persistida,
snapshot transacional de toda a história elegível e seleção auditada de duas fontes.
Plano `plan/architecture-narrative-source-readers-1.md`; 444 testes finais passaram,
sem falha/skip, com hashes estáveis e revisão independente encerrada.
Prova: `evals/narrator/reports/narrative-source-readers-2026-09-10.md/json`.

A ponte interna exige agora create_narrative_source_campaign; ensure_campaign
genérico não registra origem B. read_source_context_snapshot é a leitura obrigatória
de contexto e consulta interna. O executor confere cena, recibo e reserva; commit e
controle preservam a origem e recusam estado incompatível. Nenhum leitor v1 é usado
para compor o pacote B. Default, UI e save do teste ficam preservados.
O feedback positivo do usuário não reclassifica falhas nem aprova CAP-001.

Preparador interno B também CONCLUÍDO: prepare_source_turn_draft recebe snapshot
e declaração/recibo ordinário tipado do servidor, sem RNG, classificador, efeitos
ou leitor v1. Plano `plan/architecture-narrative-source-preparation-1.md`;
40 testes próprios +7 integrações distintas verdes, com motor real/dados controlados,
FakeLLM e SQLiteTemp. Prova:
`evals/narrator/reports/narrative-source-preparation-2026-09-10.md/json`.
As duas etapas anteriores totalizaram491 casos distintos em etapas.

Coordenador e retenção B CONCLUÍDOS: prepare_retained_source_turn cria a cápsula;
execute_retained_source_turn recupera draft/recibo/configuração por sessão/operação.
Persistência transacional em controle técnico separado, sem DDL/avanço de estado.
Cápsula pronta admite primeira H6; pending/terminal não autoriza takeover/retry.
Reinício, CAS, corrupção, cancelamentos repetidos e replay após4turnos comprovados.
Plano `plan/architecture-narrative-source-coordinator-1.md`;575 testes distintos
em rodada final focada (491 anteriores+84 novos), todos verdes, hashes estáveis.
Prova: `evals/narrator/reports/narrative-source-coordinator-2026-09-10.md/json`.
Zero chamada real, revisão encerrada, executor/funções anteriores de persistência
intactos. Garantia inicia no recibo já resolvido retido; não é gate antes do RNG
externo nem implementação de retry/pausa. protected_secrets deve permanecer vazio.

Harness da entrada retida B CONCLUÍDO e verificado offline: dois turnos
dependentes em Galeria, base nova, alvo Qwen/Groq explícito e prompt preservado.
Plano `plan/feature-retained-source-probe-1.md`;72 testes distintos finais verdes,
hashes estáveis, revisão encerrada e preflight real -PreflightOnly exit0.
Prova: `evals/narrator/reports/retained-source-probe-preparation-2026-09-10.md/json`.
Zero chamada externa nesta preparação; sem resultado ou aprovação live.

Observação retida e9689855-aef3-4765-8213-704aaaeff4f0 ENCERRADA:
lifecycle finished/0 em 10/09/2026 23:56:58 UTC. Duas chamadas HTTP200/stop,
duas cápsulas, schemas, rotas, commits e replays; fonte anterior completa no
segundo USER. 2693 tokens de entrada e327 de saída reportados; custo indisponível.
Revisão narrativa: continuidade/agência preservadas, progressão fraca/repetição;
pequeno endurecimento de "parece parado" para "permanece parado" sem novo suporte.
Não alterar raw summary/JSONL/SQLite nem repetir/importar este lote.
Relatório: `evals/narrator/reports/retained-source-observation-e9689855-2026-09-10.md/json`.

Variante SYSTEM narrative-source-progress-v1 preparada e verificada: 77 testes
distintos em duas rodadas, sem falhas/skips; cinco provas de isolamento; review
encerrado; preflight real sem chave com saída0. Plano concluído para preparação:
`plan/feature-progressing-source-observation-1.md`.
Prova: `evals/narrator/reports/progressing-source-preparation-2026-09-10.md/json`.
Preserva SYSTEM anterior e acrescenta um parágrafo para acontecimento observável
durante a espera, mantendo agência/incertezas. Na preparação, nenhuma chamada da variante havia ocorrido.

Lote progressing 19b93f22-a4da-408d-992f-2c1dd42213b0 ENCERRADO: finished/0,
11/09/2026 00:14:10 UTC (10/09 local). Duas chamadas HTTP200/stop, dois commits
e replays, fonte anterior íntegra. 2961 tokens de entrada +291 de saída reportados.
Critério narrativo principal NÃO satisfeito: poeira só muda ligeiramente, cena
permanece estática. Revisão independente concorda; gates técnicos não reclassificados.
Relatório: `evals/narrator/reports/progressing-source-observation-19b93f22-2026-09-10.md/json`.
Não repetir esse lote nem investir em outra paráfrase de SYSTEM sem diagnóstico.

Contraprova offline de progressão CONCLUÍDA: quatro testes passaram (um positivo
e três negativos delimitados), sem alterar core/gates. O coordenador admitiu o
acontecimento autorado, conservou as fontes e repetiu o resultado sem nova chamada.
Prova: `evals/narrator/reports/source-progression-admission-2026-09-10.md/json`.
Permite essa progressão concreta; não prova capacidade do modelo. O negativo
mecânico cobre conteúdo interno explícito, não detector geral de efeitos inventados.

Diagnóstico puro de contexto PREPARADO: fontes autoradas steady/event_started,
independentes, mesmo SYSTEM/modelo/schema/ação. Sem campanha, SQLite, commit ou replay.
74 testes distintos finais verdes, review encerrado, 65 hashes preservados,
preflight real sem chave exit 0. Plano `plan/feature-source-progression-diagnostic-1.md`
Completed para preparação; relatório `evals/narrator/reports/source-context-preparation-2026-09-10.md/json`.

Lote source-context cc09080a-8368-421c-b892-b18dfa79bc85 ENCERRADO: finished/0
em 11/09/2026 01:01:15 UTC (10/09 local). Duas chamadas HTTP200/stop, gates aceitos,
zero skips; 3371 tokens de entrada +295 de saída. Fonte estável não avançou;
fonte em curso gerou novidade parcial, fechando causas sem suporte perceptível.
Critérios autorados integrais não satisfeitos; revisão independente concordou.
Prova: `evals/narrator/reports/source-context-observation-cc09080a-2026-09-10.md/json`.
Não repetir o lote, afrouxar política ou investir em outra paráfrase de SYSTEM.

Trabalho retomado em 11/09/2026 pelo usuário, após teste de acesso remoto.
Preflight confirmou branch e alterações anteriores preservadas no worktree b008.

Consulta interna de operação B CONCLUÍDA: estado e causa segura original,
fotografia transacional somente leitura, identidade/hashes revalidados e sem H6.
673 casos distintos verificados em rodadas focadas (98 novos +575 regressões);
revisão independente encerrada e 93 funções anteriores preservadas.
Plano `plan/feature-narrative-source-operation-status-1.md`; prova
`evals/narrator/reports/narrative-source-operation-status-2026-09-11.md/json`.

Contrato da entrada optativa B e guarda interna CONCLUÍDOS em 11/09/2026:
SourcePlayerActionRequest contém somente operation_id/player_input; sessão é
autoridade do chamador servidor. Texto literal até500 caracteres, ID B até240,
padding externo recusado sem normalização. Guarda revalida cópia do snapshot
contra sessão/origem/cena, sem autenticar banco, classificar ou autorizar efeitos.
161 testes focados passaram (72 novos +89 regressões), revisão independente encerrada.
Prova: `evals/narrator/reports/narrative-source-entry-2026-09-11.md/json`.
Plano `plan/feature-narrative-source-opt-in-entry-1.md` concluído para entrada+desenho.

Produtor pré-recibo B CONCLUÍDO em 11/09/2026:
`plan/feature-narrative-source-input-producer-1.md` Completed. Modelos, claim/finalize
SQLite, adaptador local e prepare_source_player_action implementados e revisados.
P reservado antes de produção; K/P gravados juntos; replay terminal antes do CAS;
base obsoleta/escopo/esclarecimento como falha segura sem cápsula. Recuperação
histórica process_interrupted validada sem reescrita. Pending não autoriza rerrolar.
96 funções anteriores de persistência textualmente intactas, schema preservado.

Rodadas finais: modelos167, persistência272, adaptador137 e serviço18 passaram,
zero falha/skip, com um aviso preexistente por rodada. São594 casos distintos do
produtor; incluindo entrada/contexto,683 distintos e288 novos nesta sequência.
Prova: `evals/narrator/reports/narrative-source-input-producer-2026-09-11.md/json`.
Perfil interno local: espera, fala dirigida a NPC conhecido e investigação ordinária
Wits+Investigation/dificuldade3; ficha elegível/Fome0, sem efeitos genéricos.
Texto fora da cobertura e condições especiais recusados antes de RNG. Não é
compreensão geral, campanha completa ou prova de qualidade live. UI/default intactos.

Setup/introdução B CONCLUÍDOS em 11/09/2026:
`plan/feature-narrative-source-setup-1.md` Completed, manifesto autorado puro,
criação atômica com origem e leitor próprio somente leitura após reinício/progresso.
110 funções anteriores e schema da persistência preservados. Composição por
setup→ação sintética escolhida→produtor→K→H6 sem wrapper ou rota novos.
488 testes distintos passaram, incluindo184 novos. Modelos210, persistência270,
fluxo8; revisão independente encerrada. A primeira rodada do fluxo teve4falhas/3pass
por alias NPC omitido na configuração sintética; logs preservados, caller corrigido
com npc_aliases=("Mara",), texto/política intactos e contraprova acrescentada.
Prova: `evals/narrator/reports/narrative-source-setup-2026-09-11.md/json`.

Observação source-player PREPARADA e verificada em11/09/2026:
43 testes do executor passaram na primeira rodada e7 cenários do launcher em
rodadas focadas; só fixture PowerShell corrigida após5pass/2fail, logs preservados.
Revisão independente encerrada. P/K sob cancelamento recuperados sem reprodução,
recibo declarado e erros fechados conferidos, limites HTTP/eco de chave testados.
Preflight real70034cd6-b60c-4565-a8de-2fce835315da exit0/preflight_only_completed,
28 arquivos conferidos, sem chave/live. Prova:
`evals/narrator/reports/source-player-preparation-2026-09-11.md/json`.

Lote source-player83921947-4094-4798-990c-af65f7963e61 ENCERRADO em11/09,
19:03 local: finished/0, duas HTTP200/stop, dois commits e replays, zero skips.
Auditoria offline aprovada,28 hashes congelados preservados; espera inicial62,731411s,
intervalo61,972224s. Uso3110entrada+365saída; custo indisponível.
Revisão narrativa independente: fala pertinente porém metafórica, luz pisca/lápis
para; novidade mínima real, avanço substantivo insuficiente. Continuidade/agência
e incertezas preservadas. Objetos plausíveis e fala atribuída não são violações.
Não reescrever summary/JSONL/SQLite nem repetir lote. Relatório separado:
`evals/narrator/reports/source-player-observation-83921947-2026-09-11.md/json`.
Plano de observação Completed; qualidade geral, experiência, runtime eCAP-001
continuam não aprovados. Nova credencial não é necessária para o incremento local.

Projeções públicas B CONCLUÍDAS e revisadas: api/narrative_source_transport.py
com contratos estritos e fábricas puras para briefing, preparação/retida/pending,
completa/recusada e unavailable. Identidade/turno confirmado vinculados; n/q
literais, sem objetos internos ou autoridade retry.215 casos finais passaram,
205 novos+10regressões. Primeira rodada202 verdes; review identificou três pares
legítimos provider timeout/cancelled e delivery cancelled;3contraprovas reais
falharam antes da correção explícita, logs preservados. Nenhum core antigo mudou.
Prova: `evals/narrator/reports/narrative-source-public-projection-2026-09-11.md/json`.

Próxima tarefa registrada no plano de transporte (reconciliar com prioridade acima):
TASK-001, fechar seleção/vínculo do ensaio local
inativo antes dos leitores/reservas/accept legados. Padrão existente: desktop de
um operador, loopback e banco sintético, sessão escolhida pelo servidor. Inspeção
e alternativas registradas; hash/UUID não autentica jogador. Acesso direto remoto
é decisão distinta, ainda não tomada. TASK-003 só projeta; despacho requer handler.
Experiência do source-player continua parcial e não autoriza ativação de produto.

`plan/feature-narrative-source-transport-1.md` está In progress somente no contrato
público puro/inativo; inspeção inicial
registrou ausência de vínculo explícito de proprietário no endpoint legado,
sem inferir exposição remota. Contrato de acesso/rota deve ser definido antes
da ativação, sem introduzir autenticação por arrasto. UI/default/save preservados.
Autonomia reiterada por voz em11/09: avançar em tudo que não exigir intervenção
estrita. Pending/terminal sem retry e decisões CAMP/DEC continuam preservados.

Correções do uso teste e seus hashes continuam registradas em
`evals/narrator/reports/manual-current-game-guards-continuity-2026-09-09.md/json`.
Última sessão observada em09/09: local.4cfd5337-1c84-487e-bd77-8fe8e4d78a29,
9turnos/revisão11, guardas preservados. Run04e0a3ce-8112-4b58-8919-ea8f7e681221,
servidor30516, launcher23100 eram ready naquela observação; estado operacional
não revalidado nesta retomada. Não duplicar janela, recuperar chave ou mexer no
banco desse teste como parte do incremento B.

## Funcionalidade aprovada para depois — bandeja de dados

`spec/design-visible-v5-dice-tray.md` registra aprovação em25/08 e adiamento:
proposta do teste → clique obrigatório quando há rolagem → faces/resultado
persistido → narrativa automática. Interface atual ainda possui envio de ação
e atalhos, sem botão separado de confirmação. Não é controle oculto. O desenho
requer estado intermediário durável; não antecipar implementação/refinamento
antes de concluir e aceitar o escopo predecessor. A consulta de11/09 confirmou
o documento e o código; não alterou a decisão nem a prioridade da direção B.

Lembrete futuro, sem tarefa nem implementação: desenhar com calma a orientação
de perícias/habilidades junto da bandeja, incluindo exemplos de uso, seleção por
clique, adequação à cena e restrições explicadas com base no que o personagem sabe.
Distinguir restrição do personagem/cena de funcionalidade ainda não suportada.
O usuário pediu explicitamente conservar isso apenas como lembrete, sem abrir task
ou desenvolver agora. As sugestões discutidas não são requisitos já fechados.

## Planejamento atual — Resolvedor determinístico de cenas e intenções de NPCs

Registro iniciado em12/09/2026 como proposta provisória de backlog e promovido
para planejamento por decisão humana em14/09/2026.
Motivação: investigar cenas que estagnam e respostas de NPCs pouco consistentes,
preservando uma experiência interessante e causalmente ligada às ações do jogador.
O planejamento está aprovado; implementação e detalhes DEC-RES-001 a DEC-RES-005
continuam pendentes.

Prioridade recomendada e provisória: alta para o funcionamento narrativo, depois
de fechar o trabalho técnico corrente de transporte e comparação/decisão de modelo.
Recomenda-se discutir a resolução e a progressão das cenas antes de fechar o roteiro
macro da campanha, articulando-a ao checklist abaixo; a revisão ampla do design
system/modal fica após a estabilização funcional. Esta é uma recomendação de posição,
não uma reordenação aprovada: o próximo passo corrente, a bandeja de dados e suas
dependências permanecem preservados. A criação inicial da ficha continua por último.

Relação com entregas existentes: `plan/architecture-llm-memory-turns-1.md` está
**Completed**, incluindo eventos, contexto, memória e persistência; a referência
à tarefa de regras/memória como parcial não corresponde ao estado atual desse plano.
O diagnóstico `plan/feature-source-progression-diagnostic-1.md` também está concluído.
A proposta é uma evolução relacionada a essas bases, sem duplicá-las, reabri-las
ou afirmar que este resolvedor já existe. Relaciona-se ainda a CAMP-09–11 e
CAMP-17–20 em `plan/checklist-planejamento-campanha-hibrida.md`.

Dependência da base do resolvedor: um contrato mínimo e estruturado das fichas
que participam da resolução, ao menos ficha/estado do NPC e, quando a ação,
capacidades ou restrições do jogador influenciarem o resultado, os campos mínimos
da ficha do jogador. Esse contrato pode ser definido e testado com dados sintéticos
ou perfis predefinidos; integra a base do resolvedor e não antecipa a interface
de criação da ficha.

A experiência completa de criação da ficha — modal, clãs, habilidades, pontos de
poder, revisão e fixação do perfil após o início — permanece como o último item
do backlog atual. Quando chegar sua vez, deverá consumir o contrato estável
definido anteriormente, sem antecipar ou duplicar essa construção.

A definição futura do contrato não equivale à implementação da ficha. Campos,
escalas e regras de balanceamento continuam abertos; esta distinção documental
preserva a prioridade alta provisória e a posição recomendada do resolvedor.

Escopo proposto para refinamento futuro:

- Após a ação do jogador, avaliar contexto, cena, relações e limites da ficha do
  NPC; definir um conjunto de comportamentos compatíveis com sua personalidade.
- Considerar modificadores da cena, da relação e da ação do jogador para propor
  postura/intenção momentânea, pressão e avanço da cena quando forem pertinentes.
- Selecionar apenas desfechos plausíveis, com aleatoriedade controlada quando
  couber: ouvir, interromper, recuar, escalar o conflito, deslocar-se ou iniciar
  combate somente quando as regras e a situação permitirem a transição.
- Preservar uma única rolagem reproduzível e persistida para a resolução aplicável;
  falha na prosa não justificaria nova rolagem ou reaplicação de efeitos.
- Entregar uma saída estruturada ao narrador para verbalização, com validação
  antes de torná-la canônica e sem permitir ações ou estados inventados em conflito
  com o resultado, os fatos estabelecidos ou a liberdade do personagem do jogador.
- Prever testes sintéticos/offline de reprodutibilidade, limites da ficha,
  transições impossíveis, relevância causal e prevenção de turnos estagnados.

Decisões abertas: dado de1–5, mapeamento de posturas, clamp versus amostragem direta,
número de escalas e regras de transição. Pressão/temperatura da cena é um conceito
ficcional a definir, distinto da temperatura da API. Também fica aberta a divisão
de autoridade entre resolvedor e narrador: hoje `spec/spec-improvisational-scene-direction.md`
permite ações/falas de NPCs, pressão e transições improvisadas sob admissão.
Transferir parte dessas escolhas para regras exige discussão arquitetural própria;
este registro não altera essa fronteira nem fixa técnicas, pesos ou escalas.

Registro documental apenas: nenhum código, teste, acesso a credenciais/banco ou
desenho de interface foi iniciado para esta proposta.

## Pauta futura — planejamento da campanha híbrida

Em10/09 o usuário aprovou este roteiro de planejamento. As perguntas serão
retomadas **depois de concluir
as tarefas já em andamento**. Checklist com 24 perguntas:
[Checklist de planejamento da campanha híbrida](plan/checklist-planejamento-campanha-hibrida.md).
Abrange sessão zero, estrutura geral, mundo/segredos, improvisação/agência,
ritmo/culminação e encerramento/integração. Retomar um bloco por vez quando chegar
esse momento. A preferência pelo modelo misto orienta o planejamento; respostas
e decisões detalhadas permanecem abertas. Esta pauta não substitui a prioridade
corrente nem inicia implementação de campanha ou altera a direção B.

## Mini-tarefa futura — conforto visual e imersão da interface

- [ ] **Refinar a interface e o design system para conforto visual e imersão** —
  tarefa futura de experiência/interface, com implementação dependente de refinamento.

Relato do usuário: o fundo/cenário muito branco e claro causa incômodo visual;
cores, composição e design system parecem estranhos no conjunto e não produzem imersão.

Prioridade **recomendada e provisória: P2 / média-alta de experiência do produto**,
sujeita à decisão humana, sem alterar prioridades já aprovadas. Não interromper
o trabalho técnico corrente nem a comparação/decisão de modelo. Posicionamento
recomendado: depois da estabilização do fluxo funcional atual e antes de novas
superfícies importantes de jogador, especialmente a criação inicial da ficha/modal.
A tarefa de criação da ficha abaixo permanece explicitamente como o último item.

Escopo a refinar: auditar telas, tokens, modal e layout geral do jogo; investigar luminância/fundos claros,
contraste e legibilidade, cores, tipografia, espaçamento, hierarquia, estados e
coerência entre componentes; definir uma direção coerente com o tom do jogo e mais
imersiva; prototipar em uma cena representativa; avaliar conforto, legibilidade e
imersão; somente depois propagar o sistema revisado. Não fixar cores, fontes ou
estética final; orientações da skill frontend-design não são requisitos do produto.
Modal e layout são áreas a auditar e refinar quanto à hierarquia, composição,
navegação, legibilidade, coerência e imersão, sem solução de interface fixada.

Observação separada: se o excesso de branco estiver impedindo o uso, uma correção
mínima de conforto visual pode ser considerada para antecipação, sem antecipar a
revisão completa. Esse impedimento não foi confirmado aqui e este registro não
inicia a correção. Nenhum código, teste ou desenho visual dessa mini-tarefa foi iniciado.

## Última tarefa futura do backlog atual — criação inicial da ficha

- [ ] **Criação inicial da ficha de personagem pelos jogadores** — tarefa futura
  de **experiência do jogador e fluxo de jogo**, com escopo ainda a refinar.

Posicionamento explícito: **último item da sequência/backlog atual, depois de todas
as tarefas já registradas**, incluindo o trabalho técnico corrente e as pautas
futuras acima. Não altera prioridades existentes nem antecipa sua execução.

Quando chegar sua vez, refinar o fluxo de início de jogo em que cada jogador cria
a ficha do personagem, distribui pontos de poder e define os demais elementos
iniciais necessários. Regras, validações, persistência e reflexos na experiência
do jogo são temas do escopo a refinar, não decisões arquiteturais aprovadas.
Ideia de experiência a refinar: criação em um modal próprio, com seleção guiada
por componentes como carrosséis de clãs e de habilidades, além da distribuição
de pontos de poder e dos demais elementos iniciais da ficha. Modal, carrosséis,
clãs e habilidades ficam registrados como direção/ideia de produto para discussão
futura, sem decisão de UI, requisito fechado ou autorização de implementação.

Registro documental apenas: nenhuma implementação, teste ou desenho técnico iniciado
para esta tarefa; ela permanece separada das tarefas técnicas correntes.

## Autorização atual — continuidade plena em 07/09/2026

O usuário ampliou explicitamente a autorização para novas observações necessárias
à continuidade. Não pedir nova aprovação por hipótese, variante ou lote. As
restrições humanas mantidas são chaves/credenciais e ações de intervenção que
exijam sua atuação direta. Esta instrução supera os pedidos históricos de nova
decisão específica presentes nos relatórios e nos estados abaixo.

Estado corrente: direção B APROVADA em 07/09/2026. O usuário respondeu:
“Concordo. A direção B parece mais promissora. Prossiga”. Não pedir novamente
aprovação de B. Fundação e perfil experimental já implementados e verificados:
24 testes de fonte/binding/assessment e 57 casos distintos de n/q/política/contexto.
Uma projeção source_only conserva n integral e atribuído, separado de q; verdade
semântica geral permanece not_assessed e afirmação canônica livre indeterminada.
A ponte de aplicação abaixo é optativa; o caminho padrão do produto, migração e canonização de novidades livres não foram ativados.

Planos concluídos: `plan/architecture-narrative-grounding-1.md` (fundação/pilotos/desenho)
e `plan/architecture-narrative-source-bridge-1.md` (ponte interna local optativa).
A integração mais ampla de leitores/default/save continua distinta. Desenho revisado em
`evals/narrator/reviews/narrative-source-integration-design-2026-09-07.md`.
Lote Estufa f97a8568:1 chamada HTTP200/schema válido, q="O que fazes?" recusada,
0 projeções e1 skip. Cadeia não observada. Brutos/prepared_* históricos preservados.
Auditoria anterior à correção em `evals/narrator/reports/narrative-source-observation-f97a8568-2026-09-07.md/json`.
Não repetir Estufa: executor bloqueia --live histórico antes da credencial.

Falso negativo corrigido localmente por família integral delimitada;274 testes
focados passaram,30 novos, com agência/sigilo/mecânica/interlocutor preservados.
API SHA143ebab307b8720b8380c5daa2cab691048c5cffccfc7ed0c9a8d0e7996fa921.
Prova em `evals/narrator/reports/player-question-fazes-fix-2026-09-07.md/json`.
O resultado histórico não foi reclassificado nem a narrativa reexecutada.

Pátio f6483710 ENCERRADO:2 chamadasHTTP200/2schemas,1política/projeção válida,
segunda saída155palavras recusada por scene_narrative_too_long (limite150correto).
Primeira fonte integral/atribuída entrou exatamente no segundo USER, q separado.
Uma passagem observada, não2turnosadmitidos; continuidade textual majoritariamente
repetitiva. Uso2.462tokens, custoindisponível. Lifecyclefinished/exit1, chave descartada;
janela NoExit PID4080podepermanecer. Não relançar ou ajustar limiteparaaprovar.
Auditoria: `evals/narrator/reports/narrative-source-courtyard-observation-f6483710-2026-09-07.md/json`.
Pacote histórico: `evals/narrator/reports/narrative-source-courtyard-preparation-2026-09-07.md/json`;
66testes finais executor/wrapper, zerochamada externa na preparação, hashes/brutos intactos.
Ponte local CONCLUÍDA: execute_source_turn, perfil de aplicação próprio, envelope
narrative-source-turn-v1, obrigação ancorada antes da geração, commit/replay/recuperação.
85 casos contratuais +29 de persistência B +7 legados +31 integrados passaram em rodadas
focadas distintas; três turnos/reinício, n>600 integral, q separado, falhas/CAS/cancelamento.
Prova: `evals/narrator/reports/narrative-source-local-bridge-2026-09-07.md/json`.
Nenhuma nova chamada externa na ponte. Últimas duas fontes comprometidas, contexto do
chamador vazio e cena l/p de origem servidor; não é adaptador de saves v1 nem campanha
completa. Padrão do produto, frontend e banco real sem ativação B.
Modelo adicional obrigatório, API paga, migração automática e promoção CAP/runtime
não são aprovados por arrasto.

Estado anterior: consolidação e auditoria local de memória concluídas em 07/09/2026.
Corpus `evals/narrator/reviews/record-summary-semantic-corpus-v1-2026-09-07.md/json`:
seis saídas, 46 relações autoradas, 81 trechos literais, oito brutos intactos;
revisão independente sem achados materiais. Não há classificador semântico novo.
Auditoria `evals/narrator/reviews/narrative-memory-admission-boundary-2026-09-07.md/json`:
três controles locais passaram como caracterização: fiel preservado, referência
inexistente recusada e transferência base azul→luz azul admitida até CONHECIDO.
Adaptador falso, SQLite Temp, zero rede, sem segundo turno/LLM ou replay CAP.
Isso demonstra limite do desenho abstrativo atual, já reconhecido na especificação;
referências e política delimitada não são prova semântica geral.

Correção local concluída em api/memory_service.py: fallback summary="" sem resumo
canônico agora mantém origem LLM/PENDING. Resumo canônico existente e rejeição de
espaços preservados. RED reproduziu a falha; 15 testes finais passaram, revisão
independente e diff check concluídos. API SHA4a8bfa8004879053417771b3f69020b48b5eaa18be4af6ca73e2040ca1755cf4;
testes SHA2407825b5e1125e25c38c72a2fb70527e044c266a401cccd96e00784699af54d.
A correção ocorreu depois dos lotes: preservar metadados/hashes históricos.

A consolidação anterior foi concluída. Sua comparação de alternativas foi
sucedida pela aprovação explícita de B acima. As declarações históricas de
“proposta não aprovada” ou de espera por nova decisão não são bloqueios atuais.
Não reabrir fontes/lotes encerrados para aumentar taxa. O piloto fonte integral
é uma hipótese distinta de representação, já coberta pela direção aprovada.

Estado anterior: summary-relational `faad6837-cc0b-408d-85a6-025d0db770b3` encerrado e analisado.
Run `eval-results/20260907T214523Z-c8bd771b-741e-4c06-97ff-085c9882bdf2`.
PID 1096 finished em 2026-09-07T21:47:25.3117077Z, exit 0; credencial descartada.
Duas chamadas control→relational, uma fonte gallery-reflection e USER idêntico,
HTTP 200/stop, rotas Groq/Qwen e schemas válidos. Controle 19 palavras/128 caracteres;
relational 23/156. Mesmo trecho espacial ambíguo nos dois: “espelho reflete tapeçaria
diante de janela fechada”; não afirmar transferência inequívoca ao espelho.
A variante retém o apoio das molduras contra a parede; demais omissões são não
informativas. Nenhuma falsidade explícita ou defeito local demonstrado; sem vencedor,
causalidade, taxa ou aprovação geral de fidelidade/runtime/CAP-001.
Uso 996 entrada + 86 saída = 1.082; raciocínio null/não zero, custo indisponível.
Revisão autorada separada do bruto not_performed/approval null.
Relatório `evals/narrator/reports/record-summary-relational-observation-faad6837-2026-09-07.md`
e JSON associado, com matriz por relação e auditoria final independente.
Summary SHA `49cf7ad2f9abb57be49da3dd8338d04d8329a334716bbccc6e3c18a4935cd178`;
JSONL SHA `2b8484a9d9f0a122d2d7438224335ad742bcc3c054943b6cd13652fdec5e982c`.
Auditoria 961b6ea6 confirmou 10 arquivos de preparação, 81 históricos, 20 brutos
anteriores e dois novos intactos no momento registrado; conjuntos podem se sobrepor.
Os 86 testes pertencem ao preparo, sem repetição nesta análise. Shared 16074216,
executor 98af671d e wrapper 867bd41c são fingerprints históricos desta execução;
não reescrever metadados antigos por evolução posterior.
Hipótese encerrada após os dois braços, nenhum skip ou chamada pendente.
Próximo trabalho local autorizado: consolidar summary-only, budget, color e relational,
separar evidências informativas, ambiguidades, omissões e lacunas para definir a
próxima direção. Nenhum novo SYSTEM, lote ou entrada de chave agendado; não repetir
esta hipótese nem reformular em sequência. Não pedir confirmação genérica nem
criar bloqueio humano para esse trabalho independente de credenciais.

Estado anterior: summary-color `0e7b0ac3-b88a-4962-b383-cc6f813c9d4a` encerrado e analisado.
Run `eval-results/20260907T211537Z-dd5ca339-6fe5-4f8d-8aeb-81abaf5c26b0`.
PID 25276 finished em 2026-09-07T21:17:39.7995660Z, exit 0; chave descartada.
Duas chamadas reading-room-a/b, HTTP 200/stop, rotas Groq/Qwen e schemas válidos.
Ambos têm 20 palavras; A 129 caracteres e B 121. “Luminária azul” deixa a
atribuição da cor AMBÍGUA nos dois, conforme critério prévio: não conta como
preservação demonstrada nem transferência explícita inequívoca base↔luz.
Escopo da iluminação/lista, posição da luminária e adjunto perto da porta também
ficaram menos claros; não impor uma leitura sem suporte como falha categórica.
Omissões periféricas são não informativas. Nenhum defeito local de retenção/medição demonstrado.
Uso 964 entrada + 78 saída = 1.042; raciocínio null/não zero, custo indisponível.
Revisão autorada separada do bruto not_performed/approval null, sem aprovação geral.
Relatório `evals/narrator/reports/record-summary-color-observation-0e7b0ac3-2026-09-07.md`
e JSON associado. Summary SHA `d10d14c885452e1e3b160056c46b1e531b1b7da8710caad273d07bab6325919e`;
JSONL SHA `3d415e680deed39fd496e2bdd57116baf240876c60afec4812b3645c09e20480`.
Auditoria db18f75a reconstruiu metadados, os dois pedidos, summary/schema/medidas;
9 arquivos de preparação, 71 históricos e 18 brutos anteriores intactos no momento
da auditoria. Conjuntos podem se sobrepor. Os 68 testes são do preparo, não repetidos.
Shared 8b9fb32c, executor 2caf4e3f e wrapper 24ba566d são fingerprints históricos
desta execução; novas guardas posteriores não reclassificam estes metadados.
Não relançar PID 25276 ou repetir fontes/lotes encerrados; nenhum skip a preencher.
A preparação subsequente summary-relational foi concluída e consta no estado corrente acima; este fechamento histórico não declara novo envio.

Estado anterior: summary-budget `95dd9fd2-f78f-4467-858f-b3948479aa10` encerrado e analisado.
Run `eval-results/20260907T204016Z-b929bf2c-302d-4b26-b36b-abb0eec249d9`.
PID 21744 finished em 2026-09-07T20:41:18.2606505Z, exit 0; chave descartada.
Uma chamada station-clock, HTTP 200/stop, rota Groq/Qwen e schema verificados.
Resumo de 23 palavras/120 caracteres; revisão independente sem afirmação retida
sem suporte identificada. Relógio parado marcando seis horas não afirma hora atual.
“No banco” é menos preciso, compatível com a fonte; janela aberta/proximidade
omitidas ficam não informativas. Não há hipótese modal nesta fonte.
Uso 459 entrada + 38 saída = 497; raciocínio null/não zero, custo indisponível.
Relatório `evals/narrator/reports/record-summary-budget-observation-95dd9fd2-2026-09-07.md`
e JSON associado; revisão autorada separada do bruto not_performed/approval null.
Summary SHA `487117deccd95da1585147a3149b3e8bded146803a3c49a88bea01b1d7c5f211`;
JSONL SHA `91edd2cbe2791da84329ac61465e580f5c8974bfa8d0c1d9daa02a2fdb6de17f`.
Auditoria 658cc0e2 reconstruiu metadados/pedido/summary/medição e confirmou
10 arquivos de preparação, 60 históricos e 16 brutos anteriores preservados.
Esses conjuntos podem se sobrepor. Os 65 testes são do preparo, sem repetição na análise.
Fingerprints e596329c/f2fe52f1/303e0da1 são históricos desta execução;
novas preparações podem acrescentar guardas sem reescrever essa evidência.
Não repetir station-clock nem relançar a janela/wrapper. Este pedido completou
os estágios operacionais sob teto 768; não demonstra causalidade, taxa ou estabilidade.
A preparação subsequente summary-color foi concluída e consta no estado corrente acima; este fechamento histórico não declara novo envio.

Estado anterior: par summary-attachment `1edf4d3e-13f0-4161-916c-a178b58c1825` encerrado por HTTP 429.
Run `eval-results/20260907T193504Z-6322b0c6-b87e-4eb2-b0d8-a2404e694515`.
PID 24720 finished em 2026-09-07T19:36:06.2011876Z, exit 2; chave descartada.
Somente observatory-a foi chamado; observatory-b tem skip previous_operational_failure.
Não há texto retornado. Schema, medição de palavras e fidelidade não foram avaliados;
não concluir incapacidade do modelo nem tratar B como omissão semântica.
Groq observado, modelo efetivo/uso/finish indisponíveis; rota não verificada.
Recurso tokens e origem desconhecida nos metadados locais. O Console informa
expectativa de saída 1.096 acima do limite OTPM 1.000 no serviço on_demand. Essa
anotação externa não sobrescreve o bruto nem revela fórmula, consumo ou reset.
Não há ETA demonstrado; não usar retryable como autorização para repetir.
Relatório `evals/narrator/reports/record-summary-attachment-observation-1edf4d3e-2026-09-07.md` e JSON associado.
Summary SHA `77090a6559e696e0caecc28c6726cbf4f3d68b4b9187b36f00ae1faa6ad085e5`;
JSONL SHA `91482cf3cfcfb06fe24e8deab5dfeab93a66838048e587e9bb63aea0743f79da`.
Os 199 testes são da preparação; não repetidos nesta análise. Metadados históricos
e critérios preservados. Não relançar a janela ou o wrapper nem preencher B.
A preparação operacional subsequente foi concluída e consta no estado corrente acima; este fechamento histórico não declara uma nova chamada.

Estado anterior: summary-only `21cf338b-5783-43a4-91ad-82f8bac86e96` encerrado e analisado.
Run `eval-results/20260907T190328Z-33c26c5a-59ef-4ef7-a40e-178fe3a65a16`.
Uma chamada archive-vibration, HTTP 200/stop, Groq/Qwen e schema verificados,
código operacional 0. PID 26012 confirmado finished em 2026-09-07T19:04:30.3081925Z;
chave descartada. Não relançar a janela ou o wrapper nem repetir este pedido.
Resumo de 21 palavras/134 caracteres cumpre comprimento, mas falha em fidelidade:
“luz vermelha” transfere para a luz uma cor atribuída à lanterna na fonte.
Existência/posição do motor continuam como possibilidade; funcionamento omitido
fica não informativo. Nenhum defeito local de medição/retenção demonstrado.
Uso 472 entrada + 39 saída = 511; raciocínio null/não reportado, não zero;
custo indisponível. Revisão autorada separada do bruto not_performed/approval null.
Relatório `evals/narrator/reports/record-summary-only-observation-21cf338b-2026-09-07.md`
e JSON associado. Summary SHA `8ab373f9d31f982fd16f7acf34ad36d1676255e21d87b1dd610dfa3543ccceb2`;
JSONL SHA `c4bbd85c68255cb4cdb0aa1125861326e76ac591c0b7f89b187d93a95da5286d`.
Auditoria operacional concluída no relatório; os 336 testes são da preparação,
sem repetição nesta análise. Metadados, fingerprints e critérios históricos preservados.
Executor 662cfc8d, contrato ad3324da, wrapper 6bc2628f e shared ec7113ff são os hashes
desta execução, não exigências para reclassificar alterações posteriores.
A preparação contrastiva posterior foi executada e encerrada por disponibilidade,
com identidade e evidência próprias no estado corrente acima.
Não repetir archive-vibration, escalar esforço/teto ou acrescentar instruções em loop.

Lote anterior `94a95216-9d0b-479e-85d3-e6c577ce4fa3` Qwen inline encerrado e analisado.
Run `eval-results/20260907T175847Z-83c88116-fb4c-4fff-b479-11d91ee655d7`.
Uma chamada archive-vibration, HTTP 200/stop, Groq/qwen/qwen3.8-27b verificados,
rota/schema/projeção válidos, código operacional 0. PID 19232 confirmado finished
em 2026-09-07T17:59:49.5067634Z; chave descartada, limite do lote esgotado.
Resumo literal fiel à fonte, 32 palavras > 25 e 191 caracteres, com separador correto.
O segundo segmento repete fatos e hipótese sob suggested; a redação conserva
sugere/talvez, sem confirmar motor. open_questions vazio é permitido e não informa
capacidade de formular perguntas sem pressuposições; não penalizar ou premiar a omissão.
Nenhum defeito no projetor, reparo ou impossibilidade dos critérios demonstrados.
Uso: 774 entrada + 97 saída = 871; raciocínio null/não reportado, não zero; custo indisponível.
Relatório: `evals/narrator/reports/record-inline-evidence-qwen-observation-94a95216-2026-09-07.md`
e JSON associado. Summary SHA `795cc05b6211fdbf0961d61b938fb3f14a02a8b688fb541c61584c8c1e98edee`;
JSONL SHA `cb39f07387198c31b66f8bab564ed72284985c055b08ffd274e681db349ff21a`.
Auditoria reconstruiu exatamente preflight, summary, projeção e auditoria de segmentos;
confirmou 8 fingerprints de preparação, 32 históricos e 10 brutos históricos intactos
naquele momento. Os 240 testes são da preparação, não repetidos para analisar o resultado.
Contrato e92f7690, executor Qwen21c1a52c, wrapperbbe16b41, shared c725c94e são hashes
históricos desta execução. Preservar metadados/fontes/saída; mudanças posteriores devem
pertencer a outra preparação e não reescrever proveniência ou critérios antigos.

Rubrica e preparação de resumo textual sozinho permanecem como registros históricos
concluídos. A execução summary-only também foi encerrada e analisada no estado acima.
Não relançar PID 26012, PID 19232, Qwen94 ou GPT687 nem reutilizar wrappers encerrados.

O lote anterior GPT-OSS687 teve 32 palavras, falta de espaço e uma pergunta com pressuposição
indevida do motor. A comparação com Qwen é descritiva, sem conclusão causal ou taxa.
O lote independente d1b9a968 permanece encerrado: biblioteca recusada por quote_missing,
oficina não chamada. Medium84ea, claim-check9192 e lotes anteriores também encerrados.
Não preencher a oficina nem retornar a variações na abertura. Somente resumo e questões
abertas foram observados; oito campos, atores, runtime e CAP-001 permanecem sem aprovação.

Cada lote conserva limites e identidade próprios. Depois do resultado, analisar
e avançar autonomamente à próxima observação necessária, sem repetir silenciosamente
ou alterar artefatos antigos. Não promover aprovação de produto por uma resposta.

## Evidência anterior — target-spans terminou por comprimento

Batch `26547182-1133-477d-92a7-fa9f5729c423`, run
`eval-results/20260907T141851Z-99b5d672-db46-4720-b302-961d7934fa42`.
Uma chamada, HTTP 200, `finish_reason:length`; rota Groq/GPT-OSS verificada.
Uso no observador: 2.484 entrada + 1.536 saída = 4.020; raciocínio 1.031.
Erro público `malformed_response/generation_truncated`, exit 1. Nenhum retry,
fallback, Mara ou narrativa nova. Não há response_envelope/derived_records.
Schema, suportes, schema final e admissão não foram alcançados. Não concluir
que os intervalos melhoraram, repetiram a falha ou regrediram semanticamente.

Preflight e resumo reconstruídos exatamente antes da preparação seguinte;
nenhum defeito local demonstrado. A revisão semântica é impossível sem registros.
Uso agregado herdado fica unavailable, mas provider_observation preserva os
contadores explícitos; custo desconhecido. partial_output:false não significa
zero tokens gerados. A comparação histórica não demonstra causalidade.
Relatório: `evals/narrator/reports/record-evidence-target-spans-observation-26547182-2026-09-07.md`
e JSON associado. Hashes dos artefatos preservados. A preparação anterior teve
479 testes aprovados; esse número não é nova rodada de análise.

## Evidência anterior — orçamento executado e analisado

A única execução aprovada com teto 1.536 foi realizada após o usuário inserir
a chave no prompt protegido. Batch `b129ceaa-599c-4448-b095-d37c0f0411c1`,
run `eval-results/20260907T132254Z-a1b6496d-fa4b-4ce8-9a03-2ebc04c6af27`.
Uma chamada, sem retry, fallback, Mara ou nova narrativa; exit 1. Janela
confirmou `finished` às 13:24:00 UTC de 07/09. Não há chave/chamada pendente
nesse lote e não se deve executar novamente o wrapper de orçamento.

HTTP 200, `finish_reason: stop`, Groq/openai/gpt-oss-120b verificados.
Uso: 2.320 entrada + 1.112 saída = 3.432; 658 raciocínio contabilizado,
sem ler conteúdo de raciocínio. Custo indisponível. Schema inicial passou;
envelope rejeitado por `record_evidence_span_invalid`. Cinco de seis suportes
estão fora do campo derivado. Schema final/admissão não foram alcançados;
seus falsos/zeros não são rejeições executadas. O resumo foi reconstruído
e a rejeição reproduzida com o contrato congelado. Nenhum defeito local demonstrado.

Revisão semântica autônoma concluída: “Quem ou o que está observando?”
pressupõe observação que a fonte só sugere; rótulo suggested não corrige a
redação. Resumo conserva “sugere”, mas não separa modalidades no suporte.
Outros campos estão fundamentados; cobertura não demonstrada. Comparação
histórica com 768 não é causal e não comprova causa do HTTP 400 anterior.

Relatório atual: `evals/narrator/reports/record-evidence-budget-observation-b129ceaa-2026-09-07.md`
e JSON correspondente. Summary/JSONL e todos os hashes de implementação
ficaram intactos durante a análise. A preparação anterior teve 993 testes
distintos aprovados (276 novos, 717 existentes); não foi suíte integral.
Detalhes: `evals/narrator/reports/record-evidence-budget-1536-v1-2026-09-07.md`.

Próximo desenho já preparado documentalmente:
`evals/narrator/reports/record-evidence-target-spans-hypothesis-b129ceaa-2026-09-07.md`,
com corpo revisável no JSON draft associado. Somente acrescenta ao SYSTEM
uma explicação de intervalos no campo derivado, mantendo USER, contrato,
schema, parâmetros e teto 1.536. O documento e seu draft mantêm o status histórico
anterior à autorização ampliada. A implementação foi concluída sob a autorização
atual registrada acima. O lote de orçamento continua encerrado e imutável;
novos lotes têm identidade própria. Não recuperar chave fora do prompt seguro.

## Evidência anterior — lote 2c1cafde encerrado e analisado

Continuação após login em 07/09: a consulta ao Console foi concluída.
O ID completo foi confirmado por cópia da própria linha e do erro:
`req_01m1xtmhhdeyjbew0n7ffxv9tg`, created_at 11:39:11.789Z.
Console: openai/gpt-oss-120b, HTTP 400 json_validate_failed,
2.320 tokens de entrada e 768 de saída; TTFT 0,331918 s, latência 1,959371 s.
O erro copiado não contém failed_generation ou finish_reason.
A saída coincide com o teto: esgotamento do orçamento é hipótese sustentada,
mas truncamento e causa exata não estão demonstrados. Login resolvido.
Evidência: `evals/narrator/reports/groq-console-evidence-2c1cafde-2026-09-07.md`
e JSON correspondente. Artefatos originais e 12 hashes de implementação
preservados; nenhum código/teste alterado ou nova inferência realizada.

O próximo desenho já está documentado em
`evals/narrator/reports/record-evidence-budget-hypothesis-2c1cafde-2026-09-07.md`:
uma única abertura fixa, teto 1.536, metadados de término/erro limitados e
nenhum retry. O documento conserva o status histórico de proposta; a decisão posterior
está no estado atual acima. Não representa aprovação do produto.
A única diferença proposta no corpo é max_completion_tokens; comparação
histórica não será causal. O desenho foi aprovado, preparado e executado; resultado no estado atual. Autonomia local preservada.

O usuário executou record-evidence-v1 em 07/09/2026:
`2c1cafde-7508-43a6-b415-172f2c139aa0`, diretório
`eval-results/20260907T113910Z-6c9951b4-2c5b-46bc-85ec-ba7cec8ea3fa`.
Uma chamada na abertura recebeu HTTP 400 `groq_json_validate_failed`;
Mara foi pulada por `previous_operational_failure`. Exit 1 coerente com
a regra de parada, sem retry ou fallback. Nenhum envelope foi disponibilizado.

A análise foi concluída. Não há amostra para avaliar registros, suportes ou
fidelidade; contadores de schema/admissão zerados não são rejeição semântica.
Na resposta disponível ao avaliador, Groq observado, modelo e uso
indisponíveis; o Console acrescenta os metadados posteriores acima. Custo
continua desconhecido. Não atribuir causa definitiva à coincidência com o
teto ou a uma incompatibilidade de schema. Phase connect não comprova
falha de conexão.

O preflight e o resumo foram reconstruídos exatamente. Hashes de fontes,
SYSTEM, USER, schemas, executor e implementação conferem. Trinta testes
focados passaram, sem falhas ou skips, com um aviso preexistente.
Nenhum defeito local foi demonstrado; código, testes e resultados originais
permaneceram intactos. Nenhuma nova chamada de inferência feita pelo agente.

Relatório: `evals/narrator/reports/record-evidence-observation-2c1cafde-2026-09-07.md`
e JSON correspondente. Dossiê local:
`evals/narrator/reports/record-evidence-request-dossier-2c1cafde-2026-09-07.json`.
É corpo de requisição reconstruído, sem headers/chave/resposta; não captura
de tráfego. O rascunho `record-evidence-provider-request-2c1cafde-2026-09-07.md`
na mesma pasta está pronto e não foi enviado a terceiros.

A causa depende de detalhes adicionais do request
`req_01m1xtmhhdeyjbew0n7ffxv9tg` no provedor, se disponíveis.
A sondagem está encerrada; não há chamada pendente apenas de chave.
A segunda chamada não usada não autoriza repetição ou outro diagnóstico.
A autonomia local permanece; qualquer novo lote exige desenho específico,
e CAP-001/runtime continuam sem aprovação.

## Preparação histórica — record-evidence-v1 preparado e verificado

Em 07/09/2026, o usuário respondeu “Prossiga” ao desenho experimental de
origem/modalidade por afirmação. Essa preparação foi implementada e concluída.
Relatório atual: `evals/narrator/reports/record-evidence-v1-2026-09-07.md`
e JSON correspondente. O desenho anterior à aprovação permanece histórico.

O novo envelope tem `records` e `supports`; valida referências, caminhos e
intervalos Unicode, sem inferir fidelidade ou cobertura. Usa as mesmas duas
narrativas originais bb98, com unidades completas da fonte, e compõe o schema
final com n literal. Contrato de atores, admissão, API, H6, memória e saves
permaneceram intactos. O avaliador legado recebeu somente seis linhas para
recusar esta identidade experimental em seus dois caminhos de replay CAP.

Verificação final: **2.998 testes passaram, zero falhas e zero skips** em
três grupos disjuntos, incluindo 243 novos testes. Um aviso preexistente.
Duas revisões independentes sem achados materiais pendentes. Preflight real
mais wrapper PS7 com chave vazia: exit 3 esperado na validação da credencial,
sem chamada externa ou artefato. A falha temporal histórica de persistência
não reapareceu na suíte ampla atual; não houve correção daquela área.

SYSTEM: `6282cb3c46fee52c6ef261cd5e9103e90b516cdd38d4d4f7ceb5b077a3908b6c`.
Executor: `25b500339fd0418714889d7b87b4a6b078e1f0dd4ee073346c7259424c629974`.
USERs: 367 e 751 tokens estimados por caracteres/4, sem omissões, limite 2.000.
Exemplos autorados de envelope: 171 e 221 estimados; não medem tokens reais.

Na preparação não houve chamadas de inferência. A execução única prevista
foi posteriormente realizada pelo usuário no lote 2c1cafde, conforme o estado
atual acima. Seu limite de parada foi atingido na primeira entrada; não
reutilizar o comando histórico como nova rodada autorizada.

## Estado anterior — derivação c9c01a48 executada e analisada

O usuário executou a sondagem autorizada em 07/09/2026:
`c9c01a48-a69d-43bd-9fa2-414ad0d6685b`, diretório
`eval-results/20260907T102110Z-8db00c2e-ec83-4c63-b80a-399db4be6599`.

Duas chamadas, duas propostas admitidas, rota Groq/GPT-OSS verificada e exit 0.
Uso reportado completo: 3.234 entrada + 956 saída = 4.190 tokens; custo
indisponível. Inícios UTC locais separados por 60,249545 s. Não houve
diagnóstico, retry, fallback, erro, skip ou nova geração de narrativa.

A revisão semântica também foi concluída. A abertura ainda pergunta “Quem ou
o que está observando ao longe?”, embora a narrativa apenas sugira observação.
O resumo reforça essa leitura, mas a pressuposição da pergunta é a evidência
decisiva. O local inventado da abertura desapareceu. Em Mara, não reapareceu o
vínculo papel→endereço; a pendência do endereço tem origem legítima no contexto.

Pelo critério pré-registrado, a hipótese não foi sustentada nesta sondagem.
Sucesso operacional continua registrado como exit 0; o summary/JSONL originais
não foram reescritos. Comparação histórica não é causal; CAP-001 e runtime
continuam sem aprovação.

Relatório atual:
`evals/narrator/reports/record-derivation-observation-c9c01a48-2026-09-07.md`
e JSON correspondente. Próximo passo offline já concluído:
`evals/narrator/reviews/modality-thread-matrix-c9c01a48-2026-09-07.md`.
Nove verificações em memória, sem amostras novas: schema/atores 9/9; admissão
8/9. Dimensões semânticas e resultados automáticos estão separados.

Uma resolução prematura só no controle autorado foi admitida: “revelado”
em “prestes a ser revelado” satisfaz o marcador atual. r real=[].
Projeção somente em memória mostrou duplicação semântica de rótulos, sem
apagamento da pendência original. Ambos foram registrados para acompanhamento
separado; nenhum código, campanha ou gate foi alterado nesta análise.

Os hashes da preparação e dos artefatos foram conferidos. API preservada:
`520ad02bd4c0cac2961bb11556533f93eaa94cbfeac3cbb4ef20df14b49cbc58`.
Executor preservado:
`da9b63cc33da7e09cb2ea62b4d933d8741fb0c46ce10846a5c9935526e697bdb`.
Os 179 testes novos pertencem à preparação anterior; não foram repetidos
nesta análise documental. A falha temporal ampla de persistência continua
registrada no relatório da preparação, sem reclassificação.

A autorização concedida foi executada até o fim, incluindo revisão autônoma.
O ciclo de duas chamadas terminou. Não repetir faithful ou esta sondagem para
obter uma taxa melhor. A próxima hipótese está documentada em
`evals/narrator/reports/record-evidence-hypothesis-c9c01a48-2026-09-07.md`:
suporte por afirmação, com origem e modalidade explícitas. A decisão posterior
do usuário e a preparação concluída estão no estado atualizado acima.
A sondagem c9 permanece encerrada, sem repetição autorizada.

## Estado anterior — observação de recorrência concluída

O lote `bb98ae1e-529b-4645-be17-ffe42734db14` foi analisado integralmente.
Ele executou a única observação completa faithful preparada após a sondagem
`8636fac3`: sete chamadas, cinco propostas válidas no schema, duas admitidas
(abertura e Mara), dois skips dependentes no galpão e exit 1.

Perguntas pré-registradas respondidas:

1. A abertura preservou a agência nesta resposta.
2. Método físico e deriva narrativa→memória reapareceram. Galpão acrescentou
   atividade recente somente ao resumo; Mara ligou papel→endereço só num fato.
   Cadeado recebeu manipulação física não declarada.
3. A rejeição do predecessor impediu observar as duas continuações do galpão.

Corrigidos dois defeitos locais: o estado “ele permanece firme” do cadeado
era atribuído ao jogador, e “manipular” não exigia uma declaração reconhecida.
A proposta original continua recusada, agora por `interact`, sem edição.
As cinco decisões de admissão e os dois skips permanecem iguais.

O pacer também somava a espera prevista ao horário antigo. A correção usa
`perf_counter`, relê o relógio após a espera e aguarda o restante necessário.
Reprodução determinística e limites dos timestamps UTC estão no relatório.
Validador final: `520ad02bd4c0cac2961bb11556533f93eaa94cbfeac3cbb4ef20df14b49cbc58`.
Avaliador final: `0fc29dc11b4472bd6b67db9be0980beed9f69f3e4947a87f811727af644f0e82`.

Verificação final: **2.654 testes passaram, sem falhas ou skips** nos dois
grupos executados. Inclui 73 novas regressões. A revisão independente confirmou
16/16 contraprovas integrais. Os testes operacionais de wrappers permaneceram
históricos; a integração Python da sondagem foi reexecutada. Detalhes e
contagens sem duplicação no relatório.

SYSTEM faithful preservado:
`76a9ffdb37296be672e94e1a8c741d90cb5c44164c8dcf888107d308865218d2`.
A revalidação não altera a geração nem os resultados históricos.
Não houve chamada real nova pelo agente. Relatório atual:
`evals/narrator/reports/scene-faithful-observation-bb98ae1e-2026-09-06.md`
e JSON correspondente.

O ciclo delimitado está encerrado com falhas registradas. Não repetir faithful
para obter admissão, não repetir o probe HTTP 400 e não acrescentar SYSTEM por
arrasto. A hipótese seguinte já foi formulada no documento
`evals/narrator/reports/record-derivation-hypothesis-bb98ae1e-2026-09-06.md`.
Ela propôs derivar registros de duas narrativas fixas, com máximo de duas
chamadas. A decisão foi posteriormente concedida e a preparação concluída,
conforme o estado atualizado no início deste documento.

## Autonomia: autorização contínua ampliada

Trabalhe em AUTONOMOUS_TASK. A instrução de 07/09 no início deste documento
cobre intervenções locais e novas observações necessárias. Não solicitar aprovação
por lote, hipótese, prompt experimental ou correção reversível. Registrar o desenho,
executar verificações, observar e analisar; continuar ao próximo passo necessário.

Somente chaves/credenciais ou intervenção direta efetivamente humana justificam
a pausa operacional. Preservar segurança, limites explícitos de cada chamada,
critérios de aceitação e integridade dos resultados. A autorização não transforma
amostras experimentais em validação de qualidade, CAP-001 ou produto.

## Workspace e preflight curto

- Pasta de trabalho: `C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller`.
- Branch verificada: `codex/planejamento-agente-storyteller-v5`.
- HEAD verificado: `5e563824fcba4c53cc37b5084a8ce65f3fa30356`.
- Checkout original de comparação, **não modificar**:
  `C:\Users\skate\Desktop\WorkSpace\Antigravity\SandBox\AgenteStoryteller`.
- Há muitas alterações e arquivos não rastreados acumulados. Preserve-os;
  não use reset/checkout destrutivo nem atribua todo o diff ao trabalho atual.
- Leia a cadeia `AGENTS.md` e o `AGENTS.md` local, que já registra minha autonomia.
  Inspecione `git status` e os arquivos afetados. Use a skill específica adequada.
- `state/PROJECT_STATE.md` não existia no fechamento. Se passar a existir, leia-o.
  `SESSION_LOG.md` é explicitamente histórico e tem informações superadas. Não
  retome sua antiga fase distribuída nem migre o estado como tarefa oportunista.
- Nunca abrir, copiar, imprimir ou registrar `.env` ou chaves. Não reutilizar
  credenciais antigas do chat. Solicitar chave somente pelo prompt seguro local.
- Não iniciar servidor, instalar dependências, migrar saves, fazer commits/PRs
  ou mudar configurações globais como efeito colateral desta avaliação.

## Produto a preservar

React/TypeScript + FastAPI/Python, monólito modular local-first, não microsserviços
operacionais. Inferência pode ser remota. A fronteira LLM é agnóstica de provedor.
Regras, cálculos, RNG, estado e commits são locais/determinísticos. A LLM dirige
improviso, ações de NPCs e continuidade; não escolhe ações pelo jogador, muda
resultados mecânicos ou reescreve o passado. Mundo pode evoluir por propostas
validadas; não é jogo roteirizado. Memória deriva dos acontecimentos validados.

Avaliações usam somente fixtures sintéticas. Alvo explícito, sem troca de
modelo/provedor por arrasto, sem retry narrativo/fallback. Modelo gratuito é uma
hipótese operacional, não justificativa para narrador repetitivo/controlador.
CAP-001 e promoção ao runtime continuam sem aprovação. Planos de pausa/retomada
e API paga são frentes separadas, não próximo trabalho automático.

## Contexto histórico da preparação grounded

Estamos avaliando a qualidade do Narrador, não voltando a escolher plataformas
do zero. Candidato deste experimento:
`gpt-oss-120b-groq-free-synthetic-low`, modelo `openai/gpt-oss-120b`, Groq direta,
raciocínio baixo. Não confundir Groq com Grok. O manifesto é um snapshot para
avaliação; não é promessa de catálogo, cota ou preço futuros.

Último lote com `scene-focus-v1`: `baf5d410-834b-4703-b593-ee1cfb41825e`.
Artefatos em `eval-results/20260906T141735Z-96e61649-1eac-41c1-95d2-9cc56fd3147e/`.
Dois diagnósticos passaram; cinco propostas tiveram schema válido, mas nenhuma
foi admitida. As duas continuações do galpão foram puladas por predecessor
rejeitado. Não houve 429/timeout nesse lote. Não chamar isso de aprovação nem
concluir que todo problema está só no modelo ou só no código.

Correções locais anteriores já feitas e testadas: atribuição de sujeito NPC
no caso de Mara e abertura implícita de barreira em construção temporal.
Há contraprovas de agência e sigilo nos resumos. As respostas antigas continuam
rejeitadas por violações reais; não relaxar validadores para melhorar a taxa.
A família `vasculhar` não foi equiparada indiscriminadamente a `investigar`.

A sondagem `e15dd4d1-80a5-4224-98a6-4d23750b1cab` passou transporte/schema/admissão
com predecessor sintético **autorado**, mas teve problemas de português, tamanho
do resumo e fidelidade narrativa→memória. Não importar essa descoberta como se
fosse gerada pelo modelo na bateria completa.

## Preparação histórica grounded — já sucedida por attributed e faithful

Foi implementada a variante **`scene-grounded-v1`**, apenas no experimento.
Ela pede narrativa primeiro e registros fiéis: resumo e fatos visíveis não
acrescentam acontecimentos ausentes de `n`; local/presenças conservam o estado;
segredos `storyteller` permanecem separados. Continua permitindo improviso.

Somente SYSTEM muda em relação a `scene-focus-v1`: mesmo pacote USER, foco,
schema/contrato de atores, corpus, validadores e parâmetros. A instrumentação
registra baseline e `causal_comparison: false`. Um braço histórico isolado não
constitui conclusão causal A/B. Prompts antigos e H6 de runtime não mudaram.

Arquivos desta ação: `evals/narrator/prompts/scene-grounded-v1.md`,
`scripts/evaluate_narrator_models.py`, `scripts/run_groq_prompt_experiment.ps1`,
`tests/test_narrator_grounded_prompt.py`, `tests/test_prompt_experiment_runner.py`
e documentação correlata. Novo modo `-GroundedOnly` exclusivo dos outros modos
de braço único, fixando GPT-OSS. Replay legado recusa focus/grounded para não
descartar o contrato de atores.

Hash do SYSTEM definitivo:
`ff47d144200ddaac14c7db30f6328f73de5fb466730fe178fb49dc335dbac331`.
Prompt maior que o anterior; melhora de qualidade/latência ainda não foi medida.
Não houve chamada ao vivo desta variante na preparação.

Verificação no fechamento: **2.081 testes passaram, 126 omitidos, um aviso,
zero falhas**. Skips: testes operacionais do wrapper no PowerShell 5 por falha
de carregamento do módulo de política; execução operacional no PowerShell 7
e parser em ambos passaram. Detalhes em
`evals/narrator/reports/scene-grounded-v1-2026-09-06.md`. Testes usam venv existente,
`STORYTELLER_DISABLE_DOTENV=1`, persistência isolada e bloqueio de rede externa.
Não desativar esses controles nem inventar percentual de cobertura.

## Leia estes documentos de forma progressiva

1. `AGENTS.md`,
   `evals/narrator/reports/grounded-progression-live-readiness-2026-09-22.md`
   e `evals/narrator/reports/grounded-progression-live-gate-2026-09-22.md`.
2. Para reconstruir HYP-001:
   `evals/narrator/reports/grounded-progression-contract-preparation-2026-09-22.md`
   e `evals/narrator/grounded_progression_contract_protocol_v1.md`.
3. Para o fechamento anterior de pausa/retomada:
   `plan/feature-narrator-pause-resume-1.md` e
   `evals/narrator/reports/narrator-pause-resume-technical-audit-2026-09-22.md`.
4. Somente se for necessário investigar avaliações antigas:
   `evals/narrator/reports/record-evidence-budget-observation-b129ceaa-2026-09-07.md`.
   Próximo desenho: `evals/narrator/reports/record-evidence-target-spans-hypothesis-b129ceaa-2026-09-07.md`.
   Evidência anterior: `evals/narrator/reports/groq-console-evidence-2c1cafde-2026-09-07.md`.
   Análise local anterior: `evals/narrator/reports/record-evidence-observation-2c1cafde-2026-09-07.md`.
   Para detalhes da preparação, consultar `evals/narrator/reports/record-evidence-v1-2026-09-07.md`.
   Para a análise anterior, ler `evals/narrator/reports/record-derivation-observation-c9c01a48-2026-09-07.md`.
   Para as duas fontes fixas, consultar a análise bb98 referenciada ali.
5. Se precisar da hipótese SYSTEM testada:
   `evals/narrator/reports/scene-faithful-v1-2026-09-06.md`.
6. Para revisar fidelidade: `evals/narrator/reviews/narrative-memory-fidelity-v1.md`.
7. Comandos em `evals/narrator/README.md`; produto em
   `spec/spec-improvisational-scene-direction.md`.

Não carregue todos os relatórios, prints ou transcrições antigos indiscriminadamente.

## Histórico de passos anteriores — não vigente

O bloco abaixo preserva a sequência antiga de execução e não deve ser usado para
escolher o próximo passo. Os gates de catálogos, transporte e pausa/retomada aqui
citados foram sucedidos pelo estado HYP-001 descrito no início e no fim deste
documento.

Fundação, integração da direção B, catálogo mínimo de Mara e contraprova ao vivo
estão concluídos e auditados. Não repetir lotes, reclassificar resultados, preencher
skips ou pedir novamente confirmação da direção B. Não há credencial, chamada ou
correção local pendente neste incremento.

A arquitetura dos catálogos determinísticos foi escolhida e as cinco decisões
foram aprovadas. TASK-005 a TASK-017 estão concluídas. Para Brujah, único clã
`base_reachable`, a compulsão de dois dados está testada; a perdição dependente de
Frenesi permanece não suportada, e o campo de penalidade comportamental é apenas
narrativo. Para Alleycat, único predador `base_reachable`, o pool Strength + Brawl
está tipado e a preferência de ressonância é apenas pista narrativa. `unarmed` é
a única arma `base_reachable`: usa Strength + Brawl, modificador zero e falha
fechada para categorias desconhecidas; ocultabilidade permanece informativa. Os
três poderes `base_reachable` foram alinhados ao V5: Armas Ferais +2 e dano
superficial não reduzido contra vampiros; Salto Ascendente passivo e sem rolagem;
Fascínio nível 1, gratuito e com bônus contextual de Presença em ações suportadas
de Carisma. TASK-018 também está concluída: apenas Príncipe e Xerife fornecem
mecânica de NPC, e apenas Potência de Sangue 1 fornece Surto +1 e Cura 1. Campos
sem consumidor permanecem narrativos ou não suportados; entradas adiadas não
alteram regras. TASK-019 introduziu o candidato imutável e estrito de contexto de
catálogo, com sinais explícitos de relevância e referências de origem. O próximo
TASK-020 removeu o corte `blocks[:3]` de `lore_service`: todos os candidatos são
produzidos tipados antes da seleção, inclusive NPCs múltiplos, e a projeção textual
é apenas compatibilidade temporária. TASK-021 versionou a política de prioridade e
as omissões auditáveis; `unarmed` irrelevante é excluído antes do orçamento. O
TASK-022 integra cada candidato selecionado como `ContextItem` individual no
orçamento real do narrador, com visibilidade, importância, sinais e referências
preservados. O caminho de ação não concatena catálogos antes da seleção. O próximo
TASK-023 também está concluída: consultas de cena produzem clã e todos os NPCs
reconhecidos como candidatos independentes, sem `blocks[:3]`, e reutilizam a
mesma política e o mesmo orçamento final. O próximo passo é TASK-024, auditando
o pacote H6 final contra catálogo integral, duplicação e omissão posicional.
TASK-024 concluiu essa auditoria: o orçamento efetivo é aplicado uma vez por
`assemble_context`, apenas itens selecionados chegam à projeção, textos repetidos
são emitidos uma vez, fatos obrigatórios e segredos permanecem íntegros, e o
contrato H6 conserva a admissão de improviso coerente. O próximo passo é TASK-025,
criando o lookup tipado e fundamentado para consultas diretas de lore. TASK-025
está concluída: consultas nomeadas retornam fatos tipados, fontes, cobertura e
limitações; consultas desconhecidas retornam `not_covered`. O próximo passo é
TASK-026 e TASK-027 estão concluídas: H4 direto reformula somente fatos
selecionados; `not_covered` não chama modelo; Q&A fundamentado e atmosfera
opcional possuem contratos distintos, e a atmosfera não pode criar mecânica ou
fato. O próximo passo é TASK-028, alinhando os contratos Markdown ao runtime como
fonte editorial única conforme DEC-002. TASK-028 e TASK-029 estão concluídas:
H0/H1/H4/H6 carregam Markdown versionado, enquanto H2 foi formalmente
descontinuado como skill e documenta o módulo relacional determinístico e o commit
transacional. TASK-030 a TASK-033 também estão concluídas: TEST-001 a TEST-010
foram implementados, a seleção e os caminhos determinísticos foram verificados,
o diff foi auditado e a matriz foi atualizada somente com evidência. A suíte focal
consolidada aprovou 184 testes. O diagnóstico amplo aprovou 3.198 testes antes de
detectar duas frases contratuais ausentes no Markdown H6; ambas foram restauradas
e os grupos relacionados aprovaram 101 e 37 testes. A continuação aprovou mais
287 testes e parou em hash congelado de experimento histórico já incompatível com
o contrato de ator atual. A leitura SQLite `wrong_session` também mantém uma falha
preexistente no Windows por sidecars `-wal`/`-shm`. Não reescrever essas evidências
históricas no incremento de catálogos. TASK-034 foi aceita pelo usuário em
2026-09-21 com “prossiga”; o plano de catálogos está `Completed`. Essa aceitação
não decidiu por arrasto o acesso do transporte B nem pausa/retomada. Em seguida,
o usuário confirmou com “continue” a alternativa recomendada do transporte B:
um único operador local, somente em loopback, sem API publicada para outra máquina.
O recorte optativo separado está `Completed`; `App`/default v1 permanecem iguais.
Renovação: 598 testes backend, 245 frontend, build próprio e preflight sem chave
passaram. O próximo bloqueio estritamente humano são as decisões DEC-001/002/003
do plano de pausa/retomada; não implementá-las por inferência.
Referências sem página original e metadados
desconhecidos permanecem `partial`/`null`; não promover essa proveniência editorial
a validação jurídica ou regra mecânica.

## Próximo passo exato vigente

Em 03/10, a opção A de posição também foi aprovada e TASK-014 foi concluída
offline (relatório `evals/narrator/reports/campaign-record-location-v2-2026-10-03.md`).
Não reabrir essa decisão. HYP-007-L3 executado: uma chamada, zero turnos completos,
custo final estimado USD 0,0007078; autenticação funcional naquela execução.
Parada de política reproduzida como falso positivo NPC e corrigida localmente
em TASK-015. Relatório `evals/narrator/reports/hybrid-campaign-luna-hyp-007-l3-2026-10-03.md`.
410 regressões e sete testes específicos passaram; dez testes finais incluem
os três da preparação L4 (contagens sobrepostas). Preservar registros, trava e
hashes L3, gate live fechado. Não aceitar L3 retroativamente como campanha completa.
L4 foi autorizado e executado: duas chamadas, um turno completo, rejeição R-05
por política e custo final estimado USD 0,0014972, sem confirmação de cobrança.
O pronome de objeto na prosa do resgate gerou atribuição ambígua de espera na
reprodução local. L5/prompt v3 preparado offline para explicitar o sujeito do
estado físico, com detector e gates inalterados; sem novo gasto/autorização.
L4 live fechado; não solicitar sua chave nem repetir o lote. Aceite narrativo
L4 continua pendente, nenhum narrador/default admitido.
Em 16/10 o usuário priorizou auditoria e correções de segurança: SEC-001/002
corrigidos e verificados, relatório em `docs/security-audit/README.md`.
Ao retomar a avaliação, renovar primeiro preflight e manifesto prospectivo com
o runtime corrigido: hashes antigos não podem ser reescritos para fazê-los passar.
L5 permanece bloqueado para gasto; não transferir saldo de chamadas anteriores.
A auditoria não aceita campanha, release ou novo orçamento. Preservar as
correções e os limites de operador local/loopback. As observações lexicais de
agência continuam separadas, sem prioridade ou expansão automática.

Contexto de continuidade: PROG-ROUTE-B e DEC-PROG-001/002 estão aprovadas. A opção A de ritmo foi escolhida
e TASK-012 (integração B opt-in com autoridade transacional, replay e RNG único)
está verificada. TASK-013 está tecnicamente preparada com ensaio HTTP local
autor do texto, mas precisa de aceitação da experiência e depois avaliação Luna
sob orçamento e ativação específicos. 70 testes focados e 288 v1 passaram; a
suíte ampla diagnóstica encontrou duas falhas históricas independentes (sidecars
SQLite no Windows; hash congelado de schema de ator), documentadas no relatório
de integração. O servidor offline pode ser lançado por
`python -m scripts.run_campaign_source_offline_trial` no worktree, sem chave;
o navegador externo deve abrir a URL de loopback exibida. Latência
artificial/custo Luna foram corrigidos e verificados offline antes desta rota.
Recomendação: Sol low para operação/verificação, Sol high para auditoria de
persistência e orçamento live. Não executar silenciosamente a fila OpenRouter
L3-B nem repetir HYP-006; não solicitar credencial nesta etapa.
Lotes históricos e rejeições permanecem intactos. Nenhum narrador/default
está admitido. Bandeja, conforto de interface e ficha por último continuam
na sequência do MVP; esta etapa não cria um segundo modelo resolvedor.
