---
goal: Diagnosticar a aderência do Qwen ao orçamento de palavras sem alterar o gate narrativo
version: 1
date_created: 2026-09-12
last_updated: 2026-09-12
status: 'Completed'
---

# Diagnóstico de orçamento por campo

As recusas Qwen de 155 e 157 palavras no comparativo encerrado motivam uma hipótese
prospectiva: uma solicitação com margem por campo pode evitar exceder o teto existente.
A leitura dos campos, 146+9 e 153+4, não sustenta a explicação de ignorar apenas q.
Não é nova paráfrase de progressão, reabertura de comparação ou seleção de modelo.

## Contrato

- Quatro slots independentes: A/C1, B/C1, B/C2, A/C2. C1 Relojoaria/Bela e C2
  Pavilhão/Caio são autorados e novos, sem dados de campanha ou propostas antigas.
- A usa narrative-source-progress-v1 intacto. B substitui somente o pedido total
  de 30–150 palavras por n70–110 e q até10, total solicitado até120. A admissão
  permanece 30–150 e q até15; medir separadamente solicitação e gate original.
- USER idêntico entre braços de cada contexto; nenhuma resposta vira entrada
  de outra. Fonte anterior C2 tem autoria e identidade explícitas, sem commit.
- Qwen qwen/qwen3.8-27b via Groq, reasoning none, strict schema n/q,
  temperatura 0,65 e 768 tokens por chamada, máximo 3.072 no lote.
- Espera inicial, intervalo global entre inícios e deadline de 60 segundos.
  Sem diagnóstico extra, retry, reparo, truncamento, fallback, SQLite ou UI.
- Recusa tipada registra o slot e segue apenas ao próximo previsto. Falha local,
  timeout, cancelamento, quota, autenticação, rota divergente, eco de credencial
  ou erro não tipado encerra globalmente e marca os restantes não enviados.
- Preflight e verificador sem chave/rede. Launcher PowerShell 7 com ambiente filho
  restrito e entrada protegida para execução concreta. Não ler outro processo.

## Entregas e verificação

| Entrega | Estado |
|---|---|
| Hipótese, corpus, delta e critérios prévios | Concluído e congelado; diferença única de SYSTEM e fontes autoradas verificadas |
| Harness puro com preflight/freeze/verificador | Concluído; diagnóstico operacional separado preserva a evidência e impede continuidade indevida |
| Launcher seguro próprio e contraprovas | Concluído; 60 casos distintos verdes em etapas e preflight integrado exit 0 sem credencial |
| Verificação offline e revisão independente | Concluído; executor com 86 casos distintos verdes em etapas, 26 no hash final; revisão independente focal aprovada |
| Lote novo delimitado | Encerrado: 291b3960, quatro HTTP200/stop, exit1, duas admissões e duas recusas preservadas |
| Auditoria e revisão descritiva das respostas | Concluídas: extensão não discriminante; omissão de aliases reproduzida offline; nenhuma promoção de modelo |

Arquivos novos: corpus/protocolo/prompt em evals/narrator, script
scripts/evaluate_source_word_budget.py, scripts/run_groq_source_word_budget.ps1,
tests/test_source_word_budget.py e tests/test_source_word_budget_launcher.py.
Não editar avaliadores/artefatos encerrados, gate, runtime ou default.

Contraprovas: pareamento e diferença única; quinta chamada e slot duplicado;
drift de corpo/USER/schema/target; contagem por campo/total; limites cronológicos;
parada global e recusa sem retry; cancelamento antes do próximo envio; artefatos
incompletos/adulterados; segredo sintético fora de saída e ambiente não autorizado.
Validar a origem autorada sem fabricar história confirmada.

## Interpretação e continuidade

Registrar integridade, disponibilidade, contagens, admissões e revisão de agência,
utilidade, continuidade e clareza separadamente. B conforme em2/2 e excesso de A
em ao menos um contexto é apenas sinal exploratório compatível com a hipótese.
Ambos conformes não diferenciam o efeito; excesso de B não sustenta aderência
integral. Ausências não recebem notas. Não ocultar perda de conteúdo pela concisão.

Nenhum resultado elege narrador, demonstra causalidade estatística/generalização
ou aprova piloto/CAP-001. Não repetir para obter o resultado esperado. A autorização
contínua cobre preparação e observação sintética; não cobre cobrança/plano pago
ou promoção de decisões de produto. Se a chave só estiver na janela do usuário,
concluir toda a preparação antes de fornecer o único comando de execução necessário.

Documentação oficial conferida em12/09/2026: [modelos](https://console.groq.com/docs/models),
[saída estruturada](https://console.groq.com/docs/structured-outputs) e
[reasoning](https://console.groq.com/docs/reasoning). O alvo aparece como preview,
com strict:true e reasoning none. Isso não verifica chave, quota ou acesso da conta.

Provas anteriores preservadas: [comparativo encerrado](../evals/narrator/reports/source-comparison-observation-61b83a2f-2026-09-11.md)
e [composição técnica local](../evals/narrator/reports/source-local-resume-2026-09-12.md).


## Fechamento da preparação em 12/09/2026

Na conclusão da preparação técnica, o lote live e sua revisão ainda não haviam
sido executados. O encerramento posterior está registrado abaixo. A primeira falha de truncamento e os achados do verificador foram
corrigidos com reproduções preservadas. Das 86 últimas execuções distintas verdes,
26 ocorreram no hash final e 60 na etapa anterior; não se alega suíte integral
reexecutada. Dez verificações independentes em memória não aumentam essa contagem.

O preflight integrado 802f5b6e-2374-4eb2-aef3-0979817679f6 concluiu com exit 0,
sem Credential, stderr ou drift. O contexto Git correto e todos os pedidos foram
congelados. [Relatório e evidências](../evals/narrator/reports/source-word-budget-preparation-2026-09-12.md).

A única intervenção restante é iniciar o launcher uma vez na janela PowerShell 7
que conserva a chave como SecureString. O agente não herda nem extrai essa variável.
Depois do lote, auditar summary/JSONL e cronologia e fazer a revisão narrativa
descritiva. Não repetir o lote em caso de recusa/skips e não promover modelo/default.


## Fechamento da observação e diagnóstico em 12/09/2026

O lote 291b3960-55a5-4fdc-a9f4-31d9cfa695f7 terminou finished/1. Quatro chamadas
HTTP200/stop, quatro schemas/rotas válidos, zero skips e duas recusas de agência.
Comprimento total: 77,78,104,122 palavras, todos dentro do gate. Os dois B atenderam
à margem, mas os dois A também passaram ao gate; não se diferenciou a hipótese.
Auditoria e revisão independentes encerradas, sem nova chamada ou reclassificação.

As recusas C1 vieram do caller omitir npc_aliases; a contraprova com Bela explícita
admitiu os mesmos textos. Vinte e duas verificações exploratórias conservaram as
barreiras de agência. O fluxo B configurado já repassa aliases, conforme inspeção;
nenhum núcleo ou harness histórico foi editado. Propostas mantêm avanço modesto
e um estado da porta não estabelecido na fonte. Não adotar a variante de orçamento.

[Relatório final](../evals/narrator/reports/source-word-budget-observation-291b3960-2026-09-12.md)
e checkpoints separados de observação e diagnóstico preservam as provas.
O comando protegido anterior já foi executado; não é mais uma pendência de chave.
A [proposta de recorte B](proposal-source-player-trial-scope-1.md) torna concreta
a próxima aceitação de experiência prevista em DEP-005, sem reaprovar arquitetura B.
