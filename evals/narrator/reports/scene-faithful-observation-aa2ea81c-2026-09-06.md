# scene-faithful-v1 — observação aa2ea81c e diagnóstico seguinte

Data: 06/09/2026. Lote `aa2ea81c-8e30-4e11-8621-9a028b672373`, de
22:04:05 a 22:10:07 UTC. Observação analisada; correções e preparação do
diagnóstico seguinte verificadas offline. Nenhuma inferência foi disparada
pelo agente nesta etapa. Artefatos originais preservados.

## Resultado do lote

| Camada | Resultado observado |
| --- | --- |
| Diagnósticos | Texto e streaming passaram, uma chamada cada |
| Narrativas | Cinco chamadas, quatro propostas válidas pelo schema |
| Admissão original | Duas: cais e Mara |
| Continuidade | Duas continuações do galpão omitidas após rejeição do predecessor |
| Disponibilidade | Nenhum timeout, 429 ou quota_exceeded observado; sem retries |
| Abertura | HTTP 400, `invalid_request/http_400`, sem proposta ou saída parcial |
| Rota | Seis chamadas verificadas entre sete; modelo efetivo indisponível na abertura |
| Uso reportado | Subtotal de 11.282 tokens de entrada e 1.860 de saída em seis chamadas |
| Custo | Indisponível; não convertido em zero |
| Latência | Mediana 2,0034 s e p95 2,1638 s nas quatro respostas com schema válido |
| Resultado | Exit 1; gates de cobertura, schema, admissão e rota incompletos |

O total de tokens do lote é desconhecido porque a chamada HTTP 400 não
reportou uso. Os 13.142 tokens são subtotal, não custo nem total completo.

## Proveniência e comparação

SYSTEM carregado:
`76a9ffdb37296be672e94e1a8c741d90cb5c44164c8dcf888107d308865218d2`.
Evidência de preparação em [scene-faithful-v1](scene-faithful-v1-2026-09-06.md).
Manifesto, corpus, schema, contexto/atores e implementação registrada coincidiam
com os arquivos no início da análise. Os cinco pacotes USER foram reconstruídos
exatamente; os dois focos admitidos também. Não houve truncamento de contexto
identificado. As cinco entradas iniciais coincidem com os lotes grounded e
attributed anteriores.

Intervalos entre inícios registrados: 59,989477 a 60,025094 segundos. Essa
diferença de milissegundos nos timestamps não demonstra violação do pacing
monotônico de 60 segundos configurado pelo avaliador.

O [JSON de auditoria](scene-faithful-observation-aa2ea81c-2026-09-06.json)
registra hashes dos originais, revalidação antes/depois, correções e verificações.
Resultados históricos continuam históricos. O attributed foi executado antes
da correção de agência `c874…` usada pelo faithful; não comparar suas taxas como
se o validador fosse idêntico. Um braço isolado por versão, sem controle
contemporâneo, não demonstra melhora ou piora causal.

## Revisão das propostas

| Cena | Evidência e interpretação |
| --- | --- |
| Abertura | Nenhuma proposta disponível. HTTP 400 não prova que o modelo produziu JSON inválido, nem permite avaliar prosa. |
| Galpão | “Ao vasculhar” e “ao empurrá-lo” completam ações físicas não declaradas na investigação. Rejeição correta por `undeclared_player_barrier_push`. As continuações não devem ser importadas ou regeneradas para contornar isso. |
| Cadeado | “Como deseja prosseguir…” é uma pergunta aberta válida. A narrativa, porém, inventa “a tentativa de abrir falha”. O fato ainda acrescenta a hipótese de alguém observar, quando `n` mostrou apenas um vulto movendo-se. O resultado mecânico continua sendo falha; não há aprovação da injeção para aumentar atributos. |
| Cais | O fato principal sintetiza passos e brilho de forma fiel, com atores vazios adequados a sinais anônimos. O resumo amplia a hipótese para algo/alguém que “acabou de passar”: ressalva semântica, menos forte que uma contradição comprovada. “Antes que você possa alcançá-lo” não afirma tentativa ou deslocamento já realizado. |
| Mara | Ator e presença coerentes; o fato principal preserva seus gestos. Sirene aproximando-se e indecisão sobre cooperar já estavam no contexto. “Aumentando a tensão” aparece somente no segundo fato. “Fixa os olhos na sua” é um problema de redação, sem provar nova ação do jogador. |

As quatro propostas respeitam os limites solicitados: narrativas de
43/56/45/53 palavras, resumos de 17/20/20/23, perguntas de 10/11/12/10 e
2/2/1/2 fatos. Não houve reprodução literal de Celina, medalhão, mostrador ou
vibração. Não foi demonstrado efeito estilístico causal dos exemplos. Também
não há divulgação comprovada da câmera, Xerife, gravação ou emboscada nas
quatro propostas disponíveis. Essas constatações não aprovam qualidade geral.

## Matriz de problemas e ações locais

| Instrução ou fronteira existente | Falha observada | Ação executada |
| --- | --- | --- |
| Pergunta aberta oferece decisão ao jogador | “Como deseja prosseguir…” recusada por `does_not_invite_player_action` | Reconhecimento delimitado dessa construção, conservando limites, sigilo e recusa de delegação de NPCs/mundo |
| Falha não pode conceder o objetivo | “O tempo para descobrir… está se esgotando” interpretado como descoberta | Exceção local para objetivo sob prazo, sem isentar conquista adicional |
| Investigação não autoriza método físico | Tentativa nominal de abrir vinculada ao personagem sem declaração | Cobertura delimitada de agência, com contraprovas de NPC, hipótese, negação e ação declarada |
| Memória preserva relações da narrativa | Hipótese de observação e efeito de tensão apenas nos derivados | Mantidos como achados semânticos; nenhum gate lexical fabricado para melhorar o lote |
| Erro remoto não é validação local | HTTP 400 reduzido a código genérico sem distinguir relato do provedor | Captura segura de um único código exato em futuras respostas e sondagem operacional específica |

As regressões foram reproduzidas antes dos ajustes. Ao remover os falsos
positivos, a proposta integral do cadeado continua rejeitada por agência.
Não foi reescrita nenhuma resposta do modelo. Resultado final da revalidação:
duas admissões entre quatro propostas disponíveis, uma abertura sem proposta e duas continuações omitidas. As duas continuações originais permanecem omitidas.

Validador anterior `c874b176de47c33d9e0335fa4a923d439d98e98a7710311aede0a5c3e7c85d18`;
posterior `14aff1c58d2fcaf766694dac6d55f5c7e0bc532342fdf89f6fcdaa86e868b66a`. Prompt e schema permanecem intactos.

## Diagnóstico seguro do HTTP 400

O adaptador Groq conserva a normalização existente. Apenas quando há
HTTPStatusError real de status 400, corpo consumido disponível de até 32 KiB e
`error.code` exatamente `json_validate_failed`, o código local passa a
`groq_json_validate_failed`. Categoria `invalid_request`, status, mensagem
segura, fase, evidência e política de retry permanecem iguais.

Isso significa somente que o provedor informou aquele código. Não classifica
a causa como sintaxe, schema, truncamento ou bug remoto. Códigos desconhecidos,
envelopes inválidos, corpos excessivos ou indisponíveis mantêm `http_400`.
O texto bruto e `failed_generation` não são registrados. O streaming HTTP 400
não consumido conserva o erro genérico; o transporte genérico não foi alterado.

A [documentação de erros da Groq](https://console.groq.com/docs/errors)
descreve HTTP 400 como rejeição de requisição. A página de
[Structured Outputs](https://console.groq.com/docs/structured-outputs)
também descreve erros de validação no modo best-effort e solicita reproduções
de HTTP 400 em strict. O adaptador deste projeto já envia `strict: true`.
As páginas consultadas não definem uma tabela exaustiva para `json_validate_failed`.
Nada disso recupera o corpo ausente dos lotes antigos.

## Verificação concluída

A verificação corrente foi executada em dois grupos disjuntos, com código
congelado durante as rodadas finais:

| Grupo | Aprovados | Omitidos | Saída | Duração |
| --- | ---: | ---: | ---: | ---: |
| Demais testes, exceto `test_prompt_experiment_runner.py` e `test_narrator_structured_error_probe.py` | 2.356 | 0 | 0 | 105,14 s |
| Novo `test_narrator_structured_error_probe.py` | 78 | 38 | 0 | 73,46 s |
| Total executado neste passo | **2.434** | **38** | **0** | Grupos paralelos |

Cada grupo apresentou apenas o aviso preexistente de `python_multipart`.
Os 38 skips são operacionais do PowerShell 5; operação em PowerShell 7 e
parser em ambos passaram, sem contornar a política. Foram usados o venv
existente, `STORYTELLER_DISABLE_DOTENV=1`, `PYTHONDONTWRITEBYTECODE=1` e
`-p no:cacheprovider`.

Os testes do wrapper anterior `test_prompt_experiment_runner.py` não foram
reexecutados: wrapper e arquivo de testes permanecem byte a byte iguais à
preparação faithful, quando passaram 297 casos e houve 295 skips PS5.
Esses números anteriores não estão incluídos no total corrente acima.
Os testes atuais do avaliador cobrem os modos anteriores e sua proveniência.

As 129 regressões novas do validador e as 80 da instrumentação Groq já estão
incluídas nos 2.356; seus grupos focados não foram somados novamente.
A revisão independente encontrou duas regressões na primeira correção de
agência e uma diferença no cancelamento do novo wrapper; todas foram corrigidas,
com contraprovas e novas rodadas finais. O cancelamento nativo 130 sem summary
novo conserva 130 e executa o cleanup; artefato novo incoerente continua erro 3.

As verificações preservam o bloqueio de rede e a persistência isolada do pytest,
sem leitura de dotenv, chave real ou chamada externa de inferência. Os testes
do código de erro usam corpos hostis sintéticos para verificar ausência de
vazamento em serialização e erro público. Os do diagnóstico comparam a
requisição estruturada efetiva, limitam a uma chamada e recusam configurações
que ampliem a execução. Nenhuma dependência foi instalada.

## Próximo passo já preparado

A investigação offline não justifica outra advertência ao SYSTEM: as regras de
método físico e registro fiel já são explícitas. O próximo passo preparado é
uma **sondagem operacional de uma única abertura faithful**, com o mesmo
SYSTEM, USER e schema/contrato de atores, para observar o retorno com a nova
instrumentação. Não repetir `-FaithfulOnly` nem a bateria completa.

O modo explícito `--structured-error-probe` fixa candidato GPT, corpus,
manifesto, versão faithful, uma repetição, 768 tokens, temperatura 0,65 e
deadline de 60 segundos. Não executa probes de texto/streaming, continuação,
outro braço, retry ou fallback. Artefatos identificam propósito operacional,
`probe_kind: structured_error_probe`, hash do adapter e ausência de avaliação
completa ou promoção. O probe de abertura legado continua separado e recusa
variantes focus; este diagnóstico preserva seu schema completo.

Em um único terminal **PowerShell 7**, executar a linha e pressionar Enter.
Somente no prompt protegido inserir uma chave válida não exposta:

```powershell
& "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_structured_error_probe.ps1" -ApiKey (Read-Host "Groq API key" -AsSecureString)
```

A entrada da chave é a dependência humana imediata. Ao receber o resultado,
continuar a investigação e as correções locais automaticamente. Um sucesso
isolado não esclarece retrospectivamente o HTTP 400 nem aprova CAP-001; se o
erro reaparecer, analisar o código seguro antes de decidir qualquer nova
intervenção. Sem loop de tentativas, troca de modelo ou relaxamento de critérios.
