# Preparação concluída — target-spans com teto 3.072

**Estado posterior à preparação:** execução d4491c21 encerrada; nenhuma chamada ou chave pendente neste lote. [Resultado analisado](record-evidence-target-budget-observation-d4491c21-2026-09-07.md). As instruções de execução abaixo são registro histórico.

Data: 07/09/2026. Status: **implementado e verificado; somente a entrada protegida da chave permanece como dependência humana**. A autorização contínua do usuário inclui esta observação e os próximos passos necessários, sem nova confirmação de hipótese ou lote.

A [observação anterior](record-evidence-target-spans-observation-26547182-2026-09-07.md) terminou explicitamente por comprimento e não disponibilizou envelope. O [desenho fixado](record-evidence-target-budget-3072-design-26547182-2026-09-07.md) mantém o request inteiro e muda apenas `max_completion_tokens: 1536 → 3072`. O [registro JSON](record-evidence-target-budget-3072-v1-2026-09-07.json) contém hashes, parâmetros e verificações completos.

## Implementação e limites

Novos executor `scripts/evaluate_narrator_record_target_budget.py` e wrapper `scripts/run_groq_record_target_budget_probe.ps1`. Identidade experimental `record-evidence-target-spans-3072-v1`; o prompt continua `record-evidence-target-spans-v1`. SYSTEM, USER, fontes, schema, temperatura e raciocínio ficam preservados. O preflight restaura somente o teto 1.536 para reproduzir a baseline, e exige igualdade integral com o dossiê de 3.072.

Uma chamada total, apenas opening bb98. Groq direta / openai/gpt-oss-120b, raciocínio low, include_reasoning false, temperatura 0,65, structured sem streaming. Espera inicial 60 segundos e deadline de 60 após a espera. Nenhuma Mara, narrativa nova, diagnóstico, retry ou fallback. Qualquer resultado encerra este lote; o runner não amplia seu próprio teto.

A subclasse de observação muda somente a guarda do corpo aprovado. Herda sanitização, metadados permitidos, limite de erro de 64 KiB, deadline e cancelamento. Nenhum corpo bruto de erro ou conteúdo de raciocínio é persistido. Referências/intervalos continuam sendo validados sem reparo; schema inicial, envelope, schema final, admissão e revisão semântica são etapas separadas.

Corpo canônico novo: `5e376cb4cdee903b0f1a5bbcd3a14fa181d966656102f4c4985d87b4eb9ea186`.
SYSTEM: `fdba32bb00dd20144ec5553d72635c3a2388fee9c4621486f3bddd6f3b1721cb`.
USER: `42eb962a2042c00b2030d5cb63b1f7e1f17894158e5df61cdcad0d317c32a480`.
São fingerprints da reconstrução, não captura de tráfego. O SYSTEM mantém sua menção histórica a 768 para isolar a mudança do parâmetro da API; essa limitação permanece explícita.

## Verificação

**294 testes distintos passaram: 103 novos e 191 existentes, sem falhas ou skips.** Não é uma nova suíte integral, e os 479 testes da preparação anterior não foram somados.

| Grupo | Aprovados | Tempo |
|---|---:|---:|
| Replay novo e fronteiras anteriores | 212 | 3,89 s |
| Novo executor | 35 | 27,92 s |
| Novo wrapper | 47 | 94,48 s |

Smoke repetido e rodadas RED foram excluídos da contagem. Apenas o aviso preexistente de `python_multipart`. Usados o venv existente, dotenv e bytecode desabilitados e isolamento de rede/persistência do pytest.

Revisões independentes do diff e da interpretação não encontraram defeitos materiais. O preflight real confirmou o corpo exato e os mesmos hashes de SYSTEM e USER. A integração com SecureString vazia aceitou o preflight e parou com exit 3 exatamente em credential validation: stderr vazio, zero chamadas externas, nenhum artefato criado/removido e 17 hashes preservados.

As contraprovas cobrem tetos incorretos, uso repetido, streaming, stop/length, intervalos inválidos sem correção, literalidade das perguntas, proveniência, credencial, cancelamento, pacing, deadline e drift. O avaliador legado recebeu somente duas guardas, 12 linhas adicionais, para recusar esta identidade como avaliação CAP. API, contratos, validadores e instrumentos/resultados anteriores permanecem preservados.

## Próximo passo

Abrir uma única janela dedicada do PowerShell 7 para a chave protegida e executar o wrapper. Se já existir janela aguardando ou rodando, não iniciar outra. A chave não deve ser escrita no chat, lida de arquivo ou recuperada do Console. Depois, analisar summary/JSONL e prosseguir autonomamente conforme o resultado.

A comparação histórica permanece sem conclusão causal A/B. Sucesso operacional não garante fidelidade, cobertura ou aprovação CAP/runtime. Uma nova falha de comprimento orientará reavaliação da tarefa; não dispara uma escalada mecânica de tetos.
