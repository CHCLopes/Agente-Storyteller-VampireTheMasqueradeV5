# Continuidade de fonte integral — desenho Pátio

Esta observação suplementar terá um caso sintético novo, `courtyard-observe-wait`, após a correção comprovada do falso negativo de “O que fazes?”. O lote Estufa f97a8568 foi encerrado com rejeição da primeira pergunta e nenhum segundo envio; não testou a passagem real entre fontes. Seus resultados, prompt e fixture permanecem históricos. Não preencher aquele skip nem reclassificar sua falha.

## Hipótese e pergunta observável

O perfil B pode usar uma primeira narrativa integral admitida como fonte atribuída do segundo pedido, sem copiá-la para afirmação canônica, memória CONHECIDO ou pergunta q. Verificar identidade, texto integral e audiência na passagem real; ler agência e continuidade das duas saídas como análise autorada. Identidade textual não prova verdade semântica ou qualidade geral. Não há comparação causal com Estufa nem estimativa de taxa.

## Entradas e limites anteriores ao envio

Cena canônica `Pátio coberto`, sem NPC. Primeiro input: “Observo o pátio coberto do lugar onde estou, sem tocar em nada.” Segundo: “Continuo no mesmo lugar e aguardo, sem tocar em nada.” O segundo USER só pode conter a fonte integral validada do primeiro n; q permanece separado. Mesmo SYSTEM narrative-source-v1, schema n/q e perfil da direção B; nenhum novo wording para obrigar uma pergunta específica.

Groq direto / qwen/qwen3.8-27b, candidato gratuito exclusivamente sintético, reasoning none e structured output nativo. Máximo duas chamadas de768 tokens,1536 no total, temperatura0,65. Espera inicial, intervalo e deadline60 segundos. Sem diagnóstico, retry, fallback, juiz ou reparo. Parar na primeira falha de rota/schema/política/projeção ou transporte e registrar skip. Encerrar após duas posições ou primeira falha, sem repetir para aumentar taxa.

## Preparação e critérios

Reutilizar o executor e wrapper já testados, acrescentando seleção explícita e fechada de caso; o caso histórico fica disponível para compatibilidade offline. O executor recusa Estufa em --live antes da credencial e o wrapper operacional aceita somente Pátio, também como default. A escolha deve atravessar preflight, execução, resumo e verificação com fingerprints; rejeitar caso desconhecido/troca entre etapas antes da credencial/envio. Não aceitar caminho de fixture arbitrário. O launcher novo selecionará Pátio explicitamente.

Antes da chave: confirmar regressões da correção de pergunta, testar isolamento dos casos e reconstrução do segundo USER, conferir hash e preflight real, executar integração de chave vazia. Congelar pacote final e registrar uma única janela protegida. Nova entrada de chave é a única dependência humana; não há novo pedido de aprovação de B ou de lote.

## Limites de conclusão

Passagem das duas fontes, se ocorrer, será uma observação restrita em cena conhecida. Não valida abertura sem cena, novos NPCs, resolução mecânica, persistência, saves, default do produto, semântica geral ou CAP-001. O plano de integração pode avançar documentalmente em paralelo, mantendo esses gates pendentes.
