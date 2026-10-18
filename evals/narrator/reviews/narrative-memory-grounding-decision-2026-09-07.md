# Direção B aprovada: autoridade dos registros narrativos

Status: direção B aprovada pelo usuário em 07/09/2026: “Concordo. A direção B parece mais promissora. Prossiga”. A decisão autoriza avançar no plano delimitado de representação, admissão e verificação e nas etapas técnicas cobertas pela autonomia contínua. Não seleciona um verificador semântico, modelo, runtime, migração de saves ou CAP-001 por arrasto. A comparação abaixo registra as alternativas consideradas; o código correspondente ainda não está declarado implementado.

O contrato atual permite que H6 proponha narrativa, resumo, fatos e pendências em campos distintos. Uma política determinística admite novidades dentro de limites; o resumo admitido é copiado para cena, evento, candidato de memória e contexto. A especificação reconhece que essa política não prova qualidade semântica geral. A [consolidação de seis respostas](record-summary-semantic-corpus-v1-2026-09-07.md) mostra por que referências corretas e concisão não bastam: o vínculo de uma cor ou posição pode mudar ou ficar ambíguo.

A investigação separou um defeito local de origem no fallback de resumo vazio, tratado na correção correspondente, dessa fronteira de produto. Corrigir esse helper não oferece uma prova de fidelidade dos resumos normalmente admitidos.

## Alternativas concretas

| Alternativa | Comportamento e superfície | Limite e decisão necessária |
| --- | --- | --- |
| A — Preservar a admissão atual e manter o candidato em avaliação | Permanecem os campos abstrativos n/s/f/t/r e o commit existente. Rótulos de fidelidade continuam externos às verificações estruturais. Não há promoção do candidato que falhou ou ficou indeterminado. Nenhuma mudança de arquitetura é necessária para manter esse estado. | O risco entre narrativa e registro permanece conhecido. Aprovação futura de produto exige evidência adequada e aceitação humana; não se obtém essa aprovação repetindo as fontes encerradas ou alterando critérios depois do resultado. |
| B — Revisar o contrato de canonização para separar fonte e interpretação | A narrativa admitida permanece uma fonte identificável. Registros derivados carregam vínculos e um estado de admissão explícito; existência da proposta ou da referência deixa de representar confirmação semântica. Um derivado sem suporte suficiente não pode entrar silenciosamente em evento, cena, memória ou contexto como fato confirmado. A implantação alcançaria contrato, admissão, projeção, turno, persistência e recuperação, com versão/migração examinadas antes de escrever dados. | Exige decidir quais representações podem ser aceitas mecanicamente e o que ocorre quando a fidelidade fica indeterminada. Citação/intervalo literal demonstra origem, não equivalência: cortes podem perder hipótese, negação, sujeito ou contexto. Não há solução geral já comprovada. |

A opção B precisaria preservar as decisões existentes: agência e mecânica determinísticas, visibilidade, fontes imutáveis, commit transacional e ausência de fallback silencioso. A regra atual é não consumir o turno quando sua admissão falha; entregar narrativa com memória pendente seria outra mudança de produto e não está embutida nesta proposta.

Uma chamada adicional obrigatória por turno não é detalhe autorizado por arrasto: [ALT-004](../../../plan/architecture-llm-memory-turns-1.md) a rejeita como padrão devido a latência, custo e dependência. Esta proposta não escolhe juiz LLM, provedor adicional ou API paga.

## Critérios para qualquer revisão futura

- A origem de cada campo deve ser rastreável sem alterar fontes anteriores.
- Separar existência de referência, correspondência textual e admissão semântica. Nenhum dos dois primeiros resultados deve afirmar automaticamente o terceiro.
- Preservar modalidade, participantes, negação, visibilidade e referências; manter casos ambíguos indeterminados em vez de convertê-los em fatos.
- Provar que conteúdo recusado ou pendente não reaparece no evento, cena quente, memória episódica, consolidação ou contexto como confirmado.
- Validar o caminho completo em isolamento, incluindo sucesso, rejeição e ausência de commit parcial. Não importar saídas experimentais para replay CAP.
- Explicitar o impacto na concisão e no orçamento. Copiar texto integral pode preservar formulação e exceder o limite; extrair um fragmento pode alterar sentido.

## Recomendação e fronteira de autoridade

Recomendo uma decisão explícita sobre B antes de outra tentativa de resolver o mesmo problema apenas por redação de SYSTEM. A recomendação é rever a autoridade dos registros; não afirma que vínculos literais sozinhos resolvem fidelidade. B é a direção aprovada. A descreve o comportamento implementado antes desta aprovação, cuja substituição deve seguir o plano e a verificação.

A pergunta de produto é se registros abstrativos continuarão podendo ser canonizados pela política atual ou se o contrato deverá exigir uma admissão de fidelidade distinta da presença da proposta. Essa escolha muda a autoridade de canonização e o tratamento do turno indeterminado. A seção Authority das instruções AGENTS.md fornecidas pelo usuário reserva novas direções arquiteturais à decisão humana. Isso é diferente de pedir autorização de nova observação ou correção local, que já foi concedida.

A escolha de B já foi concedida e não deve ser solicitada novamente. A etapa atual é preparar o plano delimitado com representação, comportamento de falha e verificação definidos, preservando os limites anteriores. Nenhum lote, entrada de chave ou migração automática está agendado por este registro.
