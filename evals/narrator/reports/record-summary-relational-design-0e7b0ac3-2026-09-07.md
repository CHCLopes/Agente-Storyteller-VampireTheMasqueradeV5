# Seleção de afirmações completas — par exploratório prévio em 07/09/2026

Status: preparação autorizada sob continuidade após o encerramento do par summary-color 0e7b0ac3. Nenhum envio foi feito durante esta preparação. Não se repetem gallery-reflection de um lote anterior (é fonte inédita), reading-room, station-clock, observatory, arquivo municipal, biblioteca ou oficina.

## Pergunta e fundamento

**Em uma fonte nova idêntica nos dois braços, orientar seleção de poucas afirmações completas produz uma descrição mais explícita e fiel das relações retidas que a instrução de resumo congelada?**

Os dois resumos do par anterior tiveram sucesso operacional e 20 palavras, mas tornaram ambígua a relação de cor; a segunda resposta também deixou sem suporte claro a posição da luminária sobre o mapa. Esse resultado é compatível com perda de relações na compressão em inventário, sem demonstrar sua causa. Uma nova rodada apenas de fontes sob a mesma instrução ampliaria exemplos sem examinar essa hipótese de tarefa. Em vez disso, registram-se um controle novo e uma variante em um único lote delimitado.

Este é um par exploratório com uma observação por braço, ordem fixa controle→variante. Não é A/B completo, teste causal, estimativa de taxa ou comprovação de superioridade. Variação estocástica, ordem e condições de serviço não são controladas. O custo máximo continua sendo duas chamadas de 768 tokens.

## Fonte única nova

Case_id gallery-reflection:

> Na galeria vazia, um espelho reflete uma tapeçaria pendurada diante de uma janela fechada. Um catálogo permanece sobre o banco; à direita da entrada, duas molduras vazias estão apoiadas contra a parede.

A fonte tem 32 palavras. O arquivo conserva exatamente seis chaves inline. n0 contém a primeira frase e um espaço final; n1 contém a segunda frase inteira. As unidades completas concatenam literalmente a narrativa. Nenhuma rubrica, análise de fonte, gabarito ou exemplo corretivo integra o USER. Sua string inteira, inclusive case_id e IDs de unidades, é byte a byte idêntica nos dois pedidos.

## Braços e alteração isolada de pedido

control usa o SYSTEM record-summary-budget-v1 congelado. relational usa record-summary-relational-v1, derivado por substituição somente do parágrafo FORMATO. A variante preserva até 25 palavras, 8 a 600 caracteres e todas as proibições; orienta poucas afirmações completas com participantes e relações explícitos, omitindo afirmações inteiras quando não couberem. O front matter muda apenas o nome da variante e não integra o HTTP. Autoridade, fonte, certeza, agência e teto de 768 permanecem iguais nos demais parágrafos. Não se adicionam exemplos de reflexão, cor ou respostas corretas.

Entre os corpos HTTP somente messages[0].content difere. Permanecem USER, response_format nativo estrito SummaryOnlyProposal, protocolo de saída record-summary-only-v1, Qwen qwen/qwen3.8-27b por Groq oficial, reasoning_effort=none, temperatura 0.65, stream=false, include_reasoning ausente e max_completion_tokens=768. O protocolo de entrada continua record-inline-evidence-v1.

Os metadados distinguem arm_id de case_id. Há um caso e dois braços, não duas fontes independentes nem alteração artificial do USER para diferenciar chamadas. As operações são summary-relational.control e summary-relational.relational; pedidos, prompts, observações e medições são ligados ao braço e ao mesmo caso. O dossiê contém um mapa ordenado explícito, validado antes da chave.

## Critérios prévios separados do modelo

Avaliar cada resposta antes de compará-las. Uma afirmação retida deve conservar os participantes e a relação que a fonte expressa. O espelho reflete a tapeçaria; a tapeçaria está pendurada diante da janela fechada. Essa posição não foi atribuída ao espelho. O catálogo está no banco; as duas molduras vazias apoiam-se na parede à direita da entrada. Não se exige mencionar todos esses fatos ou conservar a redação original.

Omissão é permitida e fica não informativa na dimensão omitida. Relação explicitamente alterada é falha. Se a redação deixar o vínculo ambíguo, registrar ambíguo, sem escolher interpretação favorável ou desfavorável para fabricar um resultado. Mais objetos mencionados não significam melhor memória; menor contagem de palavras não demonstra fidelidade. Comparar relações retidas fiéis, ambíguas, omitidas ou sem suporte, sem um gabarito textual único.

Uma melhora observada vale somente para esse par de saídas. Ambas fiéis não estabelecem confiabilidade; ambas omissas/ambíguas não estabelecem equivalência; uma falha operacional não é falha semântica. A contagem de até 25 palavras permanece medição instrucional, não gate semântico nem critério que impede o segundo braço.

## Identidade, limites e parada

Purpose/probe_kind summary_relational_qwen_probe; experimento record-summary-relational-qwen-observation-v1; target summary-relational-qwen-3.8-27b-groq-free-synthetic-nonthink. Persistir summary_relational_call/skip com arm_id e case_id. Esses registros ficam fora do replay CAP.

Máximo de dois envios, um por braço, ordem control→relational, 768 tokens cada e 1536 totais. Espera local inicial conservadora e intervalo mínimo entre inícios de 60 segundos; deadline de 60 segundos iniciado após cada espera. Preflight sem chave/cliente verifica fonte única, prompts, schema, mapa de braços e corpos exatos. A segunda chamada é um braço previamente registrado, não retry da primeira.

Parar na primeira falha de provedor/transporte, deadline, rota indisponível/divergente, schema, processamento local ou cancelamento. Persistir o braço restante como skip. Não substituir, preencher depois, repetir, usar fallback, diagnóstico, outro modelo ou escalar esforço/teto. Resultado semântico ruim ou excesso de palavras não interrompe o segundo braço se o primeiro foi operacionalmente válido. Fechar após as duas posições ou a primeira falha, sem ciclo de reformulações dentro deste experimento.

## Escopo técnico e validação

Reusar o contrato, adapters e observador existentes sem mudanças de runtime. Criar novos assets e executor/wrapper aditivos a partir do fluxo de duas chamadas, adaptando explicitamente o eixo caso→braço e preservando a fonte única. Não criar engine genérica, monkeypatch global, reparo de saída, anotações de evidência, perguntas ou oito campos.

Testes focados verificam USER idêntico, SYSTEM exclusivo por braço, mapa/ordem exatos, recusa de braço/caso trocados ou forjados, payload por operação, orçamento, espera/deadline, parada, skips e persistência. O wrapper valida metadados/saída por braço, status/exit, preflight antes de SecureString e restauração do ambiente. Uma integração real com chave vazia antecede a dependência humana de inserção segura da chave. A preparação não chama o provedor.

Schema, rota e conclusão sem erro local definem resultado operacional. Preservar texto literal, uso reportado ou desconhecido e observação sanitizada. O bruto mantém semantic_fidelity_review not_performed/approval null; a avaliação autorada é separada. Nada promove qualidade narrativa, memória de produto, runtime, modelo, provedor ou CAP-001.
