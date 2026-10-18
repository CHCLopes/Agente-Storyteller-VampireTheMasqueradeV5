# Preparação de record-evidence-target-spans-v1

Data: 07/09/2026. Status: **preparação concluída e observação posteriormente executada**. O lote `26547182` terminou por comprimento e sua [análise está concluída](record-evidence-target-spans-observation-26547182-2026-09-07.md). Não há chave ou chamada pendente neste lote.

O usuário autorizou explicitamente prosseguir com novas observações necessárias à continuidade, mantendo dependência humana somente para chaves, credenciais e intervenções diretas. Isso supera o pedido histórico de autorização específica do [desenho target-spans](record-evidence-target-spans-hypothesis-b129ceaa-2026-09-07.md) e do draft associado. Não solicitar confirmação adicional desta observação nem das próximas etapas necessárias.

## Desenho fixado antes da chamada

Uma abertura bb98, Groq direta / openai/gpt-oss-120b, reasoning low, include_reasoning false, temperatura 0,65, teto 1.536, sem streaming. Espera inicial conservadora de 60 segundos e deadline de 60 após a espera. Nenhuma geração narrativa, Mara, diagnóstico, retry ou fallback. Cada novo resultado encerra este lote, é analisado e orienta o próximo passo autônomo.

Somente o SYSTEM acrescenta a explicação dos intervalos no campo derivado. USER, schema, contratos, fontes e parâmetros são iguais ao lote b129ceaa. Corpo canônico: `8138c098ec49cdc768e7c5d9fe19cc952001939f1c54af11bdb1241762526a09`; SYSTEM: `fdba32bb00dd20144ec5553d72635c3a2388fee9c4621486f3bddd6f3b1721cb`. A menção histórica a 768 no SYSTEM permanece deliberadamente, para isolar o esclarecimento dos índices; o teto transmitido ao provedor é 1.536.

O executor e o wrapper têm identidade própria. O observador seguro é herdado, com guarda exclusiva para o novo corpo; o observador e executor de orçamento permanecem congelados. Não flexibilizar os intervalos nem corrigir respostas. Schema inicial, envelope, schema final, admissão e revisão semântica continuam etapas distintas. Nenhuma amostra, nem a autonomia de execução, constitui aprovação automática do produto.

## Verificação concluída

**479 testes distintos passaram: 188 novos e 291 existentes, sem falhas ou skips.** São grupos focados disjuntos, não uma nova suíte integral. O [registro JSON](record-evidence-target-spans-v1-2026-09-07.json) contém comandos, hashes e proveniência completos.

| Grupo | Aprovados | Tempo |
|---|---:|---:|
| Fronteiras de replay | 191 | 3,51 s |
| Executor/observador de orçamento anteriores | 121 | 57,12 s |
| Novo executor | 68 | 63,66 s |
| Contraprovas adicionais de UUID | 3 | 0,50 s |
| Novo wrapper | 96 | 192,86 s |

As três contraprovas foram acrescentadas após o grupo principal, sem mudar o executor. Os 68 deselected dessa rodada não são skips; smoke e rodadas RED não foram somados. Apenas o warning preexistente de `python_multipart`. Venv existente, dotenv desabilitado, sem bytecode e com os controles de rede/persistência do pytest.

A revisão independente não encontrou problema material no executor. O preflight reconstruído confirmou o corpo exato e o mesmo USER de b129ceaa. Na integração real do wrapper com SecureString vazia, o preflight foi aceito e a execução terminou com código 3 exatamente em credential validation: stderr vazio, nenhuma chamada externa, nenhum artefato criado/removido e 17 hashes preservados.

Os casos cobrem corpo diferente, uso repetido, streaming, cancelamento, espera e deadline, drift, identificadores, captura de saída, proveniência, intervalos inválidos sem reparo e ausência de aprovação semântica automática. O avaliador legado recebeu somente 12 linhas adicionais para rejeitar replay target-spans; contratos, validadores, runtime, executor/observador anteriores e artefatos históricos permaneceram preservados.

## Execução concluída e continuidade

A chave foi inserida na janela protegida e o wrapper executou uma chamada. O launcher confirmou `finished`, exit 1, às 14:19:56 UTC. HTTP 200/length, saída1.536 e raciocínio1.031; nenhum envelope disponibilizado. O estado anterior de espera de credencial é histórico e não exige reabrir a janela.

O [próximo desenho](record-evidence-target-budget-3072-design-26547182-2026-09-07.md) mantém o SYSTEM e muda somente o teto da API para3.072. Sua preparação segue a autorização contínua, sem nova confirmação. Depois das verificações, apenas a entrada protegida da chave poderá exigir atuação humana. Não reinterpretar a execução encerrada como retry ou saldo de chamadas.
