# Observação — cobertura lexical de retirada na campanha

Data: 03/10/2026. Estado: descoberta técnica registrada, sem expansão automática
do backlog ou prioridade. Não é nova decisão de produto ou gate retroativo.

Ao testar o repasse de NPCs canônicos após HYP-007-L3, duas contraprovas
sintéticas foram admitidas no turno R-01 (apenas pergunta sobre ajuda):
"Você aponta para a passagem e retira o registro da bancada." e
"Seu personagem retira o registro da bancada." O texto completo incluía o
registro na bancada, a superfície seca na Galeria e Mara aguardando a decisão.

Evidência local: `_action_authorizations('Como posso ajudar?') == {}` e
`_action_signatures('retira o registro da bancada') == frozenset()`.
A família lexical de retirada não é reconhecida pelo detector genérico;
o guard da campanha recusa `Você retira...` imediato, mas a coordenação
`Você aponta... e retira...` e `Seu personagem...` não entram nesse padrão.
Isso precede a correção de aliases: o incremento só acrescenta NPCs do roster
canônico ao contexto da política; não mudou padrões ou famílias de verbos.

Impacto: limitação de detecção de agência **na prosa**. A proposta não fornece
delta e não altera o efeito canônico de R-01; ainda assim, narrar uma escolha
não declarada é contrário às balizas do produto. Essa descoberta não permite
declarar proteção semântica integral, nem converter um ID correto em prova de
fidelidade. Não foi observada na resposta live L3, que não retirou o documento.

Fora da correção delimitada de atribuição NPC: ampliar padrões exige testes de
ação/objeto, negadores, fala direta e coordenação de sujeitos, mantendo as
famílias separadas e sem autorizar resgate após só perguntar. Registrar como
pendência de cobertura para reconciliação de agência antes do aceite integral;
não atribuir prioridade, abrir nova frente ou mexer no detector genérico por
arrasto. Não bloqueia a reprodução local do falso positivo NPC; permanece
limite conhecido da avaliação e da futura admissão. Contraprovas existentes
de `pega/abre` continuam recusadas com o repasse do roster.
