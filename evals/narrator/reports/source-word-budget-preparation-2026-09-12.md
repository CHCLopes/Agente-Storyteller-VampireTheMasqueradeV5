# Preparação do diagnóstico de orçamento de palavras — 12/09/2026

Preparação técnica concluída, com revisão independente e preflight integrado
aprovados. Nenhuma chamada real a modelo ocorreu nesta preparação. A execução
do lote novo ainda depende de um comando na janela protegida do usuário.

## Hipótese e desenho congelado

O comparativo 61b83a2f continua encerrado sem candidato qualificado. Duas propostas
Qwen excederam o limite total de 150 palavras: 146+9 e 153+4 em n+q. Ignorar apenas
q não explica os dois excessos. Este diagnóstico testa uma solicitação com margem
numérica por campo, preservando o gate existente.

Dois contextos novos autorados, Relojoaria/Bela e Pavilhão/Caio, são usados nos
quatro slots independentes A/C1, B/C1, B/C2, A/C2. O USER de cada par é idêntico.
A usa o corpo de narrative-source-progress-v1 intacto. B substitui apenas a frase
de orçamento total por n de 70 a 110 palavras, q até 10 e total solicitado até 120.
A admissão original continua de 30 a 150 palavras no total e q até 15. A medida
de aderência ao pedido B fica separada da admissão. O contador é o mesmo do gate.

Qwen qwen/qwen3.8-27b via Groq, reasoning none, schema strict n/q, temperatura
0,65 e 768 tokens de saída por chamada. No máximo quatro chamadas e 3.072 tokens
de saída solicitados. Espera inicial, espaçamento global entre inícios e deadline
por chamada: 60 segundos. Não há diagnóstico extra, retry, reparo, truncamento,
fallback, campanha, SQLite, commit, interface ou alteração do default.

A fonte C2 tem origem autorada explícita, sem evidência de provedor ou turno
confirmado. As respostas não alimentam os outros pedidos. A revisão de agência,
utilidade, continuidade e clareza será descritiva e independente, sem modelo juiz.

Documentação oficial conferida em 12/09: [modelos](https://console.groq.com/docs/models),
[saída estruturada](https://console.groq.com/docs/structured-outputs) e
[reasoning](https://console.groq.com/docs/reasoning). Ela lista o alvo preview,
strict:true e none; não comprova quota, credencial ou acesso da conta.

## Implementação e achados corrigidos

O executor congela arquivos, pedidos, SYSTEMs, USERs, schema, parâmetros e slots.
O verificador reconstrói registros e summary sem chave ou rede, recusando drift,
ordem ou cardinalidade incorreta e contradições internas de observação.

A primeira rodada preserva 68 casos aprovados e uma falha: finish_reason=length
permitia continuar como recusa de conteúdo. A revisão independente também
reproduziu falsos sucessos ao remover a observação HTTP; combinar accepted com
HTTP429/finish incompatível; declarar uso acima do teto; ou terminar depois do
deadline e do próximo envio. Uma segunda leitura encontrou subobjetos unavailable
com conteúdo contraditório. Essas evidências não foram apagadas ou reclassificadas.

A correção mantém a proposta, o outcome e a evidência originais e acrescenta um
diagnóstico operacional separado. O diagnóstico é recalculado pelo verificador,
bloqueia o próximo envio e impede sucesso, inclusive se ocorrer no quarto slot.
Uso ausente continua desconhecido. Término tardio pode ficar registrado como
falha auditável, com slots seguintes não enviados. Recusa tipada de schema/política
só permite o próximo slot previsto quando rota e observação permanecem coerentes.

O launcher PowerShell 7 aceita Read-Host -AsSecureString ou um SecureString da
mesma sessão. Cria uma cópia e descarta apenas essa cópia. A credencial passa só
ao ambiente do processo filho live; preflight e verificador usam allowlist sem
credencial. Saídas live são capturadas e descartadas; mensagens de falha são
sanitizadas. Não há leitura de outro processo, histórico, arquivo de chave, .env
ou IPC. O objeto original do usuário é preservado.

## Verificação e limites da evidência

| Frente | Resultado |
|---|---|
| Executor, primeira rodada | 68 passaram e 1 falhou; reprodução preservada |
| Executor, correção principal | 82 passaram |
| Executor, refinamento final | 25 passaram, 61 desmarcados |
| Executor, controle positivo final | 1 passou, 85 desmarcados |
| Reconciliação do executor | 86 casos distintos com última execução verde; 26 executados no hash final e 60 preservados da etapa anterior |
| Launcher | 60 casos distintos com última execução verde em duas etapas: 8 e 53, com um caso revalidado; nenhuma falha |
| Revisão independente | 10 verificações focais em memória com resultado esperado; leitura estática do launcher sem achado material aberto |
| Preflight real pelo launcher | Exit 0, lifecycle preflight_only_completed, stderr vazio, hashes estáveis e nenhuma credencial fornecida |

As dez verificações independentes não são dez testes pytest adicionais. A suíte
integral de 86 casos do executor não foi repetida após o refinamento final;
reexecutaram-se os casos afetados e o controle positivo completo. Os testes do
executor emitiram apenas o aviso preexistente de python_multipart. Reconciliações,
logs, hashes e reproduções estão no checkpoint separado desta preparação.

Preflight integrado: 802f5b6e-2374-4eb2-aef3-0979817679f6, SHA-256
`d2ea0b8c76223453e3d6701e2a85e4ce657657eb5cbdd4ed13886672a45ca9bc`.
Foi produzido no contexto Git correto: HEAD 5e563824fcba4c53cc37b5084a8ce65f3fa30356,
dirty true. O preflight inicial wkfe7v11, anterior às correções e com Git null/null,
permanece apenas como evidência histórica. Não é o freeze da execução futura.

Fontes finais:

- Evaluator: `de475337d8b07f3f7a0800da126a2c88c11845a532ad6356d1bd59f99be41144`.
- Launcher: `648a6c01e99068a5c6387996c8b751334325d3ea391b93921a590a4d8c975b4b`.
- Corpus: `d68fe07680844c76b88d8ff401311ef1f0c54a0441da945da55ca509463cc52e`.
- Protocolo: `96a2cad0260f718c1021c6771692b71fb8bc1352b9b7abaaa2663b5865035a33`.
- Arquivo SYSTEM B: `18428fef897a31dda7b27ba472bbdaf4a5c988bf4bd0f836c4f4ce790e9d5067`.

Checkpoint: `eval-results/checkpoints/source-word-budget-preparation-20260912/manifest.json`.
São 75 cópias revalidadas por tamanho e hash; manifest SHA-256
`efe70534e6453c27c3bca73cc41dd4dc5edfe71cf5ad7ef36e26dbf84c6674b3`. Hashes locais demonstram consistência, não autenticidade
externa. Não se mediu chegada remota, custo ou qualidade narrativa nesta preparação.

## Próximo passo operacional

A inserção protegida foi concluída em uma janela PowerShell 7 do usuário. A chave
permanece como SecureString somente naquele processo; não foi validada no provedor.
O usuário deve executar uma única vez, nessa mesma janela:

```powershell
& 'C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_source_word_budget.ps1' -Credential $StorytellerGroqKey
```

Essa referência passa o objeto seguro, não uma chave literal. O agente não herda
a variável de outra janela. A execução ali é a única intervenção humana estrita
restante para iniciar este lote; não é nova autorização do escopo. Se a janela
for fechada, executar o launcher sem -Credential solicita nova entrada protegida.

O launcher criará outro UUID e seu próprio preflight/binding, conferirá o freeze
antes do live e auditará os artefatos ao terminar. Manter essa janela aberta até
o término. Falha operacional encerra o lote; não reexecutar para completar skips.
Depois, comparar summary/JSONL, requisições e cronologia antes da revisão narrativa.

O diagnóstico não reabre o comparativo anterior nem aprova narrador, piloto,
campanha, default ou CAP-001. Quatro observações não demonstram causalidade
estatística ou confiabilidade geral. A [composição técnica local](source-local-resume-2026-09-12.md)
está concluída em evidência separada; as pautas futuras conservam a ordem existente.
