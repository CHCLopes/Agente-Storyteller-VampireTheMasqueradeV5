# A2 em navegador — observação de 22/10/2026

## Resultado

Ensaio isolado implementado em `scripts/run_expression_selection_browser_trial.py`.
Reutiliza o modo determinístico e a persistência A2, sem gateway ou inferência.
Não montado em api/main.py. Banco novo exclusivo, sem migração. Texto da página
por textContent. Token local transitório e LocalRequestBoundary; listener verificado
somente em 127.0.0.1:8032. Nenhuma credencial lida ou necessária.

## Verificação automatizada

10 casos passaram: sete novos de navegador/boundary e três do harness offline
anterior. XML final: `eval-results/expression-selection-browser-tests-final-2026-10-22.xml`.
Cobrem início/desfecho, replay idempotente, IDs longos distintos, input fora do
catálogo sem operação nem avanço, reabertura do banco, retomada explícita de
preparação com/sem seleção já conservada, cancelamento explícito de preparação
interrompida sem reroll, sessão ausente, token/origem/Host e recusa de modo modelo.
Advertência preexistente de python_multipart; nenhuma falha.

Os 32 hashes implementation/supporting do gate L86 foram reconferidos sem divergência.
records.jsonl L86 permanece com SHA256
792b7df18cc297804102501714d9f100314cb91a5d5b14776d674d3860368e1c.

## Navegador real

Verificação no navegador interno do Codex, não em navegador externo:

1. Nova sessão -> turno 0 e abertura no Arquivo.
2. “Como posso ajudar?” -> turno 1, fala de Mara e registro ainda na bancada.
3. “Por que?” -> aviso de catálogo não coberto; turno permanece 1; rascunho preservado.
4. Reformulação para “Mara, leve o registro” -> turno 2 e orientação, sem mover objeto.
5. “Retiro o registro” -> turno 3, registro preservado, desfecho e controles bloqueados.
6. Reload -> mesmos três turnos e desfecho.
7. Reinício do servidor com o mesmo banco -> primeira navegação durante startup
   recebeu conexão recusada. Após listener restabelecido, nova aba no mesmo endereço
   recuperou sessão/histórico/desfecho. Não houve perda de sessão nem novo turno.

Capturas reais no diretório autorizado de visualizações:
`C:/Users/skate/.codex/visualizations/2026/10/20/01a15b86-c5a8-7a30-9708-fd098562abee/a2-unsupported.png`
e `a2-recovered.png`. Banco e logs próprios em
`eval-results/expression-selection-browser-2026-10-22/`.
Não foi injetada interrupção por interface durante uma operação; essa recuperação
foi exercitada nos testes de contrato/HTTP. Não afirmar teste de reconexão automática
ou suporte a qualquer browser externo. Página de ensaio de um operador, não UI final.

## Limites observados e gate

O recorte é funcional, porém fechado. “Por que?” não tem interpretação contextual;
Mara ajuda por orientação, não executa livremente o pedido. A prosa repete posição
do registro e a pergunta de ação. Sem nova inferência: custo de provedor desta etapa USD 0.
Não há evidência nova sobre desempenho de modelos locais/gratuitos ou improvisação.

CAMP-13 a CAMP-16 e CAMP-24 continuam abertos. Não reduzir seu requisito silenciosamente.
Decisão preparada em `plan/proposal-expression-selection-next-scope-2026-10-22.md`:
A prioriza integração do recorte fechado; B (recomendado) prioriza desenho e teste
offline de interpretação delimitada, com modelo sem autoridade causal e sem integração.
Nenhuma das alternativas foi aprovada por este relatório.
