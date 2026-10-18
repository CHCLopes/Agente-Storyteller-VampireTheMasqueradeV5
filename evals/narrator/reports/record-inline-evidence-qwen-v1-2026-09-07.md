# Observação Qwen inline — preparação executada

A preparação de `archive-vibration` com Qwen 3.8 27B/Groq, perfil `none`, foi executada no lote `94a95216-9d0b-479e-85d3-e6c577ce4fa3`. O [resultado analisado](record-inline-evidence-qwen-observation-94a95216-2026-09-07.md) encerra a rodada com sucesso operacional e descumprimento do limite de palavras e da separação modal. A ausência de perguntas é permitida e não informativa para a formulação de perguntas. A autorização contínua permanece. [Registro histórico da preparação](record-inline-evidence-qwen-v1-2026-09-07.json).

O [desenho prévio](record-inline-evidence-qwen-design-6876955e-2026-09-07.md) e o [dossiê congelado](record-inline-evidence-qwen-dossier-6876955e-2026-09-07.json) mantêm os mesmos SYSTEM, USER, fonte, schema, projeção literal, temperatura e teto da [observação 6876955e](record-inline-evidence-observation-6876955e-2026-09-07.md). Só mudam no corpo HTTP modelo, esforço e omissão de include_reasoning, parâmetro específico de GPT-OSS no adaptador atual. O corpo `bd7219cf…` foi reconstruído independentemente; não há comparação causal, controle novo ou importação dos contadores antigos.

## Implementação e verificação

Executor e wrapper são aditivos; os anteriores ficam preservados. O novo observador aceita exclusivamente `qwen/qwen3.8-27b` reportado e `none`, com rota direta e corpo de uso único. Herda o tratamento limitado de erros, cancelamento e sanitização. Conserva a estrutura válida e roteada se a projeção falhar, sem reparar o texto; não confunde schema/projeção com fidelidade. Foram acrescentadas 12 linhas à guarda CAP compartilhada, sem remoções, para a nova identidade nas duas entradas de replay.

| Verificação focada | Testes distintos aprovados |
| --- | ---: |
| Executor Qwen e transporte simulado | 56 |
| Wrapper: parser e fluxos PowerShell 7 | 91 |
| Fronteira de replay CAP: 25 novos e 68 existentes | 93 |
| Total | 240 |

São 172 testes novos e 68 existentes, sem falhas pendentes ou skips; não foi executada a suíte integral. O grupo do executor passou 51 casos inicialmente e cinco após corrigir exclusivamente uma expectativa de teste: a identidade é recusada antes de o executor alcançar o schema. Os outros 51 testes e o executor não mudaram. Os 91 do wrapper foram grupos disjuntos de 12 e 79. Dois RED anteriores à guarda CAP demonstraram a ausência da identidade nova; não entram como testes finais adicionais. O aviso de python_multipart é preexistente. Revisão independente do executor/guarda e revisão do wrapper não deixaram achados materiais.

A integração real PS7 com SecureString vazia passou o preflight e encerrou com código 3 na validação da credencial, como esperado: nenhum acesso ao provedor ou artefato novo. O primeiro helper de integração omitia PATHEXT/COMSPEC em seu ambiente reduzido; preservar essas variáveis restaurou a execução nativa do Python. A saída Python já era UTF-8 válida. Não houve correção de código do projeto motivada por esse problema do helper.

A auditoria final confirmou 32 fingerprints históricos e dez artefatos brutos intactos, além da mudança CAP delimitada. Os critérios semânticos continuam externos: revisar pressuposições, modalidade, relações, agência, limite de 25 palavras e junção dos segmentos. Dimensão omitida é não informativa, não um acerto presumido.

## Limites da execução

Exatamente uma chamada, teto 3.072 tokens, temperatura 0,65, espera local mínima de 60 segundos e deadline de 60 segundos iniciado depois da espera/preflight. Encerrar em qualquer resultado; sem diagnóstico, retry, fallback, geração narrativa, novo caso ou juiz LLM. Chave somente pelo prompt protegido local e descartada ao final. O lote executado consumiu esse limite; não iniciar outra janela para o mesmo pedido.

A documentação oficial foi verificada e vinculada no desenho. A disponibilidade efetiva continua dependente da conta; não comprar, mudar plano ou habilitar cobrança. A evidência histórica Qwen inclui falhas graves de fidelidade/agência e segredo sintético; esta entrada contém somente dados públicos autorados, e a observação de dois campos não resolve nem dispensa esses bloqueios. Oito campos, admissão de atores, runtime e CAP-001 continuam sem aprovação.

## Estado do launcher

PID 19232 confirmado `finished` em 2026-09-07T17:59:49.5067634Z, código 0. Uma chamada HTTP 200/stop, rota/schema/projeção válidos. Chave descartada; não há credencial ou chamada pendente neste lote. Não relançar a janela ou repetir o pedido. Summary e JSONL estão preservados e vinculados no relatório do resultado.

A continuidade autorizada é o trabalho offline de rubrica e a preparação de uma observação de resumo textual sozinho, em curso e com conclusão ainda pendente. Este registro não declara uma nova execução pronta nem solicita aprovação genérica adicional. Eventual chave ou intervenção direta continua sendo dependência humana somente quando necessária. Oito campos, atores, runtime e CAP-001 permanecem sem aprovação.
