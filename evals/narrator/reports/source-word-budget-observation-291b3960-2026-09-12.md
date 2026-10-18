# Diagnóstico de orçamento de palavras — lote 291b3960

Lote `291b3960-55a5-4fdc-a9f4-31d9cfa695f7` encerrado em 12/09/2026 com
`finished/1`. Foram quatro chamadas HTTP 200/stop, quatro schemas e rotas válidos,
duas propostas admitidas e duas recusadas por agência. Nenhum slot ficou sem envio.
O launcher concluiu a auditoria offline e preservou o exit 1 do avaliador.

Todos os textos respeitaram o gate original de palavras. Os dois textos B também
cumpriram a margem solicitada. Como os dois controles A passaram ao mesmo gate,
o resultado não diferencia a hipótese de vantagem da margem. A versão B permanece
experimental; o lote não escolhe modelo, não altera default e não aprova CAP-001.

## Extensão, admissão e disponibilidade

| Slot | Contexto / braço | n | q | Total | Gate original | Margem B | Resultado registrado |
|---|---|---:|---:|---:|---|---|---|
| 1 | Relojoaria / A | 74 | 3 | 77 | Passou | Atende, sem ter sido solicitada | Recusa de agência |
| 2 | Relojoaria / B | 74 | 4 | 78 | Passou | Atende | Recusa de agência |
| 3 | Pavilhão / B | 99 | 5 | 104 | Passou | Atende | Admitido |
| 4 | Pavilhão / A | 118 | 4 | 122 | Passou | Não atende, sem ter sido solicitada | Admitido |

A margem é uma medida separada, não um gate novo para A. A recusa dos slots 1 e 2
é `scene_player_agency_violation`; não houve erro de extensão, schema, provedor,
rota ou diagnóstico operacional. A credencial funcionou nesta execução concreta.

Uso reportado: 4.962 tokens de entrada e 598 de saída, total 5.560. Nenhuma saída
excedeu o teto de 768 tokens. Custo e tokens de raciocínio permanecem indisponíveis.
Não houve retry, fallback, corte, reparo, commit, SQLite ou dados de campanha.

A auditoria independente recompôs metadados, corpos, pareamento de USER, diferença
única do SYSTEM, contagens, uso, sequência e hashes sem repetir o verifier.
Intervalos entre inícios HTTP: 60,963940; 60,869374; 60,846559 segundos. Espera
inicial até criar o primeiro pedido: 60,490008 segundos. Duração local total:
244,930450 segundos. Não houve sobreposição nem término após o deadline.
Os tempos são locais e não medem chegada remota ou consumo global da conta.

Checkpoint da observação: `eval-results/checkpoints/source-word-budget-observation-291b3960-20260912/manifest.json`,
41 cópias verificadas, SHA-256 `520fb3c29474a4142cebd7a3b1092337f5c8072074245cf2b0785b012d9184b7`.
Inclui os cinco artefatos finais, fontes congeladas, auditoria e revisão narrativa.
Summary original: `265c85a6259ca95d88865e795eae081f03a08d9ed42d3c7a77280c4986fce1e5`;
JSONL: `76f44a05b9b1720612970787731060b3e8406088499671e19e956f5d9af02dba`.
Integridade local não comprova autenticidade externa; o corpo HTTP completo de
sucesso não foi arquivado separadamente da proposta e de seus metadados.

## Leitura narrativa

Na Relojoaria, A aponta um relógio de bolso com uma agulha que treme e um ponteiro
parado. O gesto oferece algo observável, mas a razão de priorizar esse relógio
antes do fechamento fica implícita. B dá uma informação mais direta pela fala de
Bela: o relógio não anda há dias. Ainda falta desenvolver sua relevância específica
para a pergunta. Ambos conservam a iniciativa do jogador na pergunta final.

No Pavilhão, há avanço físico pequeno em ambos: o pano ou a bandeja deslizam mais,
e a ameaça já presente se intensifica. B acrescenta uma leve reação de Caio. A
descreve mais o ambiente e insiste na espera. Não é repetição literal total, mas
a novidade oferece pouco além do risco que a fonte já apresentava.

Ambos os textos do Pavilhão dizem que a porta “continua” aberta ou entreaberta.
A fonte só dizia que a passagem entre a mesa e a porta estava livre; não estabelecia
a abertura da porta. Essa continuidade não está sustentada pela fonte. Quem abriu
a janela continua desconhecido. B também tem a construção pouco clara “Suas mãos
continuam paradas [...] observando a cena”, que liga observação às mãos.

A leitura principal não encontrou ação, decisão ou emoção do jogador imposta nos
dois textos recusados. As ações descritas pertencem a Bela/ela. Isso motiva uma
reprodução local do detector; não altera a recusa guardada nos artefatos do lote.
A revisão independente concordou com a interpretação não discriminante do orçamento,
o atendimento mais explícito de C1/B, o progresso modesto e a continuidade não
sustentada da porta. Não se alega cegamento: os rótulos A/B e a hipótese eram conhecidos.
Nenhum resultado de política foi alterado pela leitura semântica.

## Diagnóstico local de contexto de política

A reprodução identificou a omissão de `npc_aliases` nas chamadas do harness ao
validador. O elenco canônico e os aliases confiáveis de política são campos
separados por contrato. Nos dois textos C1, “ela” chegou ao detector com
`subject=ambiguous_pronoun` e sem antecedente reconhecido como NPC. Os trechos
envolviam mover/observar ou afastar/observar; as perguntas finais não causaram a recusa.

Os quatro resultados originais foram reproduzidos. Uma contraprova que forneceu
somente `npc_aliases=('Bela',)` em C1 admitiu os mesmos textos pelas regras já
existentes, mantendo C2 aceito. Outras 22 verificações exploratórias de agência
e antecedente distante tiveram os resultados esperados: aliases ausentes/errados,
antecedente jogador/desconhecido, ação ou emoção imposta e pergunta pressuposta
continuam recusados. Isso não é uma nova suíte pytest e não aumenta a contagem
dos testes da preparação.

A inspeção de código confirmou que a composição local B configurada e o comparador
retido já passam aliases confiáveis por configuração, cápsula e executor. Não foi
executado novo runtime nem demonstrado defeito nesse caminho. O achado está no
caller do diagnóstico encerrado. Não se alterou núcleo, gate, modelo, prompt ou
harness para reclassificar esse lote. Um futuro caller deve fornecer o contexto
explicitamente e congelá-lo, sem inferir aliases da narrativa gerada.

Anexo independente: `eval-results/checkpoints/source-word-budget-agency-diagnosis-291b3960-20260912/manifest.json`,
10 cópias verificadas, SHA-256 `b9636e973a7be4b806c99350e8f3e0b2fc5ead6fd2a4f0133d419802c1fa127f`.
Os 30 arquivos acompanhados na reprodução permaneceram íntegros; não houve chamada
ao provedor nem edição dos artefatos históricos.

## Continuidade

O trabalho local deste diagnóstico está concluído. Não adotar o SYSTEM de margem
nem preparar outra amostragem equivalente apenas trocando nomes de cenas. A
[matriz de evidências](source-model-choice-status-2026-09-12.md) separa o que os
testes técnicos comprovaram do que continua pendente na escolha do narrador.

Foi concluída uma [proposta concreta de recorte de uso B](../../../plan/proposal-source-player-trial-scope-1.md):
uma cena conhecida, NPC presente, objetivo imediato, diálogo/espera e acesso
somente local. O artefato técnico com respostas autoradas já existe; não equivale
a um jogo completo ou a ligação interativa Groq pronta. A aceitação desse recorte
para ativação é uma decisão humana de produto prevista em DEP-005. Não se pede
novamente aprovação da direção B ou das correções técnicas. A preparação local
da ligação interativa pode prosseguir sem inferência antes dessa aceitação e está
sendo investigada em escopo separado. Nenhum novo ensaio foi iniciado.

As quatro propostas originais, seus estados e as ausências de medidas permanecem
intactos. O comparativo 61b83a2f e o diagnóstico 291b3960 não serão reabertos ou
reexecutados para procurar um resultado favorável. Melhorar uma atribuição de ator
no validador não corrige a utilidade narrativa do modelo nem comprova qualidade.
