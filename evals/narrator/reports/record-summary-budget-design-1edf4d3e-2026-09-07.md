# Sondagem operacional com teto de 768 — desenho prévio em 07/09/2026

Status: preparação autorizada sob continuidade. Este documento congela uma única observação nova; nenhum envio foi feito durante sua elaboração. O lote 1edf4d3e está encerrado após uma chamada recusada e um caso omitido. Não se repete observatory-a nem se preenche observatory-b, e não se reabre archive-vibration ou qualquer caso histórico.

## Pergunta e fundamento

**Uma única solicitação nova de resumo textual, com teto explícito de 768 tokens, consegue completar transporte, rota e schema neste perfil Qwen?**

No Console, a recusa anterior informou output tokens per minute (OTPM), limite 1000 e saída esperada 1096, enquanto o pedido transmitia max_completion_tokens=3072. Essa é uma atribuição ao provedor, não uma medição local de uso: a fórmula da estimativa permanece desconhecida. Não se infere TPD esgotado, reset de conta, ETA, consumo acumulado ou uma garantia de aceitação para 768. A rota da resposta recusada permanece indisponível no artefato local.

O adapter existente transmite o teto corretamente; não há correção demonstrada a aplicar no runtime. Encerrar toda observação agora deixaria a viabilidade operacional de um pedido menor sem medição. Esta nova sondagem oferece essa informação com uma chamada e nenhuma continuação automática. Ela não estima a causa do erro anterior, taxa de sucesso ou qualidade semântica do produto.

## Fonte nova congelada

Caso station-clock, autorado e inteiramente sintético:

> Na estação vazia, um relógio parado marca seis horas. Um envelope lacrado repousa sobre o banco; perto da janela aberta, a cortina se move com a brisa.

O arquivo conserva as seis chaves do pacote inline: schema, case_id, synthetic_only, origin, narrative e source_units. n0 é a primeira frase completa seguida de um espaço; n1 é a segunda frase completa. Sua concatenação Unicode literal reproduz a narrativa. Não se enviam rubrica, gabarito, decomposição semântica ou exemplos corretivos ao modelo. A fonte é nova e neutra em relação ao par de cores encerrado.

## Diferenças declaradas e invariantes

O corpo é derivado do dossiê summary-only 94a95216. Há exatamente três campos HTTP diferentes: messages[0].content, messages[1].content e max_completion_tokens. No SYSTEM, muda somente a frase numérica de 3.072 para 768; o nome de front matter muda para record-summary-budget-v1 e não integra o HTTP. O USER muda integralmente para station-clock. O teto de transporte muda para 768. Nenhuma dessas mudanças é ocultada como comparação causal de um fator.

Permanecem Qwen qwen/qwen3.8-27b via Groq oficial, candidato qwen-3.8-27b-groq-free-synthetic-nonthink, reasoning_effort=none, temperatura 0.65, stream=false, include_reasoning ausente, response_format nativo estrito e contrato SummaryOnlyProposal. O protocolo de saída continua record-summary-only-v1; a variante do prompt é distinta. summary permanece string estrita de 8 a 600 caracteres; a instrução é até 25 palavras. O prefixo e o formato do pacote USER continuam inline, versão record-inline-evidence-v1.

## Identidade, orçamento e parada

Purpose/probe_kind: summary_budget_qwen_probe. Experimento: record-summary-budget-qwen-observation-v1. Target: summary-budget-qwen-3.8-27b-groq-free-synthetic-nonthink. Operação: summary-budget.station-clock. Linhas persistidas: summary_budget_call e summary_budget_skip, impedidas de replay CAP.

Máximo de uma chamada, 768 tokens totais de saída, espera local inicial conservadora de 60 segundos e deadline de 60 segundos iniciado depois da espera. O USER tem limite local de 2000 tokens estimados por caracteres/4; essa estimativa não é a estimativa OTPM do provedor. Preflight reconstrói fonte, prompt, schema, parâmetros e corpo antes de acessar chave ou construir cliente.

O primeiro resultado encerra a sondagem. Falhas de provedor, transporte, rota, schema, processamento local ou cancelamento não disparam retry, diagnóstico, fallback, novo modelo, outro caso ou escalada de teto/esforço. Uma nova recusa não autoriza uma escada de tetos menores nesta sondagem. Não há geração narrativa, derivação dos oito campos, admissão de ator, alteração de campanha ou promoção de CAP-001.

## Critérios e interpretação

Sucesso operacional exige uma única resposta com rota verificada e SummaryOnlyProposal válido, concluída sem erro local. HTTP 200 ou JSON parseável isoladamente não bastam. A contagem de palavras usa a função existente e permanece informativa: acima de 25 é descumprimento de instrução a registrar, sem mudar o exit operacional. Fidelidade permanece revisão separada, status not_performed e approval null no resumo automático. Nenhum resultado implica aprovação narrativa ou semântica.

Registrar texto literal e medições somente após rota/schema válidos, sem reparo. Preservar erros sanitizados, uso reportado ou desconhecido, finish_reason e os limites de observação existentes, sem corpo bruto de erro, reasoning ou credencial. Uma resposta útil informa viabilidade deste pedido; com fonte e SYSTEM alterados, ela não demonstra que o teto foi a causa de eventual diferença em relação a 1edf4d3e.

## Implementação e verificação mínima

Derivar novos executor e wrapper explícitos do summary-only congelado por mudanças finitas de identidade, fonte, prompt, fingerprints e teto. Preservar algoritmo, contrato, adapters, manifesto e arquivos históricos. Adicionar apenas os marcadores exatos de recusa de replay CAP. Não criar engine genérico, monkeypatch, fallback automático ou alterações de produto.

Verificar preflight puro e pedido exato com transporte simulado, recusa de fonte/prompt/teto divergentes, uso único, deadline após espera, cancelamento e 429 sem novo envio. No wrapper, verificar identidade e hashes, SecureString após preflight, status/exit, artefato novo único e restauração do ambiente. Executar somente grupos focados distintos e integração real com chave vazia; esta preparação não envia chamada ao provedor. A chamada delimitada depende da inserção segura da chave pelo usuário, sem nova aprovação da hipótese.
