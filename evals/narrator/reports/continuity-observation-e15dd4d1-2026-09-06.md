# Continuidade observada — e15dd4d1

Status: uma chamada sintética analisada. Continuidade referencial observada nesta
amostra, com ressalvas de linguagem e fidelidade dos resumos. Não é aceitação
humana, seleção de modelo, aprovação CAP-001 ou promoção ao runtime.

## Evidência e integridade

- Run: `e15dd4d1-80a5-4224-98a6-4d23750b1cab`, 06/09/2026, 14:01:53 UTC.
- Diretório: `eval-results/continuity-probe/e15dd4d1-80a5-4224-98a6-4d23750b1cab/`.
- Perfil: `gpt-oss-120b-groq-free-synthetic-low`; Groq direta,
  `openai/gpt-oss-120b`, low; SYSTEM `scene-focus-v1`.
- Uma chamada, sem diagnósticos, retry ou fallback; saída máxima 768,
  temperatura 0,65. Transporte, schema, admissão e rota passaram; exit 0.
- Latência desta chamada: 2,278948 s; uso reportado: 1.920 tokens de entrada,
  494 de saída, 2.414 no total. Custo não informado, não presumido zero.

Hashes SHA-256 conferidos:

| Artefato | SHA-256 |
| --- | --- |
| request.json | `f97a0e1d9f9c6b26c0b67393ffb0b27396f99e5864a8c26dc360728cfa3caf7c` |
| response.json | `13c6e73dfbc2b51e0f31f137356e3020080a111f06b3cecac903d3b2b2c398ae` |
| summary.json | `d4fd94867370daedb086faf761e7e478fad4c166f7ff1decb9407891db56ee56` |

O request coincide com o preparado offline. Os seis hashes de implementação
registrados coincidem com os arquivos atuais. Nenhum artefato original foi
editado; `continuity_human_assessment` permanece null.

## O que foi observado

O predecessor é autorado para o teste, admitido e projetado somente em memória.
Ele estabelece uma faixa de tinta azul úmida que termina sob um painel; rádio e
símbolo no cadeado permanecem como fundo antigo. Não é uma descoberta produzida
pelo modelo. O jogador pede: “Examino com cuidado o detalhe que a investigação
revelou.” O outcome fornecido é unresolved, sem teste mecânico exigido.

| Dimensão | Avaliação do agente sobre esta amostra |
| --- | --- |
| Referência recente | Retoma a faixa azul/fresta/painel, não o rádio ou símbolo antigo. |
| Progressão | Acrescenta brilho, odor e rangido ligado à parede. Avanço pequeno, pertinente; não é só repetição de atmosfera. |
| Agência | Examinar foi declarado. Não inventa tocar/abrir o painel, deslocamento, fala ou decisão do personagem. A pergunta final é aberta. |
| Mecânica e continuidade espacial | Preserva unresolved, o rótulo do lugar e ausência de NPC identificado. |
| Português | “como se algo se moverá” tem erro de modo verbal; “como se algo se movesse” seria compatível com a hipótese. A resposta não foi corrigida retroativamente. |
| Concisão | Contagem por espaços: narrativa 53 palavras (35–70), resumo 29 (pedido: até 25), pergunta 6 (até 15). O limite de palavras é uma instrução de geração, não um gate existente de schema. |
| Fidelidade narrativa → fatos | “brilho metálico” vira “contém partículas metálicas”. Aparência não comprova composição. O fato também acrescenta “selo ou mecanismo oculto”, ausente da narrativa. |
| Fidelidade narrativa → resumo/foco | O resumo introduz a hipótese de mecanismo; o `next_focus` reproduz resumo e fato com esses acréscimos. Parte da incerteza permanece em “pode”/“sugerindo”, mas isso não torna o conteúdo derivado de `n`. |

O problema de fidelidade nasce na proposta do modelo e passa pela admissão.
A projeção copia os campos recebidos; não há evidência nesta amostra de corrupção
local do contexto, troca de modelo ou truncamento. Foram omitidos zero detalhes
antigos; o pacote USER estimado em 500 tokens não inclui SYSTEM/schema e não
deve ser comparado ao total de entrada como se fosse tokenização equivalente.

O `next_focus` é um artefato sintético do diagnóstico, não uma gravação na memória
de campanha. Ainda assim, ele torna observável o risco de carregar uma hipótese
mais específica para a próxima geração. Passar pela admissão não prova
equivalência semântica entre todos os campos nem qualidade literária.

## Decisão técnica desta revisão

Não alterar o prompt congelado, normalizar a resposta, enfraquecer agência ou
acrescentar regex específica de “tinta/partículas” para fabricar aprovação.
Não promover uma exigência nova a gate retroativo. A restrição de fidelidade já
existe no prompt e permanece como critério explícito de revisão qualitativa.

Nenhum defeito novo de montagem/transporte foi demonstrado que justifique um
patch de runtime nesta etapa. A revisão registra a limitação de admissão
semântica, sem alegar que ela foi solucionada. Foram atualizadas apenas a
documentação desta observação e a navegação para ela.

Uma resposta positiva com predecessor claro demonstra uma capacidade neste
contexto, não a frequência dessa capacidade. Também não prova que o modelo era
ou não era o único gargalo, que o foco causou a melhora, ou que narrará bem em
português durante uma sessão. Não houve controle, repetição ou dados de campanha.

## Próxima execução delimitada

O diagnóstico de uma chamada já respondeu à sua pergunta estreita. Não repeti-lo
até obter uma saída mais bonita. O próximo passo usa a bateria `FocusOnly`
existente, uma única execução nova previamente delimitada, para observar a
cadeia com descoberta produzida pelo próprio modelo, além dos casos de agência
e ataques. Isto é uma nova observação, não um A/B ou prova causal.

- Mesmo candidato e variante; corpus CAP preservado, sem importar o predecessor
  autorado ou escolher a melhor resposta dos lotes anteriores.
- Na cadeia do galpão: investigar → seguir a descoberta → observar/esperar.
  Se o predecessor for rejeitado, a continuação dependente é pulada. Isso é
  resultado da avaliação, não permissão para enxertar uma resposta admitida.
- Manter todas as falhas anteriores; não executar em loop nem repetir até passar.
- Máximo de nove chamadas normais (dois diagnósticos + até sete turnos), com até
  duas repetições limitadas de diagnóstico já previstas pelo runner. Intervalo
  mínimo de 60 s. Sem retry narrativo ou fallback.
- Revisar referência, reação à intenção, agência, idioma, fidelidade n/s/f e
  evolução da incerteza em cada turno. Palavras-chave isoladas não aprovam
  continuidade; forma/schema não aprovam a memória.
- Resultado insuficiente mantém o candidato em avaliação; não autoriza dados
  reais, promoção ao jogo ou alteração automática de provedor.

O executor já existe; não foi necessário criar outra CLI nem alterar o corpus.
No PowerShell 7, chave somente no prompt seguro:

```powershell
& "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_prompt_experiment.ps1" -FocusOnly -ApiKey (Read-Host "Groq API key" -AsSecureString)
```

## Verificação local

Nesta revisão: **71 testes passaram**, em 2,21 s, com
`STORYTELLER_DISABLE_DOTENV=1` e:

```powershell
& .\.venv\Scripts\python.exe -m pytest -q tests/test_continuity_probe.py tests/test_narrator_scene_focus.py tests/test_narrator_replay_skips.py
```

Somente o aviso preexistente do Starlette sobre `python_multipart`. Esta rodada
não é a bateria inteira e não mede qualidade narrativa. A revisão independente
concordou com continuidade referencial/agência preservadas e com a deriva dos
resumos. A skill `agentic-eval` orientou a separação entre sucesso técnico,
observação qualitativa do agente e aceitação humana; nenhum loop de otimização
foi introduzido. Não houve nova chamada externa, acesso a chave/.env, campanha,
serviço, instalação, migração, commit ou alteração do checkout original.
