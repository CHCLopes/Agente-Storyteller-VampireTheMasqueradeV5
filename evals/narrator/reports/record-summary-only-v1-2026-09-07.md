# Resumo textual sozinho — preparação concluída

`record-summary-only-qwen-observation-v1` foi executada e analisada sob autorização contínua. PID 26012 confirmado `finished` em `2026-09-07T19:04:30.3081925Z`, exit 0; chave descartada, uma chamada e lote encerrado. [Resultado 21cf338b](record-summary-only-observation-21cf338b-2026-09-07.md): 21 palavras/134 caracteres, dentro do limite, com falha de fidelidade pela transferência da cor da lanterna para a luz. Sucesso operacional não aprova semântica. Não relançar esta preparação. [Metadados históricos e verificações preservados](record-summary-only-v1-2026-09-07.json). O [Qwen inline 94a95216](record-inline-evidence-qwen-observation-94a95216-2026-09-07.md) permanece encerrado e imutável.

A [rubrica offline](record-inline-evidence-rubric-proof-94a95216-2026-09-07.md) está concluída: exemplos autorados distintos demonstram possibilidade representacional, sem provar confiabilidade de modelo. A revisão autorada distingue promoção de certeza, erro de anotação e pressuposição; essas contraprovas também passam a estrutura. Casos de fronteira não alteram critérios históricos.

O [desenho](record-summary-only-design-94a95216-2026-09-07.md) e o [dossiê](record-summary-only-dossier-94a95216-2026-09-07.json) perguntam se Qwen consegue resumir fielmente em até 25 palavras quando se solicita apenas texto. Mantêm USER inteiro, narrativa e source_units completos, manifesto, Groq/Qwen none, temperatura 0,65 e teto 3.072. Mudam SYSTEM e nome/schema da resposta; uma amostra não isola o efeito de cada componente.

## Implementação e verificação

Executor e wrapper são aditivos. O schema contém somente summary, string estrita de 8 a 600 caracteres. Após rota/modelo e schema válidos, response_structure e summary_text são preservados literalmente, inclusive espaços. A revalidação recusa instâncias forjadas com tipos ou limites inválidos. Não há projetor, perguntas, IDs, modalidades, reparo ou admissão de atores.

instruction_measurements registra a contagem Unicode congelada e o cumprimento das 25 palavras. Testes com 25, 26 e 32 palavras confirmam que a medição não altera o exit operacional nem aprova fidelidade. Afirmações presentes serão revisadas contra as fontes; omissões legítimas ficam não informativas nas dimensões omitidas.

| Verificação focada | Testes distintos aprovados |
| --- | ---: |
| Executor, contrato e medição | 82 |
| Wrapper protegido | 136 |
| Fronteira CAP: 25 novos e 93 existentes | 118 |
| Total | 336 |

São 243 novos e 93 existentes, sem falhas pendentes; não houve suíte integral. Executor: 81 casos iniciais e um após corrigir só a fixture para adulterar evidence.provenance.invocation_id, preservando código e expectativas. Wrapper: 102 anteriores inalterados mais 34 finais (20 novos de evaluation_status e 14 regressões/sintaxes, 74,27 s); os repetidos não foram somados novamente. A revisão demonstrou a ausência da guarda de status, corrigida em cinco linhas e revalidada. Falhas intermediárias e dois RED anteriores à guarda CAP estão documentados no JSON e excluídos das contagens finais. O aviso python_multipart é preexistente.

Revisão independente sem achados restantes. Integração real PS7 com SecureString vazia: preflight final aprovado, exit 3 na validação da credencial, zero chamadas/artefatos e stderr vazio. A auditoria final confirmou corpo/USER exatos, 39 fingerprints históricos e 12 brutos históricos intactos. CAP recebeu somente 14 linhas adicionais, sem remoções. Hashes e evidências finais substituem apenas os registros intermediários desta preparação.

## Próximo passo e limites

A execução desta preparação está encerrada e sua evidência foi analisada. Não abrir outra janela nem relançar scripts/run_groq_summary_only_probe.ps1. O próximo trabalho autorizado é preparar fontes novas em par contrastivo, com o mesmo SYSTEM/schema/parâmetros; está em curso, sem nova execução pronta ou envio. A chave desta execução foi descartada; não há ação humana pendente neste lote.

Limites históricos executados: uma chamada, teto 3.072, espera local mínima de 60 segundos e deadline de 60 segundos após espera/preflight. O lote foi encerrado; brutos preservados e operação, concisão e fidelidade analisadas separadamente. Sem diagnóstico, retry, fallback, geração narrativa, juiz LLM, novo caso, segunda condição ou escalada para reparar a amostra. Omissão da hipótese não prova capacidade de resumir sua incerteza nem autoriza repetir para preenchê-la.

Os bloqueios históricos permanecem. Perguntas, anotação modal, oito campos, atores, runtime e CAP-001 seguem sem aprovação; não há nova autorização genérica pendente.
