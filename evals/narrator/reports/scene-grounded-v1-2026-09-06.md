# scene-grounded-v1 — preparação de observação SYSTEM-only

Data: 06/09/2026. Estado: implementação offline da observação; geração ao vivo
ainda não executada. Não é aprovação de modelo, CAP-001, qualidade ou runtime.

## Evidência e hipótese

O [lote baf5d410](scene-focus-observation-baf5d410-2026-09-06.md) recebeu cinco
propostas com estrutura válida, nenhuma admitida. As duas continuações
dependentes do galpão não foram chamadas. Não houve indisponibilidade nessa
rodada. Portanto, trocar cota ou repetir o mesmo comando não resolve os motivos
de rejeição observados. As correções delimitadas de falsos positivos locais
estão documentadas naquele relatório; as propostas originais permanecem rejeitadas.

A [sondagem e15dd4d1](continuity-observation-e15dd4d1-2026-09-06.md) mostrou que
uma continuação pode ser admitida quando recebe um predecessor sintético
autorado. Também evidenciou acréscimos entre narrativa, fatos e foco seguinte.
Não demonstra continuidade autogerada completa nem qualidade suficiente.

A hipótese desta variante é que uma instrução de narrativa primeiro e registro
fiel possa reduzir ações indevidas e deriva dos registros sem suprimir improviso.
Não se introduzem exemplos com respostas do corpus, roteiro ou regra lexical
que confunda fidelidade semântica com coincidência de palavras.

## Intervenção implementada

- Novo prompt congelado `evals/narrator/prompts/scene-grounded-v1.md`.
- Registro explícito no avaliador, com o mesmo builder USER e
  `FocusedSceneContinuationProposal` de `scene-focus-v1`.
- Novo modo `-GroundedOnly` no wrapper existente. Exclusivo dos outros modos
  de braço único e restrito ao candidato GPT-OSS já usado no experimento.
- Proveniência identifica a variante e o baseline `scene-focus-v1`, com
  `interventions: [system_prompt]`, `context_contract_version: scene-focus-v1`
  e `causal_comparison: false`. Contexto, schema e implementação têm suas
  identidades/hashes preservados nos relatórios.
- Replay legado recusa também a nova identificação de prompt, sem remover
  atores para revalidar com um schema menos exigente.

SHA-256 do SYSTEM carregado pelo avaliador:
`ff47d144200ddaac14c7db30f6328f73de5fb466730fe178fb49dc335dbac331`.
São 4.841 caracteres e 697 palavras por separação de espaços. O SYSTEM
`scene-focus-v1` tem 3.609 caracteres e 521 palavras. A nova instrução é maior;
esses números não são contagem de tokens do provedor nem prova de desempenho.
O orçamento estimado de `user_packet` não inclui SYSTEM/schema. Uso, latência,
aderência e risco de limite deverão ser medidos na observação, sem inferir custo zero.

## O que permanece igual

Baseline técnico: `scene-focus-v1`. Mesmos dados USER, contexto recente,
contrato de atores, schema, corpus e política de admissão. Mesmo candidato
`gpt-oss-120b-groq-free-synthetic-low`, modelo `openai/gpt-oss-120b`, adapter
Groq, raciocínio baixo, temperatura 0,65 e uma repetição. Tetos de 768 tokens
para narrativa e 128 para cada diagnóstico; prazo de 60 segundos por chamada
começa após pacing, com pelo menos 60 segundos entre inícios.

Até nove chamadas normais e dois retries diagnósticos delimitados. Zero retry
narrativo/fallback; predecessores rejeitados continuam impedindo suas chamadas
dependentes. O braço antigo não é executado nem importado automaticamente.
Uma comparação com lotes históricos é observacional, não A/B causal completo.

Nenhuma alteração nesta etapa em H6 de runtime, validadores de domínio, corpus,
manifesto, helpers de contexto/atores, contratos públicos ou dados da campanha.
Prompts congelados anteriores e artefatos das execuções anteriores são preservados.

## Revisão de segurança, clareza e experiência

A revisão estática, orientada pelas skills de avaliação e segurança de prompts,
conservou autoridade do motor, separação instruções/dados, agência do jogador,
resultado mecânico e sigilo também nos campos derivados. Dois conflitos de
redação foram corrigidos antes de congelar o novo prompt:

1. Fatos visíveis derivam de `n`; fatos `storyteller` não são obrigados a aparecer
   na narrativa e continuam fundamentados somente no confidencial fornecido.
2. Local e presenças preservam o estado anterior quando não há mudança narrada;
   não se exige recontar todo o estado a cada turno.

O prompt permite pistas, reações de NPCs e complicações novas, sem obrigar
perigo/violência nem transferir construção do mundo ao jogador. Uma ação ampla
não autoriza escolher método físico por ele; incerteza não vira certeza só no
resumo. Não acrescenta filtros morais ao horror ficcional nem instruções
estereotipadas. Ausência dessas instruções não prova ausência de viés na geração.

Limitações: linguagem natural não garante adesão, resistência a injeção,
separação de segredos ou fidelidade semântica. Os validadores delimitados não
substituem revisão da prosa e memória. Não se atribui nota empírica de segurança,
qualidade, custo ou desempenho com base apenas nesta inspeção.

## Verificação offline

Testes novos capturam os pedidos reais montados por `_run_turn` nos cinco
episódios iniciais e em uma continuação com foco admitido não vazio: tudo é
igual entre focus/grounded, exceto SYSTEM e identidade/deadline novos por chamada.
Conferem também hashes congelados, proveniência, recusa de caminhos arbitrários,
falhas antes de credenciais/rede e preservação dos skips dependentes.

O wrapper é testado em diretórios sintéticos isolados, com processo Python
simulado para a avaliação, sem chave real nem chamadas ao provedor. São cobertos
seleção, limites, credencial de teste, códigos de saída, validação de resumo e
compatibilidade dos modos anteriores.

Suíte completa executada nesta etapa, incluindo o wrapper alterado:

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
& .\.venv\Scripts\python.exe -m pytest -q
```

**2.081 passaram, 126 omitidos, um aviso**, código de saída 0, em 319,26 s.
Os 126 skips pertencem aos testes operacionais do wrapper no PowerShell 5:
o host não conseguiu carregar o módulo de política de execução. Não se confirmou
uma política específica nem se aplicou contorno. O parser passou nos dois
PowerShells; os testes operacionais passaram no PowerShell 7. O aviso existente
é `PendingDeprecationWarning` de `python_multipart`. Não foi medido percentual
de cobertura nem executado build/frontend ou teste de jogo nesta etapa.

Antes da suíte completa, os grupos focados passaram: 107 testes de registro,
contexto/proveniência/replay e 128 testes do wrapper, estes com os mesmos 126
skips. Esses grupos se sobrepõem à suíte completa, não são contagens adicionais.

Inspeção final dos arquivos alterados e verificação de whitespace concluídas.
Os hashes do validador de cenas, corpus, manifesto e dos dois artefatos do lote
baf5d410 coincidem com o snapshot anterior à nova variante. O teste congela os
SYSTEMs anteriores e o novo SYSTEM. Não houve chamada ao provedor, acesso a
chave real, alteração de `.env`, checkout original ou registros históricos.

## Próximo passo exato

Executar uma única observação `-GroundedOnly`, mediante inserção segura da chave
pelo usuário, e inspecionar `summary.json` e o JSONL do mesmo lote. Não usar chave
antiga do chat nem abrir `.env`. Comando no [README](../README.md).

Separar transporte, estrutura, admissão, coerência narrativa→memória e revisão
de experiência. Se houver correção local necessária dentro do escopo, a
autorização contínua do usuário permite executá-la sem pedir nova confirmação,
preservando contraprovas e resultados originais. Não promover o candidato após
uma resposta aceita ou substituir avaliação completa/revisão humana por este braço.
