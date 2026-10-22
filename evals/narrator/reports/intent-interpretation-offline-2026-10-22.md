# Interpretação delimitada — escopo B offline, 22/10/2026

## Resultado e limites

Humano escolheu B. Contrato experimental, corpus de 24 casos e avaliador offline
implementados em arquivos separados. Sem gateway, inferência, sorteio, banco de
sessão ou integração ao jogo. Custo de provedor desta etapa: USD 0.

O contrato exige versão, vínculo ao envelope de sessão/operação/hash de estado/
entrada, enum de intenção existente e até quatro trechos literais sem sobreposição.
JSON estrito até4096 bytes, sem duplicatas, narrativa ou campos extras. O hash vincula
os dados fornecidos; não autentica sua origem nem prova a verdade do estado. O corpus
usa sessão sintética e hash de estado artificial, não estado de um save real.

O gate independente reaplica o classificador existente à entrada completa. Só
considera elegível uma proposta concordante já reconhecida por esse classificador.
Entradas novas ficam pendentes. Não há função de execução/commit neste módulo.
`eligible_existing_intent` significa elegibilidade offline, não ação aplicada.

## Evidência

Corpus prospectivo: oito paráfrases, quatro ambiguidades, quatro negação/ator,
quatro métodos inéditos e quatro injeções de cânone. Rótulos e propostas de referência
são autorados pela aplicação; não saídas de modelo nem aprovação canônica humana.

| Medida | Observado neste corpus |
|---|---|
| Propostas de referência estruturalmente válidas |24|
| Referências com intenção conhecida |10|
| Baseline reconhece corretamente |4 dessas10|
| Paráfrases fiéis bloqueadas pela baseline e pelo guard |6: P01..P06|
| Intenções incorretas aceitas pela baseline |0 neste corpus|
| Propostas elegíveis pelo guard |4|
| Propostas pendentes de conferência independente |6|
| Referências sem ação |14|

Essas contagens não medem acurácia de LLM, probabilidade de segurança ou cobertura
geral. A baseline produz intenção/None; não distingue dúvida de método não coberto.
O guard conserva seu teto de cobertura, portanto não demonstrou ganho de interpretação.

## Contraprovas

A variante baseada apenas em formato e evidência literal foi reprovada e encerrada
na primeira contraprova: N01, “Não retiro o registro.”, proposta `rescue`. O texto
inteiro é citado literalmente e o formato é válido, mas o sentido foi invertido.

Diagnóstico separado (não continuação da variante admitida): sete propostas erradas
autoradas passaram em formato/literalidade e ficaram pendentes no guard independente.
Incluem negação, comando a Mara convertido em ação do jogador, fala citada, método
inédito, injeção de resultado, referência ambígua e troca de intenção conhecida.
Não houve tentativa de elevar taxa por retries ou edição dos rótulos.

## Verificação e publicação

61 testes focados passaram (54 novos do contrato e sete do browser A2).
Regressão conjunta dos experimentos relacionados:197 casos passaram. Um aviso
preexistente de python_multipart; nenhuma falha. XML local em
`eval-results/intent-publication-regression-2026-10-22.xml`.
32 hashes de fontes L86 reconferidos intactos. Manifesto com hashes e observação
sintética publicável em `evals/narrator/spikes/intent-interpretation-2026-10-22/`.
Sem alterações no checkout original, defaults, saves, credenciais ou módulos congelados.

Diretrizes humanas registradas em AGENTS.md: commit/push antes de gate humano e
bloco obrigatório de configuração. Publicação pela branch atual, sem promover main.
Arquivos de ambiente preexistentes e dados de eval-results ficam fora do commit.
O resultado real do push deve ser confirmado por ref remoto antes do relato ao humano.

## Próximo gate

Recomendar conservar o contrato como fronteira experimental de propostas, sem
admitir um interpretador novo. Não há razão demonstrada para gastar com um modelo
antes de decidir quem valida paráfrases que o classificador atual desconhece.

Proposta concreta: `plan/proposal-intent-paraphrase-admission-2026-10-22.md`.
Aprovar um catálogo explícito das seis paráfrases para experimento separado é a
opção de menor complexidade; manter interpretação aberta exige outra fonte de
validação semântica e nova decisão. CAMP-13..16/CAMP-24 permanecem abertos.
