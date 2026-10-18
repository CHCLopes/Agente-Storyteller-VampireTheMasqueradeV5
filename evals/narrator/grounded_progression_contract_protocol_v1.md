# Protocolo prospectivo — contrato de progressão fundamentada v1

Data: 22/09/2026. Congelado antes de qualquer inferência deste experimento.
Hipótese aprovada: `grounded_progression_contract_v1` (`HYP-001`).

## Pergunta

Um bloco estruturado de fatos canônicos, transições autorizadas, estados
desconhecidos e suposições proibidas permite que um alvo narre progressão quando
ela é autorizada e sustente a cena quando não é, sem inventar estado, controlar
o jogador, revelar segredo ou reverter resultado mecânico?

O corpus executável é `grounded_progression_contract_v1.json`. Este protocolo,
o corpus, o verificador e os contratos locais citados pelo preflight integram o
freeze por SHA-256. O lote histórico `source_comparison_v1` permanece imutável.

O SYSTEM prospectivo é a composição byte a byte do prompt-base
`prompts/narrative-source-progress-v1.md`, preservado, seguida por duas quebras
de linha e `prompts/grounded-progression-contract-v1.md`. A extensão HYP-001
substitui somente a obrigação genérica de avanço quando não existe transição
autorizada. O USER é JSON canônico gerado do caso; marcadores de verificação e
expectativas de aprovação nunca entram no request.

## Preparação offline

Esta fase admite somente preparação local: validar o corpus, gerar manifesto e
templates sem alvo real, verificar artefatos sintéticos e testar adulterações.
Ela faz zero chamadas, não lê ambiente de credencial e não escolhe candidato.
O preflight não pode ser usado como autorização para inferência.

## Casos e ordem

Oito classes novas e congeladas, na ordem declarada pelo corpus: espera sem
avanço, espera com evento, objeto conhecido, objeto desconhecido, sucesso
mecânico, falha mecânica, segredo de NPC e ação ambígua. Todos os candidatos
futuros receberão os mesmos casos, ordem, contrato, parâmetros e orçamento.
Os dois casos de espera formam uma cadeia: a resposta confirmada do primeiro é
fonte atribuída do segundo para testar continuidade e repetição material. Os
demais casos são independentes e não herdam texto de outro candidato ou caso.

Cada resposta terá 30 a 150 palavras e um registro de revisão independente. O
verificador exige alvo solicitado e reportado idênticos, proveniência explícita,
schema e vínculo de cápsula válidos, zero retry oculto e zero fallback.

## Gates fatais

Todos devem passar em todos os casos:

1. zero contradição de fato canônico;
2. zero estado ou transição inventada;
3. zero ação, fala, decisão ou sentimento atribuído ao jogador;
4. zero segredo não autorizado;
5. identidade e proveniência exatas;
6. schema e vínculo de cápsula válidos;
7. nenhuma troca, repetição ou fallback oculto.

Marcadores lexicais do corpus são uma contraprova determinística mínima, não um
classificador semântico completo. A revisão humana continua obrigatória e não
pode ser substituída pela ausência desses marcadores.

## Gates de progressão

- Caso com transição requerida: a resposta deve declarar exatamente o ID
  autorizado, fundamentar todos os fatos exigidos e receber revisão de avanço.
- Caso sem transição: a resposta não pode declarar transição, deve fundamentar
  os fatos exigidos e receber revisão de sustentação coerente.
- Estado listado como desconhecido não pode aparecer entre estados afirmados.
- Continuidade materialmente repetitiva reprova o caso dependente.
- Latência e disponibilidade são descritivas e não compensam falha narrativa.

## Regra de admissão

Um alvo exato só é elegível se os oito casos passarem integralmente. Qualquer
gate fatal ou de progressão falho torna o alvo não elegível neste protocolo.
Não relaxar critérios, completar slots ou repetir para forçar vencedor. Um lote
sem candidato elegível é resultado válido.

Qualificação neste protocolo não escolhe default, provedor, custo, orçamento,
fallback, `SEC-001` nem configuração produtiva. Admissão final continua humana.

## Gate para chamadas vivas

Chamadas vivas permanecem proibidas até autorização humana separada, emitida
depois da revisão do relatório de preparação, hashes, templates de request,
alvos exatos, parâmetros, orçamento de chamadas e tratamento de credencial.
