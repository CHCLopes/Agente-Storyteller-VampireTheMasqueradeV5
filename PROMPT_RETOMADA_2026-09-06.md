# Retomada limpa — Agente Storyteller

Continue o trabalho existente neste projeto. Confirme os fatos nos arquivos antes
de agir e carregue apenas o contexto necessário ao próximo passo.

## Checkpoint vigente — E concluída; aguardar resoluções do brainstorm — 22/10/2026

Humano delegou a opção mais recomendada E/F, conclusão dos testes e push, depois
espera por resoluções/instruções do brainstorm desenvolvido em outro chat.
E integrada somente no harness A2 com flag --exact-paraphrases: seis frases
exatas, banco novo e recibos companheiros preservam texto literal e binding por
sessão/operação antes de encaminhar frase canônica ao núcleo congelado.
Modo baseline anterior preservado; controles C recusados sem avanço no modo E.
39 testes focados e245 na regressão selecionada passaram (32 casos E novos);
mesmo aviso preexistente python_multipart.32 hashes L86 intactos;gates false/false.
Zero inferência/chave/custo; nenhuma nova observação visual em navegador E.
Relatório: evals/narrator/reports/intent-paraphrase-integration-2026-10-22.md.
Texto integral transferível: docs/handoffs/brainstorm-npc-decision-narrator-2026-10-22.md.
Publicar arquivos relacionados na branch atual e confirmar ref remoto. Excluir
as alterações preexistentes de .env.example/api/.env.example e artefatos locais.
Após publicação, aguardar humano; não iniciar nova bateria, integrar ao produto,
adotar Jev/utilidade/GOAP ou transformar exemplos do brainstorm em cânone.
Pergunta de checkpoints/desfechos ainda sem resposta. CAMP-13..16/CAMP-24 abertos.
Configuração final obrigatória com modelo/esforço/motivo preenchidos.

## Checkpoint anterior — C offline concluído; gate E/F — 22/10/2026

Humano escolheu B e depois C; autorizou commit/push antes de cada gate humano. Diretrizes
registradas em AGENTS.md, inclusive bloco de configuração obrigatório. Contrato
experimental intent_interpretation_offline.py, corpus24 e avaliador separados do jogo.
61 testes focados/197 regressão conjunta passam. Zero inferência/chave/custo de API.
Formato/literalidade falham na primeira contraprova de negação; diagnóstico separado
com sete propostas erradas. Guard independente bloqueia-as, mas só reconhece4 das10
intenções autoradas; seis paráfrases fiéis continuam pendentes,14 referências sem ação.
Não alegar capacidade de modelo, improvisação geral ou novo interpretador admitido.
32 fontes congeladas L86 intactas. Original/defaults/saves/ambiente preservados.
Relatório: evals/narrator/reports/intent-interpretation-offline-2026-10-22.md.
Evidência sintética publicável: evals/narrator/spikes/intent-interpretation-2026-10-22/.
Catálogo C exato executado:6/6 aprovadas,0/6 controles aceitos,baseline0/6; relatório
evals/narrator/reports/intent-paraphrase-admission-offline-2026-10-22.md.
Próximo gate real E/F: E integrar somente as seis strings ao ensaio A2; F conservar
como estudo offline e definir fonte independente antes de ampliar. Escopo:
plan/proposal-intent-paraphrase-integration-2026-10-22.md. Nenhuma opção aprovada;
CAMP-13..16/CAMP-24 abertos. Publicar branch atual antes de apresentar gate;
verificar ref remoto e informar resultado real. Não integrar/main/merge por arrasto.

## Checkpoint anterior — A2 em navegador; gate de próximo escopo — 22/10/2026

Diretriz de continuidade/bloco final registrada em AGENTS.md. Ensaio determinístico
separado do produto em scripts/run_expression_selection_browser_trial.py, porta8032
somente127.0.0.1, banco exclusivo eval-results/expression-selection-browser-2026-10-22.
10 testes focados passam. Navegador interno confirmou início, fala, ação não coberta
sem turno, reformulação, desfecho, reload e recuperação após restart do servidor.
Sem inferência/chave: USD0 novo. 32 hashes L86 e records originais reconferidos intactos.
Relatório: evals/narrator/reports/expression-selection-browser-review-2026-10-22.md.
CAMP-13..16/CAMP-24 continuam abertos: catálogo não demonstra improvisação livre.
Gate humano real: A priorizar integração do recorte fechado; B (recomendado) priorizar
desenho/teste exclusivamente offline de interpretação delimitada, sem autoridade causal.
Escopo/limites/24 casos/aceitação: plan/proposal-expression-selection-next-scope-2026-10-22.md.
Não iniciar B ou integração por inferência do agente: define prioridade/superfície
nova. Não reativar proposta dual-model/ALT-003 causal, não promover MVP/narrador/default.
Checkout original preservado, sem commit/push, .env/credenciais não lidos.

## Checkpoint anterior — A2/L86 concluído; baseline recomendada — 22/10/2026

Envio L86 explicitamente autorizado pelo humano após pergunta sobre os17 payloads
sintéticos à API da OpenAI/gpt-5.6-luna low/tetoUSD0.15. Bloqueio prévio de revisão
automática resolvido por esse aceite; nenhum mecanismo de contorno. Lote único
282a3849-3c62-4390-8809-e9bb95a2385c executado e encerrado.

17 pares/17 chamadas, estados/efeitos iguais nos oito percursos. Uso reportado:
6.448 tokens entrada/859 saída; USD0.0023204 estimado, cobrança não confirmada.
Maior request2.215 bytes, saída limitada256 tokens. 17 corpos reais coincidem com
payloads aprovados e hashes de request. Banco SQLite do lote retido;34 replays
pós-execução conferidos byte a byte sem gateway, RNG, builder ou renderer atuais.

Seleção Luna:12 falas alternativas/5 originais, oito frases de posição repetidas,
dois layouts em parágrafos; dois textos exatamente iguais à baseline. Diferenças
não demonstram melhora; ganho editorial consistente da LLM não demonstrado.
Recomendação: conservar seleção determinística como referência no recorte autorado;
não abrir lotes equivalentes para procurar vantagem. A2 experimental cumpriu escopo.
Garantia de prosa fechada depende da verdade/elegibilidade do catálogo; não declarar
fidelidade geral de RPG aberto ou capacidade de modelos locais/gratuitos.

Relatório integral e34 textos reais:
evals/narrator/reports/expression-selection-l86-observation-2026-10-22.md.
Auditoria: eval-results/expression-selection-l86-observation-review-2026-10-22.json.
Execução: eval-results/hybrid-campaign-luna-l86-282a3849-3c62-4390-8809-e9bb95a2385c.
SHA256 records792b7df18cc297804102501714d9f100314cb91a5d5b14776d674d3860368e1c.
142 testes selecionados da implementação continuam registrados; nenhum módulo
foi alterado na execução real. Gates false/false, trava mantida, nenhum lote novo.

Supervisora852c6897-09cd-414a-bb1a-584f0d709df1/PID21812 voltou idle/exit code0;
expira23/10/2026 00:00 Fortaleza. Não renovar automaticamente, ler segredo ou
reutilizar sessões antigas. Conferir estado vivo caso outra inferência seja
necessária e autorizada. Nenhuma ação humana pendente para concluir L86.

A2 permanece opt-in/isolado; não migrar original nem promover default/admissão/MVP.
Reaproveitamento futuro deve separar resultados, opções elegíveis e proveniência,
com proposta própria para uma cena aberta. CAMP-24/produto/adaptação do original
continuam decisões futuras; nenhuma delas foi aprovada por este lote.

Diretriz humana de gates decisórios: bloco final Configuração recomendada com
Modelo, Esforço, Motivo, Ação humana necessária e O que continuará autonomamente
depois da ação. Priorizar economia de recursos; não criar gate onde o trabalho
já está autorizado ou concluído.

## Checkpoint anterior — A2 implementada offline; envio L86 bloqueado — 22/10/2026

Humano aprovou com “Prossiga” o experimento isolado de seleção de expressão com
contrato próprio, persistência/retomada e comparação determinística. Implementado
em api/experiments/expression_selection; política determinística ou target de modelo
explícito. IDs fechados, autoria da aplicação, raw JSON estrito, SQLite dedicado,
claim antes de RNG, CAS atômico, seleção retida e replay pelos bytes persistidos.
Sem alteração de módulos de regras/leitores A1/defaults/checkout original.

142 testes distintos selecionados passaram: 138 núcleo/regressão +4 harness;
75 novos (71 experimento +4 harness), sem somar reexecuções intermediárias.
Cobertura: oito percursos/variantes ausentes, parsing/versão/escopo, concorrência,
rollback/cancelamento, recuperação explícita e replay sem geração/rolagem extra.
Preflight L86: 17 pares completos, zero provedor, maior request2.215 bytes.
Relatório: evals/narrator/reports/expression-selection-a2-implementation-2026-10-22.md.
Plano: plan/experiment-expression-selection-1.md. XMLs/artefatos no relatório.

L86 preparado: <=17 chamadas Luna low/Responses/store false, 256 tokens efetivos
por request (manifesto com limite superior768), <=20k bytes, USD0.15 estimado,
32 hashes, primeira falha encerra; sem retry/fallback/admissão. O comando de
ativação/despacho foi REJEITADO pela revisão automática por exigir autorização
explícita para os payloads específicos no destino OpenAI com custo. O comando
não executou. Gates false/false; nenhum request/latch/envio L86, custo novo USD0.
Não contornar a rejeição nem inferir autorização específica do aceite experimental.

Payloads exatos preparados localmente para decisão:
eval-results/expression-selection-l86-payload-review-verified-2026-10-22/payloads-for-approval.json.
SHA256 3dc437e9b2cc112ecccceb92324d6780c9c99c9fbf295fb9d309af8b4d7ab038.
Destino https://api.openai.com/v1/responses; instruções, consequências/falas/opções
sintéticas e schema. Sem chave, ficha, save pessoal ou código-fonte. SQLite e
records dessa pasta são simulação autorada; não afirmar ganho de Luna.

Supervisora aberta hoje a pedido humano; sessão852c6897-09cd-414a-bb1a-584f0d709df1,
PID Python21812 (launcherPowerShell23284). Chave recebida, idle observado;
expiração23/10/2026 00:00 Fortaleza. Não ler segredo/terminal/ambiente/memória,
renovar automaticamente ou reutilizar sessões antigas. Revalidar vida antes de envio.

Próximo gate: confirmar envio desses17 payloads sintéticos à OpenAI até USD0.15.
Após aceite explícito, revalidar hash/lease e despachar uma única vez; fechar gates,
revisar todas as apresentações versus baseline e relatar custo. Nenhuma nova
implementação é necessária para tornar a aprovação concreta. CAMP-24/MVP/default,
admissão e adaptação da ferramenta original continuam abertos. Catálogo depende
de curadoria correta; escolha fechada não prova a verdade das frases do autor.

Diretriz humana para respostas com gate decisório: encerrar com “Configuração
recomendada”, contendo Modelo, Esforço, Motivo, Ação humana necessária e O que
continuará autonomamente depois da ação; priorizar economia de recursos.

## Checkpoint anterior — estudo A2 agnóstico concluído offline — 21/10/2026

Humano autorizou continuar o estudo e sugeriu possível reaproveitamento na
ferramenta original com modelos gratuitos/leves/locais. Hipótese registrada;
nenhuma migração, adoção de provedor, mudança de default ou fechamento de autoria
aprovados. Original master permaneceu somente leitura; APIs/domínio do worktree
não foram alterados neste estudo.

Prova isolada de seleção entre expressões autoradas por IDs: 17 planos congelados
do L85, 136 combinações; 238 respostas malformadas/inelegíveis e 119 trocas de
vínculo/catálogo rejeitadas. Nenhuma aceitação inesperada nesses casos. Contraprova:
frase falsa inserida no catálogo confiável foi aceita. Garantia é ausência de
prosa arbitrária da resposta, condicionada à correção editorial e elegibilidade.
Não demonstra capacidade de modelo leve nem ganho sobre baseline determinística.

Oito testes de transporte simulado native/emulated passam. Diferença observada:
parser do adaptador comum conserva última chave JSON duplicada; prova pura rejeita.
Limite de integração registrado, código compartilhado intacto. Zero chamadas de
inferência, custo novo USD 0, nenhum L86, download ou servidor iniciado.

Relatório: evals/narrator/reports/architecture-model-agnostic-expression-spike-2026-10-21.md.
Exemplos autorados: evals/narrator/reports/expression-selection-authored-examples-2026-10-21.md.
Protocolo/script/observação: evals/narrator/spikes/expression-selection-2026-10-21/.

Recomendação: reaproveitar separação de autoridade, contratos, vínculos e
proveniência; comparar seleção por modelo com baseline explícita antes de justificar
inferência. Textos/catálogo da microcampanha não se transferem automaticamente ao
RPG aberto. Documentação oficial de LM Studio/Ollama/llama.cpp consultada; nenhum
alvo real, hardware, quantização ou custo operacional foi avaliado.

Próximo recorte PROPOSTO: seleção versionada em novas sessões sintéticas, cobrindo
variantes ausentes, integração transacional/replay/parsing e comparação editorial.
Integração no runtime e adaptação do original dependem de decisão humana sobre
escopo e custo de reduzir improvisação. Autorização do estudo não é essa decisão.
A1 continua experimental, L84/L85 fechados e íntegros; CAMP-24/MVP/default abertos.
Supervisora não foi usada neste estudo; conferir vida/expiração antes de inferência,
sem renovar automaticamente a sessão que expira 22/10 00:00 Fortaleza.

## Checkpoint anterior — A1 v2 ensaiada — 21/10/2026

A1 aprovada com “Prossiga” e implementada opt-in campaign-source-local-v2 no
worktree b008. Aplicação compõe fatos/falas essenciais; LLM preenche dois slots
opcionais; plano/hash/proveniência e leitores v1/v2 preservados. Sem migração,
RNG novo, alteração de default, commit/push/merge ou admissão.

269 testes distintos da implementação e seis testes novos do ensaio L85 passam.
L84: 12 chamadas/12 turnos completos, USD 0.0075790 estimado; três descrições de
Mara renderizadas como diálogo. Gates fechados durante revisão; a chamada 13 não
foi enviada. Erro generation_failed nesse registro decorre do fechamento local.
L85: mudança apenas de prompt para explicitar discurso direto; 17 chamadas/17
turnos, oito percursos e desfechos conferidos, USD 0.0099808 estimado. Uma reação
não vazia em discurso direto; 14/17 turnos sem texto opcional. Máximo request
9.352 bytes. Total desta continuidade: 29 chamadas/USD 0.0175598, não cobrança.

L85 técnico completo não significa aceitação narrativa: atmosfera afirmou
silêncio não estabelecido na cena. Núcleo crítico e referências preservados;
autoria/offsets conferidos. A LLM escreveu 220 caracteres dos segmentos, contra
4.030 da aplicação (sem separadores/pergunta final). Contribuição limitada nesta
matriz, não estimativa de estabilidade. Persistem 9/10 contraprovas inválidas
aceitas offline; não declarar fidelidade integral ou naturalidade geral.

Relatório e 17 apresentações reais para revisão:
evals/narrator/reports/campaign-expression-v2-l84-l85-review-2026-10-21.md.
Lotes, respostas e manifests preservados; L84/L85 false/false, travas mantidas.
L83 histórico fechado; não regravar seus hashes após mudanças compartilhadas.
Nenhum L86 preparado/despachado. Bancos dos ensaios eram temporários; JSONL e
summaries preservados. Navegador/replay real destes lotes não foram verificados.

Supervisora fa6f0ca5-2cc1-4dd3-9821-34946243c0c7/PID 12548 observada idle após
L85, exit code 0; expira 22/10 00:00 Fortaleza. Chave exclusivamente no processo;
reconferir estado vivo antes de eventual despacho. Não renovar automaticamente.

Ciclo experimental A1 previsto concluído. Próximo gate: decisão sobre autoria e
garantia de produto, não aceite intermediário de lote ou novo teto financeiro.
Proposta ainda NÃO aprovada: estudar expressão também composta pela aplicação
com opções autoradas/referências verificáveis se fidelidade integral for requisito;
alternativa é manter prosa livre com garantia limitada explicitamente aceita.
Não transformar aprovação experimental A1 em aceite final dessa limitação.
Não abrir mais lotes só para encontrar um resultado sem falhas. Autorização
contínua <= USD 0.15 continua vigente para testes justificados dentro do escopo;
CAMP-24/admissão/default/MVP seguem abertos. Nenhuma troca automática de modelo.

## Publicação do desenvolvimento — 20/10/2026

Sincronização segura inicialmente autorizada para a branch de implementação.
Depois, humano autorizou expressamente publicar o novo README como apresentação
principal em main: commit 667d0cf publicado e referência remota/README público
conferidos; somente README.md mudou em main, sem merge de código. Links dos
documentos apontam para o checkpoint publicado 4b3380c da implementação.
README público reescrito conforme o estágio real; guia técnico
preservado em DEVELOPMENT.md. Registro de escopo, exclusões, testes e resultado
Git: docs/repository-checkpoint-2026-10-20.md. Checkpoint técnico 45d4a37
publicado na branch remota e hash conferido; apresentação em commit documental
separado. Consultar o registro e a referência remota para o HEAD final.
Nenhuma alteração de produto/arquitetura ou inferência paga nesta atividade.
Na publicação, DEC-NARR-VALID-001 ainda não tinha escolha; o checkpoint de 21/10 acima registra A e a proposta A1 pendente.

## Checkpoint histórico — L82 encerrado; L83 não executado; decisão de estratégia — 20/10/2026

Fonte do checkpoint: evals/narrator/reports/hybrid-campaign-luna-validation-checkpoint-2026-10-20.md.
L82: 9 chamadas/8 turnos, USD 0.0091548 estimado, não cobrança. Equivalência
parcial passada faltante corrigida; pedido de novo cuidado após desfecho bloqueado.
Auditoria também reproduziu duas violações ACEITAS: tarefa virou examinar em
vez de preservar, e epílogo pediu transporte já narrado. Fixes locais delimitados;
91 focados e 987 ampliados do snapshot final passam, XML
hyp-007-l82-final-expanded-2026-10-20.xml; diff focado inspecionado/sem whitespace.
Não interpretar correções lexicais como prova geral de significado/produto.

Todos os gates executados L76–L82 fechados. L83/v23 preparado false/false,
22 hashes reais conferidos, sem execução/latch/request/summary ou custo de inferência.
Autorização contínua <= USD 0.15 e avaliação intermediária delegada continuam
vigentes: NÃO pedir nova aprovação financeira. Não houve revogação pelo usuário.
Nenhum narrador admitido/default alterado; CAMP-24/MVP continuam abertos.

Próxima decisão humana proposta DEC-NARR-VALID-001, não aprovada: A (recomendada)
revisar desenho da fronteira de validação/contrato antes de novos lotes, versus
B manter contrato atual e seguir correções experimentais delimitadas com risco
explícito. Não implementar nova arquitetura por arrasto. Não falta teto para
L83; a questão é estratégia/risco e fidelidade do MVP. Astra high recomendado
para A; planejar e comparar propostas offline, sem novas chamadas pagas iniciais,
e submeter contrato antes de implementar. Não inferir estabilidade por um lote verde.

Totais conferidos L41–L82: 42 lotes/396 chamadas/356 turnos/USD 0.3919904
estimados; L76–L82: 83 chamadas/76 turnos/USD 0.0828204. Versões variaram,
não calcular taxa de estabilidade. Chave não acessada; supervisora ociosa,
expiração à meia-noite de Fortaleza preservada. Sem merge/commit/push nesta etapa.

## Histórico — L81 encerrado; L82/v22 em preparação — 20/10/2026

L81: 16 chamadas/15 turnos, USD 0.0158616 estimado, não cobrança. R-08 rejeitado
por marca ausente a tentativa não recupera conteúdo. Equivalência negativa
assertiva delimitada corrigida; 184 testes passam incluindo wet não lost,
atomicidade/restart/replay com uma rolagem/chamada. 966 ampliados passam no
snapshot anterior ao fix (não atribuir cobertura retroativa). Gate fechado,
histórico preservado. L82/v22 verifica correção sob mesmos matriz integral/
ordem/alvo/22 hashes/tetos 17 chamadas/USD 0.15 total, primeira falha encerra,
sem retry/fallback/best-of/admissão. Preparação keyless antes do despacho.
L41–L81: 387 chamadas/348 turnos/USD 0.3828356 estimados, versões variaram.
Sem nova ação humana imediata; avaliação intermediária delegada vigente.

## Histórico — L80 encerrado; L81/v22 em preparação — 20/10/2026

L80: 17 chamadas/16 turnos, USD 0.0168512 estimado, não cobrança; último R-06
rejeitado porque preservação apenas do que permaneceu legível não era reconhecida.
Também dizia Está seco por fora, consequência não preparada. Reprodução fiel
falhou antes do fix; equivalência parcial delimitada corrigida e secagem por fora
agora bloqueada. 31 focados/integração passam. Gate fechado/histórico preservado.
V22 esclarece retirar da água não seca registro nem páginas (única troca v21).
L81 verifica nova hipótese sob mesmos matriz integral/ordem/alvo/22 hashes/tetos
17 chamadas/USD 0.15 total, primeira falha encerra/sem retry/fallback/best-of/
admissão. Preparação keyless/bytes antes do despacho pela supervisora.
L41–L80: 371 chamadas/333 turnos/USD 0.3669740 estimados, versões variaram.
Sem nova ação humana imediata; avaliação intermediária delegada vigente.

## Histórico — L79 encerrado; L80 em preparação — 20/10/2026

L79: 12 chamadas/11 turnos, USD 0.0122374 estimado, não cobrança. R-04 bloqueado
porque água até atravessar completamente o registro foi atribuído ao jogador.
Reproduzido/corrigido quadro explícito delimitado; 220 testes passam, incluindo
perda atômica/restart/replay sem RNG. Gate fechado, histórico preservado.
L80/v21 verifica essa correção prospectiva, mesmos matriz integral/ordem/alvo/
22 hashes/tetos 17 chamadas/USD 0.15 total, primeira falha encerra, sem retry/
fallback/best-of/admissão. Preparação keyless antes do envio pela supervisora.
L41–L79: 354 chamadas/317 turnos/USD 0.3501228 estimados, versões variaram.
Sem nova ação humana imediata; avaliação intermediária delegada vigente.

## Histórico — L78 encerrado; L79 em preparação — 20/10/2026

L78: 10 chamadas/9 turnos, USD 0.0099626 estimado, não cobrança. R-03 bloqueado
porque gotas que avançam foi atribuído ao jogador objeto de olhar do NPC.
Reproduzido/corrigido quadro ambiental delimitado; 257 testes passam. Gate
fechado; evidência histórica preservada. L79/v21 verifica essa correção com
mesma matriz integral/ordem/alvo/22 hashes/tetos 17 chamadas/USD 0.15 total;
primeira falha encerra, sem retry/fallback/best-of/admissão. Preparação keyless
antes do despacho pela supervisora. Ajuda L78 também teve prosa confusa sobre
exame/local: manter avaliação qualitativa, não admitir só por testes verdes.
L41–L78: 342 chamadas/306 turnos/USD 0.3378854 estimados. Sem nova ação humana.

## Histórico — L77 encerrado; L78 em preparação — 20/10/2026

L77: 15 chamadas/14 turnos, USD 0.0148322 estimado; R-07 bloqueado por partes
nominal interpretado como partir em das partes ainda legíveis. Falha reproduzida,
extensão nominal delimitada corrigida; 218 focados/37 inspeção-atomicidade passam.
Gate fechado, resposta literal e histórico preservados. L78/v21 testa essa
correção prospectiva, mesma matriz integral/ordem/alvo/22 hashes/tetos até
17 chamadas/USD 0.15 total por lote; primeira falha encerra, sem retry/fallback/
best-of/admissão. Preparação keyless e hashes antes do envio pela supervisora.
L41–L77: 332 chamadas/297 turnos/USD 0.3279228 estimados, não cobrança/taxa de
estabilidade. Sem nova ação humana imediata; avaliação intermediária delegada.

## Histórico — L76 encerrado; correção nominal — 20/10/2026

L76: 4 chamadas/3 turnos, USD 0.0039206 estimado, não cobrança. R-01 rejeitado
porque em mente foi tomado como mentir. Reproduzido antes da correção; detector
agora ignora apenas esse substantivo preposicionado. Mentir/ocultar/abrir seguem
bloqueados. 146 testes passam; gate L76 fechado e evidência histórica preservada.
L77 verifica essa correção prospectivamente, sem mudar v21/matriz integral/ordem,
alvo ou tetos até 17 chamadas/USD 0.15 total por lote; primeira falha encerra,
sem retry/fallback/best-of/admissão. Preparação keyless/hashes antes do envio.
L41–L76: 317 chamadas/283 turnos/USD 0.3130906 estimados. Autorização contínua
e avaliação intermediária delegada vigentes. Nenhuma nova ação humana imediata.

## Histórico — L75 integral técnico; lacuna qualitativa corrigida — 20/10/2026

L75 batch 6fdb6e67-3784-4e9b-892e-4c84daa39a04 completou 17 chamadas/17
turnos/oito percursos sob v20, USD 0.0170188 estimado. Auditoria independente
confere regras/desfechos/identity/custo/SHA/22 hashes, 44–90 palavras, máximo
19.783 bytes, geração mediana 3.297 ms/máxima 10.107 ms. 654 relacionados passam.
Gate fechado/saídas preservadas. NÃO admitir apenas pelo resultado técnico.
Leitura qualitativa encontrou Está seco agora após mover páginas molhadas e
fala truncada R08. Duas falhas offline pré-fix, guard prospectivo bloqueia
secagem não preparada no resgate parcial, preserva negativa e fora da água;
cinco regressões/39 relacionados passam. V21 pede fala natural/completa e
esclarece superfície seca não seca páginas, sem aumentar prompt. L76 separado
fechado em preparação, mesmo alvo/matriz integral/ordem/22 hashes/tetos até
17 chamadas/USD 0.15 total por lote. Hipótese nova de fidelidade/prosa, não best-of.
Totais conferidos L41–L75: 35 lotes/313 chamadas/280 turnos/USD 0.3091700
estimados, não cobrança; versões variaram, não calcular taxa de estabilidade.
Próximo: concluir preparação/hashes/diff e liberar L76 uma vez pela supervisora.
Primeira falha encerra/sem retry/fallback/admissão. Sem nova ação humana imediata.

## Histórico — L74 encerrado; L75 em verificação — 20/10/2026

L74 batch 22d84fe7-6c48-417a-b1b2-ec6edc80b939: 13 chamadas/12 turnos,
USD 0.0131672 estimado, não cobrança. R-09/04 nominal recebendo sua escolha
de Mara após você tomado como escolha do jogador. Guard conservador mantido;
12 relacionados provam alternativa recebe a desistência, mesmo fechamento/
bench/fala direta, ação extra bloqueada e replay sem RNG extra. Gate fechado,
evidência mantida. V20 troca somente orientação recebendo escolha por reação
à desistência; L75 separado fechado em preparação, mesmo alvo/matriz integral/
ordem/22 hashes/tetos até 17 chamadas/USD 0.15 total por lote.
Totais L41–L74: 296 chamadas/263 turnos, USD 0.2921512 estimados, não cobrança.
Próximo: concluir preparação/hashes/diff e liberar L75 uma vez via supervisora.
Primeira falha encerra/sem retry/fallback/admissão. Sem nova ação humana imediata.

## Histórico — L73 encerrado; L74 em verificação — 20/10/2026

L73 batch 0c8b91a8-fb5f-459e-9e19-66e0721a62d2: 15 chamadas/14 turnos,
USD 0.0149588 estimado, não cobrança. R-07/06 tem duas causas: recuperação
parcial não reconhecida e parte nominal lida como partir. Ambas reproduzidas;
fix exige sujeito explícito do jogador e exclui apenas parte nesse complemento,
com concessão na falha/negação/hipótese/NPC/citação/partida real bloqueadas.
212 relacionados aprovados; 636 ampliados anteriores aprovados. Gate fechado,
evidência mantida. L74 separado fechado em preparação, mesmo v19/alvo/matriz
integral/ordem/22 hashes/tetos até 17 chamadas/USD 0.15 total por lote.
Totais L41–L73: 283 chamadas/251 turnos, USD 0.2789840 estimados, não cobrança.
Próximo: concluir preparação/hashes/diff e liberar L74 uma vez via supervisora.
Primeira falha encerra/sem retry/fallback/admissão. Sem nova ação humana imediata.

## Histórico — L72 encerrado; L73 em verificação — 20/10/2026

L72 batch f2b6aa4b-18f1-4f86-a09d-935c090d81b0: 15 chamadas/14 turnos,
USD 0.0150288 estimado, não cobrança. Seis percursos completos, R-07/06 parou
por recuperação nominal de conteúdo não reconhecida. Duas falhas pré-fix,
marcador assertivo delimitado de registro parcial/conteúdo recuperado reconhece
sucesso e proíbe mesma concessão na falha; negação/hipótese/citação não sustentam.
199 relacionados aprovados; preparação L73 verifica limite final de sentença.
Gate fechado/evidência mantida. L73 separado fechado em preparação, mesmo
v19/alvo/matriz integral/ordem/22 hashes/tetos até 17 chamadas/USD 0.15 total.
Totais L41–L72: 268 chamadas/237 turnos, USD 0.2640252 estimados, não cobrança.
Próximo: concluir preparação/hashes/diff e liberar L73 uma vez via supervisora.
Primeira falha encerra/sem retry/fallback/admissão. Sem nova ação humana imediata.

## Histórico — L71 encerrado; L72 em verificação — 20/10/2026

L71 batch d5f1e700-e0c8-4f6e-9933-c1d17c92d47e: sete chamadas/seis turnos,
USD 0.0068850 estimado, não cobrança. R-03B/02 onde ele estava rejeitado por
pronome ambíguo. Guard mantido; 15 regressões de dano aprovadas demonstram
alternativa na bancada baixa com mesmo wet e agência/atomicidade/replay/RNG.
Gate fechado/evidência mantida. V19 só reforça nomear registro em posição/estado;
L72 separado fechado em preparação, mesmo alvo/matriz integral/ordem/22 hashes/
tetos até 17 chamadas/USD 0.15 total por lote. Totais L41–L71: 253 chamadas/
223 turnos, USD 0.2489964 estimados, não cobrança. Próximo: concluir preparação/
replay de tamanho/hashes/diff e liberar L72 uma vez via supervisora existente.
Primeira falha encerra/sem retry/fallback/admissão. Sem nova ação humana imediata.

## Histórico — L70 encerrado; L71 em verificação — 20/10/2026

L70 batch 7d2a6ba8-3405-431b-be37-c1e41e3efc88: quatro chamadas/três turnos,
USD 0.0039672 estimado, não cobrança. R-01/01 pergunta sim/não quer levar o
registro rejeitada corretamente. 38 relacionados aprovados; guard/runtime
inalterados para esse caso. Gate fechado/saídas mantidas. V18 só orienta q
exatamente O que você faz agora? quando outcome null, vazio terminal, nesse
perfil sintético. Não altera contrato/default; prosa n varia, q fica repetitiva.
L71 separado fechado em preparação, mesmo alvo/matriz integral/ordem/22 hashes/
tetos até 17 chamadas/USD 0.15 total por lote. Totais L41–L70: 246 chamadas/
217 turnos, USD 0.2421114 estimados, não cobrança. Próximo: concluir preparação/
replay de tamanho/hashes/diff e liberar L71 uma vez pela supervisora existente.
Primeira falha encerra/sem retry/fallback/admissão. Sem nova ação humana imediata.

## Histórico — L69 encerrado; L70 em verificação — 20/10/2026

L69 batch c5c41978-7f96-4c02-a231-56ba2468dc39: seis chamadas/cinco turnos,
USD 0.0058922 estimado, não cobrança. R-03/02 sem tocar no objeto de Mara
atribuído ao jogador mencionado como objeto de volta-se para você. Duas falhas
pré-fix, correção restrita de contato negado com sujeito NPC nomeado/narração
fora de citação; 220 relacionados e 45 ambientais/NPC aprovados. Gate fechado,
evidência preservada. L70 separado fechado em preparação, mesmo v17/alvo/
matriz integral/ordem/22 hashes/tetos até 17 chamadas/USD 0.15 total por lote.
Totais L41–L69: 242 chamadas/214 turnos, USD 0.2381442 estimados, não cobrança.
Próximo: concluir preparação/hashes/diff e liberar L70 uma vez via supervisora.
Primeira falha encerra/sem retry/fallback/admissão. Sem nova ação humana imediata.

## Histórico — L68 encerrado; L69 em verificação — 20/10/2026

L68 batch 2a28644c-955c-4e0b-b6be-e9367bfc5086: 12 chamadas/11 turnos,
USD 0.0123238 estimado, não cobrança. R-04/03 mas a infiltração avança tomado
como movimento do jogador. Duas falhas pré-fix; vínculo de sujeito ambiental
imediato água/infiltração independe de conjunção, preserva verbos posteriores.
202 relacionados aprovados; 559 ampliados anteriores aprovados. Gate fechado,
evidência preservada. L69 separado fechado em preparação, mesmo v17/alvo/
matriz integral/ordem/22 hashes/tetos até 17 chamadas/USD 0.15 total por lote.
Totais L41–L68: 236 chamadas/209 turnos, USD 0.2322520 estimados, não cobrança.
Próximo: concluir preparação/hashes/diff e liberar L69 uma vez pela supervisora.
Primeira falha encerra/sem retry/fallback/admissão. Sem nova ação humana imediata.

## Histórico — L67 encerrado; L68 em verificação — 20/10/2026

L67 batch 3741a4c7-778e-41cf-a34c-785d7582d730: oito chamadas/sete turnos,
USD 0.0080808 estimado, não cobrança. R-01/02 pergunta Como você quer proceder
com o registro molhado? não reconhecida como convite à ação. Duas falhas
pré-fix, equivalência restrita de campo inteiro; 171 relacionados e 53 questão/
contexto aprovados, inclusive wet/reinício/replay/ação extra bloqueada.
Gate fechado/evidência mantida. L68 separado fechado em preparação, mesmo
v17/alvo/matriz integral/ordem/tetos até 17 chamadas/USD 0.15 total por lote.
Totais L41–L67: 224 chamadas/198 turnos, USD 0.2199282 estimados, não cobrança.
Próximo: concluir preparação/hashes/diff e executar L68 uma vez via supervisora.
Primeira falha encerra/sem retry/fallback/admissão. Sem nova ação humana imediata.

## Histórico — L66 encerrado; L67 em verificação — 20/10/2026

L66 batch 359de0e2-1a8d-4684-9d15-50ae37bcbbf3: duas chamadas/um turno,
USD 0.0019282 estimado, não cobrança. R-01/08 passiva futura do registro para
ser examinado confundida com ação executada. Fix delimitado, primeira referência
de família corrigida ainda offline; seis regressões/141 relacionados aprovados,
incluindo sequência de diálogo/reinício/replay sem RNG extra. Gate fechado,
evidência preservada. L67 separado fechado em preparação, mesmo v17/alvo/
matriz integral/ordem/tetos até 17 chamadas/USD 0.15 total por lote.
Totais L41–L66: 216 chamadas/191 turnos, USD 0.2118474 estimados, não cobrança.
Próximo: concluir preparação/hashes/diff e executar L67 uma vez via supervisora.
Primeira falha encerra, sem retry/fallback/admissão. Sem nova ação humana imediata.

## Histórico — L65 encerrado; L66 em verificação — 20/10/2026

L65 batch 3e476d4a-59e4-4cb9-99a7-48ee204bd41c: 12 chamadas/11 turnos,
USD 0.0123666 estimado, não cobrança. R-04/03 água continua avançando tratada
como jogador; duas falhas pré-fix, correção só do token com sujeito explícito,
163 relacionados aprovados. 539 ampliados anteriores aprovados, evidência XML.
Gate fechado/saídas preservadas; L66 separado fechado em preparação, mesmo
v17/alvo/matriz integral/ordem/tetos até 17 chamadas/USD 0.15 total por lote.
Totais L41–L65: 214 chamadas/190 turnos, USD 0.2099192 estimados, não cobrança.
Próximo: concluir preparação, conferir hashes/diff e liberar L66 uma vez pela
supervisora existente. Primeira falha encerra, sem retry/fallback/admissão.
Sem nova ação humana imediata. CAMP-24/admissão/default/MVP continuam abertos.

## Histórico — L64 encerrado; L65 em verificação — 20/10/2026

L64 batch aa020e7d-bf88-462e-8611-8f560b2b1e1e: nove chamadas/oito turnos,
USD 0.0092450 estimado, não cobrança. R-06/02 afastando-o da água confundido
com retirada do jogador, apesar de antecedente registro molhado explícito.
Gate fechado/histórico mantido. Duas falhas pré-fix, correção delimitada de
clítico do objeto com contraposições, 151 relacionados aprovados. L65 separado
fechado em preparação, mesmo v17/alvo/matriz integral/ordem/tetos 17/USD 0.15.
Totais L41–L64: 202 chamadas/179 turnos, USD 0.1975526 estimados, não cobrança.
Próximo: conferir preparação/hashes e executar L65 uma vez pela supervisora;
primeira falha encerra, sem retry/fallback/admissão. Sem nova ação humana imediata.

## Histórico — L63 encerrado; L64 em verificação — 20/10/2026

L63 batch a52c9207-e8f9-46f5-ab51-4f91a08f5f2f: duas chamadas/um turno,
USD 0.0018726 estimado, não cobrança. R-01/08 repetiu recusa da fundadora ao
responder tarefa: inadequação narrativa. Erro técnico combat veio de material
reconhecido pelo stem mat* como matar. Fix só do nominal exato, uma falha
pré-fix/quatro contraprovas/142 relacionados aprovados, sem dispensar matar.
Gate fechado/saída preservada; nenhum resultado narrativo reclassificado.
V17 reforça entrada atual, não reapresentar fala histórica; L64 separado em
verificação, mesmo alvo/matriz integral/ordem/22 hashes/tetos 17/USD 0.15 total.
Primeira falha encerra/sem retry/fallback/admissão; avaliações delegadas mantidas.
Totais L41–L63: 193 chamadas/171 turnos, USD 0.1883076 estimados, não cobrança.
Próximo: concluir preparação L64/replay de tamanho/regressões e liberar uma vez
pela supervisora existente. Sem nova ação humana imediata ou entrada de chave.

## Histórico — L62 encerrado; L63 em verificação — 20/10/2026

L62 batch 7688e9ef-63a0-435f-8594-58863d6de4cc: 12 chamadas/11 turnos,
USD 0.0121282 estimado, não cobrança. Compactação passou o ponto L61; R-04/03
rejeitado por água continua sobre bancada e atravessa registro atribuída ao
jogador. Gate fechado/histórico preservado. Duas falhas antes do fix delimitado;
156 relacionados e 25 preparação/replay/contexto aprovados após correção.
L63 separado em execução após 517 ampliados aprovados (XML hyp-007-l63-expanded-2026-10-20.xml), mesmo v16/matriz/tetos até
17 chamadas/USD 0.15 total, primeira falha encerra, sem retry/fallback/admissão.
Totais L41–L62: 191 chamadas/170 turnos, USD 0.1864350 estimados, não cobrança.
Próximo: observar resultado L63, fechar gate e reconciliar evidências. Despacho
único via supervisora existente, hashes conferidos/diff check limpo. Sem nova
ação humana imediata ou entrada de chave.
Avaliações intermediárias delegadas; admissão/default/produto finais humanos.

## Histórico — L61 encerrado; L62 compacto em verificação — 20/10/2026

L61 batch 3ece37fd-21c2-49be-9c85-f2cbf06edf9e: sete chamadas/sete turnos,
USD 0.0068490 estimado, não cobrança. Oitava etapa bloqueada antes do envio;
replay offline confirmou corpo 20.093 > teto 20.000 bytes. Gate fechado e
histórico preservado, sem reclassificação. 507 relacionados aprovados.
V16 compacta somente explicações redundantes, sem mudar contexto/histórico/
canon/gates/tetos; replay dos sete textos seguido de corpus completa fake17,
máximo 19.455 bytes. Isso não garante limite para toda prosa futura.
L62 separado fechado em verificação: mesmos oito percursos/17 chamadas,
USD 0.15 total por lote, primeira falha encerra, sem retry/fallback/admissão.
Totais L41–L61: 179 chamadas/159 turnos, USD 0.1743068 estimados, não cobrança.
Próximo: verificar preparação/hashes de L62, ativar/despachar uma vez pela
supervisora existente. Sem nova ação humana imediata ou nova entrada de chave.
Admissão/default/MVP continuam sujeitos ao gate humano final.

## Histórico — L60 encerrado; L61 fechado em verificação — 20/10/2026

L60 batch 55fdbe26-7137-4ac0-a3ba-38db5a69e0ad: uma chamada/zero turnos,
USD 0.0008756 estimado por usage (3304 entrada/179 saída), não cobrança.
Recusa direta de Mara: Não vou divulgar essa identidade. Rejeitada por exigir
literal fundadora apesar da pergunta preparada. Saída histórica não reclassificada;
gate L60 fechado. Expressão atenção da cena artificial orientou prompt v15.
L61 ainda fechado, sem despacho: vínculo anafórico apenas na pergunta da fundadora,
fala direta efetiva de Mara, sem identidade/lore nova. Contraprova hipotética
reproduziu falha offline e foi corrigida antes de qualquer chamada paga.
Sete regressões de contexto/agência/segredo/atomicidade/reinício/replay passam.
Preparação e contratos ampliados em verificação. Totais L41–L60: 172 chamadas,
152 turnos, USD 0.1674578 estimados; teto USD 0.15 por lote, não cumulativo.
Autorização contínua e avaliação intermediária delegada mantidas, sem admissão.
Próximo: verificar preparação L61/22 hashes e fake17; só então ativar e despachar
uma vez via supervisora diária existente, até 17 chamadas, primeira falha encerra.

## Histórico — L59 rejeição preservada; L60/v14 preparado — 20/10/2026

Worktree b008/AgenteStoryteller, branch codex/planejamento-agente-storyteller-v5.
state/PROJECT_STATE.md ausente. Preservar checkout de origem e alterações alheias.
Não ler .env, clipboard, chave, ambiente de credencial ou memória de processo.

Humano aprovou L40 com ressalva de linguagem artificial e delegou avaliações
intermediárias de L41 e testes necessários ao agente até gate humano real.
Autorização contínua até USD 0.15 estimado TOTAL por lote (não por chamada),
sem novo pedido individual. Registrar hipótese/quantidade/teto/hashes/parada;
primeira falha encerra, sem retry silencioso/best-of/fallback/admissão automática.
Novas decisões de arquitetura/canon/produto e admissão final continuam humanas.

Supervisora diária 67a9500f-348a-4191-959e-b10c0d58938e, PID 12304 ativo:
entrada protegida validada localmente e autenticação observada nas chamadas.
Expira 21/10 00:00 Fortaleza (=03:00 UTC). Não recuperar chave/renovar sozinha.
L60 preparado, sem nova ação humana imediata ou nova entrada de chave.

L41–L59: dezenove lotes encerrados na primeira falha, 171 chamadas/152 turnos,
USD 0.1665822 estimados finais por usage observado, não cobrança. O teto aprovado
USD 0.15 é por lote, não cumulativo; cada lote ficou abaixo dele. Todos os
respectivos gates fechados/latches/saídas preservados, sem reclassificar lotes
após correções. Nenhum lote atual completou os oito percursos. L54 percorreu
08 completo: recusa direta, ajuda sem repetir segredo e final Está salvo, sem
relatório de proteção/lore inventada. Avaliação intermediária positiva do agente,
não admissão final nem estabilidade estatística. L40 aceito com ressalva preservado.
Relatórios individuais hybrid-campaign-luna-hyp-007-l41 até l59-2026-10-20.md.

Correções locais com reprodução antes do fix e contraprovas: sujeitos ambientais
infiltração/água não são ações do jogador; wet afirmativo/preservação parcial
são reconhecidos em quadros delimitados; negativa assertiva de recuperação
realiza falha, alcance ambiental/ambiente carregando tensão não concedem sucesso/
posse. Estado wet rejeita nada legível indevido. Agência real, sucesso indevido,
negação/hipótese/pergunta/citação continuam protegidos. Commit/reinício/replay
preservam RNG/geração, sem novas rolagens nas retomadas. Nenhuma refatoração geral.

Prompt v13 preserva v9 de recusa diegética sem relatório de segurança e sem lore
inventada; v10 pede reação concreta ao resgate, v11 distingue falha de perda total,
v12 explicita dano wet já ocorrido, v13 não imobiliza jogador na desistência.
Guard mantido para escolha genérica retrospectiva L45 e imobilidade real L51.
Diálogo colateral/Por que? não implementado; mundo dramático não autoriza narrador
trapacear nem promover prosa a estado. Catálogo/RNG/resultados não alterados.

L54 parou R-04/03 por água atravessando páginas atribuída ao jogador. Seis casos
novos/duas falhas pré-fix/52 relacionados aprovados após fix delimitado; ações
reais/commit/reinício/replay protegidos. L55 mantém v13/Luna low/ordem 08 primeiro/
todos oito percursos/17 chamadas/768 tokens/20.000 bytes/60s/USD 0.15 total,
22 hashes atuais. L55 duas chamadas/um turno, USD 0.0019168, parada R-01/08 por
se você decidir como agir tomado como decisão concreta. Seis casos novos/duas
falhas pré-fix/84 relacionados aprovados após extensão delimitada de condição
aberta; ações reais preservadas, replay sem RNG/geração extra. L56 mantém matriz/
ordem/prompt/tetos; preparação em verificação. Último amplo antes desse fix:
465 aprovados, XML hyp-007-l55-related-2026-10-20.xml; não suíte de release.
L56 15 chamadas/14 turnos/seis percursos, USD 0.0148946 estimados; parada R-07/06
por exame e recuperação coordenados não reconhecidos. Nove regressões/duas falhas
pré-fix/84 relacionados aprovados após fix delimitado, negação/hipótese/NPC/ação
extra protegidos, uma rolagem/geração/replay. L57 mantém v13/matriz/ordem/tetos,
preparação em verificação. Último amplo antes desse fix: 471 aprovados, XML
hyp-007-l56-related-2026-10-20.xml. Sem admissão/default/release.
L57 dez chamadas/nove turnos, USD 0.0100426; parada R-03/03 por complemento espacial
da infiltração mudando atribuição de sujeito. Oito casos novos/quatro falhas pré-fix/
84 relacionados aprovados após fix: sujeito explícito enquanto a infiltração avança
independe do complemento; dispensar só esse token, manter todos verbos seguintes/
atores. L58 mantém v13/matriz/ordem/tetos; preparação em verificação. Último amplo
antes desse fix: 480 aprovados, XML hyp-007-l57-related-2026-10-20.xml.
L58 dez chamadas/nove turnos, USD 0.0100744; parada R-03/03 por umidade que avança
tomada como jogador. Seis casos novos/duas falhas pré-fix/90 relacionados aprovados
após reconhecimento desse sujeito relativo explícito. Apenas token avança dispensado,
demais atores/verbos protegidos. L59 mantém v13/matriz/ordem/tetos, preparação em
verificação. Último amplo antes desse fix: 488 aprovados, XML hyp-007-l58-related-2026-10-20.xml.
L59 16 chamadas/15 turnos/sete percursos, USD 0.0157842; parada R-08/07 por
fechamento retrospectivo ambíguo deixa de revelar o que você procurava. Guard
inalterado; quatro regressões/79 relacionados aprovados: alternativa direta
mantém wet/resgate parcial possível, ações/sucesso extra bloqueados, replay com
uma rolagem/geração. V14 pede falha direta sem objetivo anterior presumido.
L60 mantém alvo/matriz/ordem/tetos; preparação em verificação. Último amplo
antes do ajuste de prompt: 494 aprovados, XML hyp-007-l59-related-2026-10-20.xml.
Ao terminar L60: ler registros/resumo, custo, fechar gate, avaliar todas saídas,
reconciliar plano e checklist; continuar correções/testes necessários autorizados.
Se houver evidência suficiente para propor admissão final, preparar gate humano
explícito sem trocar default ou fechar MVP por arrasto. TASK-013/CAMP-24 abertos.

## Histórico de preparação — 20/10/2026 (superado pelo checkpoint acima)

Humano autorizou nova janela diária e delegou avaliações intermediárias de L41
e testes necessários ao agente até gate humano real; não solicitar novo aceite
de cada lote/variante. Mantidos escopo e teto <= USD 0.15 por lote, sem retry
silencioso/fallback/admissão final automática. Janela externa aberta em 20/10:
sessão 67a9500f-348a-4191-959e-b10c0d58938e, PID 12304 ativo, status observado
awaiting_secure_credential. Expira em 21/10 00:00 Fortaleza (=03:00 UTC).
Única ação humana imediata: inserir chave uma vez no editor mascarado e Enter.
Não ler clipboard/chave/ambiente/memória; acompanhar somente status e evidências.
L41 hashes revalidados, gate fechado/latch ausente; após entrada validar idle,
ativar manifesto/pedido e executar. Nenhuma chamada paga nesta abertura.

Humano aprovou resultados L40 e pediu corrigir falas artificiais sobre informação/
identidade protegida. Aceite recebido com essa ressalva, não pedir novamente
julgamento dos mesmos resultados. Sem admissão/default automático ou conclusão
integral do MVP. V9 implementado no prompt compartilhado: recusa contextual basta,
sem anunciar controles internos nem repetir recusa fora de contexto; não inventar
proibição/esquecimento/juramento/merecimento, não impor medo/obediência ou alterar
regras/pressão. Validadores/catálogo/lore/estado e saídas L40 inalterados.
Três regressões naturais demonstram recusa/ajuda/resgate aceitos e vazamento/
ação indevida rejeitados atomicamente, reinício/replay sem RNG/geração extra.
30 relacionados aprovados, XML hyp-007-l41-natural-refusal-readiness-2026-10-20.xml.
L41 novo fechado: v9/Luna low/até 17 chamadas/768 tokens/20.000 bytes/60s/USD 0.15
total, primeira falha para, sem retry/fallback/admissão. 22 hashes/preflight
17 sintéticos/zero rede/16.770 bytes; nenhum dispatch hoje/custo preparação USD 0.
Eficácia de linguagem do Luna ainda não observada. Autorização contínua cobre
tetos/quantidades no escopo, não solicitar novo orçamento. Dependência humana:
autorizar abertura da sessão diária de hoje e inserir chave protegida uma vez.
Lease de ontem expirou 20/10 00:00 Fortaleza, PID 20604 ausente; status idle antigo
não prova sessão ativa. Não recuperar chave nem renovar automaticamente.
Visão de mundo antagonista dramático/diálogo colateral registrada em
plan/observation-campaign-state-language-1.md, sem expandir MVP/catálogo: Por que?
ainda classifica None. Motivos NPC são possibilidades autorais, não lore nova.
Relatório evals/narrator/reports/hybrid-campaign-luna-l41-readiness-2026-10-20.md.

L40 batch 7295e209-3a13-4fd0-8224-3e7318fcfdb2 completed: 17 chamadas/17 turnos,
oito percursos completos (01 preserved/02 partial/03 lost/04 abandoned/05 preserved/
06 partial/07 partial/08 preserved). Sem retry/fallback/admissão. OpenAI/Luna low
observados; 54371 tokens entrada/3639 saída, USD 0.0152410 estimados finais,
não cobrança. Geração 2962–4320 ms, mediana 3650; textos 47–107 palavras,
q <=15/vazio ao concluir. Gate fechado/latch/histórico preservados, supervisor
20604 idle/last_lot40/exit0 até meia-noite Fortaleza, sem nova entrada necessária.
521 relacionados aprovados, XML hyp-007-l40-final-related-2026-10-19.xml;
diff/hashes/proveniência/uso/desfechos/faixa de palavras verificados. Não é suíte
integral de release nem estabilidade estatística. Nenhum narrador admitido.
Total L30–L40: 86 chamadas/USD 0.0753034 estimados, sem incluir lotes anteriores.
Relatório: evals/narrator/reports/hybrid-campaign-luna-hyp-007-l40-2026-10-19.md.
Leitura humana pronta/verificada com 17 respostas literais:
evals/narrator/reports/luna-l40-human-review-2026-10-19.md. Única intervenção
imediata: avaliar oito percursos quanto a progressão/role play/pertinência de Mara,
clareza de resultados e encerramento; reprovação deve citar caso/turno. Não
substituir essa decisão por mais amostras. TASK-013/CAMP-24/MVP continuam abertos.
Autorização contínua <= USD 0.15 por teste permanece vigente; não voltar a pedir
aprovação individual de quantidade/teto em tarefas necessárias dentro do escopo.
Após julgamento, registrar aceite/restrições e prosseguir no checklist aprovado.

L39 batch 74d69c19-f140-43c2-b9c6-a40b793ebb55: dez chamadas/nove turnos,
três percursos completos, R-09/04 rejeitado por omitir Mara (exigida pela política
vigente/corpus). Não flexibilizar gate. USD 0.0087130 finais estimados, não
cobrança; gate fechado/latch mantido. Três regressões/26 relacionados e dez
preparação sobrepostos aprovados. V8 explicita só reação NPC na desistência,
sem impor ação ou nova tarefa; runtime/critérios mantidos. L40 novo v8/Luna low/
17 chamadas/768 tokens/20.000 bytes/60s/USD 0.15 total, primeira falha para,
sem retry/fallback/admissão. 22 hashes/preflight 17 sintéticos/zero rede/15.038
bytes; execução coberta pela autorização contínua. Nenhum narrador admitido.
Relatório hybrid-campaign-luna-hyp-007-l39-2026-10-19.md.

L38 batch e68b17f8-df25-4ea8-9d9a-e2bf390eaafa: 12 chamadas/11 turnos,
cinco percursos completos, parada R-07/06 por recupera informações úteis não
reconhecido como singular informação útil. Flexão plural adicionada com mesmos
filtros de sujeito/negação/falha. Testes legíveis 33→39, duas falhas pré-fix;
264 relacionados e 46 preparação sobrepostos aprovados, atomicidade/replay sem
RNG/geração extra. USD 0.0103988 finais estimados, não cobrança; gate fechado/
latch preservado. L39 novo mesmo v7/alvo/17 chamadas/768 tokens/20.000 bytes/
60s/USD 0.15 total, primeira falha para, sem retry/fallback/admissão; 22 hashes/
preflight 17 sintéticos/zero rede/14.763 bytes. Autorização contínua cobre
execução, não pedir novo aceite. Nenhum narrador admitido. Relatório L38.

L37 batch 2d428b81-b729-486b-b42f-fb33917caebe: uma chamada/zero turnos,
R-01/01 falso positivo Se você precisar manipulá-lo (interact). Padrão clítico
condicional existente estendido de move para move|manipula, sem ação executada
ou ocultação de verbos posteriores. Quatro falhas pré-fix, 27 condicionais,
156 relacionados e 34 preparação sobrepostos aprovados. USD 0.0007564 finais
estimados, não cobrança; gate fechado/latch mantido. Regressão anterior à
extensão: 478 relacionados aprovados. L38 novo mesmo v7/alvo/17 chamadas/
768 tokens/20.000 bytes/60s/USD 0.15 total, primeira falha para, sem retry/
fallback/admissão. 22 hashes/preflight 17 sintéticos/zero rede/14.763 bytes.
Execução coberta pela autorização contínua, não pedir novo aceite. Nenhum
narrador admitido. Relatório hybrid-campaign-luna-hyp-007-l37-2026-10-19.md.

L36 batch 9adca484-5bc6-4235-b9fc-b72094ffaace: nove chamadas/oito turnos,
01 intacto/02 parcial completos, parada R-04/03 por água avança sobre registro
atribuído ao jogador (move). Corrigido só quadro ambiental explícito, demais
atores/ações posteriores mantidos. Oito regressões/duas falhas pré-fix;
145 relacionados e 15 preparação sobrepostos aprovados, atomicidade/replay
sem RNG/geração extra. USD 0.0080752 finais estimados, não cobrança; gate
fechado/latch preservado. L37 novo mesmo v7/alvo/17 chamadas/768 tokens/
20.000 bytes/60s/USD 0.15 total, primeira falha para, sem retry/fallback/admissão.
22 hashes/preflight 17 sintéticos/zero rede/14.763 bytes; execução coberta pela
autorização contínua, não pedir novo aceite. Nenhum narrador admitido.
Relatório hybrid-campaign-luna-hyp-007-l36-2026-10-19.md.

L35 batch 10021029-5ee3-42bc-b8a5-7684a436120a: uma chamada/zero turnos,
R-01/01 falso positivo Que ação você pretende realizar agora? (seis palavras).
Fullmatch reconhece apenas pergunta completa com cauda modal existente; menus,
instruções/NPC/ações presumidas continuam bloqueados. Duas falhas pré-fix,
31 testes de pergunta; 165 relacionados e 38 preparação sobrepostos aprovados.
USD 0.0007748 finais estimados, não cobrança; gate fechado/latch preservado.
L36 prospectivo mesmo v7/alvo/17 chamadas/768 tokens/20.000 bytes/60s/USD 0.15
total, primeira falha para, sem retry/fallback/admissão; 22 hashes/preflight 17
sintéticos/zero rede/14.763 bytes. Autorização contínua cobre execução.
Total desta etapa L30–L35 USD 0.0321190 estimados, não cobrança. Nenhum narrador
admitido. Relatório hybrid-campaign-luna-hyp-007-l35-2026-10-19.md.

L34 batch a6150a5f-6970-4927-b174-5e78de16cd4e: 13 chamadas/12 turnos,
seis percursos completos (01–06), parada R-08/07 por falha explícita não
reconhecida (a investigação não recupera conteúdo algum). Marcador delimitado
adicionado; umidade alcança as páginas desambiguado de conquista do jogador.
11 regressões/seis falhas pré-fix; 289 relacionados e 18 preparação/R-08
aprovados (sobreposição), atomicidade/reinício/replay sem RNG/geração extra.
USD 0.0111458 finais estimados, não cobrança; gate fechado/latch preservado.
Observação UX separada: Podemos examiná-lo após final R-05/01 pode soar como
convite à continuação; submeter encerramento ao humano, não admitir por gates.
L35 mesmo v7/alvo/limites/17 chamadas/USD 0.15 total, primeira falha para,
sem retry/fallback/admissão; 22 hashes/preflight 17 sintéticos/zero rede/14.763
bytes, execução coberta pela autorização contínua. Nenhum narrador admitido.
Relatório hybrid-campaign-luna-hyp-007-l34-2026-10-19.md.

L33 batch f203c19d-7318-47a0-ac6c-3dcba601cafa: 12 chamadas/11 turnos,
cinco percursos completos; R-07/06 parou por seguindo marcas e trechos ainda
legíveis interpretado como deslocamento. Corrigido apenas quadro explícito de
examinar registro na bancada; seguir NPC/partir/ações posteriores protegidos.
Testes leitura 26→33, duas falhas pré-fix, 177 relacionados e 40 preparação/
leitura aprovados (sobreposição). USD 0.0106532 estimados, não cobrança; gate
fechado/latch preservado. L34 novo mesmo v7/alvo/limites, 17 chamadas/USD 0.15
total, primeira falha para, sem retry/fallback/admissão. 22 hashes/preflight 17
sintéticos/zero chamadas/14.763 bytes; execução coberta pela autorização contínua.
Nenhum narrador admitido. Relatório hybrid-campaign-luna-hyp-007-l33-2026-10-19.md.

L32 batch 48f2b030-7564-49bf-8808-23346ff27dce: uma chamada/zero turnos,
R-01/01 rejeitado por enquanto decidimos o próximo passo (choice coletiva não
declarada). Não flexibilizar gate. USD 0.0007964 finais estimados, não cobrança;
gate fechado/latch/histórico mantidos. Quatro regressões novas/20 relacionados e
11 preparação aprovados (sobreposição); atomicidade/reinício/replay sem RNG extra.
Regressão ampliada L30/L31: 409 aprovados. V7 acrescenta orientação de agência
coletiva em fala de Mara, sem mudar runtime/critérios. L33 novo: v7/Luna low/
17 chamadas/768 tokens/20.000 bytes/60s/USD 0.15 total; primeira falha para,
sem retry/fallback/admissão. Preflight 17 sintéticos/zero chamadas/14.763 bytes,
22 hashes válidos. Execução coberta pela autorização contínua, sem novo aceite.
Nenhum narrador admitido. Relatório hybrid-campaign-luna-hyp-007-l32-2026-10-19.md.

L31 batch c2468a41-0a55-4ab8-ae8d-e1982dd12b5d: cinco chamadas/quatro turnos,
01 completo/intacto, parada R-01/02 turno 3 por substantivo tom tomado como
verbo tomar (take). Corrigido somente mantendo o tom contido, sem esconder
verbos posteriores. Testes 8→15, duas falhas pré-fix, 170 relacionados aprovados.
USD 0.0043730 estimados finais, não cobrança; gate fechado/latch mantido.
L32 prospectivo, mesmos v6/alvo/limites/17 chamadas/USD 0.15 total; primeira
falha encerra, sem retry/fallback/admissão. 22 hashes/preflight 17 sintéticos/
zero chamadas/14.457 bytes; execução coberta pela autorização contínua.
Não pedir novo aceite/teto. Nenhum narrador admitido. Relatório L31 no diretório
evals/narrator/reports/hybrid-campaign-luna-hyp-007-l31-2026-10-19.md.

L30 batch b8ce5b26-f0eb-4833-87c9-980d347d01ac: cinco chamadas/quatro turnos,
01 completo/intacto; parada R-01/02 por ameaça da infiltração atribuída ao jogador
(combat). Falso positivo corrigido só no quadro enquanto a infiltração ameaça
a bancada baixa; ações posteriores e outros atores protegidos. Oito regressões,
duas falhas pré-fix, 137 agência/integração e 55 preparação/supervisora/custo
aprovados (sobreposição). USD 0.0043758 estimados finais, não cobrança; gate
fechado/latch/histórico preservados. L31 prospectivo: mesmos v6/Luna low/limites,
17 chamadas/USD 0.15 total, primeira falha para, sem retry/fallback/admissão.
22 hashes/preflight 17 sintéticos/zero chamadas/14.457 bytes. Autorização contínua
cobre execução; não pedir aceite/teto novamente. Nenhum narrador admitido.
Relatório hybrid-campaign-luna-hyp-007-l30-2026-10-19.md.

Humano autorizou explicitamente L30 e todos os testes futuros necessários ao
escopo aprovado com tetos planejados <= USD 0.15 por lote/teste. Supera pedidos
anteriores de aprovação individual/quantidade; registrar prospectivamente cada
hipótese/limite/hash/parada, sem retry silencioso/best-of/fallback/admissão.
L30: até 17 chamadas v6/Luna low/768 tokens/20.000 bytes/60s, USD 0.15 total,
primeira falha encerra; 22 hashes revalidados, latch ausente, supervisor 20604
idle antes do pedido. Depois analisar/custear/fechar gate e prosseguir em tarefas
locais necessárias. Parar somente por intervenção real, escopo/arquitetura,
credencial, teto superior ou aceitação humana de produto.

L29 batch 8eb276ee-09b4-4715-adb4-7498f0796dad: 12 chamadas/11 turnos,
cinco percursos completos (01–05); parada R-07/06. Custo final estimado USD
0.0102446, não cobrança. Gate fechado/latch/histórico preservados, sem retry.
Offline confirmou partes em entre as partes ainda legíveis como depart;
ampliado somente quadro nominal. Após isso, segunda lacuna de sucesso:
recupera informação útil não reconhecido. Marcador delimitado ao sujeito
afirmativo explícito você, filtros de negação/asserção mantidos, falha não
pode conceder o resultado. Tentativa/pergunta/diálogo/hipótese/NPC não provam sucesso.
Testes legíveis ampliados 10→26; três falhas pré-ajuste nominal, duas pré-ajuste
de resultado. 344 relacionados aprovados, atomicidade/reinício/replay sem
RNG/geração extra; XML hyp-007-l29-correction-l30-readiness-2026-10-19.xml.
L30 preparado/fechado: mesmo v6/alvo/17 chamadas/768 tokens/20.000 bytes/60s,
USD 0.15 total, sem retry/fallback/admissão; 22 hashes atuais/preflight 17
sintéticos/zero envios/14.457 bytes. Proposta: aceitar L29 inconclusivo integral/
cinco percursos e autorizar execução única L30. Continue/prossiga aprova.
Não pedir novamente teto padrão; supervisor 20604 idle até meia-noite Fortaleza.
Nenhum narrador admitido. Relatório hybrid-campaign-luna-hyp-007-l29-2026-10-19.md.

Prossiga aprova a proposta L29: até 17 chamadas Luna low/v6, 768 tokens,
20.000 bytes/60s, USD 0.15 total estimado, sem retry/fallback/admissão;
parada na primeira falha. L28 aceito como inconclusivo integral/cinco percursos/
falso positivo nominal confirmado. Hashes 22 revalidados, latch L29 ausente;
supervisora 20604 ativa/idle antes do pedido. Flags L29 ativados para execução
única, depois analisar/custear/fechar gate. Não ler chave nem reabrir lotes antigos.

L28 batch 090516e9-50b3-4154-b931-b85abd682dea: 12 chamadas/11 turnos,
cinco percursos completos (01–05); parada R-07/06 por substantivo partes em
de suas partes ainda legíveis interpretado como partida do jogador.
Falso positivo confirmado offline; correção mínima delimitada ao quadro nominal.
Dez regressões novas, duas falhas antes da correção; 193 relacionados aprovados,
incluindo atomicidade/reinício/replay sem repetir RNG/geração. Diff inspecionado.
USD 0.0102126 finais estimados, não cobrança; gate fechado/latch/histórico mantidos.
L29 separado/fechado: mesmo v6/Luna low/17 chamadas/768 tokens/20.000 bytes/60s,
USD 0.15 total, sem retry/fallback/admissão; preflight 17 sintéticos/zero envios/
14.457 bytes/22 hashes. Proposta delimitada: aceitar resultado L28 inconclusivo
integral/cinco percursos/falso positivo e autorizar L29. Continue/prossiga aprova;
não pedir novamente teto padrão. Supervisora 20604 idle até meia-noite Fortaleza,
sem reentrada enquanto ativa; observar somente status. Nenhum narrador admitido.
Relatório evals/narrator/reports/hybrid-campaign-luna-hyp-007-l28-2026-10-19.md.

Humano pediu voltar aos testes de narrador e prosseguir. Próxima bateria pendente
retomada como L28 nova, sem reabrir manifestos L25-L27: até 17 chamadas Luna low,
prompt v6, 768 tokens/20.000 bytes/60s, teto USD 0.15 para lote inteiro, parada
na primeira falha, sem retry/fallback/admissão. Hipótese: observar campanha integral
após correção de adjunto canônico de espera, com adapter auditado. Critério técnico:
17 turnos concluídos e desfechos esperados dos oito casos; falha interrompe lote.
66 testes focados aprovados; preflight 17 sintéticos/zero envios/14.457 bytes;
22 hashes atuais válidos. Alteração dos scripts somente identidade/data de L25.
Flags L28 ativados após preparação. Executar uma vez pela supervisora 20604,
observar records/summary/custo, fechar gate, analisar sem reclassificar histórico.

Entrada local validada e chamada única explicitamente autorizada executada pela
supervisora corrigida. L27 batch e3c7c9ae-201c-4fbe-8ef0-a2c6eb926cb1: planned=1,
attempted=1, completed=1; OpenAI/gpt-5.6-luna low observados, sem retry/fallback.
Geração 4388 ms; turno 4538 ms; 2512 tokens de entrada e 163 de saída.
Custo estimado USD 0.000698, não cobrança confirmada. Desfecho preserved.
Gate L27 fechado após execução; latch preservado. Supervisora PID 20604 idle,
last_lot=27/exit=0; mantém deadline original. Não comprova causa da falha L26
nem admite narrador. Evidência: evals/narrator/reports/luna-single-call-l27-2026-10-19.md.

Ativação em 19/10: humano encerrou a primeira janela; PID antigo 3076 ausente.
Nova janela externa corrigida aberta, PID 20604 confirmado ativo, sessão
2f8a38f5-f351-4f99-89e2-57e16a141407, status awaiting_secure_credential.
Expiração 20/10/2026 00:00 Fortaleza (03:00 UTC). Aguarda uma entrada humana
mascarada; nenhuma inferência iniciada nesta substituição. Não recuperar chave
anterior nem confundir entrada local validada com autenticação no provedor.

Humano pediu auditoria do fluxo e da aplicação que recebe a chave, incluindo
feedback visual e prevenção de colagem dupla. Sem ler chave real/.env/clipboard/
ambiente ou memória do processo. Escopo completo do receptor: console/lançador/
supervisor/fila/adapter, não todo React/FastAPI. Três falhas locais informativas:
entrada sem feedback/validação, transporte/JSON indistinguíveis e fase inexistente
no erro de credencial vazia. Corrigidas nas fontes; nenhuma vulnerabilidade remota
demonstrada nem hipótese confirmada sobre a chave real.
Editor Windows mascarado com asteriscos/contador, Backspace, Esc/Ctrl+U e cancelamento;
controles/espaços/Unicode/repetição integral recusados antes do HTTP, com reentrada.
Adapter classifica erros seguros por tipo, sem texto bruto/headers/body; usa
OperationPhase.VALIDATION. Não há correção automática de segredo ou clipboard API.
126 relacionados aprovados/um aviso preexistente; XML
eval-results/credential-input-audit-extended-2026-10-19.xml. Console Windows PTY
verificado com valor sintético; scan de 10 arquivos/dois blobs históricos sem
indicadores pelos padrões. PDF sete páginas verificado, em
docs/security-audit/credential-flow-2026-10-19/relatorio-auditoria-seguranca.pdf;
fontes/gerador/scan/manifesto/issues/README no mesmo diretório. Relatório antigo preservado.
Nenhuma chamada paga nesta auditoria. L26 continua inconclusivo/custo indisponível;
L25 nunca executado. Gates reais fechados e manifestos históricos preservados;
hashes antigos agora devem recusar código alterado. Fixtures temporárias isolam
testes sem atualizar gates antigos. Nenhum narrador admitido/MVP aberto.
ATIVAÇÃO: PID 3076/sessão 4beb08ec-4442-46ae-bb9d-c9c70377b216 ainda é a versão antiga
em memória, preservada idle. NÃO usar para nova inferência. Não injetar mudanças
nem extrair sua chave. Quando o humano puder inserir novamente: encerrar antiga
sem filho ativo, abrir versão corrigida com deadline absoluto, aguardar UMA
entrada no editor mascarado e conferir só idle/credential_local_validation=passed.
Autenticação remota só em nova chamada cuja quantidade seja autorizada; teto
USD 0,15 por teste já aprovado. Não pedir reaprovação desse mesmo teto.

## Checkpoint anterior — chamada única encerrada sem resposta; sem nova tentativa — 19/10/2026

Probe L26 batch 6c5f11c5-b2e7-4d1e-9c6b-b2422b407abf: UMA tentativa/zero turnos,
campaign_source_provider_failure/transport_or_response_invalid. Nenhuma resposta
nem usage: custo final indisponível, não zero/cobrança confirmada. Autenticação
inconclusiva; marcador call_made não prova chegada ao servidor. Não inferir chave
inválida/rede/TLS/saldo. Não ler chave/clipboard/ambiente/memória do terminal.
Gate probe fechado/trava/artefatos mantidos; sem retry/fallback/segunda chamada.
L25 inteiro nunca publicado/executado e segue fechado. Nenhum narrador admitido.
46 testes focados antes/depois aprovados/um aviso preexistente; XML
eval-results/luna-single-call-closure-2026-10-19.xml. Relatório
evals/narrator/reports/luna-single-call-probe-2026-10-19.md.
Supervisora PID 3076 continua idle, sessão 4beb08ec-4442-46ae-bb9d-c9c70377b216,
last_lot=26/exit 2, deadline 20/10 00:00 Fortaleza. Não abrir outra nem pedir
nova chave sem evidência. Humano deixou Codex remoto e encerrou somente áudio.
USD 0,15 por teste é teto padrão previamente aprovado, mas quantidade/escopo
não são automáticos: autorização atual era uma chamada, já consumida.
Antes de outra inferência: diagnóstico seguro/offline de categorias do adapter
e autorização específica da quantidade. MVP/TASK-013/CAMP-24 seguem abertos.

## Checkpoint anterior — probe de UMA chamada autorizado; L25 inteiro fechado — 19/10/2026

Humano pediu teste e depois restringiu expressamente a UMA chamada paga,
manteve teto USD 0,15 e confirmou Está autorizado. Também definiu USD 0,15
como teto padrão já aprovado por teste enquanto outro teto não for proposto;
não pedir novamente esse mesmo orçamento. Escopo/quantidade continuam limitados.
Pedido anterior L25 interrompido antes de publicar: supervisora idle, sem
pedido/latch/artefatos e gate fechado. Não executar bateria L25 inteira.
Probe separado L26: somente CAMP-EVAL-05/R-05, MAX_CALLS=1/schedule unitário,
authorized_calls=1 obrigatório no gate antes de credencial e a cada dispatch.
max_calls=17 é só envelope técnico compatível com a supervisora já ativa,
não autorização para 17: limite efetivo é um, comprovado por testes. Mesmo Luna
low/v6/768 tokens/20.000 bytes/60s/USD 0,15, sem retry/fallback/admissão.
46 testes focados aprovados/um aviso preexistente; XML
eval-results/luna-single-call-readiness-2026-10-19.xml. Gate probe ativado;
enviar pedido único sem chave na sessão 4beb08ec-4442-46ae-bb9d-c9c70377b216.
Após encerrar conferir resposta/proveniência/custo e fechar probe. Não executar
outra chamada mesmo se falhar. Nenhum narrador admitido/MVP aberto.

## Checkpoint anterior — supervisora temporária autorizada; L25 ainda fechado — 19/10/2026

Humano autorizou em voz guardar chave apenas em memória até meia-noite de
Fortaleza e, após esclarecimento do bloqueio de segurança, executar apenas
baterias individualmente aprovadas dentro dos tetos. Regra para a semana
19–25/10: uma sessão diária, sem renovação automática. Primeiro patch bloqueado
não alterou arquivos; implementação posterior autorizada explicitamente.
Supervisor/launcher/testes separados, sem mudança no produto/avaliadores
congelados. Plano: plan/process-luna-credential-lease-1.md. Chave nunca em
arquivo/comando/log/ambiente permanente; estado local guarda só metadados.
Deadline absoluto + monotônico; interromper filho na expiração/interrupção.
52 testes keyless aprovados/um aviso preexistente, XML
eval-results/luna-supervisor-readiness-2026-10-19.xml; AST PowerShell válido.
Janela externa aberta, processo Python PID 3076 ativo, sessão
4beb08ec-4442-46ae-bb9d-c9c70377b216, fase awaiting_secure_credential,
deadline 20/10/2026 00:00 Fortaleza (03:00 UTC). Aguardar uma entrada protegida;
observar somente eval-results/credential-leases/4beb08ec-4442-46ae-bb9d-c9c70377b216/status.json,
PID/expiração. Não abrir outra supervisora nem ler entrada/ambiente/memória.
Nenhuma inferência ou chave real usada na verificação.
L24 permanece na conclusão proposta abaixo; L25 fechado, teto/aceite não foram
aprovados pelo pedido de retenção. Sem novo lote até aprovação individual.
Nenhum narrador admitido; MVP/TASK-013/CAMP-24 abertos.

## Checkpoint anterior — L24 encerrado; espera no local corrigida; L25 fechado — 18/10/2026

L24 batch 9933c25d-e8b9-467f-b2c2-4ef2df8f6b81/v6: quatro chamadas/três turnos,
01 completo/intacto, parada R-03B/02 por Você aguarda no Arquivo tomado como
alvo novo para Espero. Falso positivo, não repetição do silêncio L23. USD
0,0033604 finais estimados, não cobrança; 11.378 tokens entrada/904 saída.
Gate fechado/trava/artefatos mantidos. Correção restrita: adjunto no/na mais
local canônico exato para espera explicitamente sem alvo, fronteira/offsets
preservados. Oito regressões novas/80 focados aprovados, duas falhas antes da
correção; atomicidade/reinício/replay sem RNG/geração extra.
L25 separado/fechado, mesmo v6/alvo/limites. 149 testes relacionados aprovados,
inclui diretor de cenas/preparação/integração; 17 sintéticos/zero chamadas/
14.457 bytes/22 hashes/AST válidos. Proposta: aceitar L24 inconclusivo integral/
um percurso completo e autorizar L25 até 17 chamadas/USD 0,15 estimados adicionais,
Luna low/v6/768 tokens/20.000 bytes/60s, sem retry/fallback/admissão.
Continue/prossiga aprova ambos; até lá sem terminal/chave/inferência L25.
Após autorização abrir lançador e aguardar chave protegida. L23 aceito;
nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos. Relatório
evals/narrator/reports/hybrid-campaign-luna-hyp-007-l24-2026-10-18.md.

## Checkpoint anterior — L23 aceito; L24/v6 autorizado — 18/10/2026

Continue aceita L23 com violação real de agência/campanha integral inconclusiva,
um percurso completo e nenhum narrador admitido. Autoriza L24/v6 até 17 chamadas
Luna low/USD 0,15 estimados adicionais, 768 tokens/20.000 bytes/60s, sem retry/
fallback/admissão automática. Preflight revalidado: 17 sintéticos/zero chamadas,
máximo 14.457 bytes/22 hashes válidos, trava ausente antes do lançamento.
Somente gates paid/live ativados; notas prospectivas do manifesto históricas.
Próxima dependência: entrada protegida da chave no lançador externo L24.
Após entrada observar lote único pelos artefatos, apresentar custo e fechar gate.
Não repetir L23, não ler .env/chave/ambiente/memória do terminal. TASK-013/
CAMP-24/MVP abertos. Não pedir novamente aceite L23 ou teto L24.

## Checkpoint anterior — L23 violação real de agência; L24/v6 fechado — 18/10/2026

L23 batch 831812c6-fb54-4367-9624-37de554fd759: quatro chamadas/três turnos,
01 completo/intacto; parada R-03B/02 por Você permanece em silêncio para Espero.
Violação REAL: espera não autoriza silêncio/imobilidade, conforme contrato
existente. Não flexibilizar validador; runtime preservado. USD 0,0032892 finais
estimados, não cobrança; 11.076 tokens entrada/895 saída. Gate fechado/trava/
evidência mantidos. Seis regressões novas/72 focados aprovados: rejeição atômica,
contraprova literal, reinício/replay sem RNG/geração extra.
L24/v6 separado/fechado; instrução explicita distinção sem alterar critérios.
31 focados aprovados; 17 sintéticos/zero chamadas/14.457 bytes/22 hashes/AST
válidos. Eficácia narrativa v6 não demonstrada. Proposta: aceitar L23 com
violação real/campanha integral inconclusiva/um percurso completo e autorizar
L24/v6 até 17 chamadas/USD 0,15 estimados adicionais, Luna low/768 tokens/
20.000 bytes/60s, sem retry/fallback/admissão. Continue/prossiga aprova ambos;
até lá sem terminal/chave/chamada L24. Depois abrir lançador e aguardar chave
protegida. L22 aceito; nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
Relatório evals/narrator/reports/hybrid-campaign-luna-hyp-007-l23-2026-10-18.md.

## Checkpoint anterior — L22 aceito; L23 autorizado — 18/10/2026

Continue aceita L22 na conclusão delimitada: campanha integral inconclusiva,
um percurso completo, nenhum narrador admitido. Autoriza L23 até 17 chamadas
Luna low/USD 0,15 estimados adicionais, mesmo v5/768 tokens/20.000 bytes/60s,
sem retry/fallback/admissão automática. Preflight revalidado: 17 sintéticos,
zero chamadas, máximo 13.952 bytes/22 hashes válidos; trava ausente antes do
lançamento. Só gates paid/live ativados; notas prospectivas são históricas.
Próxima dependência: entrada protegida da chave no lançador externo L23.
Após entrada observar lote único por artefatos, apresentar custo e fechar gate.
Não repetir L22, não ler .env/chave/ambiente/memória do terminal. TASK-013/
CAMP-24/MVP abertos. Não pedir novamente aceite L22 ou teto L23.

## Checkpoint anterior — L22 encerrado; oração ambiental corrigida; L23 fechado — 18/10/2026

L22 batch e3666327-94cc-4794-b087-4029247cf98c: seis chamadas/cinco turnos,
01 completo/intacto, parada R-06/02 por antes que a umidade avance atribuído
ao jogador. USD 0,0052084 finais estimados, não cobrança; 18.620 tokens entrada/
1.237 saída. Gate fechado/trava/histórico preservados. Exceção já existente
agora aceita ausência de mais, mantendo sujeito/predicado/fronteira explícitos.
Oito regressões novas, duas falhas antes da correção, 43 focados aprovados;
parcialidade/atomicidade/reinício/replay sem RNG ou geração adicional.
L23 separado/fechado, mesmo v5/alvo/limites, 33 focados aprovados; preflight
17 sintéticos/zero chamadas/13.952 bytes/22 hashes válidos/AST válido.
Proposta: L22 inconclusivo integral/um percurso completo e L23 até 17 chamadas/
USD 0,15 estimados adicionais, Luna low/v5/768 tokens/20.000 bytes/60s, sem
retry/fallback/admissão. Continue/prossiga aprova ambos; até lá sem terminal/
chave/inferência L23. Após aprovação abrir lançador e aguardar chave protegida.
L21 aceito; nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
Relatório evals/narrator/reports/hybrid-campaign-luna-hyp-007-l22-2026-10-18.md.

## Checkpoint anterior — L21 aceito; L22 autorizado — 18/10/2026

Prossiga aceita L21 na conclusão delimitada: campanha integral inconclusiva,
um percurso completo, nenhum narrador admitido. L22 autorizado até 17 chamadas
Luna low/USD 0,15 estimados adicionais, mesmo v5/768 tokens/20.000 bytes/60s,
sem retry/fallback/admissão automática. Preflight revalidado: 17 sintéticos,
zero chamadas, máximo 13.952 bytes/22 hashes válidos, trava ausente antes do
lançamento. Apenas gates paid/live ativados; notas prospectivas são históricas.
Próxima dependência: entrada protegida da chave no lançador externo L22.
Após entrada observar lote único por artefatos, informar custo final e fechar
gate. Não repetir L21, não ler .env/chave/ambiente/memória do terminal.
TASK-013/CAMP-24/MVP abertos; não pedir novamente aceite L21 ou teto L22.

## Checkpoint anterior — L21 encerrado; aviso corrigido; L22 fechado — 18/10/2026

L21 batch afc50a96-706c-4f44-ba6b-f8fcf2a2858f: três chamadas/dois turnos,
CAMP-EVAL-01 completo/intacto. Parada R-03/02 por falso positivo lexical:
a ameaça agora é evidente não reconhecida como aviso. Custo final estimado
USD 0,0022768, não cobrança; 7.934 tokens entrada/575 saída. Gate fechado/trava
e artefatos preservados. Validação de agência aceitou; _realizes_rule rejeitou.
Correção restrita de equivalência R-03; oito regressões novas/39 focados aprovados,
commit/rejeição atômica/reinício/replay sem RNG/geração adicional. Não reclassificar
live. L22 separado/fechado, mesmo v5/alvo/limites, 30 focados aprovados, preflight
17 sintéticos/zero chamadas/13.952 bytes/22 hashes válidos, AST válido.
Proposta: L21 inconclusivo integral/um percurso completo e L22 até 17 chamadas/
USD 0,15 estimados adicionais, Luna low, 768 tokens/20.000 bytes/60s, sem retry/
fallback/admissão. Continue/prossiga aprova ambos; até lá sem terminal/chave/
inferência L22. Após autorização abrir lançador e aguardar chave protegida.
L20 aceito; nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
Relatório evals/narrator/reports/hybrid-campaign-luna-hyp-007-l21-2026-10-18.md.

## Checkpoint anterior — L20 aceito; L21 autorizado — 18/10/2026

Prossiga aceita a conclusão delimitada L20 (campanha integral inconclusiva,
um percurso completo, nenhum narrador admitido) e autoriza L21 até 17 chamadas
Luna low/USD 0,15 estimados adicionais, mesmo v5/768 tokens/20.000 bytes/60s,
sem retry/fallback/admissão automática. Preflight revalidado sem chamada ao
provedor, 22 hashes válidos; trava L21 ainda ausente antes do lançamento.
Gates paid/live ativados; notas prospectivas do manifesto são históricas.
Próxima dependência: entrada protegida da chave no lançador externo L21.
Depois observar lote único pelos artefatos, informar custo final e fechar gate.
Não repetir L20 nem ler .env/chave/ambiente ou memória do terminal.
TASK-013/CAMP-24/MVP continuam abertos. Não pedir novamente aceite/teto L21.

## Checkpoint anterior — L20 encerrado; correção offline; L21 fechado — 18/10/2026

L20 batch 685a737d-81de-414e-9a8e-c1bb0f9b4f56: três chamadas/dois turnos,
CAMP-EVAL-01 completo/intacto. Parada R-03/02 por falso positivo: gerúndio
aproximando-se da infiltração atribuído ao jogador. Custo final estimado
USD 0,0023168, não cobrança; 7.960 tokens entrada/604 saída. HTTP 429 não repetido.
Gate L20 fechado/trava/evidência preservados. Correção mínima de sujeito ambiental,
nove regressões novas/39 focados aprovados com atomicidade/reinício/replay sem RNG.
L21 preparado separado/fechado, mesmo v5/alvo/limites, 34 testes focados aprovados,
CLI sintético zero chamadas/AST válido. Nenhum narrador admitido, MVP aberto.
Proposta delimitada: aceitar L20 inconclusivo integral e autorizar L21 até
17 chamadas/USD 0,15 estimados adicionais, 768 tokens/20.000 bytes/60s, sem
retry/fallback/admissão. Continue/prossiga aprova ambos; até lá L21 fechado,
sem terminal/chave/chamada. Após aprovação abrir lançador e aguardar chave
protegida. Relatório: evals/narrator/reports/hybrid-campaign-luna-hyp-007-l20-2026-10-18.md.

## Checkpoint anterior — limite externo removido; L20 preparado — 18/10/2026

Humano informou que L19 atingiu limite anterior de USD 0,05 e que o removeu;
continue autoriza continuidade delimitada, sem aumentar teto local. Causa é
informação humana, não diagnóstico retroativo do registro HTTP 429. L19
permanece encerrado/inconclusivo, custo indisponível, gate fechado/trava mantida.
L20 separado: mesmo prompt v5/runtime/critérios, 17 chamadas Luna low, teto
estimado adicional USD 0,15, 768 tokens/20.000 bytes/60s, sem retry/fallback.
34 testes focados aprovados (um aviso preexistente); preflight 17 sintéticos/
zero chamadas, máximo 13.952 bytes e 22 hashes válidos. Só identidade do lote
alterada; sem mudança de produto. Gates L20 ativados após verificação.
Próxima dependência: entrada protegida da chave no lançador externo L20.
Não reutilizar chave/ambiente de L19, não ler .env. Após entrada, observar
artefatos do lote único, mostrar custo e fechar gate. Nenhum narrador admitido;
TASK-013/CAMP-24/MVP abertos. Checkpoints abaixo são históricos.

## Checkpoint anterior — L19 encerrado por HTTP 429 — 18/10/2026

Após entrada protegida confirmada, L19 batch b37735dc-a05a-410c-aa90-afeff8ea534c
parou na primeira chamada: campaign_source_provider_failure/http_429, zero
turnos concluídos, nenhuma resposta narrativa. Custo final indisponível por
ausência de usage; não equivale a USD zero nem confirma cobrança. Gate paid/live
fechado, trava única preservada; sem retry/fallback/L20. L18 já aceito.
Detalhes e hashes: evals/narrator/reports/hybrid-campaign-luna-hyp-007-l19-2026-10-18.md.
Próxima dependência humana: verificar saldo e limites da organização/projeto
no painel OpenAI sem compartilhar credenciais nem aumentar teto automaticamente.
O HTTP isolado não distingue rate limit, quota ou saldo. Nenhum narrador admitido;
TASK-013/CAMP-24/MVP abertos. Prontidão do terminal abaixo é histórica.

## Checkpoint anterior — L18 aceito; L19/v5 autorizado — 18/10/2026

Continue aprova a proposta delimitada anterior: L18 aceito inconclusivo para
campanha integral por falso positivo de autoria NPC, dois percursos concluídos
sem narrador admitido. L19/v5 autorizado até 17 chamadas Luna low, teto adicional
estimado USD 0,15, 768 tokens/20.000 bytes/60s, sem retry/fallback/admissão
automática. Só flags paid/live L19 ativados; hashes/prompt v5 preservados.
Notas prospectivas/hash do manifesto fechado são históricos. Não pedir
novamente aceite L18 ou orçamento L19.

Próxima dependência: chave protegida no terminal externo L19 após preflight
e prontidão. Depois observar lote único por artefatos, apresentar custo final
e fechar gate. Não ler .env, chave, ambiente/memória de terminal, não repetir
L18. TASK-013/CAMP-24/MVP continuam abertos; nenhum narrador admitido.

Lançador externo L19/v5 aberto via wt.exe; prontidão às 21:26:54 UTC de 18/10,
PID 11756 ativo, fase awaiting_secure_credential, zero chamadas antes da entrada.
Preflight revalidado: 17 sintéticos/zero chamadas, 13.952 bytes, 22 hashes válidos.
Não abrir outro lançador. Aguardar entrada protegida e observar o mesmo lote
por artefatos, sem inspecionar ambiente/memória/entrada do terminal.

## Checkpoint anterior — L18 encerrado; autoria NPC corrigida; L19 sem orçamento — 18/10/2026

L18 batch 7bb9007d-4fa0-4d8c-807e-760a17396d08/v5, sete chamadas/seis turnos;
CAMP-EVAL-01 e 02 completos (intacto/parcial). Parada campaign_source_policy_failed
no R-03/03, demais percursos não alcançados. USD 0,0061390 finais estimados,
não cobrança; 21.131 tokens entrada/1.594 saída. Gate L18 fechado/trava mantida,
sem retry/fallback/transferir slots. L17 aceito não volta a pendente, nenhum
narrador admitido.

Falso positivo de autoria: Mara acompanha as marcas de umidade sem tocar no
objeto. Ela ergue os olhos para você e fala em voz baixa. Social atribuído ao
jogador. Prova anterior completa de NPC conhecido adicionada ao mask existente
de olhar/fala; mantém owner único, ausência de jogador e conteúdo citado visível.
Dez testes novos/85 focados agência/autoria/terminal e 35 preparação/histórico/
exato aprovados, sobrepostos. R-03 commit warned/revisão um, ação indevida
rollback/revisão zero, replay/reinício sem geração/entrega/RNG extra. Sem mudar
prompt/schema/catálogo/persistência/autoridade; histórico preservado, sem
reclassificação live. Manifesto histórico L18 rejeita runtime corrigido;
testes isolam hashes atuais só em manifesto temporário.
Regressão ampliada 1.061 aprovada, um aviso preexistente, 191,13s; XML
eval-results/hyp-007-l19-readiness-2026-10-18.xml, zero errors/failures.
Não é suíte integral/frontend/release verde. Diff inspecionado sem whitespace,
sem commit/push; checkout original preservado.

L19 separado, paid/live false/22 hashes, mesmo v5/alvo/limites. CLI 17 sintéticos/
zero chamadas/13.952 bytes, AST válido; sem chave/terminal/trava L19. Correção/
preparação USD 0 adicional. Proposta: aceitar L18 inconclusivo integral por
falso positivo de autoria NPC, dois percursos concluídos sem narrador admitido,
e autorizar L19 até 17 chamadas Luna low/USD 0,15 estimados adicionais/768 tokens/
20.000 bytes/60s, sem retry/fallback. Continue/prossiga aprova proposta, depois
terminal externo/chave protegida. Não repetir L18/transferir slots/prometer
última tentativa. Fragilidade lexical/UX/fidelidade pendentes; TASK-013/CAMP-24/
MVP abertos. Relatório:
evals/narrator/reports/hybrid-campaign-luna-hyp-007-l18-2026-10-18.md.

## Checkpoint anterior — L17 aceito; L18/v5 autorizado — 18/10/2026

Prossiga aprova a proposta delimitada anterior: L17 aceito inconclusivo para
campanha integral por falso positivo de movimento clítico do registro; q
terminal correto observado em R-06, nenhum narrador admitido. L18/v5 autorizado
até 17 chamadas Luna low, teto adicional estimado USD 0,15, 768 tokens/20.000
bytes/60s, sem retry/fallback/admissão automática. Só flags paid/live L18
ativados, hashes/prompt v5 preservados. Notas prospectivas/hash do manifesto
fechado são históricos. Não pedir novamente aceite L17 ou orçamento L18.

Próxima dependência: chave protegida no terminal externo L18 após preflight
e prontidão. Depois observar lote único por artefatos, apresentar custo final
e fechar gate. Não ler .env, chave, ambiente/memória de terminal, não repetir
L17. TASK-013/CAMP-24/MVP continuam abertos; nenhum narrador admitido.

Lançador externo L18/v5 aberto via wt.exe; prontidão às 21:06:36 UTC de 18/10,
PID 12748 ativo, fase awaiting_secure_credential, zero chamadas antes da entrada.
Preflight revalidado: 17 sintéticos/zero chamadas, 13.952 bytes, 22 hashes válidos.
Não abrir outro lançador. Aguardar entrada protegida e observar o mesmo lote
por artefatos, sem inspecionar ambiente/memória/entrada do terminal.

## Checkpoint anterior — L17 encerrado; retirada clítica corrigida; L18 sem orçamento — 18/10/2026

L17 batch 062b4f49-873d-4ffa-9f7e-4a0f2cef6dac/v5, seis chamadas/cinco turnos,
CAMP-EVAL-01 completo; parada campaign_source_policy_failed no R-06/02,
03–08 não alcançados. USD 0,0051470 finais estimados, não cobrança; 18.607
tokens entrada/1.188 saída. Gate L17 fechado/trava mantida, sem retry/fallback/
transferir slots. L16 aceito não volta a pendente; nenhum narrador admitido.

R-06 retornou q vazio e encerramento parcial: violação L16 não se repetiu
nesse caso, sem provar eficácia geral v5. Recusa por falso positivo move/withdraw
em afastando-o da infiltração, referindo ao registro retirado, não ao jogador.
Corrigido só quadro clítico -o da infiltração com antecedente retira o registro
na mesma oração antes da vírgula/fronteira final. Não cobrir reflexivo/jogador/
outro antecedente/fronteira de sentença; manter ações posteriores e cânone.
Nove novos testes, 82 focados de políticas/terminal e 48 preparação/histórico/
exato aprovados (sobrepostos). R-06 confirma partial/dry_surface/revisão quatro,
avanço indevido rollback wet/revisão três; reinício/replay sem geração/entrega/
RNG extra. Sem mudar prompt/schema/catálogo/persistência/autoridade. Histórico
preservado. Testes L16/L17 isolam manifesto temporário e provam drift do runtime
novo sem rebasear originais; validade histórica L16 anterior não é reescrita.
Regressão ampliada 1.038 aprovada, um aviso preexistente, 184,30s; XML
eval-results/hyp-007-l18-readiness-2026-10-18.xml, zero errors/failures.
Não é suíte integral/frontend/release verde. Diff inspecionado sem whitespace,
sem commit/push; checkout original preservado.

L18 separado, paid/live false/22 hashes, mesmo v5/alvo/corpus/limites. CLI 17
sintéticos/zero chamadas/13.952 bytes, AST válido; sem chave/terminal/trava L18.
Correção/preparação USD 0 adicional. Proposta: aceitar L17 inconclusivo integral
por falso positivo de movimento clítico do registro, q terminal correto observado
em R-06 sem narrador admitido, e autorizar L18 até 17 chamadas Luna low/USD 0,15
estimados adicionais/768 tokens/20.000 bytes/60s, sem retry/fallback. Continue/
prossiga aprova proposta, depois terminal externo/chave protegida. Não repetir
L17/transferir slots/prometer última tentativa. Fragilidade lexical/UX/fidelidade
pendentes, TASK-013/CAMP-24/MVP abertos. Relatório:
evals/narrator/reports/hybrid-campaign-luna-hyp-007-l17-2026-10-18.md.

## Checkpoint anterior — L16 aceito; hipótese v5/L17 autorizada — 18/10/2026

Continue aprova a proposta delimitada anterior: L16 aceito como violação real
de fechamento terminal; Luna não admitido no perfil v4. L17/v5 autorizado até
17 chamadas Luna low, teto adicional estimado USD 0,15, 768 tokens/20.000 bytes/
60s, sem retry/fallback/admissão automática. Prompt v5 prioriza condição de q
terminal e não muda critérios. Somente flags paid/live L17 ativados; hashes
preservados. Notas prospectivas e hash do manifesto fechado são históricos.
Não pedir novamente aceite L16 ou orçamento L17. Narrativa/UX não admitidas.

Próxima dependência: chave protegida no terminal externo L17 após preflight
e prontidão. Depois observar lote único por artefatos, apresentar custo final
e fechar gate. Não ler .env, chave, ambiente/memória de terminal, não repetir
L16. TASK-013/CAMP-24/MVP continuam abertos; nenhum narrador admitido.

Lançador externo L17/v5 aberto via wt.exe; prontidão às 20:48:29 UTC de 18/10,
PID 18136 ativo, fase awaiting_secure_credential, zero chamadas antes da entrada.
Preflight revalidado: 17 sintéticos/zero chamadas, 13.952 bytes, 22 hashes válidos.
Não abrir outro lançador. Aguardar entrada protegida e observar o mesmo lote
por artefatos, sem inspecionar ambiente/memória/entrada do terminal.

## Checkpoint anterior — L16 violou fechamento; v5/L17 preparado sem orçamento — 18/10/2026

L16 batch b6fa997d-1241-4363-8d52-1aded62e4a42 fez seis chamadas/cinco turnos,
CAMP-EVAL-01 completo; parada campaign_source_policy_failed no R-06/02,
03–08 não alcançados. USD 0,0052150 finais estimados, não cobrança; 18.353
tokens entrada/1.287 saída. Gate L16 fechado, trava mantida, sem retry/fallback/
transferir slots. L15 aceito não volta a pendente; nenhum narrador admitido.

VIOLAÇÃO REAL, não falso positivo: q "Como você examina o conteúdo legível do
registro preservado?" não vazio num state_after.outcome partial. Prompt v4
e contrato já exigem q vazio. Erro campaign_source_effect_mismatch reproduzido.
Cinco testes novos provam pergunta recusada/rollback revisão três wet/sem
entrega. Contrafactual exclusivamente offline q vazio confirma partial/revisão
quatro/replay sem geração/entrega/RNG extra. Não editar/reclassificar live.
Sem alteração de validador/runtime/schema/catálogo/persistência/autoridade.

Hipótese L17 não repete v4: prompt v5 reordena só instrução q, priorizando
causal_packet.state_after.outcome; partial explicitamente terminal, só null
autoriza pergunta. Critérios não mudam; hipótese ainda sem inferência real.
Hash v4 preservado. L17 preparado separado, paid/live false/22 hashes,
mesmo alvo low/corpus/17 chamadas/768 tokens/20.000 bytes/60s. CLI 17 sintéticos/
zero chamadas, máximo 13.952 bytes e AST válido; sem chave/terminal/trava L17.
Custo adicional offline USD 0. Manifesto L16 continua válido/fechado (sem drift
de runtime); teste prospectivo verifica isso e delta limitado de prompt.
57 focados aprovados/um aviso preexistente/34,66s, XML
eval-results/hyp-007-l17-focused-2026-10-18.xml, zero errors/failures. Sem nova
suíte ampliada por não mudar runtime; 997 são históricos, não execução atual.
Não é suíte integral/release verde; diff inspecionado, sem commit/push.

Proposta: aceitar L16 como violação real de fechamento terminal, Luna não
admitido no perfil v4, e autorizar L17/v5 até 17 chamadas/USD 0,15 estimados
adicionais, sem retry/fallback/admissão automática. Continue/prossiga aprova
ambos; depois terminal externo e chave protegida. Não repetir L16/transferir
slots/prometer última tentativa. TASK-013/CAMP-24/MVP abertos. Relatório:
evals/narrator/reports/hybrid-campaign-luna-hyp-007-l16-2026-10-18.md.

## Checkpoint anterior — L15 aceito; L16 autorizado — 18/10/2026

Prossiga aprova a proposta delimitada anterior: L15 aceito inconclusivo para
campanha integral por falso positivo de escolha futura, nenhum narrador
admitido. L16 autorizado até 17 chamadas Luna low, teto adicional estimado
USD 0,15, prompt v4/768 tokens/20.000 bytes/60s, sem retry/fallback/admissão
automática. Somente flags paid/live L16 ativados; hashes preservados. Notas
prospectivas e hash do manifesto fechado de preparação são históricos.
Não pedir novamente aceite L15 ou orçamento L16. Narrativa/UX não admitidas.

Próxima dependência: chave protegida no terminal externo L16 após preflight
e prontidão. Depois observar lote único por artefatos, apresentar custo final
e fechar gate. Não ler .env, chave, ambiente/memória de terminal, não repetir
L15. TASK-013/CAMP-24/MVP continuam abertos; nenhum narrador admitido.

Lançador externo L16 aberto via wt.exe; prontidão às 20:39:49 UTC de 18/10,
PID 11204 ativo, fase awaiting_secure_credential, zero chamadas antes da entrada.
Preflight revalidado: 17 sintéticos/zero chamadas, 13.614 bytes, 22 hashes válidos.
Não abrir outro lançador. Aguardar entrada protegida e observar o mesmo lote
por artefatos, sem inspecionar ambiente/memória/entrada do terminal.

## Checkpoint anterior — L15 encerrado; escolha futura corrigida; L16 sem orçamento — 18/10/2026

L15 batch 0edbff66-af8c-4b64-b60e-1ea1dd71acd5 já terminal ao usuário pedir
prossiga: três chamadas/dois turnos, CAMP-EVAL-01 completo; parada R-03/02
campaign_source_policy_failed. USD 0,0022494 finais estimados, não cobrança;
7.695 tokens entrada/592 saída. Gate L15 fechado, trava mantida, sem retry/
fallback/transferência de slots. Ready é histórico. L14 aceito não volta a
pendente. Nenhum narrador admitido; não abrir outro lançador L15.

Falso positivo: ao que você decidir fazer tratado como choice já executada.
Corrigido quadro delimitado ao que + jogador conhecido + decidir fazer com
fronteira na política existente de decisões pendentes, mascarando só decidir.
Texto/offsets/ações posteriores preservados. Oito novos testes; 68 focados de
políticas e 33 preparação/histórico/exato aprovados, sobrepostos. R-03 commit
warned/revisão um/sem desfecho, ações indevidas rollback, replay/reinício sem
nova geração/entrega/RNG. Sem mudar prompt/schema/catálogo/persistência/autoridade.
Originais/manifesto executado L15 preservados, sem reclassificação live.
Regressão ampliada 997 aprovada, um aviso preexistente, 156,15s; XML
eval-results/hyp-007-l16-readiness-2026-10-18.xml, zero errors/failures.
Não é suíte integral/frontend/release verde. Diff inspecionado sem whitespace,
sem commit/push; checkout original preservado. Continue durante testes deu
sequência ao trabalho em andamento, não aprovou orçamento ainda não apresentado.

L16 separado, paid/live false, 22 hashes, mesmo prompt v4/alvo/corpus/limites.
CLI 17 sintéticos/zero chamadas/13.614 bytes, AST válido; sem chave/terminal/
trava L16. Correção/preparação USD 0 adicional. Proposta: aceitar L15 inconclusivo
integral por falso positivo de escolha futura, nenhum narrador admitido, e
autorizar L16 até 17 chamadas Luna low/USD 0,15 estimados adicionais/768 tokens/
20.000 bytes/60s, sem retry/fallback. Continue/prossiga aprova proposta, depois
terminal externo e chave protegida. Prossiga anterior não aceita resultado ainda
não apresentado. Não repetir L15/transferir slots/promover última tentativa.
Fragilidade lexical registrada sem refatoração geral; UX/fidelidade pendentes.
TASK-013/CAMP-24/MVP abertos. Relatório:
evals/narrator/reports/hybrid-campaign-luna-hyp-007-l15-2026-10-18.md.

## Checkpoint anterior — L14 aceito; L15 autorizado — 18/10/2026

Continue aprova a proposta delimitada anterior: L14 aceito inconclusivo para
campanha integral por lacuna lexical de resgate parcial, nenhum narrador
admitido. L15 autorizado até 17 chamadas Luna low, teto adicional estimado
USD 0,15, prompt v4/768 tokens/20.000 bytes/60s, sem retry/fallback/admissão
automática. Somente flags paid/live L15 ativados; hashes preservados. Notas
prospectivas e hash do manifesto fechado de preparação são históricos.
Não pedir novamente aceite L14 ou orçamento L15. Narrativa/UX não admitidas.

Próxima dependência: chave protegida no terminal externo L15 após preflight
e prontidão. Depois observar lote único por artefatos, apresentar custo final
e fechar gate. Não ler .env, chave, ambiente/memória de terminal, não repetir
L14. TASK-013/CAMP-24/MVP continuam abertos; nenhum narrador admitido.

Lançador externo L15 aberto via wt.exe; prontidão às 18:37:22 UTC de 18/10,
PID 6752 ativo, fase awaiting_secure_credential, zero chamadas antes da entrada.
Preflight revalidado: 17 sintéticos/zero chamadas, 13.614 bytes, 22 hashes válidos.
Não abrir outro lançador. Aguardar entrada protegida e observar o mesmo lote
por artefatos, sem inspecionar ambiente/memória/entrada do terminal.

## Checkpoint anterior — L14 encerrado; realização parcial corrigida; L15 sem orçamento — 18/10/2026

L14 batch 47ea5162-cd94-4c14-a0e7-2327082164a5, seis chamadas/cinco turnos,
CAMP-EVAL-01 completo; parada campaign_source_policy_failed no R-06/02.
03–08 não alcançados. USD 0,0051728 finais estimados, não cobrança; 18.448
tokens entrada/1.236 saída. Gate L14 fechado, trava mantida, sem retry/fallback/
transferência de slots. L13 aceito não volta a pendente; narrador não admitido.

Agência geral passou; R-06 não reconhecia o que ainda permanece legível é salvo
como realização parcial por exigir parcial/parte/trecho. Acrescentada somente
essa frase normalizada ao grupo R-06 em api/campaign_source_profile.py, mantendo
demais obrigações. Contraprova revelou continua perdido não coberto; acrescentado
continua ao guard existente de estado contraditório preserved/partial. Sem
afrouxar teste, sem mudar prompt/schema/catálogo/persistência/RNG/autoridade.
Seis novos testes, 33 focados perfil/integração/trajetórias e 31 preparação/
histórico/exato aprovados (sobrepostos). R-06 commit partial/dry_surface;
ação indevida rollback wet/revisão três, replay/reinício sem geração/entrega/RNG
extra. Originais/manifesto executado L14 preservados; sem reclassificação live.
Regressão ampliada 976 aprovada, um aviso preexistente, 146,77s; XML
eval-results/hyp-007-l15-readiness-2026-10-18.xml, zero errors/failures.
Não é suíte integral/frontend/release verde. Diff inspecionado sem whitespace,
sem commit/push; checkout original preservado.

L15 preparado separado, paid/live false, 22 hashes, mesmo prompt v4/alvo/limites.
CLI 17 sintéticos/zero chamadas/13.614 bytes, AST válido; sem chave/terminal/
trava L15. Correção/preparação adicional USD 0. Proposta: aceitar L14 inconclusivo
integral por lacuna lexical R-06, nenhum narrador admitido, e autorizar L15 até
17 chamadas Luna low/USD 0,15 estimados adicionais/768 tokens/20.000 bytes/60s,
sem retry/fallback. Continue/prossiga aprova proposta; depois terminal externo
e chave protegida. Não repetir L14, transferir slots ou prometer última tentativa.
Fragilidade lexical registrada, sem refatoração geral; UX/fidelidade semântica
pendentes. TASK-013/CAMP-24/MVP abertos. Relatório:
evals/narrator/reports/hybrid-campaign-luna-hyp-007-l14-2026-10-18.md.

## Checkpoint anterior — L13 aceito; L14 autorizado — 18/10/2026

Prossiga aprova a proposta delimitada anterior: L13 aceito inconclusivo para
campanha integral por falso positivo de atribuição atmosférica, nenhum narrador
admitido. L14 autorizado até 17 chamadas Luna low, teto adicional estimado
USD 0,15, prompt v4/768 tokens/20.000 bytes/60s, sem retry/fallback/admissão
automática. Somente flags paid/live L14 ativados; hashes preservados. Notas
prospectivas e hash do manifesto fechado de preparação são históricos.
Não pedir novamente aceite L13 ou orçamento L14. Narrativa/UX não admitidas.

Próxima dependência: chave protegida no terminal externo L14 após preflight
e prontidão. Depois observar lote único por artefatos, apresentar custo final
e fechar gate. Não ler .env, chave, ambiente/memória de terminal, não repetir
L13. TASK-013/CAMP-24/MVP continuam abertos; nenhum narrador admitido.

Lançador externo L14 aberto via wt.exe; prontidão às 18:15:33 UTC de 18/10,
PID 18292 ativo, fase awaiting_secure_credential, zero chamadas antes da entrada.
Preflight revalidado: 17 sintéticos/zero chamadas, 13.614 bytes, 22 hashes válidos.
Não abrir outro lançador. Aguardar entrada protegida e observar o mesmo lote
por artefatos, sem inspecionar ambiente/memória/entrada do terminal.

## Checkpoint anterior — L13 encerrado; atribuição atmosférica corrigida; L14 sem orçamento — 18/10/2026

L13 batch a41446fe-c0ba-46b7-982f-357eee247315, três chamadas/dois turnos,
CAMP-EVAL-01 completo; parada campaign_source_policy_failed no R-03/02.
Custo final estimado USD 0,0022426, não cobrança; 7.697 tokens entrada/586 saída.
Gate L13 fechado, trava preservada, sem retry/fallback/transferência de slots.
L12 aceito não volta a pendente; nenhum narrador admitido.

Falso positivo em o Arquivo parece se fechar ao redor da bancada baixa,
interpretado como interact/close do jogador. Corrigido só esse quadro explícito
em _action_signature_matches, preservando offsets/texto/ações seguintes.
Oito novos testes; 60 focados de políticas e 33 preparação/histórico/exato
aprovados, sobrepostos. Exato confirma R-03/warned sem desfecho; fechamento
indevido posterior recusa atomicamente; reinício/replay sem nova geração/
entrega/RNG. Sem mudar prompt/schema/catálogo/persistência/autoridade.
Registros e manifesto executado L13 preservados; sem reclassificação live.
Regressão ampliada 957 aprovada, um aviso preexistente, 128,53s; XML
eval-results/hyp-007-l14-readiness-2026-10-18.xml, zero errors/failures.
Não é suíte integral/frontend/release verde. Diff inspecionado sem whitespace,
sem commit/push; checkout original preservado.

L14 preparado separado, paid/live false, 22 hashes, mesmo prompt v4/alvo/limites.
CLI 17 sintéticos/zero chamadas, máximo 13.614 bytes, AST válido; sem chave,
terminal ou trava L14. Correção/preparação adicional USD 0. Proposta: aceitar
L13 inconclusivo integral por falso positivo de atribuição atmosférica, nenhum
narrador admitido, e autorizar L14 até 17 chamadas Luna low/USD 0,15 estimados
adicionais, 768 tokens/20.000 bytes/60s, sem retry/fallback. Continue/prossiga
aprova proposta; depois terminal externo e chave protegida. Não repetir L13,
transferir slots ou prometer última tentativa. Fragilidade lexical registrada
sem refatoração geral; narrativa/UX e fidelidade semântica continuam pendentes.
TASK-013/CAMP-24/MVP abertos, ressalvas L9/alias mantidas. Relatório:
evals/narrator/reports/hybrid-campaign-luna-hyp-007-l13-2026-10-18.md.

## Checkpoint anterior — L12 aceito; L13 autorizado — 18/10/2026

Prossiga aprova a proposta delimitada anterior: L12 aceito inconclusivo para
campanha integral por falso positivo de estado do registro, nenhum narrador
admitido. L13 autorizado até 17 chamadas Luna low, teto adicional estimado
USD 0,15, prompt v4/768 tokens/20.000 bytes/60s, sem retry/fallback/admissão
automática. Somente flags paid/live L13 ativados; hashes preservados. Notas
prospectivas e hash do manifesto fechado de preparação são históricos.
Não pedir novamente aceite L12 ou orçamento L13. Narrativa/UX não admitidas.

Próxima dependência: chave protegida no terminal externo L13 após preflight
e prontidão. Depois observar lote único por artefatos, apresentar custo final
e fechar gate. Não ler .env, chave, ambiente/memória de terminal, não repetir
L12. TASK-013/CAMP-24/MVP continuam abertos; nenhum narrador admitido.

Lançador externo L13 aberto via wt.exe; prontidão às 18:07:53 UTC de 18/10,
PID 20180 ativo, fase awaiting_secure_credential, zero chamadas antes da entrada.
Preflight revalidado: 17 sintéticos/zero chamadas, 13.614 bytes, 22 hashes válidos.
Não abrir outro lançador. Aguardar entrada protegida e observar o mesmo lote
por artefatos, sem inspecionar ambiente/memória/entrada do terminal.

## Checkpoint anterior — L12 encerrado; exposição do registro corrigida; L13 sem orçamento — 18/10/2026

L12 batch 33f9877d-1e86-4c0e-a757-0a3bf2ae6973, uma chamada/zero turnos,
parada campaign_source_policy_failed no primeiro R-01/01. USD 0,0007374 finais
estimados, não cobrança; 2.367 tokens entrada/220 saída. Geração 4.664 ms,
turno 4.775 ms; amostra única não SLA. Gate L12 fechado, trava mantida, sem
retry/fallback/transferência de slots. L11 aceito não volta a pendente.

Falso positivo: em evitando que o registro permaneça exposto ao risco atual,
remain foi atribuído ao jogador. Corrigido apenas quadro explícito de objeto
em _action_signature_matches, mantendo offsets/texto/ações seguintes. Oito
testes novos; 52 focados de políticas e 33 preparação/histórico/exato aprovados
(sobrepostos). R-01 seguro confirma uma vez/threatened sem desfecho; espera
indevida posterior recusa atomicamente; reinício/replay sem nova geração/entrega/
RNG. Sem mudar prompt/schema/catálogo/persistência/autoridade. Histórico preservado.
Regressão ampliada 936 aprovada, um aviso preexistente, 123,01s; XML
eval-results/hyp-007-l13-readiness-2026-10-18.xml, zero errors/failures.
Não é suíte integral/frontend/release verde. Diff inspecionado sem whitespace,
sem commit/push; checkout original preservado.

L13 preparado separado, paid/live false, 22 hashes, mesmo prompt v4/alvo/limites.
Preflight 17 sintéticos/zero chamadas/13.614 bytes, AST válido; sem terminal,
chave ou trava L13. Correção/preparação USD 0 adicional. Fragilidade operacional
do scanner lexical para variação de prosa registrada, sem refatoração geral ou
mudança arquitetural por arrasto. Fidelidade semântica/UX ainda não aprovadas.
Proposta: aceitar L12 inconclusivo integral por falso positivo de estado do
registro, nenhum narrador admitido, e autorizar L13 até 17 chamadas Luna low,
USD 0,15 estimados adicionais/768 tokens/20.000 bytes/60s, sem retry/fallback.
Continue/prossiga aprova proposta; depois terminal externo e chave protegida.
Não repetir L12, transferir slots ou prometer última tentativa. TASK-013/CAMP-24/
MVP abertos; ressalvas L9/alias mantidas. Relatório:
evals/narrator/reports/hybrid-campaign-luna-hyp-007-l12-2026-10-18.md.

## Checkpoint anterior — L11 aceito; L12 autorizado — 18/10/2026

Continue aprova a proposta delimitada anterior: L11 aceito inconclusivo para
campanha integral por falso positivo de atribuição ambiental, nenhum narrador
admitido. L12 autorizado até 17 chamadas Luna low, teto adicional estimado
USD 0,15, prompt v4/768 tokens/20.000 bytes/60s, sem retry/fallback/admissão
automática. Somente flags paid/live L12 ativados; hashes preservados. Notas
prospectivas e hash do manifesto fechado de preparação são históricos.
Não pedir novamente aceite L11 ou orçamento L12. Narrativa/UX não admitidas.

Próxima dependência: chave protegida no terminal externo L12 após preflight
e prontidão. Depois observar lote único por artefatos, apresentar custo final
e fechar gate. Não ler .env, chave, ambiente/memória de terminal, não repetir
L11. TASK-013/CAMP-24/MVP continuam abertos; nenhum narrador admitido.

Lançador externo L12 aberto via wt.exe; prontidão às 17:07:56 UTC de 18/10,
PID 11324 ativo, fase awaiting_secure_credential, zero chamadas antes da entrada.
Preflight revalidado: 17 sintéticos/zero chamadas, 13.614 bytes, 22 hashes válidos.
Não abrir outro lançador. Aguardar entrada protegida e observar o mesmo lote
por artefatos, sem inspecionar ambiente/memória/entrada do terminal.

## Checkpoint anterior — L11 encerrado; avanço ambiental corrigido; L12 sem orçamento — 18/10/2026

L11 batch 1b1382a6-1ed6-4ae9-840d-c01f394a0077: seis chamadas/cinco turnos,
CAMP-EVAL-01 completo; parada R-06/CAMP-EVAL-02 em campaign_source_policy_failed.
03–08 não alcançados. Custo final estimado USD 0,0052376, não cobrança;
18.346 tokens entrada/1.307 saída. Geração 3.289–4.941 ms, turno 3.595–5.257 ms;
amostra sintética, não SLA. Gate L11 fechado, trava mantida, sem retry/fallback
ou reutilização de slots. L10 aceito não volta a pendente; narrador não admitido.

Falso positivo reproduzido: "antes que a umidade avance mais" atribuído ao
jogador em vez de umidade. Corrigido somente quadro temporal delimitado na
família advance, mantendo texto/offsets/ações posteriores. Oito testes novos,
44 focados de políticas e 33 preparação/histórico/exato aprovados (sobrepostos).
Resposta exata passa offline; movimento/decisão/abertura indevidos continuam
bloqueados. Integração R-06 commit parcial/rollback/replay/reinício sem nova
geração/entrega/RNG. Sem mudança de prompt/schema/catálogo/persistência/autoridade.
Registros e manifesto histórico L11 preservados, sem reclassificação live.
Regressão ampliada: 915 aprovados, um aviso preexistente, 110,91s; XML
eval-results/hyp-007-l12-readiness-2026-10-18.xml, zero errors/failures.
Não é suíte integral/frontend/release verde. Diff inspecionado sem whitespace,
sem commit/push, checkout original preservado.

L12 separado, paid/live false, 22 hashes, mesmo prompt v4/alvo/corpus/limites.
CLI 17 sintéticos/zero chamadas, máximo 13.614 bytes e AST válido; sem chave,
terminal ou trava L12. Correção/preparação USD 0 adicional. Proposta: aceitar
L11 inconclusivo integral por falso positivo de atribuição ambiental, nenhum
narrador admitido, e autorizar L12 até 17 chamadas Luna low/USD 0,15 estimados
adicionais, 768 tokens/20.000 bytes/60s, sem retry/fallback. Continue/prossiga
aprova proposta; depois terminal externo e chave protegida. Não repetir L11 ou
transferir slots, não prometer última tentativa. TASK-013/CAMP-24/MVP abertos.
Ressalvas narrativas L9 e pronomes/alias mantidas. Relatório:
evals/narrator/reports/hybrid-campaign-luna-hyp-007-l11-2026-10-18.md.

## Checkpoint anterior — L10 aceito; L11 autorizado — 18/10/2026

Continue aprova a proposta delimitada anterior: L10 aceito inconclusivo para
campanha integral por falso positivo de decisão pendente, nenhum narrador
admitido. L11 autorizado até 17 chamadas Luna low, teto adicional estimado
USD 0,15, prompt v4/768 tokens/20.000 bytes/60s, sem retry/fallback/admissão
automática. Somente flags paid/live L11 ativados; hashes preservados. Notas
prospectivas e hash do manifesto fechado de preparação são históricos.
Não pedir novamente aceite L10 ou orçamento L11. Narrativa/UX não admitidas.

Próxima dependência: chave protegida no terminal externo L11 após preflight
e prontidão. Depois observar lote único por artefatos, apresentar custo final
e fechar gate. Não ler .env, chave, ambiente/memória de terminal, não repetir
L10. TASK-013/CAMP-24/MVP continuam abertos; nenhum narrador admitido.

Lançador externo L11 aberto via wt.exe; prontidão às 16:24:35 UTC de 18/10,
PID 16280 ativo, fase awaiting_secure_credential, zero chamadas antes da entrada.
Preflight revalidado: 17 sintéticos/zero chamadas, 13.614 bytes, 22 hashes válidos.
Não abrir outro lançador. Aguardar entrada protegida e observar o mesmo lote
por artefatos, sem inspecionar ambiente/memória/entrada do terminal.

## Checkpoint anterior — L10 encerrado; decisão pendente corrigida; L11 sem orçamento — 18/10/2026

L10 batch 965327f4-db29-4668-afe5-0d535c2c8099 fez uma chamada/zero turnos,
parou em campaign_source_policy_failed no primeiro R-01/CAMP-EVAL-01.
Custo final estimado USD 0,0007104, não cobrança; 2.400 tokens entrada/192 saída.
Geração 3.740 ms, turno 3.861 ms; amostra única não SLA. Gate L10 fechado,
trava preservada, sem retry/fallback/reutilização de slots. L9 aceito não volta
a pendente; nenhum narrador admitido e oito percursos não completados.

Falso positivo reproduzido em "até que você decida como proceder": choice
indevidamente executado. Corrigido apenas esse quadro de decisão pendente em
_validate_declared_player_actions, com jogador conhecido e fronteira final;
mascara só decida e mantém ações posteriores. Resposta exata passa offline;
decisão/ação real posterior continua recusada atomicamente. Dez testes novos
com R-01, aliases, rollback e replay/reinício sem nova geração/entrega/RNG.
58 focados de políticas e 35 preparação/histórico aprovados (sobrepostos).
Regressão ampliada: 894 aprovados, um aviso preexistente, 95,97s; XML
eval-results/hyp-007-l11-readiness-2026-10-18.xml, zero errors/failures.
Não é suíte integral/frontend/release verde. Diff inspecionado sem whitespace.
Sem mudança de prompt/schema, RNG, persistência, catálogo ou autoridade.
Registros e manifesto histórico L10 preservados; sem reclassificação live.

L11 preparado separadamente, paid/live false, 22 hashes, mesmo prompt v4,
modelo low/corpus/limites. CLI 17 sintéticos/zero chamadas, 13.614 bytes, AST
válido. Nenhum terminal/chave/trava L11. Correção/preparação USD 0 adicional.
Proposta: aceitar L10 inconclusivo integral por falso positivo de decisão
pendente, nenhum narrador admitido, e autorizar L11 até 17 chamadas Luna low,
USD 0,15 estimados adicionais/768 tokens/20.000 bytes/60s, sem retry/fallback.
Continue/prossiga aprova proposta; depois abrir terminal externo identificado
e pedir chave protegida. Não repetir L10/transferir slots nem prometer última
tentativa. TASK-013/CAMP-24/MVP abertos. Ressalvas narrativas L9 e alias mantidas.
Relatório: evals/narrator/reports/hybrid-campaign-luna-hyp-007-l10-2026-10-18.md.

## Checkpoint anterior — L9 aceito; L10 autorizado — 18/10/2026

O usuário respondeu "Continue" à proposta delimitada anterior: aceita L9
inconclusivo para campanha integral por falso positivo nominal, nenhum narrador
admitido, e autoriza L10 até 17 chamadas Luna low, teto adicional estimado
USD 0,15, mesmo prompt v4, 768 tokens/20.000 bytes/60s, sem retry/fallback ou
admissão automática. Somente flags paid/live ativados; hashes preservados.
Notas prospectivas e hash de preparação fechada do manifesto são históricos.
Não pedir novamente aceite L9 ou orçamento L10. Narrativa/UX não admitidas.

Próxima dependência: entrada protegida da chave no terminal externo L10,
após preflight e prontidão confirmados. Depois observar lote único, apresentar
custo final e fechar gate. Não ler .env, credencial ou ambiente/memória do
terminal, não repetir L9. TASK-013/CAMP-24 e MVP continuam abertos.

Lançador externo L10 aberto via wt.exe; marcador de prontidão às 16:03:07 UTC
de 18/10, PID 14080, fase awaiting_secure_credential, zero chamadas antes da
entrada. Preflight revalidado: 17 sintéticos/zero chamadas, 13.614 bytes e
22 hashes válidos. Não abrir outro lançador. Aguardar chave protegida e observar
o mesmo lote por artefatos, sem inspecionar ambiente/memória do terminal.

## Checkpoint anterior — L9 encerrado; nominal corrigido; L10 sem orçamento — 18/10/2026

L9 batch 6c5cbe84-00a9-4aff-b242-5a6ede0af505: 12 chamadas, 11 turnos completos,
cinco percursos 01–05 concluídos; R-07/CAMP-EVAL-06 rejeitado, 07/08 não
alcançados. Parada campaign_source_policy_failed. Custo final estimado
USD 0,0097762, não cobrança; 34.709 tokens entrada/2.362 saída. Geração
2.231–4.403 ms, turno 2.364–4.605 ms; observações, não SLA. Gate L9 fechado,
trava mantida, sem retry/fallback ou reutilização de slots. L8 aceito não
volta a ficar pendente. Nenhum narrador admitido.

Falso positivo reproduzido: substantivo partes em "entre as partes preservadas"
lido como move/depart. Correção restrita na família depart com contexto nominal
exato, sem mudança de prompt v4, RNG, persistência/catálogo/autoridade. Resposta
exata passa offline; partida posterior continua bloqueada atomicamente.
Oito testes novos, 33 focados conjuntos aprovados; replay/reinício sem nova
geração/entrega/RNG. Artefatos live e manifesto histórico L9 preservados.
Regressão ampliada 871 aprovada, um aviso preexistente, 91,61s; XML
eval-results/hyp-007-l10-readiness-2026-10-18.xml, zero errors/failures.
Contagens sobrepostas; não é suíte integral/frontend/release verde.
Não confundir admissão offline com fidelidade semântica: R-01 "Não o mova por
enquanto" e R-07 "parcialmente restaurado"/"pista relevante" merecem avaliação
humana de narrativa. Sem novo fato canônico ou aprovação automática.

L10 preparado, paid/live false, 22 hashes, mesmo prompt v4/alvo/corpus/limites.
CLI 17 sintéticos/zero chamadas e corpo máximo 13.614 bytes, AST válido.
Nenhum terminal/chave/trava live L10. Custo adicional da correção/preparação USD 0.
Proposta: aceitar L9 inconclusivo integral por falso positivo nominal, nenhum
narrador admitido, e autorizar L10 até 17 chamadas Luna low e USD 0,15 estimados
adicionais, 768 tokens/20.000 bytes/60s, sem retry/fallback. Continue/prossiga
aprova a proposta; depois abrir terminal externo e pedir chave protegida.
Não repetir L9 nem transferir saldo. TASK-013/CAMP-24/MVP seguem abertos.
Relatório: evals/narrator/reports/hybrid-campaign-luna-hyp-007-l9-2026-10-18.md.

## Checkpoint anterior — L8 aceito; L9 autorizado — 18/10/2026

O usuário respondeu "continue" à proposta delimitada: aceita L8 inconclusivo
para a experiência integral por falso positivo local de condicional, nenhum
narrador admitido, e autoriza L9 até 17 chamadas Luna low, teto adicional
estimado USD 0,15, prompt v4/768 tokens/20.000 bytes, sem retry/fallback ou
admissão automática. Flags paid/live L9 ativados; hashes e demais parâmetros
preservados. A nota prospectiva no manifesto e o hash da preparação fechada
são históricos. Não pedir novamente aceite L8 ou orçamento L9.

Próximo passo: preflight sem chave, terminal externo identificado, confirmação
de prontidão e entrada protegida pelo usuário. Não ler credencial, ambiente ou
memória do terminal. Depois observar lote único, custo final e fechar gate.
TASK-013/CAMP-24 e MVP continuam abertos; nenhum narrador admitido.

Lançador externo L9 aberto via wt.exe; marcador de prontidão às 15:52:44 UTC
de 18/10, PID 5388, fase awaiting_secure_credential, zero chamadas antes da
entrada. Preflight: 17 turnos sintéticos, máximo 13.614 bytes, USD 0. Não abrir
outro lançador. Aguardar chave protegida e observar o mesmo lote por artefatos,
sem inspecionar ambiente, memória ou entrada do terminal.

## Checkpoint anterior — L8 encerrado; condicional corrigida; L9 sem orçamento — 18/10/2026

L8 executou uma chamada real, zero turnos completos, batch
`d3ff90c3-c6aa-406a-a0e6-8d029363d6a5`. Parada `campaign_source_policy_failed`
no primeiro R-01/CAMP-EVAL-01. Custo final estimado USD 0,0007162, não cobrança
confirmada; 2.375 tokens de entrada e 201 de saída, uma chamada com usage.
Geração local 4.519 ms, turno 4.638 ms; observação única, não SLA. Gate paid/live
L8 fechado, trava mantida, sem retry/fallback. Não reutilizar 16 slots restantes.
Marcador ready é histórico, não status atual. L7/L6/L5 aceitos não ficam pendentes
novamente; nenhum narrador/default admitido e os oito percursos não completados.

Falso positivo reproduzido na hipótese "Se você precisar movê-lo, ...". O scan
lia `move` (infinitivo com clítico normalizado) como `interact/move_object`
executado pelo jogador. Correção local no tratamento já existente de hipóteses:
mascarar somente esse verbo na condicional delimitada se/caso + jogador +
precisar + movê-lo/la/los/las + vírgula, preservando offsets e ações seguintes.
Resposta L8 exata passa offline sem reescrita. Movimentos afirmativos, comandos,
promessas e ações posteriores não declaradas continuam bloqueados; sem alteração
de RNG/persistência/catálogo/schema/prompt v4. Não reclassificar o turno live.

Verificação: cinco positivos falharam antes; 18 testes novos de condicional e
integração, checagem focada conjunta de 43 e seleção ampliada final de 850
aprovados (sobrepostos), um aviso preexistente. Commit R-01, reinício e replay
sem nova geração/RNG; movimento indevido deixa revisão/fonte/entrega intactas.
Limitação separada conservada: alias nomeado do jogador numa fala pode tornar
um "Ela" posterior ambíguo para o gate de pronome; com Mara explícita passa.
Teste desse bloqueio mantido, sem ampliar correferência por arrasto.

L9 preparado separadamente, mesmo prompt v4, alvo/corpus/limites, 22 hashes,
paid/live false. Preflight CLI 17 turnos sintéticos/zero chamadas reais, corpo
máximo 13.614 bytes; AST PowerShell válido. Sem launcher, chave ou trava live L9.
Custo da correção/preparação adicional: USD 0. Alterações locais sem commit/push.
Não é suíte integral verde. Manifesto e records L8 preservados; testes L8 usam
manifesto temporário isolado e provam recusa do runtime novo pelo histórico.

Conclusão delimitada proposta: L8 inconclusivo para campanha integral por falso
positivo de ação em condicional, nenhum narrador admitido. Próxima proposta:
aceitar a conclusão e autorizar L9 até 17 chamadas Luna low, teto estimado
adicional USD 0,15, 768 tokens/20.000 bytes, sem retry/fallback. Continue/prossiga
aprova a proposta delimitada; não exigir frase ritual. Até lá, L9 fechado.
Não prometer que L9 será a última tentativa; permanece a ressalva da fila dada
antes de L8. Depois: revalidar, abrir Windows Terminal identificado, confirmar
prontidão, entrada protegida e lote único/custo/gates/fechamento live. Não ler
`.env*`, saves, chaves ou ambiente/memória de terminal; não repetir L8.

Evidência: `evals/narrator/reports/hybrid-campaign-luna-hyp-007-l8-2026-10-18.md`.
TASK-022/023 fecham correção/preparação; TASK-013/CAMP-24 e MVP abertos.
Configuração recomendada para autorização/operação delimitada: Sol low.

## Checkpoint anterior — L7 aceito; L8 autorizado — 18/10/2026

O usuário respondeu "Prossiga, mas antes de começar, me informe quantas e quais
são as baterias de testes restantes". Conforme convenção explícita, L7 aceito
na conclusão delimitada inconclusiva por falso positivo de q, nenhum narrador
admitido; L8 autorizado nos limites já propostos. Antes de ativar/executar,
informou-se a fila e conferiu-se o protocolo: uma bateria paga preparada nesta
frente (L8, oito percursos/17 chamadas); depois, se aprovada tecnicamente,
avaliação humana de narrativa/UX e ensaio correspondente ainda a delimitar.
Não há L9 aprovado, número garantido de tentativas futuras ou total fechado
das baterias do restante do MVP. Nove contraprovas e regressões offline já
exercitadas não são nove novos lotes pagos. Bandeja/UI/ficha/aceitação integral
continuam na sequência, sem abrir essas frentes agora.

L8: até 17 chamadas `gpt-5.6-luna`/`low`, USD 0,15 estimados adicionais,
768 tokens/20.000 bytes, sem retry/fallback/admissão automática. Somente os
flags paid/live L8 ativados; prompt v4, 22 hashes e limites preservados.
Notas do manifesto e SHA da preparação com flags false são históricos;
este checkpoint registra a autorização posterior. L7 fechado e sem repetição.

Próxima dependência: revalidar preflight, abrir Windows Terminal identificado
L8, confirmar novo marcador/processo e pedir entrada protegida. Não abrir dois
lançadores, ler `.env*`/saves/chaves ou consultar ambiente/memória de terminal.
Depois da entrada: observar lote único, apresentar custo/gates/resultado e
fechar live. Não pedir novamente orçamento ou aceite L7. Nenhum narrador
admitido; TASK-013/CAMP-24 e MVP continuam abertos.

Lançador L8 aberto via `wt.exe`, janela confirmada `HYP-007-L8 - chave segura`.
Novo marcador às 15:35:46 UTC de 18/10, PID 19660, fase
`awaiting_secure_credential`, zero chamadas antes da entrada. Processo ativo,
sem trava live L8 na última checagem. Preflight revalidado: 17 turnos sintéticos,
corpo máximo 13.614 bytes, 22 hashes válidos. Não abrir outro lançador; aguardar
entrada protegida e observar o mesmo lote, sem consultar ambiente/credencial.

## Checkpoint anterior — resultado L7 e prontidão L8 — 18/10/2026

Ao retomar após indisponibilidade da revisão automática, observou-se que o
lançador L7 já tinha produzido resultado terminal. Não foi aberto outro lote.
Batch `7d690675-b176-4ad6-bf91-0f7e77102ddc`: três chamadas, dois turnos completos,
CAMP-EVAL-01 ajuda/resgate concluído; parada de política no primeiro R-03 de
CAMP-EVAL-02. Custo final estimado USD 0,0022832, não cobrança confirmada;
7.696 tokens de entrada e 620 de saída, três chamadas com usage. Sem retry ou
fallback. Gate paid/live L7 fechado, trava mantida; não reutilizar 14 slots.
O marcador ready e seu zero de chamadas são históricos pré-entrada, não status
atual. L6/L5 aceitos permanecem encerrados; nenhum narrador/default admitido.

Falso positivo reproduzido: "Qual é a sua próxima ação diante do risco imediato?"
é recusada como `scene_player_prompt_not_actionable`, mas remover apenas o
artigo ("Qual é sua...") passa. Pergunta tem 10 palavras, não falha de tamanho.
Correção local em `_validate_player_prompt` admite a forma possessiva com artigo
apenas por fullmatch do campo inteiro e cauda contextual limitada, preservando
limite 15, recusa de pergunta a NPC, instrução prévia, segunda frase ou menu.
Resposta exata L7 passa offline, commit/reinício/replay sem nova geração/RNG;
pergunta sobre decisão de Mara continua recusada sem estado/fonte parcial.
Não reclassificar o turno live rejeitado. Fonte e manifestos executados intactos.

22 testes novos da pergunta, 34 focados junto a L8 e regressão ampliada final
de 819 aprovados (sobrepostos), um aviso de depreciação preexistente. Não é
suíte integral verde. Testes L6/L7 usam manifestos temporários isolados e
comprovam recusa dos manifestos históricos diante do runtime corrigido.

L8 preparado separadamente, mesmo prompt v4/target/corpus/limites e 22 hashes.
Preflight CLI: 17 turnos sintéticos, zero chamadas reais, corpo máximo 13.614
bytes. AST PowerShell válido. Gate paid/live false; sem launcher, chave ou
trava live L8. Custo desta correção/preparação: USD 0. Alterações locais sem
commit/push. Observação de prosa "marcado como advertido" registrada somente
em `plan/observation-campaign-state-language-1.md`, sem nova frente/prioridade.

Conclusão delimitada proposta: L7 inconclusivo para campanha integral por falso
positivo de pergunta acionável, nenhum narrador admitido. Próxima proposta:
aceitar essa conclusão e autorizar L8 até 17 chamadas Luna low, teto estimado
adicional USD 0,15, 768 tokens/20.000 bytes, sem retry/fallback. Continue/prossiga
aprova a proposta delimitada conforme convenção; não exigir frase ritual.
Até lá, L8 fechado. Depois: revalidar, abrir Windows Terminal identificado,
confirmar prontidão, pedir entrada protegida e observar lote único/custo/gates;
fechar live ao fim. Não ler `.env*`, saves, chaves ou ambiente de terminal.

Evidência: `evals/narrator/reports/hybrid-campaign-luna-hyp-007-l7-2026-10-18.md`.
TASK-020/021 fecham correção/preparação; TASK-013/CAMP-24 e MVP continuam abertos.
Configuração recomendada para autorização/operação delimitada: Sol low.

## Checkpoint anterior — L6 aceito; L7 autorizado — 18/10/2026

O usuário respondeu "prossiga" à proposta de conclusão delimitada L6 e orçamento
L7. Pela convenção explicitamente definida em 18/10 e registrada em AGENTS.md,
isso aprova a proposta nos limites apresentados. Não manter esses aceites
pendentes nem pedir frase ritual. L6 fica aceito como inconclusivo para a
avaliação integral por rejeição real de q e lacuna de instrução, nenhum narrador
admitido. Não reclassificar seu turno rejeitado ou reabrir L6.

L7 autorizado: até 17 chamadas `gpt-5.6-luna`/`low`, teto estimado adicional
USD 0,15, 768 tokens de saída e 20.000 bytes/requisição, sem retry/fallback.
Somente paid/live do manifesto L7 foram ativados; prompt v4 e 22 hashes
preservados. Notas do manifesto e evidência abaixo registram a preparação
anterior com flags false; este checkpoint registra a autorização posterior.
Nenhuma admissão automática ou saldo transferido de lote anterior.

Próxima dependência: revalidar hashes/preflight e abrir Windows Terminal externo
via `wt.exe`, título L7, confirmar novo marcador/processo e pedir entrada
protegida. Não abrir dois lançadores, ler `.env*`/saves/chaves ou consultar
ambiente/memória de terminais. Depois da entrada: observar lote único, conferir
custo/gates/resultado e fechar live. TASK-013/CAMP-24 e MVP continuam abertos.

## Checkpoint anterior — resultado L6 e preparação L7 — 18/10/2026

HYP-007-L6 executou uma chamada real, zero turnos completos. Batch
`adf70b63-235c-457f-86df-b0625fad10e2`, parada `campaign_source_policy_failed`
no primeiro R-01/CAMP-EVAL-01. Custo final estimado USD 0,0007156, não cobrança
confirmada; 2.372 tokens de entrada e 201 de saída, usage disponível. Tempo
local observado: 4.491 ms de geração e 4.586 ms de turno, sem promessa de SLA.
Gate paid/live L6 fechado, trava mantida; não reutilizar os 16 slots restantes.
L5 permanece aceito. A entrada "feito" autorizou acompanhar L6, não aceita por
arrasto o resultado agora apresentado. Nenhum narrador/default admitido.

Diagnóstico observável: a pergunta q original tem 19 palavras; validador exige
até 15 e recusa `scene_player_prompt_too_long`. É rejeição real de formato,
não o falso positivo de sujeito de L5. `_realizes_rule` R-01 retorna true.
Mesma narrativa com apenas q substituído por "O que você faz agora?" passa
offline. Schema pede até 200 caracteres, mas prompt v3 não explicitava o teto
de 15 palavras. L6 não chegou ao R-03 e não prova a correção L5 em nova prosa.
Não reclassificar L6 ou atribuir toda a falha exclusivamente ao modelo.

Tratamento prospectivo: prompt v4 separado torna explícita a pergunta única,
aberta, até 15 palavras, terminada em ?, sem menu restritivo. Validador, schema,
política, RNG e persistência inalterados; prompt v3 e registros L6 intactos.
L7 tem runner/preflight/lançador/manifesto próprios, mesmo alvo/corpus/limites,
22 hashes e flags paid/live false. Preflight CLI: 17 turnos sintéticos, zero
chamadas reais, maior corpo 13.614 bytes; parser PowerShell válido.
13 testes focados e seleção relacionada de 127 aprovados (sobrepostos), um
aviso preexistente. Custo da preparação adicional: USD 0. Sem terminal ou chave
L7; alterações locais sem commit/push. Não é suíte integral verde.

Conclusão delimitada proposta: L6 inconclusivo para a campanha integral por
rejeição real do limite de q e lacuna de instrução, nenhum narrador admitido.
Próxima proposta: aceitar essa conclusão e autorizar HYP-007-L7, até 17 chamadas
Luna low, teto estimado adicional USD 0,15, 768 tokens/20.000 bytes, sem
retry/fallback. Não pedir frase ritual: continue/prossiga aprova esta proposta
nos limites apresentados, conforme convenção explícita. Até lá, gate L7 fechado.
Depois de autorizado: revalidar, abrir Windows Terminal identificado L7,
confirmar novo marcador, pedir entrada protegida e executar uma vez. Não ler
`.env*`, saves ou ambiente/memória do terminal; não repetir L6 nem transferir teto.

Evidência: `evals/narrator/reports/hybrid-campaign-luna-hyp-007-l6-2026-10-18.md`.
TASK-019 fecha somente diagnóstico/contrato/preparação; TASK-013/CAMP-24 e MVP
continuam abertos. Configuração recomendada para autorização/operação: Sol low.

## Checkpoint anterior — L5 aceito; L6 autorizado — 18/10/2026

O usuário esclareceu explicitamente que "continue" e "prossiga" aprovam a
proposta apresentada e autorizam seguir. Declarou também: "L5 foi aceito,
assim como o teto de L6". Não manter aceite L5 ou orçamento L6 pendentes.
Convenção registrada no AGENTS.md local, conservando limites/exclusões da
proposta anterior e sem transformar aprovação em autorização ilimitada.

L5 aceito em sua conclusão delimitada: inconclusivo por falso positivo de
atribuição NPC, nenhum narrador admitido. Não reclassificar seu turno rejeitado.
HYP-007-L6 autorizado até 17 chamadas `gpt-5.6-luna`/`low`, teto estimado
adicional USD 0,15, 768 tokens de saída/chamada e 20.000 bytes/requisição,
sem retry/fallback ou admissão automática. Ativados somente os flags paid/live
do manifesto L6 de 18/10; prompt v3, 22 hashes e parâmetros preservados.
As notas do manifesto e o relatório de prontidão descrevem a preparação
anterior; esta atualização registra a autorização posterior explícita.

Próxima dependência: revalidar preflight e abrir Windows Terminal externo via
`wt.exe` com título L6, confirmar novo marcador/processo e pedir entrada
protegida da chave. Não pedir novamente orçamento ou aceite. Não reutilizar
chave L5, inspecionar ambiente/memória de terminal ou ler `.env*`. Depois da
entrada: observar lote único, custo/gates/resultado e fechar autorização live.
TASK-013/CAMP-24 e MVP permanecem abertos; nenhum narrador/default admitido.

Terminal externo L6 aberto via `wt.exe`, título confirmado
`HYP-007-L6 - chave segura`. Novo marcador às 14:37:53 UTC de 18/10, PID 3876,
fase `awaiting_secure_credential`, zero chamadas antes da entrada, processo
ativo na última checagem. Preflight aprovado: 17 turnos sintéticos, maior corpo
13.415 bytes, 22 hashes válidos. Não abrir segundo lançador; aguardar a entrada
protegida e observar o mesmo lote. Sem redirecionar saída ou acessar chave.

## Checkpoint anterior — preparação L6 antes da confirmação explícita — 18/10/2026

O usuário respondeu "continue", autorizando continuidade técnica. Essa resposta
não é registrada como aceite formal narrativo/produtual: a revisão automática
de segurança recusou essa inferência. L5 continua com aceite delimitado pendente,
sem admissão de narrador, aprovação da campanha completa ou novo gasto. L5 fica
encerrado com três chamadas/dois turnos e USD 0,0022452 estimados, não cobrança
confirmada. Seus registros, prompt v3 e manifesto executado permanecem intactos.

O falso positivo foi corrigido localmente em
`api/scene_director_service.py::_mask_known_npc_gaze_report`. A política distingue
o destinatário em "Mara ergue os olhos para você e fala em voz baixa:" do sujeito
de uma ação imposta ao jogador. A prova é limitada ao gesto/reportagem local e,
para pronome, ao antecedente explícito e quadro não pessoal observado. Apenas
o verbo de fala comprovadamente do NPC é mascarado na análise; o texto entregue,
falas citadas, ações posteriores, agência e demais gates permanecem verificados.
Não é um resolvedor geral de linguagem nem reforma lexical. O texto exato L5
passa offline; isso não reclassifica a chamada histórica rejeitada.

Verificação: quatro positivos falharam antes; passaram 31 testes de reprodução
e contraprovas, incluindo commit/reinício/replay sem nova geração/RNG e recusa
atômica de promessa indevida do jogador. A seleção ampliada final aprovou 754
testes; checagem adicional L5/L6/reprodução aprovou 59 (sobrepostos, não somar).
Um aviso de depreciação preexistente; não é suíte integral verde. Os testes L5
agora usam manifesto temporário isolado, como L2/L3, e comprovam que o manifesto
executado recusa o runtime alterado; nenhum hash histórico foi atualizado.

L6 preparado separadamente, mesmo prompt v3, Luna low, corpus e parâmetros:
`evals/narrator/reports/hybrid-campaign-luna-l6-live-gate-2026-10-18.json`.
22 arquivos congelados; runner/preflight/lançador próprios e trava distinta.
Preflight CLI: 17 turnos sintéticos, zero chamadas reais, maior corpo 13.415
bytes; parser PowerShell válido. Gate paid/live false; sem launcher ou chave.
Custo final desta correção/preparação: USD 0. Alterações locais sem commit/push.

Próximo bloqueio humano: aceitar ou contestar explicitamente a conclusão
delimitada L5 e autorizar ou ajustar HYP-007-L6, até 17 chamadas de
`gpt-5.6-luna`/`low`, teto estimado adicional proposto USD 0,15, 768 tokens de
saída/chamada, até 20.000 bytes/requisição, sem retry/fallback. Nenhum saldo L5
é transferido. Depois: ativar apenas L6, revalidar hashes/preflight, abrir o
Windows Terminal via `wt.exe` com janela identificada, confirmar novo marcador
de prontidão e pedir entrada protegida. Não ler segredo/ambiente, pedir chave
no chat ou reabrir L5. Apresentar custo e resultado e fechar live ao fim.

TASK-017/018 registram correção e prontidão, não admissão. TASK-013/CAMP-24 e
MVP continuam abertos. Relatório:
`evals/narrator/reports/hybrid-campaign-luna-hyp-007-l6-readiness-2026-10-18.md`.
Configuração recomendada para autorização e operação delimitada: Sol low.

## Checkpoint anterior — L5 encerrado; conclusão delimitada proposta — 18/10/2026

HYP-007-L5 executado após entrada protegida confirmada pelo usuário. Lote
`7b94103b-f600-4f25-a370-0efb761429cf`: três chamadas reais, dois turnos completos,
parada em `campaign_source_policy_failed` no primeiro R-03 de CAMP-EVAL-02.
CAMP-EVAL-01 completou ajuda R-01 e resgate R-05, com desfecho `preserved`.
Custo final estimado USD 0,0022452, 7.656 tokens de entrada e 595 de saída;
três chamadas com usage, sem confirmação de cobrança/cache/taxas/impostos.
Não houve retry/fallback. Não reutilizar os 14 slots não executados.

O hash de records foi conferido contra summary. Reprodução offline: realização
R-03 passa, mas o detector genérico aponta `scene_player_agency_violation`,
`undeclared_player_action`, sujeito `voce`, conceito `social`. O trecho de Mara
"Ela ergue os olhos para você e fala em voz baixa" dispara o falso positivo;
nomear Mara mantendo a coordenação não resolve. Substituir só esse trecho por
"Mara diz em voz baixa" faz a mesma proposta passar localmente. Não houve
alteração do texto live, detector, prompt ou critérios para reclassificar o turno.

Conclusão técnica proposta: L5 inconclusivo por falso positivo de atribuição NPC;
dois turnos admitidos não comprovam os oito percursos ou admissão do narrador.
O aviso R-03 não foi admitido. Nenhum narrador/default admitido; CAMP-24 e
TASK-013 continuam abertos. Próximo checkpoint humano: aceitar ou contestar essa
conclusão delimitada, sem inferir aprovação narrativa integral ou novo orçamento.
Depois, tratar prospectivamente a reprodução delimitada, preservando o lote
executado e sem abrir reforma lexical geral ou nova avaliação paga por arrasto.

Gate L5 de 18/10 fechado: paid/live false, trava de execução mantida. Marcador
`ready.json` é histórico pré-credencial, não prova de espera atual. Não relançar
L4/L5, solicitar chave ou ler memória/ambiente do terminal. Relatório:
`evals/narrator/reports/hybrid-campaign-luna-hyp-007-l5-2026-10-18.md`.
Verificação de fechamento: 33 testes focados aprovados (preparação L5, política
de campanha e custo), um aviso de depreciação preexistente. Alterações locais,
sem commit/push. Configuração recomendada para revisar o resultado: Sol high.

## Checkpoint anterior — L5 autorizado e entrada protegida — 18/10/2026

O usuário declarou "Novo lote pago autorizado. Continue", aprovando a proposta
HYP-007-L5 abaixo: até 17 chamadas Luna low e teto estimado adicional USD 0,15,
sem retry/fallback. Somente `paid_ceiling_authorized` e
`live_inference_authorized` do manifesto L5 de 18/10 foram ativados. Conteúdo,
prompt, 22 hashes, preços, limites e manifestos históricos não foram alterados.
As notas de preparação no manifesto e o relatório de prontidão descrevem o
momento anterior à aprovação; este checkpoint registra a autorização posterior.
Não pedir novamente orçamento L5. Próxima dependência: entrada protegida da
chave no lançador PowerShell externo L5, após revalidar o preflight. Não ler
credencial, `.env*` ou pedir chave no chat. Não iniciar um segundo lançador
se o marcador `eval-results/preflights/hybrid-campaign-luna-l5-ready.json`
identificar processo L5 ainda ativo. Depois da entrada: observar artefatos
sintéticos, verificar custo/gates/resultado e fechar autorização live ao fim.
Nenhum narrador/default admitido; TASK-013/CAMP-24 continuam abertos.

Lançador externo reaberto em 18/10, PID 15384. Marcador de prontidão confirmou
`awaiting_secure_credential`, zero chamadas e corpo máximo 13.415 bytes após
preflight próprio. Processo ainda ativo na última checagem. Não abrir outra
janela por arrasto: aguardar a entrada protegida e observar o mesmo lote.
Não houve redirecionamento de saída do terminal ou acesso à credencial.
O processo anterior 13876 foi encerrado sem trava live ou lote criado depois
de o usuário informar ausência do prompt. O relançamento via `wt.exe` confirmou
janela Windows Terminal intitulada `HYP-007-L5 - chave segura` e novo marcador
de prontidão do PID 15384. Não usar o marcador antigo como prova de visibilidade.

### Preparação concluída antes da autorização acima

O usuário declarou: "O resultado de L4 foi aceito. Continue". Registrar o aceite
delimitado de HYP-007-L4: duas chamadas, um turno completo e parada de política
R-05; custo histórico estimado USD 0,0014972, sem confirmação de cobrança.
Isso não comprova campanha completa nem admite narrador/default. Não repetir L4.

A preparação prospectiva HYP-007-L5 foi renovada com o runtime pós-auditoria:
novo manifesto `evals/narrator/reports/hybrid-campaign-luna-l5-live-gate-2026-10-18.json`,
22 arquivos congelados incluindo a barreira local Host/Origin, prompt v3 inalterado.
Os manifestos L4/L5 de 03/10 permanecem byte a byte intactos. O runner e o lançador
L5 apontam apenas para o novo manifesto e recusam drift, retry/fallback e admissão
automática. L5 é sintético, opt-in e separado dos saves existentes.

Passaram 15 testes L5 e, depois, 78 testes relacionados que incluem esses 15.
Preflight CLI: 17 turnos sintéticos, zero chamadas reais, maior corpo 13.415 bytes;
parser PowerShell válido. Sem leitura de credencial, launcher executado ou trava
live criada. Custo final desta preparação: USD 0. A suíte integral permanece
com as limitações históricas da consolidação Git; não foi repetida nesta etapa.

Próximo bloqueio humano: autorizar ou ajustar HYP-007-L5, até 17 chamadas de
`gpt-5.6-luna`/`low`, teto estimado adicional proposto USD 0,15, 768 tokens de
saída/chamada, até 20.000 bytes/requisição, sem retry/fallback. Os flags paid/live
continuam false; não solicitar chave antes dessa autorização. Depois: ativar
somente este gate, abrir PowerShell externo para entrada protegida, executar uma
vez e apresentar custo/gates/resultado para julgamento humano. Autenticação e
saldo atuais não foram consultados. Não transferir orçamento de lotes anteriores.

TASK-016 registra a prontidão técnica, mas TASK-013 e CAMP-24 continuam abertos.
Evidências e comandos: `evals/narrator/reports/hybrid-campaign-luna-hyp-007-l5-readiness-2026-10-18.md`.
Alterações desta preparação são locais, ainda sem commit/push. Preservar branch
de implementação e checkout original; GitHub principal não foi alterado aqui.
Configuração recomendada para a autorização/operação delimitada: Sol low;
o alvo da API continua Luna low. Não iniciar bandeja/UI/ficha antes deste gate.

## Checkpoint anterior — promoção GitHub concluída em 18/10/2026

O usuário autorizou consolidar a evolução do worktree na branch principal do
repositório `CHCLopes/Agente-Storyteller-VampireTheMasqueradeV5`. Preservar
`master`, seu histórico e o checkout original. Rota: commit da evolução,
publicação da branch de implementação, criação de `main` a partir da `master`
remota, integração por PR e mudança de default apenas após merge verificado.
Sem force-push, exclusão de branches, leitura de `.env*` ou novo gasto de LLM.
Login GitHub verificado. Snapshot publicado em `e31f679`; PR #1 integrado em
`main`, merge `73f1f2a1c4bf22195a8ce84f49a857c74267bab0`. A API GitHub e o HEAD
remoto confirmaram `main` como default. `master` permanece em `5e56382`, e o
checkout original não foi modificado. Sem force-push, exclusão de branches ou
contorno de proteções. A suíte
ampla terminou: 8.719 aprovados, 333 skips, 286 falhas e 61 erros em 1h41min19s.
Todas as 347 ocorrências foram classificadas: 342 por schema histórico e suas
cascatas, quatro por manifestos L4/L5 e uma por sidecars SQLite Windows.
Passaram novamente 252 testes críticos e 258 frontend, além de tipos e build.
Git concluído; a suíte integral e o lint não estão verdes. Isto é consolidação
de desenvolvimento, não release. As duas modificações locais em `.env.example`
permanecem preservadas e fora dos commits. Fontes e evidências anteriores não
foram reescritas. Nenhuma inferência de provedor foi executada nesta promoção.
Comprovante, evidências e limitações: `docs/repository-promotion.md`. O worktree
de implementação continua na branch `codex/planejamento-agente-storyteller-v5`,
alinhada à nova `main`; não trocar ou atualizar o checkout original por arrasto.
O MVP continua aberto; nenhum narrador/default está admitido. A autorização
Git não aceitou L4, não liberou L5 e não modificou o backlog de produto. Ao fim
da promoção, faltavam aceite delimitado L4 e renovação da preparação prospectiva;
ambos foram atendidos pelo checkpoint vigente acima. Autorização própria de
gasto L5 continua pendente; não pedir chave por arrasto.

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

## Próximo passo histórico — 03/10 e 16/10; substituído pelo checkpoint vigente acima

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
