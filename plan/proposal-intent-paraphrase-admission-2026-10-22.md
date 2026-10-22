# Gate: quem valida paráfrases novas?

Status: opção C aprovada pelo humano em 22/10/2026. Escopo limitado ao catálogo
exato e ao experimento offline; não aprova integração, modelo real ou autoridade
causal.

O contrato rejeita formato inválido e troca de vínculo, mas não prova equivalência
semântica. Guard independente só reconhece o catálogo atual. Modelo real não medido.

## Opção C — catálogo explícito no experimento (recomendada)

Autorizar as equivalências abaixo para uma nova variante offline e isolada, sem
editar o classificador congelado, integrar ao jogo, chamar API ou admitir narrador.

| Entrada completa | Intenção proposta |
|---|---|
| Quero saber qual é a tarefa. |task|
| Mara, o que eu posso fazer para ajudar? |task|
| Fico esperando. |wait|
| Vou retirar o registro da bancada. |rescue|
| Analiso o registro. |inspect|
| Não participarei do resgate. |withdraw|

Aceite C autoriza um novo catálogo versionado de correspondência exata dessas seis
entradas e validação offline, sem expansão por similaridade/substring. A aplicação
passa a ter uma segunda referência explicitamente revisada; labels do corpus não
podem servir de oráculo oculto. Comparar contra a baseline e testar negação, ator,
citação, ações compostas e métodos diferentes. Qualquer derivação não aprovada
continua sem ação. Sem efeito causal, sorteio, mutação de sessão ou publicação em main.

Critério: seis correspondências aprovadas elegíveis, controles não aprovados recusados,
nenhuma transformação automática de método inédito em resgate; mesma entrada produz
mesma avaliação e versão retida. Não afirmar que seis exemplos provam improvisação.
Após isso, apresentar evidência para decisão de eventual integração ou estudo seguinte.

## Opção D — manter interpretação mais aberta em investigação

Não autorizar o catálogo C. Definir com o humano qual fonte independente poderá
validar novas interpretações (revisão explícita do jogador, regras de elegibilidade
mais gerais ou outra solução). Não implementar novo validador ou modelo causal por
arrasto. Um modelo sugerir e outro concordar não é, por si só, prova de fidelidade.

## Decisão pedida

Escolher C ou D. C prioriza economia e cobertura pequena verificável; D preserva
uma frente mais aberta, cujo contrato e critérios ainda exigem decisão de produto.
Nenhuma opção fecha CAMP-24 ou autoriza a proposta dual-model/ALT-003 causal.
