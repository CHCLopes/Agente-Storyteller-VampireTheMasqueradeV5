---
title: Fronteira entre efeito preparado e narração
category: Architecture
status: Investigação offline concluída; proposta de implementação pendente
priority: High
timebox: Uma rodada offline delimitada de investigação e contraprovas
created: 2026-10-21
updated: 2026-10-21
owner: Produto Agente Storyteller
tags: [technical-spike, narrator, validation, DEC-NARR-VALID-001]
---

# DEC-NARR-VALID-001 — opção A e proposta A1

O humano escolheu **A** com “Continue em A”. Está aprovada a investigação interna,
o desenho e as provas offline; a arquitetura A1 abaixo continua **proposta**.
Nenhum runtime, schema, prompt live, catálogo ou gate pago foi alterado.

**Recomendação:** experimentar um perfil B v2 que componha na aplicação as
afirmações críticas e as falas essenciais de Mara, e deixe à LLM trechos curtos
de expressão narrativa em posições delimitadas. A composição garante presença
e identidade dos trechos autorados. **Não garante ausência de contradições em
todo texto livre.** A admissão continua exigindo avaliação semântica/experiência.
Se a exigência humana for eliminar esse risco por construção em toda a saída,
a alternativa é restringir toda a saída a realizações autoradas; isso reduziria
a liberdade solicitada e exige uma decisão de produto diferente.

## Questão e resultado

Como manter a autoridade canônica e a naturalidade sem depender de palavras
soltas para provar quem fez o quê? A evidência favorece separar realização
crítica, expressão livre e julgamento semântico, em vez de aumentar a lista de
equivalências como solução principal.

A investigação termina nesta proposta revisável. A implementação só começa
após aprovação humana de A1 e de seu risco residual. Não há prazo de calendário
imposto nem novo lote live previsto neste estudo. Pesquisa externa e adoção de
código de outros projetos continuam fora do escopo.

## Estado inspecionado

- Worktree: `C:/Users/skate/.codex/worktrees/b008/AgenteStoryteller`.
- Branch: `codex/planejamento-agente-storyteller-v5`.
- HEAD inicial: `f8e1620b4fc96e88ef751534ac7d856f7a9a6d05`.
- Alterações preexistentes: `.env.example` e `api/.env.example`, somente nomes
  e estatística vistos no Git; conteúdo não lido nem alterado neste trabalho.
- `state/PROJECT_STATE.md` ausente; nenhum novo sistema de estado criado.
- Publicação documental posterior ao handoff já registrada na retomada e
  preservada. Nenhum commit, push, merge ou alteração no checkout original.
- L83 permanece false/false; os 22 hashes de implementação conferem com o
  manifesto. Este estudo não acionou L83 nem inferência.

## Evidência e limites

Protocolo prospectivo, script e resultado estão em
`../spikes/validation-boundary-2026-10-21/`:

- `prospective.md`: hipótese, amostra fixa e parada anteriores à execução.
- `probe_validation_boundary.py`: diagnóstico reproduzível do validador atual.
- `observation-2026-10-21.json`: textos completos, expectativas autoradas,
  decisões observadas, pacotes causais, hashes e inventário histórico.
- `baseline-2026-10-21.xml`: testes existentes selecionados.

**Uma execução do diagnóstico:** 24 textos (seis controles positivos e 18
contrastes). Nove textos inválidos aceitos e um texto válido rejeitado. Os seis
controles positivos passaram; nove controles estruturais foram rejeitados como
esperado (seis IDs de efeito falsos e três perguntas em desfecho). Não transformar
essas contagens numa taxa de estabilidade: é amostra adversarial autorada.

| Prova | Expectativa autoral | Resultado observado |
|---|---|---|
| `task.goal_synonym` | Rejeitar “Sua missão é investigar o conteúdo, não preservar o registro” | Aceito |
| `task.npc_extra_lore` / `refusal.invented_oath` | Rejeitar juramento/motivo não preparado | Ambos aceitos |
| `refusal.direct_natural` | Aceitar “Essa identidade eu não revelo”, dirigida à pergunta sobre a fundadora | Rejeitado por efeito não realizado |
| `refusal.authored_direct` | Aceitar “Não vou divulgar essa identidade” no mesmo contexto | Aceito |
| `warning.denied_warning` | Rejeitar aviso só sobre frio acompanhado de “Não há risco para o documento” | Aceito |
| `preserved.reopen_synonym` / `preserved.reopen_care` | Rejeitar transporte/cuidado novo no epílogo | Ambos aceitos |
| `partial.dry_synonym` | Rejeitar “As folhas já secaram por completo” | Aceito |
| `partial.restoration_synonym` | Rejeitar “Todas as linhas voltaram a ficar legíveis” | Aceito |
| `abandoned.invented_emotion` | Rejeitar vergonha atribuída ao jogador | Aceito |
| `warning.wrong_actor` | Rejeitar “Você abre a porta” sem declaração | Rejeitado |
| `partial.wet_acknowledgment` / `partial.negated_dry` | Aceitar dano conservado/negação de secagem | Ambos aceitos |

As frases usam o **validador completo** `validate_campaign_source_proposal`, não
somente `_realizes_rule`. Contextos sintéticos puros começam em revisão zero;
o contexto `partial` começa com registro molhado. Não são replays históricos
nem prova de commit das frases inválidas. Não corrigimos essas lacunas nesta
opção A: são evidência para decidir a fronteira, preservada sem ajuste oportunista.

**86 testes existentes passaram**, em 21,46 s, com um aviso preexistente de
`python_multipart`. Seleção: progressão, preparação/cápsula, perfil, oito
trajetórias, integração/storage, fala direta, secagem e objetivo/epílogo.
Inclui reconstrução, replay, consequência, posição, rollback e ausência de
rolagem/chamada adicional nos cenários cobertos. Não é suíte integral de release,
teste do v2 proposto ou medição de UX. Não somar com os 91/987 históricos.

Inventário read-only de L41–L82: **42 arquivos de records, 396 chamadas e 356
turnos completos**, com SHA-256 por arquivo. Isso confere as contagens do
checkpoint; não significa reavaliação semântica integral das 396 respostas.
As versões variam e o histórico permanece imutável. Inferência desta etapa:
**zero chamadas, USD 0**; nenhuma nova cobrança foi consultada.

## Mapa da fronteira atual

1. `api/campaign_progression_service.py:140` prepara efeito vinculado a sessão,
   operação, revisão, estado anterior/posterior e hash. `:319` constrói o pacote.
   A LLM não resolve o estado. Essa base é preservada.
2. `api/campaign_source_profile.py:36` recebe `n`, `q` e `realized_effects`.
   `:192` confere igualdade dos efeitos, contexto, pergunta e política geral;
   `:96` procura grupos lexicais/exceções para realização crítica.
3. `api/scene_director_service.py:884` valida continuação; `:1913` participa da
   correspondência lexical de ações. Verbos/nomes/contexto local não constituem
   uma interpretação geral de sujeitos, negação, modalidade ou consequência.
4. `api/campaign_source_turn.py:86` e `api/campaign_source_storage.py:718`
   revalidam envelope, preparação, fonte, fatos/eventos, operação e revisão.
   Trocar somente o prompt ou relaxar uma checagem rompe a intenção dessa cadeia.
5. `api/campaign_source_profile.py:229` atribui a projeção à fonte narrativa;
   `:251` já expõe `semantic_truth_assessed=False` no contexto. Uma apresentação
   composta precisa de proveniência segmentada para não atribuir à LLM texto da
   aplicação nem promover o texto livre a evidência canônica.

Observação de limite existente: `campaign_source_execution_service.py:205`
entrega `on_chunk` antes de `commit_turn` (`:209`). A atomicidade persistida não
equivale a entrega visual transacional. Não foi alterado; o v2 deve conservar o
protocolo existente e testar falhas, sem prometer retirada de texto já entregue.
Redesenhar essa ordem é um trabalho separado se necessário, não uma mudança
implícita deste contrato.

## Alternativas comparadas

| Alternativa | O que melhora | O que continua sem prova | Avaliação |
|---|---|---|---|
| Prosa integral + atores/spans declarados pela LLM | Localiza alegações e auxilia auditoria | A LLM pode apontar um trecho contraditório com IDs corretos | Insuficiente como correção central |
| **A1: composição crítica + expressão livre delimitada** | Fatos obrigatórios, referentes e falas essenciais aparecem em texto produzido pela aplicação; diagnóstico por segmento | Expressão livre ainda pode criar fatos, impor ações ou contradizer o núcleo | Recomendada para experimento opt-in, com risco explícito |
| Toda saída composta de alternativas autoradas | Conteúdo exposto pode ser validado por construção dentro do catálogo revisado | Correção editorial do catálogo e naturalidade ainda exigem avaliação; variedade finita | Alternativa se garantia integral tiver prioridade sobre liberdade |

Não adicionar outro LLM julgador/resolvedor. Marcar um trecho como `npc_line`
não o torna seguro: “As folhas já secaram” continua uma afirmação física, mesmo
dita por Mara. Tampouco um `effect_ref` prova implicação semântica. Os dois
exemplos de spans no JSON têm offsets exatos e o mesmo efeito; apenas um é fiel.
Essa é uma demonstração lógica de insuficiência, não benchmark de um parser novo.

## Contrato A1 proposto para aprovação

### Preparação confiável e renderização

Criar **novo perfil opt-in**, de nome proposto `campaign-source-local-v2`, para
sessões sintéticas novas. O efeito e o RNG continuam nos módulos existentes.
Uma etapa pura, determinística, prepara um plano de realização a partir do
efeito retido, da intenção classificada e dos fatos públicos. Não lê prosa
gerada para decidir fatos.

O plano retido contém versão do conteúdo/renderizador, identidade da operação,
revisão, `preparation_sha256`, mapa de entidades e uma sequência ordenada de
segmentos. Cada segmento crítico fixa:

- `segment_id`, `effect_refs` e referências de suporte da preparação;
- ator/sujeito, objeto/referente e, quando houver fala, locutor;
- afirmação, polaridade, modalidade e fase temporal;
- texto natural autorado selecionado por regra/estado/intenção;
- visibilidade e papel: consequência, resposta essencial ou encerramento.

Esses campos são produzidos pela aplicação. A LLM não pode escrever ou substituir
texto crítico, ator, estado, objetivo, destino ou ordem. O renderizador monta os
segmentos críticos exatamente uma vez, calcula spans sobre a string final
normalizada e associa cada trecho à origem real. O hash protege integridade,
não certifica significado de texto livre. A aplicação também produz a pergunta
aberta quando ativa e string vazia quando terminal.

### Parte proposta pela LLM

Forma documental proposta (não implementada):

```json
{
  "protocol": "campaign-source-expression-v2",
  "plan_sha256": "<hash do plano retido>",
  "slots": [
    {"slot_id": "mara.reaction", "text": "Ainda dá tempo."}
  ]
}
```

O plano enumera os slots permitidos e fixa interlocutor, posição, tema, tamanho
e restrições. A proposta devolve cada slot exatamente uma vez, podendo usar
texto vazio onde o plano permita. Sem `n` integral, `q`, lista autoral de efeitos,
estado novo, speaker ou campos extras. No recorte inicial, no máximo dois slots:
uma passagem atmosférica curta e uma reação curta de Mara. Limites propostos:
até 240 caracteres por slot; resultado final mantém 30–150 palavras e o limite
de 1600 caracteres da narração. O texto crítico deve poder satisfazer sozinho
os requisitos de conteúdo, sem encher frases para compensar a LLM.

O texto de cada slot é plain text, com normalização única e sem marcação que
possa criar outro locutor. Aspas e identificação de Mara são feitas pelo
renderizador. Nada é exibido antes da composição e da validação completa.
O modelo pode variar ritmo, escolha de palavras e reação compatível; só recebe
fatos públicos necessários. Segredo, justificativa não catalogada, novas tarefas,
emoção/ação do jogador, efeito físico e resultado mecânico ficam proibidos.

**Limite explícito:** essas proibições semânticas sobre slots livres não ficam
provadas por schema, tamanho, prompt ou whitelist de slots. Os guards atuais
continuam defesa complementar, e uma rubrica offline/live cobre o significado.
Não remover guards de agência/sigilo/desfecho por existir um núcleo determinístico.
Uma checagem precisa de realização dos segmentos críticos substitui somente a
busca de palavras desses segmentos; o restante permanece sujeito à política e
à avaliação qualitativa. Falha detectada reprova o turno inteiro, sem aparar o
texto, regenerar ou usar narrativa substituta silenciosamente.

### Cobertura editorial necessária

| Contexto | Conteúdo crítico produzido pela aplicação |
|---|---|
| R-01 tarefa, primeiro/repetido | Preservar registro, risco/posição atuais, superfície seca quando pertinente; não trocar objetivo por examinar |
| R-01 pedido concreto de ajuda | Resposta à ajuda conforme capacidade catalogada; não realizar resgate de Mara sem efeito preparado |
| R-02 | Recusa contextual direta sem identidade, juramento, recompensa ou motivo inventado |
| R-03 | Risco aumenta, registro ainda seco; sujeito ambiental distinto do jogador |
| R-03B | Água molha o registro na bancada; dano presente, sem perda integral |
| R-04 | Texto irrecuperável, posição conservada e conclusão em perda |
| R-05 | Resgate autorizado, destino preparado, integridade preservada e conclusão |
| R-06 | Resgate parcial, destino preparado, dano conservado e conclusão; sem secagem implícita |
| R-07 | Conteúdo parcial recuperado pelo exame e resultado mecânico retido; objeto não transportado |
| R-08 | Falha em recuperar conteúdo; wet não terminal ou lost terminal conforme estado anterior |
| R-09 | Desistência e posição do registro; nenhuma imobilidade/emoção imposta ao jogador |

Seleção editorial deve depender de regra completa, intenção, antes/depois,
conhecimento prévio e método suportado. Um dicionário só por `R-xx` é insuficiente
para R-01 e R-08. Entradas ambíguas/não suportadas continuam na fronteira atual;
este desenho não amplia o classificador nem generaliza toda a campanha.

Exemplos autorados de apresentação crítica, para avaliar a proposta:

> Mara indica a bancada: “A água ameaça o registro. A superfície seca fica na
> Galeria; você pode levar o documento até lá para protegê-lo.” O registro
> permanece na bancada baixa do Arquivo.

> Mara responde: “Essa identidade eu não revelo.” A água ainda ameaça o registro
> sobre a bancada baixa do Arquivo. O documento continua no mesmo lugar, e Mara
> mantém a resposta dirigida à sua pergunta.

> Você retira o registro molhado da bancada baixa e o coloca na superfície seca
> da Galeria. O dano permanece; apenas o conteúdo ainda legível foi preservado.
> Mara diz: “O que ainda dava para ler está preservado.”

Os exemplos não são saídas Luna, não foram apresentados em navegador e não são prova
de naturalidade futura. Nenhum controle interno aparece na fala do jogador.

### Persistência, histórico e compatibilidade

Versionar configuração, proposta, cápsula/plano, envelope, política da fonte e
leitor por contrato retido; não alterar os Literals v1 para aceitar v2 por
similaridade. Sessões antigas e preparações pendentes continuam no contrato
original. Sem migração de saves, reinterpretação de prosa antiga ou upgrade de
uma operação em andamento. Nenhum resultado histórico passa a ser aceito por A1.

Persistir texto final, spans, proveniência por segmento, versão/hash do plano,
vínculo ao efeito e resposta original do modelo conforme política de evidências.
Texto composto tem origem na aplicação; slots têm origem na invocação da LLM.
Memória canônica continua derivada de eventos validados. Contexto futuro pode
reter a apresentação como fonte atribuída com suas origens, sem transformá-la
em autorização de mutação.

Replay deve devolver os bytes de apresentação persistidos e validar o contrato
retido; não renderizar novamente com o catálogo atual, chamar modelo ou rolar.
Manter CAS/commit atômico e falha fechada em troca de operação, plano, efeito,
fonte, posição, revisão ou versão. Os armazenamentos JSON existentes sugerem
que DDL novo pode ser evitado; isso é hipótese de implementação, não garantia.
Qualquer necessidade de migração ou alteração da ordem de entrega volta ao humano.

## Implementação proposta após aprovação

1. Especificar v2 e cobrir a matriz editorial acima com funções puras e exemplos
   autorados; novos módulos para plano/renderização, sem alterar fatos/RNG.
2. Integrar perfil, cápsula, envelope, projeção/contexto e dispatch de storage
   por versão. Preservar leitores v1 e testes de rejeição de versões cruzadas.
3. Executar as oito trajetórias/17 turnos e as variantes de estado ausentes da
   matriz principal, especialmente R-01 repetido/ajuda e R-08 sobre wet.
4. Contraprovas: omissão/duplicação/ordem, ID de outra operação, hash/revisão,
   ator/ref/alvo trocado, negação/hipótese/citação, invenção de lore, dano,
   objetivo, destino, recuperação integral, nova tarefa, agência/emoção,
   Unicode/spans e contexto contaminado por fala anterior. Preservar pares fiéis.
5. Testar preparação/pausa/reinício/replay, falha de geração/validação/entrega,
   rollback/CAS, proveniência mista, ausência de RNG/chamada extra e tamanho
   real do request. Nenhum teste pode chamar rede ou carregar dotenv.
6. Só depois preparar um lote novo com hipótese v2, hashes, limites e primeira
   falha. Não reutilizar L83/v23 como se medisse esse contrato. Autorização
   contínua <= USD 0.15 por lote permanece; admissão/default/MVP continuam gates.

Critério do experimento: demonstrar as garantias estruturais e a presença dos
fatos críticos, medir o risco semântico residual e avaliar naturalidade. Uma
contradição livre aceita impede declarar que A1 resolveu toda a fidelidade.
O primeiro ciclo v2 não remove a avaliação qualitativa nem fecha CAMP-24.

## Decisão solicitada

**Aprovar A1 para implementação experimental opt-in**, com composição crítica
e fala essencial autoradas, expressão livre curta e risco residual explícito.
Isso altera a divisão de autoria/persistência da apresentação e exige aprovação
conforme o gate restaurado e o AGENTS.md. A seleção anterior de A não aprovou A1.

Configuração recomendada para decidir/revisar: **Astra high**, pelo conflito entre
liberdade, autoridade e compatibilidade. Após aprovação, **Sol high** é adequado
à integração de persistência e proveniência; operações e testes mecânicos podem
usar Sol low. Nenhuma troca automática de modelo foi realizada.

## Reprodução

Na raiz do worktree, usando a venv existente e um caminho de saída novo:

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
& .\.venv\Scripts\python.exe evals/narrator/spikes/validation-boundary-2026-10-21/probe_validation_boundary.py --root . --output eval-results/validation-boundary-new-observation.json
```

O script recusa sobrescrever uma observação. A rede é bloqueada no diagnóstico;
pytest usa o bloqueio existente em `tests/conftest.py`. Nenhum segredo é lido.
Artefatos de entrada do estudo permanecem congelados no resultado, inclusive
hash do script. Não repetir apenas para elevar a contagem ou transformar a
amostra autorada em evidência estatística.
