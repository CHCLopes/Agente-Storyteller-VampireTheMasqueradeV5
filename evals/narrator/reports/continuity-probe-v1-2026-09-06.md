# Diagnóstico curto de continuidade — continuity-probe-v1

Status: implementado e preparado offline; nenhuma chamada real ao provedor nesta
etapa. Ainda não há resultado de qualidade narrativa, seleção de modelo ou CAP-001.

## Por que um predecessor autorado

O [lote scene-focus anterior](scene-focus-observation-2164b8d6-2026-09-06.md)
não chegou a enviar foco recente: a primeira investigação foi rejeitada e as
continuações dependentes foram puladas. Repetir a bateria não isola essa lacuna.

Este diagnóstico usa uma fixture própria, independente do corpus CAP, com um
predecessor **escrito para a simulação**, não produzido pelo modelo. Uma faixa
de tinta azul úmida que termina sob um painel é a descoberta recente; rádio e
símbolo do cadeado permanecem como detalhes antigos. A próxima entrada é aberta:
“Examino com cuidado o detalhe que a investigação revelou.”

O teste pergunta se o modelo consegue desenvolver a referência recente quando
ela efetivamente chega ao contexto. Não exige uma solução ficcional única, não
fornece resposta esperada e não altera a premissa de improvisação do produto.

## Implementação e autoridade

- Autorização contínua do usuário, restrita ao escopo/pasta e guardrails, registrada
  em `AGENTS.md` local. Não foram alteradas instruções globais ou o checkout original.
- `evals/narrator/experiments/continuity-probe-v1.json`: fixture sintética própria,
  com predecessor e uma continuação, sem NPC identificado ou segredo. Resultado
  success do predecessor é uma premissa da fixture, não uma rolagem real.
- `scripts/evaluate_narrator_continuity.py`: offline por padrão; valida schema,
  atores, mecânica/agência/segredo e projeção antes de derivar foco, montar pedido
  ou consultar `GROQ_API_KEY`. Não grava campanha, estado canônico ou memória do jogo.
- Reusa o fluxo de geração/admissão existente. A única alteração no avaliador
  anterior é um prefixo de operação opcional, cujo padrão continua `CAP-001`;
  este diagnóstico se identifica como `CONTINUITY-PROBE`.
- `scripts/run_groq_continuity_probe.ps1`: credencial em SecureString, restauração
  da variável anterior no finally e uma única invocação. Verifica UUID, caminho
  exato, modo live, finalidade, candidato, prompt, contadores, flags e código.
  Preparação offline nunca pode ser apresentada como êxito de transporte.

Perfil fixo já utilizado: `gpt-oss-120b-groq-free-synthetic-low`, Groq direta,
`openai/gpt-oss-120b`, raciocínio low; SYSTEM `scene-focus-v1` preservado. Saída
768 tokens, temperatura 0,65 e deadline 60 segundos. **No máximo uma chamada**,
sem diagnósticos, streaming diagnóstico, retry, fallback ou repetição. Não há
troca configurável de corpus, fixture, candidato, prompt ou orçamento na CLI.
O nome histórico do perfil não constitui nova garantia de preço/disponibilidade.

Uma barreira no ponto de invocação confere o pedido exato preparado, modelo,
schema, parâmetros e operação; impede segunda chamada inclusive após erro.
Entradas não podem ser redirecionadas por symlink para fora do projeto ou para
`.env`. Diretórios UUID são exclusivos e não sobrescrevem resultados anteriores.

## Artefatos e interpretação

Cada execução gera `eval-results/continuity-probe/<run-id>/`:

- `request.json`: pacote sintético inspecionável, schema, configuração e hashes.
- `response.json`: resposta/classificação da única tentativa, quando houver;
  cancelamento sem resposta registra somente tentativa de conclusão desconhecida.
- `summary.json`: finalidade restrita, origem autorada do predecessor, foco,
  contagem de tentativas, rota, uso/custo, status e verificações automáticas.

O predecessor tem `provider_generated=false`, `call_made=false` e admissão apenas
local. Não entra na taxa de acerto, latência ou uso do modelo. Sem chamada, uso
e custo são `not_requested`; com tentativa sem medição, permanecem desconhecidos.
Nenhuma chave, mensagem bruta de exceção ou variável de ambiente vai ao relatório.

| Saída | Significado neste diagnóstico |
| --- | --- |
| 0 offline | Pedido preparado; nenhuma API executada. |
| 0 live | Estrutura, admissão e rota passaram; qualidade e continuidade semântica ainda exigem revisão. |
| 1 | Falha de resposta, admissão ou verificação de rota. |
| 2 | Indisponibilidade, timeout ou limite de cota; nenhuma repetição automática. |
| 3 | Erro local/configuração/execução ou evidência incompatível. |
| 130 | Cancelamento; tentativa já iniciada não é apagada nem reenviada. |

Em todos os casos `full_evaluation=false`, `cap_001_status=not_evaluated` e
`continuity_human_assessment=null` até revisão humana. Não é A/B: predecessor
claro e autorado altera a distribuição em relação aos lotes anteriores. NPCs,
segredos, sessões longas, repetição e geração espontânea do predecessor continuam
fora deste diagnóstico. Sucesso não promove a variante para o runtime.

## Preparação conferida

Execução offline: `0ffd4502-3050-4d6a-b663-c1287480e097`, status prepared,
zero chamadas. Foco `authored-continuity/authored-predecessor/r1`, scene_turn 2,
referência `visible_fact_0`, 500 tokens USER estimados por caracteres/4 e zero
omissões. A estimativa não inclui SYSTEM/schema nem substitui tokenização real.
Rádio e símbolo antigo permanecem separados da faixa de tinta recente.

- Fixture SHA-256: `c9bead3d7a2fc8c04850af967d111a92770986785cf85dac51521bf3ab9b8a06`.
- Corpo SYSTEM SHA-256: `830454df2171dabcc0bb9aeb5f775fa7b6f29066ac0dbd2675f5de14ed8b4252`.
- USER SHA-256: `f381f3fc9ebf16feec0fb1d4847f6e45e3a57527ab0d4cc1572561b57d1d3b1b`.
- Request completo SHA-256: `f97a0e1d9f9c6b26c0b67393ffb0b27396f99e5864a8c26dc360728cfa3caf7c`.

## Verificação

**1.823 testes passaram** em 103,01 s com
`python -m pytest -q --ignore=tests/test_prompt_experiment_runner.py`.
Inclui 84 novos casos: 17 do fluxo, 37 de segurança e 30 do novo wrapper.
Após o último metadado explícito `predecessor.call_made=false`, os 54 testes
Python focados foram executados novamente e passaram. Só permanece o aviso
preexistente do Starlette sobre `python_multipart`; não há alegação percentual
de cobertura, pois `pytest-cov` não está instalado.

O novo wrapper foi analisado no PowerShell 5 e 7 e executado operacionalmente no
7 com Python nativo sintético. A política Restricted do 5 não foi contornada.
A suíte do wrapper A/B antigo (172 casos) não foi repetida nesta etapa, pois
seu código não mudou; o comando acima não deve ser descrito como bateria inteira.
Foram inspecionados os arquivos novos/alterados e o whitespace.

Contraprovas incluem seed inválido, ator privado exposto, segredo sintético,
foco de outro turno/episódio/repetição, projeção e orçamento inválidos, caminhos,
colisão de execução, chave ausente, cancelamento antes/depois da invocação,
alteração de pedido e relatório offline mascarado como live. Transporte real do
adapter Groq foi exercitado com MockTransport, sem rede e com credencial sintética.

As skills `agentic-eval` e `pytest-coverage` orientaram a separação de geração,
admissão e avaliação humana, além das contraprovas; nenhum loop de otimização
automático foi introduzido. `create-agentsmd` orientou o registro local da
autorização vigente. Nenhuma API, chave real, `.env`, campanha, instalação,
migração, serviço, commit ou PR foi usado/alterado nesta etapa.

## Execução e revisão seguinte

Preparação offline, a partir da raiz do worktree:

```powershell
& .\.venv\Scripts\python.exe .\scripts\evaluate_narrator_continuity.py
```

Quando o usuário inserir a credencial, uma chamada nova:

```powershell
& .\scripts\run_groq_continuity_probe.ps1 -ApiKey (Read-Host "Groq API key" -AsSecureString)
```

Revisar resposta completa: desenvolve faixa/fresta/painel como descoberta recente,
ou apenas cita essas palavras e volta ao símbolo antigo? Acrescenta consequência
coerente sem tocar/abrir algo pelo jogador? Preserva o local, o fato anterior e
a liberdade de ação? Uma contagem de palavras-chave não decide essas perguntas.
Não repetir automaticamente até obter resultado favorável.
