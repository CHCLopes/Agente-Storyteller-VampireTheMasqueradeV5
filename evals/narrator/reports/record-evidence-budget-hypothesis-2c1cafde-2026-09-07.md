# Proposta delimitada — diagnóstico do teto de conclusão

Data: 07/09/2026. Status: **desenho documental para decisão; não implementado**.
Origem: [evidência do Console](groq-console-evidence-2c1cafde-2026-09-07.md).

## Pergunta e limite da conclusão

A abertura fixa de record-evidence consegue terminar um envelope válido
com teto de 1.536 tokens, preservando o restante da requisição que falhou
com 768 tokens contabilizados pelo Console?

Uma única observação em teto maior pode mostrar viabilidade operacional
nesse caso e recolher sinais de término. Não isola causalmente a causa do
HTTP 400 histórico: há amostragem estocástica, momentos distintos e nenhum
controle contemporâneo. Não será chamada de A/B ou prova de truncamento.

## Requisição concreta

Mesma abertura bb98 original, SYSTEM record-evidence-v1, USER, fontes,
contrato de atores e schema do dossiê congelado. Mesma Groq direta e candidato
`gpt-oss-120b-groq-free-synthetic-low`, modelo `openai/gpt-oss-120b`,
`reasoning_effort:low`, `include_reasoning:false`, `stream:false`, temperatura
0,65 e schema estrito. Nenhum seed novo, exemplo ou narrativa adicional.

A única diferença proposta no corpo enviado é:

```diff
- "max_completion_tokens": 768
+ "max_completion_tokens": 1536
```

O corpo é definido pelo campo `request.body` do
[dossiê local](record-evidence-request-dossier-2c1cafde-2026-09-07.json),
com essa substituição exata. A comparação offline em memória confirmou somente
esse campo alterado. O corpo alternativo não foi enviado ou salvo como runner.
Hash canônico original: `e646d9e810c248dc293442ecc6582dffdc070c874c11c089c13e34f16852364f`.
Hash canônico proposto: `90a5fffba8a57247439dfa1f9cfba202aeb2dff0182ba9e2235f95673ea6429f`.
Método: UTF-8 JSON, ensure_ascii=false, sort_keys=true, separators=(',',':').
Não são hashes de bytes capturados no tráfego HTTP.

## Orçamento e parada propostos

Uma chamada total, somente opening. Teto total de saída: 1.536 tokens,
incluindo registros, suportes e qualquer raciocínio contabilizado pelo provedor.
O total real de entrada não é fixável por esta proposta: o Console anterior
registrou 2.320, e o pacote permanece idêntico; isso não garante nova contagem.
USER conserva o limite de 2.000 tokens estimados por caracteres/4 e não pode
omitir fontes. Não há Mara, diagnóstico textual/streaming, juiz LLM, retry,
fallback, continuação automática ou reutilização de cota de lote antigo.

Manter deadline de 60 segundos após a espera, um único terminal e intervalo
mínimo de 60 segundos desde outra chamada conhecida. Encerrar após o único
resultado, inclusive qualquer HTTP 400/429, timeout, erro de rota/schema,
rejeição de admissão, cancelamento ou sucesso. Não aumentar o teto outra vez.
Chave apenas pelo prompt protegido após implementação e verificação offline.
Sem contratação, mudança de plano ou acesso às credenciais do Console.

## Observação adicional a preparar somente se aprovado

Identidade experimental separada: `record-evidence-budget-1536-v1`, sem
renomear SYSTEM. Recusar replay CAP-001 e impedir seleção de outros casos,
parâmetros, fontes ou modo narrativo. Reusar os contratos/validadores atuais.

O observador seria exclusivo do diagnóstico e de suas duas mensagens sintéticas
fixas (SYSTEM e USER), preservando adaptadores e retenção de erros do runtime.
Registrar request ID, código HTTP, código seguro, modelo e uso numérico
quando fornecidos, inclusive detalhamento numérico de raciocínio se existir.
Capturar finish_reason somente de campos explícitos e por enumeração
permitida (stop/length/content_filter/tool_calls/function_call; demais unknown).
Campos ausentes continuam unavailable; ausência não vira zero ou false.

Em erro, inspecionar somente em memória até 64 KiB do corpo, sob a mesma
deadline. Ao exceder o limite, registrar observação incompleta e não analisar
um recorte como se fosse corpo integral. Para `failed_generation`, se for
string presente dentro do corpo integral permitido, guardar apenas presença,
comprimento, se json.loads o aceita integralmente e posição numérica de erro
quando houver. Não completar JSON, remover fences, escolher trechos ou salvar
a string recusada. Não persistir mensagem livre, corpo bruto, prompt ecoado,
headers, chave ou campo reasoning. Ausência de finish_reason não será inferida
pelo parser; erro perto do fim é indício, não prova de término pelo teto.

Em sucesso, a resposta candidata completa pode ser guardada como artefato
sintético do experimento; os checks atuais de envelope, suportes, schema final
e admissão são aplicados sem alterações. Revisão semântica ocorre apenas se
existir resposta, separada do diagnóstico operacional e sem aprovação CAP.

## Interpretação pré-registrada

| Resultado | Leitura permitida |
|---|---|
| Envelope válido, uso maior que 768 | Esta realização consumiu mais de 768 tokens contabilizados; viabilidade observada com o novo teto. Não explica causalmente a realização histórica. |
| Envelope válido, uso até 768 | Viabilidade observada; variação entre chamadas continua explicação possível. |
| finish_reason explícito length | Há término por comprimento nesta nova resposta; não retroagir o motivo ao lote antigo. |
| Falha, novamente no teto | Hipótese de orçamento permanece; não aumentar/repetir automaticamente. |
| Falha com contagem completa explicitamente abaixo do teto | Essa contagem não evidencia esgotamento do teto; não determina a causa da falha. |
| Erro estrutural específico | Localiza uma falha de estrutura; também pode ser consequência de corte. Não determina isoladamente sua causa. |
| Corpo ausente/excedido, sem razão explícita | Diagnóstico limitado; não inventar causa. |

## Preparação e aceitação do instrumento

Antes de credencial, verificar offline: diff único do payload; uma chamada
máxima; exclusão de Mara e de modos antigos; teto/deadline/cancelamento; parada
para todas as categorias; preservação de campos indisponíveis; corpo limitado;
conservação literal de fontes; rejeição de replay CAP. Contraprovas devem
assegurar que corpo parcial não é validado, texto de erro/raciocínio/chave não
vaza e um envelope sintático não passa automaticamente pela admissão.

O instrumento estará preparado quando as verificações focadas e a inspeção
do diff passarem, sem alterações no runtime. Isso será preparação técnica;
uma execução real permanece delimitada a uma chamada e não aprova o produto.

## Decisão necessária

Autorizar este diagnóstico significa aprovar sua preparação e verificação
local e disponibilizar uma única execução com teto de 1.536 tokens e os
metadados delimitados acima. Não significa adotar orçamento maior no jogo,
retomar o lote anterior, alterar critérios ou enviar o dossiê ao suporte.

O [desenho executado](record-evidence-hypothesis-c9c01a48-2026-09-07.md)
fixou 768 por chamada e determinou: “Truncamento ou schema inválido é falha
operacional observada, sem aumentar o teto nem tentar de novo.” Aumentar o
teto e criar nova observação exige decisão específica; não é correção de
um defeito local demonstrado. Este documento não concede essa autorização.
