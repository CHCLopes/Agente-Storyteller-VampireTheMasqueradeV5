---
goal: Distinguir admissão de progressão e influência do contexto na escolha do gerador
version: 1
date_created: 2026-09-10
last_updated: 2026-09-10
owner: Agente Storyteller
status: 'Completed'
tags: [evaluation, narrative-source, diagnostic, synthetic]
---

# Diagnóstico de progressão da fonte narrativa

O lote progressing 19b93f22 concluiu duas chamadas, commits e replays. O critério
narrativo anterior não foi satisfeito: a poeira só muda ligeiramente de posição,
enquanto o texto reforça quietude e repete a pergunta. A hipótese SYSTEM adicional
fica encerrada sem melhoria demonstrada. Não repetir o lote ou reclassificar gates.

## 1. Primeiro diagnóstico: contraprova de admissão offline

Antes de nova observação, uma continuação autorada terá acontecimento substancial
com luz/ventilação já apresentados, sem impor reação ao jogador. O fluxo atual
deverá admitir e conservar a fonte por inteiro. Essa prova não é geração Groq,
não resolve capacidade do modelo e não substitui avaliação de qualidade ao vivo.

Escopo autorizado: somente novo tests/test_narrative_source_progression_admission.py
e documentação relacionada. Não modificar core, gates, prompt, limites ou saves.

- Um caso positivo: coordenador real, SQLite temporário e FakeLLM, n1 observado
  identificado como fixture sintética e n2 autorado; dois commits, fonte anterior
  integral no USER2, recuperação após reinício e replay sem gateway/chunk novo.
  Cena, estado e relações preservados; revisão/eventos de declaração avançam
  normalmente. Nenhuma novidade da prosa promovida a fato canônico.
- Três negativos independentes: ação forçada, emoção forçada e conteúdo mecânico
  interno (pool de dados); recusa antes do segundo commit/fonte, sem afrouxar validador.
- Se o positivo falhar, diagnosticar a razão antes de preparar outra chamada.
  Falha de fixture ou de política será registrada conforme a evidência.
- Se passar, a admissão permite ao menos essa progressão concreta. Isso não
  prova que toda boa narrativa passa ou que o gerador sabe produzi-la.

## 2. Próximo diagnóstico condicionado à prova local

Se a contraprova passar, preparar observação de duas condições sintéticas
independentes, com SYSTEM progressing inalterado e fontes anteriores autoradas.
Uma fonte descreve estado estável; a outra, mesmos elementos com acontecimento
em curso. O jogador aguarda em ambas. Esse teste procura saber se a presença de
um movimento já iniciado muda a resposta; não é novo diretor, evento canônico,
injeção no jogo, correção automática de narrativa ou repetição do lote encerrado.

Os textos, identidades, corpos, critérios e parada devem ser congelados antes de
qualquer chamada. Fontes autoradas precisam de origem experimental explícita,
nunca provenance Groq fabricada. Preferir diagnóstico puro de geração/admissão
com o perfil existente, sem criar seed de campanha ou migrar a aplicação.

Limites de preparação: até 2 chamadas independentes, uma por condição, 768 tokens
cada, total 1536, temperatura 0.65, reasoning none, alvo Groq/Qwen existente,
espera inicial 60 s, intervalo mínimo 60 s, prazo 60 s. Sem retry/reparo/fallback.
Indisponibilidade/credencial/rota interrompem o lote; rejeição de conteúdo de uma
condição não invalida a independência da outra. Critérios autorados separados dos
gates. Uma observação por condição é exploratória, não estimativa causal robusta.

## 3. Tarefas

| Tarefa | Entrega | Concluída |
|---|---|---|
| TASK-001 | Registrar análise do lote progressing e plano antes de alterar arquivos. | Sim |
| TASK-002 | Contraprova offline positiva e três negativos delimitados; revisão e evidência. | Sim |
| TASK-003 | Se positivo, materializar fixtures/avaliador/lançador separados e conferir isolamento de condições. | Sim |
| TASK-004 | Verificação offline, preflight protegido, relatório e próximo passo na retomada. | Sim |

## 4. Limites persistentes

Autorização contínua cobre estas observações necessárias. Credencial somente por
entrada protegida direta após toda preparação. Não recuperar chave existente.
Preservar artefatos e executáveis anteriores; nenhuma aprovação CAP-001, runtime,
qualidade geral, novo NPC, produtor anterior ao RNG ou progressão canônica.

Limitação verificada no recorte: a contraprova mecânica usa conteúdo interno explícito,
não detector geral de dano/gasto inventado quando outcome é unresolved. Não alterar
essa política por arrasto; nenhuma ocorrência desse tipo foi observada neste lote.

## 5. Corpus e contrato previstos para o diagnóstico puro

Corpus novo: `evals/narrator/source_context_cases_v1.json`. Os dois textos têm
prefixo idêntico; somente o último período altera o estado do som/luz. Condições
`steady` e `event_started`, nessa ordem, uma chamada independente por condição.
Esses rótulos ficam nos metadados; o USER contém a fonte atribuída, sem instrução
de experimento dentro dela. Fonte do primeiro caso não é resposta live; a resposta
da primeira condição não alimenta a segunda.

SYSTEM: narrative-source-progress-v1, sem alteração. Mesmo perfil de aplicação,
schema n/q, alvo/modelo e parâmetros. USER usa contexto de uma fonte autorada,
player_input, identidade opaca de turno e server_facts vazio; não simula um commit
ou fato de campanha. IDs da fonte são marcados como autoria sintética, sem criar
InvocationEvidence Groq para a autoria. Respostas reais recebem evidência própria.

Novos arquivos previstos: scripts/evaluate_source_context.py;
scripts/run_groq_source_context_probe.ps1; tests/test_source_context_probe.py;
tests/test_source_context_probe_wrapper.py; relatório source-context-preparation.
Reutilizar o observador seguro congelado por composição; nenhum monkeypatch de
runtime ou alteração de executável histórico. Este diagnóstico não reivindica
retenção, commit ou replay da aplicação. Não usar SQLite nem save.

Critério autorado principal: continuação desenvolve acontecimento observável
substantivo a partir da fonte, com abertura para o jogador; mera recapitulação,
repetição do pulso já dado ou comentário sobre passagem do tempo não basta.
Preservar agência, local/elenco e causas não informadas. Comparar resultados como
observação exploratória: duas amostras únicas não demonstram incapacidade geral,
causalidade robusta ou necessidade de um diretor no produto.

Parada: cada condição tem no máximo um envio. Falha de autorização, limite,
indisponibilidade, prazo, rota ou erro local encerra o restante; rejeição de schema
ou política de conteúdo pode seguir para a segunda condição independente. Registrar
skip explícito quando houver parada. Sem retry, diagnóstico extra ou fallback.

Contraprova concluída: 4 testes passaram, sem falha ou skip; 55 fingerprints
preservados. Prova e limites: `evals/narrator/reports/source-progression-admission-2026-09-10.md/json`.

Preparação concluída: 74 testes distintos finais do diagnóstico passaram;
review encerrado e -PreflightOnly real exit 0. Relatório:
`evals/narrator/reports/source-context-preparation-2026-09-10.md/json`.
Status Completed refere-se à preparação e à contraprova, não à observação live.

Observação cc09080a encerrada: 2 chamadas/gates aceitos; critério autorado integral
não satisfeito em ambas. event_started trouxe novidade parcial com fechamento causal
indevido. Prova: `evals/narrator/reports/source-context-observation-cc09080a-2026-09-10.md/json`.
Não repetir/reclassificar o lote. Próximo incremento local: consulta tipada de operação retida.
