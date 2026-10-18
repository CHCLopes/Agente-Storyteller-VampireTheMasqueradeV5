# Preparação do diagnóstico de contexto narrativo

Preparação concluída em 10/09/2026: **74 testes distintos passaram**, sem falha,
erro ou skip nas rodadas finais focadas. Revisão independente encerrada e preflight
real do lançador com saída 0, sem chave ou chamada externa. A contraprova de admissão
anterior passou em outros quatro testes, registrados separadamente.

## Pergunta e desenho

O lote progressing 19b93f22 passou nos gates operacionais, mas não satisfez o critério
de progressão. A contraprova offline mostrou que o fluxo aceita ao menos uma mudança
ambiental concreta. O novo diagnóstico observará como o gerador continua uma fonte
estável e outra em que um acontecimento já começou.

Corpus: `evals/narrator/source_context_cases_v1.json`. As duas fontes são autoradas,
com o mesmo prefixo e apenas o último período diferente. Na primeira, som e luz
permanecem estáveis; na segunda, o som para e a luz começa a pulsar. Ordem fixa:
steady e event_started. IDs de autoria são identificados como fixtures, sem evidência
de provedor fabricada. A resposta da primeira condição não alimenta a segunda.

Mesmo SYSTEM narrative-source-progress-v1, perfil de aplicação, schema n/q, modelo
Qwen/Groq, ação de espera e parâmetros. O USER usa uma fonte textual atribuída, cena,
ação e identidade opaca; server_facts vazio. Diagnóstico puro de geração/admissão,
sem campanha, SQLite, commit, replay ou alteração no jogo.

Até duas chamadas, 768 tokens por chamada (1536 total), temperatura 0.65 e reasoning
none. Espera inicial, intervalo mínimo e prazo por chamada: 60 segundos. O prazo
absoluto é criado depois da espera e das verificações de integridade. Sem retry,
reparo, fallback ou diagnóstico extra. Rejeição de conteúdo pode seguir à outra
condição somente com rota verificada; falha técnica encerra e registra skip.

## Verificação e revisão

Provas e hashes de código, corpus, preflight e JUnit constam no JSON correspondente.
Foram preservados 65 arquivos e artefatos anteriores.
As rodadas do avaliador e do lançador são separadas; não houve repetição agregada
dos testes históricos. O conftest bloqueou rede nos testes.

Contagem: 37 controles do avaliador e 37 do lançador. Na rodada inicial do avaliador,
36 passaram e o caso de truncamento falhou por expectativa incorreta. Apenas essa
expectativa foi corrigida e o caso passou em nova execução focada. O código do
avaliador e os outros 36 controles permaneceram idênticos; o delta exato do arquivo
de testes foi conferido por hash. A falha inicial foi preservada na evidência.

Achados da revisão foram resolvidos antes da observação: consistência de estágio
anterior ao transporte e dados residuais; cruzamento dos horários locais de lote,
HTTP, prazo e evidência. O verificador recompõe requisições e projeções congeladas,
valida schema/política e recusa resultados adulterados. Isso comprova consistência
local, não autenticação externa de um transcript.

Preflight protegido: `C:\Users\skate\AppData\Local\Temp\storyteller-source-context-window-b1002a54-3601-409f-a509-8a0fca5a7548\preflight.json`.

## Critério e próximo passo

A continuação deve desenvolver um acontecimento observável substancial a partir
da fonte, oferecendo uma nova abertura ao jogador. Recapitulação, repetição do pulso
já fornecido ou comentário sobre passagem do tempo não bastam. Preservar agência,
local, elenco e causas desconhecidas. Critério autorado separado dos gates automáticos.

Uma amostra por condição permite uma leitura exploratória; não demonstra efeito
causal robusto, capacidade geral ou necessidade de nova arquitetura. Qualidade geral,
runtime e CAP-001 não são aprovados por este diagnóstico.

Próximo passo autorizado: uma execução delimitada em janela protegida, seguida de
auditoria e avaliação dos resultados. A única dependência humana é inserir a chave
diretamente no prompt protegido; ela não deve ser enviada no chat.

## Janela de execução aberta

Lote `cc09080a-8368-421c-b892-b18dfa79bc85`, PID 10016. Estado observado em
`2026-09-11T00:56:48.6523437Z`: `awaiting_secure_credential`. Usar esta janela existente;
não abrir outra. Lifecycle: `C:\Users\skate\AppData\Local\Temp\storyteller-source-context-window-cc09080a-8368-421c-b892-b18dfa79bc85\lifecycle.json`. Próximo passo: concluir a entrada
protegida, aguardar o resultado e auditar o lote pelos critérios já registrados.
