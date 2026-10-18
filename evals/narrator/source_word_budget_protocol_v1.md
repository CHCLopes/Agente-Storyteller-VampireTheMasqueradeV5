# Protocolo prévio — diagnóstico de extensão Qwen v1

Preparação técnica autorizada em 12/09/2026; revisão e provas offline precedem qualquer live. Ainda não há resultado de inferência deste protocolo. O corpus executável é source_word_budget_v1.json.

## Pergunta delimitada

Em dois contextos sintéticos novos e fixos, a indicação de um orçamento por campo com margem produz saídas dentro do limite existente de 150 palavras totais, preservando reação útil e agência?

O resultado do comparativo 61b83a2f permanece encerrado e intocado. As duas recusas Qwen foram 155 e 157 palavras. Leitura separada dos campos nesta auditoria encontrou 146+9 e 153+4, respectivamente: ignorar apenas q não explica os dois casos. O SYSTEM atual já pede 30–150 palavras no total. A hipótese nova é uma limitação de aderência ao orçamento próximo do teto; não é ausência dessa instrução, nem um defeito demonstrado do validador.

A alteração experimental abaixo testa uma alocação numérica explícita com margem. Não reformula a direção narrativa/progressão para tentar elevar notas. Não reabre Oficina/Arquivo, importa propostas recusadas, completa skips antigos ou escolhe narrador.

## Alvo e condições constantes

- Alvo explícito: Groq, `qwen/qwen3.8-27b`, reasoning `none`; mesma conta gratuita já autorizada. Confirmar documentação oficial do alvo e capacidade antes do freeze, sem inferir quota/disponibilidade da conta.
- Schema original `NarrativeSourceProposal`: somente n/q, extras proibidos, n 40–1600 caracteres, q 3–200; normalização vigente de espaços preservada.
- Gates originais inalterados: 30–150 palavras em n+q; q até 15 palavras; português, agência, local/elenco, mecânica, continuidade e demais políticas existentes.
- Temperature 0,65; máximo 768 completion tokens/call; teto global 3.072; deadline 60 s/call.
- Espera inicial mínima 60 s e intervalo global mínimo 60 s entre inícios HTTP; uma chamada por slot, quatro chamadas no máximo.
- Sem ferramentas, streaming externo, texto diagnóstico, retry, reparo, truncamento, fallback, troca de target, SQLite, commit, UI, save ou mudança de default.
- USER idêntico entre os dois braços de cada contexto, incluindo fonte, fatos declarativos sintéticos e identidades de dados. As identidades operacionais do request são próprias de cada slot e ficam fora do USER. Nunca usar resposta gerada por um braço como entrada do outro.

## Diferença exata do SYSTEM

Braço A: corpo atual de `evals/narrator/prompts/narrative-source-progress-v1.md`, sem frontmatter, inalterado.

Braço B: mesmo corpo byte a byte, substituindo uma única ocorrência da frase:

> Use de 30 a 150 palavras no total de n e q;

por:

> Use de 70 a 110 palavras em n e no máximo 10 palavras em q, mantendo o total de n e q entre 30 e 120 palavras para deixar margem até o limite de 150;

O restante do parágrafo permanece exatamente igual, inclusive caracteres e a regra original de q até 15 palavras. Essa regra de admissão continua mais ampla que o orçamento solicitado no braço B; distinguir as duas medidas. Não adicionar contadores ao JSON, solicitar raciocínio ou usar código para cortar a resposta.

Justificativa da margem: n até 110 + q até 10 dá teto solicitado 120, deixando 30 palavras antes do gate imutável 150. O mínimo solicitado n70 evita testar apenas frases curtas que abandonem a cena. Esse intervalo é um parâmetro experimental novo, não nova regra do produto.

## Contextos novos e autoria explícita

Estes contextos são autorados para esta preparação e recebem revisão antes de serem congelados. São independentes dos textos gerados/refusados de 61b83a2f e de saves reais. Não alegar que uma fonte autorada foi produzida/confirmada por um modelo.

**C1 — pergunta sem fonte anterior**

- Local: Relojoaria.
- NPC presente: Bela.
- Objetivo: entender o que observar antes de a relojoaria fechar, sem mexer nas peças.
- Entrada literal: `Pergunto a Bela: "O que merece atenção nesta relojoaria antes de fechar, e por quê?"`
- Fontes anteriores: nenhuma.
- Entrada declarativa sem teste mecânico; server_facts vazio, sem recibo fornecido ou fabricado. Nenhuma nova ação do jogador deve ser inferida.

**C2 — espera com uma fonte anterior autorada**

- Local: Pavilhão.
- NPC presente: Caio.
- Objetivo: acompanhar o que ocorre junto à mesa sem tocar nos objetos.
- Entrada literal: `Aguardo a reação de Caio.`
- Uma fonte autorada, mantida integralmente nos dois braços:

> Caio está ao lado de uma mesa baixa no pavilhão. Uma bandeja vazia repousa perto da borda, sobre um pano cinzento. Na janela aberta, a cortina se move com o vento. Cada rajada levanta um pouco a ponta do pano e deixa a bandeja ligeiramente mais próxima da borda. Caio olha na direção da janela, mas mantém as mãos afastadas da mesa. A passagem entre a mesa e a porta permanece livre. Não há indicação visível de quem abriu a janela.

- Entrada declarativa sem teste mecânico; server_facts vazio, sem recibo fornecido ou fabricado. Nenhuma ação, decisão ou emoção adicional do jogador é fornecida.
- A fonte terá origem fixture-autoria, identidade e hash próprios; não será registrada como commit, turno confirmado ou resultado do comparativo anterior. q não entra na fonte.

## Ordem e regra de parada

Ordem fixa balanceada: A/C1, B/C1, B/C2, A/C2. Os quatro slots são independentes e não formam cadeias de turnos.

Recusa tipada de schema/política registra o slot e permite apenas o próximo slot originalmente planejado; não autoriza nova tentativa. Falha local, cancelamento, timeout, autenticação, rate limit/quota, indisponibilidade, pagamento exigido, eco de credencial, rota/modelo divergente ou causa não tipada encerra globalmente. Os slots restantes ficam explicitamente não enviados. Sem retry de erro HTTP, diagnóstico extra ou aumento de teto. Cancelar durante espera impede o próximo envio.

Truncamento, finish ausente/desconhecido, uso reportado acima de 768 tokens por chamada ou 3.072 no lote, término depois do deadline e contradição entre observador e resultado impedem o próximo slot. Um diagnóstico operacional de códigos fechados preserva o outcome, a proposta e a evidência originais; não os repara ou apaga. O verificador recomputa esse diagnóstico e recusa continuação após ele. Uso não reportado fica desconhecido; não é convertido em zero nem declarado medido.

## Critérios prévios e interpretação

Antes de revisar qualidade, auditar a integridade dos quatro pedidos: dados USER pareados, SYSTEMs com somente a substituição acima, target/parâmetros/schema exatos, cronologia e contagem global, hashes da preparação, causas de parada e ausência de chamada adicional.

Por resposta existente, registrar separadamente:

1. HTTP/finish/schema/rota e quantidade de n, q e total, em palavras e caracteres, usando o mesmo contador do gate.
2. Admissão original de extensão (30–150 total, q<=15) e admissão dos demais gates; orçamento B solicitado (n70–110, q<=10, total<=120) como observação separada.
3. Revisão descritiva independente de agência, reação útil, continuidade e clareza. C1 deve permitir entender uma resposta específica de Bela; C2 deve desenvolver ou reagir ao estado autorado, sem forçar o jogador ou transformar desconhecimento sobre a janela em certeza. Não exigir uma única continuação prevista pelo avaliador.

Interpretação delimitada: B dentro do gate em 2/2 e A excedendo em ao menos um contexto é sinal exploratório compatível com a hipótese de margem. Se ambos braços ficarem dentro em ambos contextos, a observação não diferencia a hipótese. Qualquer excesso do B não sustenta aderência integral nesses dois casos. Se houver slots sem resposta, declarar a cobertura incompleta. Variações de qualidade podem revelar perda de conteúdo apesar de melhor extensão; não esconder essa troca em uma nota agregada.

Nenhuma combinação declara vencedor, causalidade estatística, superioridade de modelo, generalização, aprovação de piloto, campanha ou CAP-001. A amostra é um diagnóstico operacional pequeno; não sustenta taxa populacional nem confiabilidade futura. Não repetir para obter o padrão esperado.

## Preparação e verificação necessárias

1. Revisar a fonte C2, os fatos declarativos e o formato de origem fixture do harness puro. O pacote deve usar caminhos existentes do perfil B sem inventar história confirmada nem depender de SQLite.
2. Materializar corpus/protocolo/prompt B novos; congelar hashes de ambos SYSTEMs, schema, USERs, arquivos executáveis, parâmetros, slots, regra de parada e data de consulta oficial. O verificador deve provar diferença única, pareamento e independência dos USERs antes de aceitar preflight.
3. Construir harness delimitado e launcher próprio, aproveitando padrões existentes sem relançar os lotes históricos. Preflight/verificação offline não pedem chave ou rede. Live só depois de preparação/revisão completas.
4. Contraprovas offline: drift/hash, slot duplicado, quinta chamada, alteração de parâmetros/alvo/SYSTEM/USER, diferenças de contador por campo/total, schema versus política, parada global por quota/timeout/erro desconhecido, recusa tipada sem retry, cancelamento durante espera, registros incompletos e credencial fora da allowlist.
5. Usar o padrão já existente de `Read-Host -AsSecureString` em PowerShell 7 e processo filho com ambiente restrito. Nenhum segredo em chat, `.env`, argumentos, logs, IPC novo ou persistência. A credencial é solicitada para esta execução concreta, descartada no término; não é um serviço permanente de armazenamento de chave.
6. Revisão independente antes do freeze/live. Após lote, auditoria e revisão separadas, com registros originais imutáveis, inclusive recusas e ausências. Não executar novamente o mesmo lote após encerramento.

## Referências consultadas

- `AGENTS.md`: autorização contínua para observações delimitadas e vedação a credenciais em arquivos/chat, fallback/retry silencioso e aprovação automática.
- `evals/narrator/prompts/narrative-source-progress-v1.md:16`: instrução total atual explícita.
- `evals/narrator/source_comparison_protocol_v1.md:108–111`: nenhum candidato qualificado, não repetir para forçar vencedor; investigação posterior exige hipótese/protocolo próprios; aceitação final humana.
- `evals/narrator/reports/source-comparison-observation-61b83a2f-2026-09-11.md:7–12,56–66`: dois excessos Qwen e falso positivo GPT-OSS separado.
- `api/narrative_source_action_producer.py:44–62`: formas declarativas escolhidas já reconhecidas, sem interpretação livre nova.
- `scripts/narrator_source_profile.py`: schema e validação do perfil n/q; sem converter autoria em commit.

Limite de alternativas: relançar GPT-OSS no Arquivo para completar o slot recusado não é esta proposta. A correção de agência já tem contraprova local; o lote antigo mantém recusa/skips. Uma futura observação GPT-OSS exigiria outra pergunta prospectiva e não pode ser importada para qualificá-lo naquele comparativo.

## Consulta oficial de 12/09/2026

Root verificou por navegação as páginas oficiais de modelos, structured-outputs e reasoning (URLs no corpus): qwen/qwen3.8-27b está listado em preview, suporta strict:true e reasoning_effort none. A consulta não estabelece disponibilidade, quota, saldo ou autorização da conta e não altera cobrança.
