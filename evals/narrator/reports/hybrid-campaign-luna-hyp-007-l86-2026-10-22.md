# HYP-007-L86 — A2 seleção de expressão versus baseline

Registro prospectivo em 22/10/2026, antes de qualquer envio L86. A2 autorizado por
“Prossiga” após proposta de experimento isolado/versionado com persistência,
retomada e comparação determinística. Hoje humano pediu abertura da supervisora
e continuidade. Autorização contínua de ensaios sintéticos <=USD 0.15 vigente.

Hipótese: um modelo pode escolher IDs de expressões elegíveis sem alterar o
resultado preparado. Comparar contribuição editorial com a baseline explícita
(original/sem atmosfera/parágrafo único) usando exatamente o mesmo catálogo,
mesmas entradas, resultados mecânicos autorados e versão. Estado/efeitos têm
que coincidir a cada turno; replay retorna apresentação retida sem inferência.
Diferença de escolha não demonstra melhora editorial, criatividade ou estabilidade.

Oito percursos, 17 chamadas no máximo, recusa primeiro. Baseline executada sem
modelo em sessão independente antes do par. Modelo gpt-5.6-luna/OpenAI Responses,
effort low, store false, sem tools/temperatura/seed/retry/fallback/best-of. A escolha
usa três enums; resposta bruta é validada localmente, inclusive chaves duplicadas.
Aplicação é autora de todos os segmentos; o modelo é autor da seleção apenas.

Teto USD 0.15 estimado para todo o lote; antes de cada chamada, guard usa bytes
UTF-8 como proxy conservador e orçamento da próxima saída. Requests <=20.000 bytes.
Manifesto do supervisor tem limite máximo 768 tokens; requests reais usam 256
(explícito no campo actual_max_output_tokens_per_call). Redução prospectiva do
limite, sem relaxar guard. Uso ausente, rota divergente ou erro encerra o lote.
Preços 0.20/1.20 USD por milhão entrada/saída reconferidos em 22/10:
https://developers.openai.com/api/docs/models/gpt-5.6-luna.

Gates começam false/false, 22 hashes principais +10 de apoio, trava única. Preflight
keyless e quatro testes de harness devem passar; 138 focados/regressão do núcleo
passaram antes desta preparação. Uma falha local no primeiro preflight falso foi
preservada e corrigida (adapter Responses não expunha capabilities); zero chamadas
nessa falha. Não reinterpretar correção do harness como melhora de modelo.

Parar na primeira falha técnica ou divergência de estado/efeito/replay. Revisão
qualitativa pode rejeitar lote técnico completo; fechar gates se identificar falha,
permitindo chamada já em voo terminar. Registrar cada escolha bruta/normalizada,
catálogo/plano/preparação, apresentações dos dois modos, evidência/uso/custo e hash.
SQLite experimental fica retido no diretório do lote; não usar saves do produto.

Critérios editoriais: fala pertinente, ausência de redundância desnecessária,
referentes claros e layout legível; não contar toda variante como melhora. Se o
modelo escolher sempre a baseline ou só mudar quebras de linha, registrar a falta
de ganho demonstrado. Preservar resultado integral e não repetir para obter ganho.
A verdade dos textos e das condições do catálogo continua obrigação editorial.
O experimento não demonstra qualidade de modelos locais/gratuitos ou RPG aberto.
Nenhuma admissão/default/MVP, migração do original, commit ou push decorrente.

## Estado após preparação, antes da execução

Quatro testes do harness passaram e preflight concluiu 17 pares/zero API,
max2.215 bytes. Despacho foi rejeitado pela revisão automática por exigir aceite
explícito de egress dos payloads específicos à OpenAI. Nenhuma chamada, request
ou latch; gates continuam false/false. Arquivo exato dos payloads e hash no relatório
expression-selection-a2-implementation-2026-10-22.md. Não contornar o bloqueio.

## Resultado real após autorização explícita de envio

Usuário respondeu “Prossiga” à pergunta específica sobre os 17 payloads sintéticos
à API da OpenAI, gpt-5.6-luna low, até USD0.15 pelo lote. Bloqueio anterior resolvido
por essa autorização, sem contorno. Lote282a3849-3c62-4390-8809-e9bb95a2385c:
17 pares completos/17 chamadas, 6.448 tokens entrada/859 saída, USD0.0023204
estimado. Maior request2.215 bytes; nenhuma divergência de estado/efeitos.
34 replays reais conferidos no banco retido sem RNG/renderer atual/gateway.

Escolhas: 12 falas alternativas/5 originais; oito frases de posição redundantes;
dois layouts em parágrafos; dois textos exatamente iguais à baseline. Ganho
editorial consistente da LLM não demonstrado. Gates fechados, trava preservada,
nenhum lote novo. Análise integral: expression-selection-l86-observation-2026-10-22.md.
