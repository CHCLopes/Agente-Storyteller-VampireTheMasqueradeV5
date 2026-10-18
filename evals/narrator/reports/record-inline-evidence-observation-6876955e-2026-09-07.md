# Evidência inline — lote 6876955e encerrado

A única observação de `archive-vibration` terminou com **sucesso operacional, código 0, e falhas semânticas e de instrução**. Houve uma chamada Groq direta a `openai/gpt-oss-120b`, HTTP 200 e `finish_reason: stop`; rota, schema e projeção passaram. O resultado estrutural não satisfaz por si só os [critérios prévios](record-inline-evidence-observation-design-d1b9a968-2026-09-07.md).

Batch `6876955e-73f6-4bd3-be22-1d156a065449`; PID 24984 confirmado `finished` em 2026-09-07T17:31:28.4972252Z. A chave foi descartada e não há entrada de credencial pendente para este lote. O limite de uma chamada está esgotado; não relançar a janela, repetir o pedido, completar a oficina ou retornar às variações da abertura.

## Evidência operacional e integridade

O [summary original](../../../eval-results/20260907T173025Z-22fb64ac-3d6e-4ad1-9255-12014c3222de/summary.json) e o [JSONL original](../../../eval-results/20260907T173025Z-22fb64ac-3d6e-4ad1-9255-12014c3222de/gpt-oss-120b-groq-free-synthetic-low.jsonl) permanecem intactos. Seus SHA-256 são, respectivamente, `0726add81d3e95543ba837e6f4bb7ad3a36385d96b1401b9c72feb7266615824` e `b39eab2f5215568aa99af75bac32e559a893abaab4fb63f246c5957afbef2624`. [Registro da análise, fontes e auditoria](record-inline-evidence-observation-6876955e-2026-09-07.json).

A auditoria independente, concluída antes do avanço para Qwen, reconstruiu exatamente preflight, summary, projeção e auditoria de segmentos; não encontrou contradição operacional acionável. Naquela auditoria, pedido `30d2713c…`, USER, schema e fingerprints de implementação correspondiam à [preparação preservada](record-inline-evidence-observation-v1-2026-09-07.json). Os 283 testes pertencem à preparação: nenhum teste ou nova chamada foi executado para este encerramento documental.

Após a análise e auditoria deste lote, a preparação separada de Qwen acrescentou 12 linhas à guarda CAP em `scripts/evaluate_narrator_models.py`: hash histórico `ee354bc4550cd408130dbc26473d02853502b2b8bb881a50b224edc1696a3b85`, novo `c725c94ebc76b5e47895214fcf4e887b61da6daa650f191738e97db650b89dea`. O registro histórico conserva o primeiro hash; não se afirma que o arquivo compartilhado atual permaneceu idêntico depois dessa mudança. Brutos, contrato, executor e wrapper desta observação permanecem preservados.

O provedor reportou 1.116 tokens de entrada e 332 de saída, total 1.448; 164 tokens de raciocínio foram contabilizados, sem acesso ao conteúdo. Custo indisponível. Mantiveram-se low, temperatura 0,65 e teto 3.072, sem retry, fallback ou diagnóstico. O intervalo UTC entre início do run e início do adaptador foi 60,507403 s; esses timestamps corroboram a sequência local, mas não reconstituem a espera monotônica exata nem a chegada remota. A duração local medida foi 1,817394 s.

## Revisão integral dos três segmentos

| Campo e modalidade | Texto retornado | Avaliação |
| --- | --- | --- |
| `summary[0]`, `established`, `n0` | “No arquivo municipal, a luz de uma lanterna vermelha ilumina uma mesa coberta de pastas.” | Fiel. Cor da lanterna, iluminação, mesa e pastas foram preservadas. Não se afirmou que a luz é vermelha. |
| `summary[1]`, `suggested`, `n1` | “Perto da porta fechada, uma vibração leve sugere que talvez exista um motor funcionando do outro lado.” | A redação conserva `sugere` e `talvez exista`, sem confirmar o motor. Contudo, o segmento único mistura porta fechada/vibração estabelecidas com hipótese de motor, contrariando a separação de modalidades instruída. |
| `open_questions[0][0]`, `unresolved`, `n1` | “O motor do outro lado está realmente em funcionamento?” | A pergunta trata motor e posição como referente definido e põe em dúvida somente o funcionamento. A fonte também deixa incerta sua existência. O rótulo `unresolved` não elimina essa pressuposição. |

O resumo tem **32 palavras e 190 caracteres**, excedendo a instrução de até 25 palavras. A contagem usa a mesma expressão de palavras registrada na análise, que separa `pastas.Perto` em duas palavras. O modelo omitiu o espaço necessário entre os segmentos e a projeção produziu literalmente **“pastas.Perto”**. A pergunta tem nove palavras e 54 caracteres. A lista contém uma questão, quantidade permitida; não se exige uma segunda pergunta nem uma paráfrase única como gabarito.

Os intervalos locais `/summary` `[0,88)` e `[88,190)`, e `/open_questions/0` `[0,54)`, reconstruíram exatamente os textos. A ausência do separador é uma falha de emissão frente à instrução; **não há defeito demonstrado no projetor** e nenhum espaço foi inserido como reparo. O limite de 25 palavras e a correspondência semântica das modalidades não são novos gates estruturais.

A posição da vibração junto à porta fechada foi preservada, assim como a posição apenas hipotética do motor no resumo. Não foram acrescentadas ações do jogador ou de NPCs. As dimensões principais deste caso foram retidas e puderam ser avaliadas; uma dimensão-alvo omitida seria não informativa, não uma falha automática. IDs existentes e intervalos corretos não comprovam implicação, atomicidade ou cobertura universal.

## Encerramento e continuidade

Os marcadores automáticos originais de revisão semântica e cobertura continuam `not_performed`, com aprovação `null`. Este relatório acrescenta uma avaliação semântica do agente em documento separado; não altera o resultado bruto, os critérios, o schema, o projetor ou a guarda CAP. A tarefa pediu somente resumo e questões abertas; os oito campos e a admissão de atores não foram avaliados.

Uma amostra com SYSTEM, USER, caso e schema próprios não demonstra melhoria causal nem frequência de erro. Runtime e CAP-001 continuam sem aprovação. O próximo trabalho autorizado é **investigar e preparar uma observação delimitada com Qwen**. Essa investigação/preparação está em curso, com conclusão ainda pendente; seus artefatos próprios devem ser conferidos antes de agir. Este encerramento não declara a próxima execução pronta e não realizou chamada Qwen. A continuidade técnica não depende de nova aprovação genérica; eventual chave ou intervenção direta continua dependência humana somente quando necessária.
