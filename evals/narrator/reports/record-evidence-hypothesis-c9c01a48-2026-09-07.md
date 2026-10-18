# Proposta delimitada — derivação com origem e modalidade explícitas

Data: 07/09/2026. Status: **desenho documental para decisão; não implementado**.
Origem: [análise c9c01a48](record-derivation-observation-c9c01a48-2026-09-07.md).
Não aprova novas chamadas, mudança de produto, validador semântico de runtime,
API paga ou promoção CAP-001.

## Pergunta investigável

Quando precisa identificar a origem e a modalidade de cada afirmação derivada,
o candidato conserva a incerteza nos registros finais dos dois casos fixos,
sem usar metadados para justificar ampliações ausentes da fonte?

A derivação isolada anterior conservou os textos de entrada e foi admitida,
mas a pergunta sobre “quem está observando” continuou pressupondo a existência
da observação. O novo mecanismo tornaria visível a associação que o candidato
declara entre afirmação, origem e modalidade. Sua função seria diagnosticar a
transformação; não se presume que acrescentar uma justificativa a corrigirá.

## O que fica fixo

As mesmas duas narrativas originais do bb98, abertura e Mara, com os hashes
já congelados. Ação, mecânica e contexto anterior permanecem os do corpus.
Nenhum derivado antigo, resposta c9c01a48 ou contraponto autorado entra no USER.

Mesmo candidato `gpt-oss-120b-groq-free-synthetic-low`, Groq direta,
`openai/gpt-oss-120b`, reasoning low. Uma chamada por entrada, máximo de duas,
sem nova narrativa, diagnóstico adicional, juiz LLM, retry, fallback ou
execução em terminais concorrentes.

O payload destinado à proposta final conserva `o/l/s/p/f/t/r/q`, e `n`
continua vindo literalmente da fonte fixa. O schema final, admissão e contrato
de atores permanecem os atuais. Nenhuma alteração em H6, cena, memória ou saves.

## Mudança experimental proposta

A resposta ganharia um envelope com dois componentes:

- `records`: os oito campos de registros já existentes.
- `supports`: metadados declarados pelo candidato, separados dos registros.

Cada item de suporte identificaria um caminho para um campo textual de
`records`, o intervalo de caracteres da afirmação naquele campo, uma ou mais
unidades de origem e a modalidade da afirmação na origem:
`established`, `suggested` ou `unresolved`.

Um resumo misto deve ter afirmações separadas. Um rótulo global “hipótese”
não pode encobrir outras afirmações certas ou uma pergunta que pressuponha
certeza. Devem ser inspecionados resumo, fatos, pendências, resoluções e
pressuposições da pergunta final. Campos copiados de contexto ou mecânica
conservam sua origem declarada; convites livres sem afirmação factual não
precisam inventar suporte.

Os IDs de origem apontariam para unidades completas apresentadas pelo
preflight: enunciados integrais da narrativa e itens integrais do contexto
original. Sua concatenação/separação deve ser auditável sem perder texto.
Abertura continua contendo o escopo completo de “sugerindo que algo ou alguém”;
não é permitido formar a origem recortando apenas “alguém observa”.

Limites de representação para preparar: até 12 afirmações por resposta,
no máximo três IDs de origem por afirmação; caminhos permitidos e intervalos
devem referir-se a campos existentes e trechos válidos. Esses limites são do
envelope experimental, sem alterar os limites do payload final. A preparação
offline deve demonstrar a representação dos dois casos antes de liberar o runner.

O executor validaria somente integridade estrutural desse envelope
(IDs/caminhos/intervalos válidos, fontes completas, orçamento e proveniência).
Não inventaria suportes, não reescreveria registros e não trataria um rótulo
como prova de fidelidade. A proposta final seria composta somente com
`records` e o `n` fixo, sob os validadores preservados.

## Critérios registrados antes de execução

O critério principal continua sendo o conteúdo dos registros:

1. O campo conserva o que a origem estabelece, sugere ou deixa em aberto?
2. Perguntas e pendências pressupõem algo que a narrativa só sugere?
3. Alguma relação nova aparece somente no registro, inclusive papel=endereço?
4. Contexto anterior foi preservado sem transformá-lo em novidade deste turno?

O envelope acrescenta diagnóstico: origem existente, contexto suficiente,
cobertura das afirmações e coerência entre modalidade declarada e redação.
Um ID correto com conteúdo infiel falha. Um rótulo `suggested` ao lado de uma
pergunta que pressupõe observação falha. O modelo não aprova a própria resposta.

As [contraprovas offline](../reviews/modality-thread-matrix-c9c01a48-2026-09-07.md)
orientam a revisão posterior pelo agente; não serão exemplos fornecidos ao
candidato nem respostas de referência obrigatórias.

## Orçamento e parada

Temperatura 0,65; teto mantido de 768 tokens de saída por chamada e 1.536 no
conjunto, **incluindo o envelope**. USER até 2.000 tokens estimados por
caracteres/4, sem truncamento silencioso. Pacing mínimo de 60 segundos entre
despachos; deadline de 60 segundos após a espera.

O envelope disputa o mesmo orçamento de saída. Truncamento ou schema inválido
é falha operacional observada, sem aumentar o teto nem tentar de novo.
Se a preparação offline mostrar que o desenho não cabe nos limites, registrar
isso antes de execução; não alterar o orçamento por arrasto.

Erro operacional de provedor/rota/schema/envelope na primeira entrada encerra
a sondagem. Rejeição de conteúdo ou admissão conserva a segunda entrada
independente. Encerrar ao consumir as duas chamadas, sem repetição para obter
taxa melhor. Chave somente por prompt protegido após preparação verificada.

Artefatos com identidade experimental própria, hashes dos textos/fontes e
envelope mantido separado. Não admitir esses resultados como replay CAP-001.

## O que o resultado poderá concluir

As mesmas duas entradas permitem investigar uma falha conhecida. Um resultado
favorável mostraria apenas que os registros desses dois casos ficaram fiéis
sob esta tarefa. Não demonstra generalização, superioridade causal, ganho
de uma cadeia em produção ou validação semântica independente.

Origem literal é condição de rastreabilidade, não garantia de implicação.
A mesma LLM escolhe registros e suportes; pode racionalizar uma resposta
posteriormente. Modificam-se SYSTEM, representação do USER e schema experimental:
não chamar isso de efeito causal de uma única variável.

## Decisão específica necessária

A proposta autoriza, se aprovada, **somente preparar e verificar offline este
envelope experimental e disponibilizar uma execução de até duas chamadas**.
Não inclui criar um validador semântico de produto ou adotar duas etapas no jogo.

A autorização anterior cobriu uma sondagem já encerrada. O limite está no
[desenho aprovado anterior](record-derivation-hypothesis-bb98ae1e-2026-09-06.md):
“Nenhum desses resultados autoriza ampliar automaticamente o experimento.”
O [AGENTS.md local](../../../AGENTS.md) também preserva decisões e exige ação
humana para ampliação material de escopo. Acrescentar esse envelope muda o
schema experimental e a responsabilidade da chamada; não é uma correção local
necessária para analisar o batch c9c01a48.

Não existe runner novo, chamada pendente de chave ou aceitação de produto
decorrente desta proposta. A análise do c9c01a48 e a matriz offline estão concluídas.
