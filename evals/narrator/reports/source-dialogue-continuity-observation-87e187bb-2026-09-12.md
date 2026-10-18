# Continuidade de diálogo: integridade confirmada, segunda proposta recusada

O lote `87e187bb-61e7-4949-9574-4aea19f23c9f`, executado pelo usuário em 12/09/2026,
encerrou `finished/1`. Houve duas chamadas HTTP 200/stop, dois schemas válidos
e duas rotas verificadas; a primeira resposta foi commitada, a segunda recusada
em política com `scene_player_agency_violation`. Não houve skips, repetição,
fallback nem chamada adicional de auditoria.

A auditoria independente passou em 70/70 verificações. O CLI separado
retornou verified=true e exit 0 para a integridade de uma observação exit 1.
Isso não transforma o lote em dois turnos concluídos. Seus oito artefatos brutos,
incluindo SQLite/WAL/SHM, preflight e lifecycle, permaneceram idênticos.
A aferição independente inicial 68/70 está preservada: dois checks comparavam
texto de timestamps equivalentes em Z e -03:00. A correção do helper comparou
os instantes, sem alterar dado ou código do lote.

Foram duas preparações P, duas cápsulas K e duas tentativas H6; seis attempts,
um turno e um evento de declaração persistidos. T2 recebeu a única fonte
completa n de T1 realmente commitado, SHA
`5885833622521f8a3b7e3f171eaeb20f7c5c74a2617470d8f407742b369abb2a`.
q não entrou na fonte. Replay de T1 e dois replays da preparação não produziram
novo turno, RNG ou HTTP. A proposta T2 permaneceu sem envelope persistido.

Uso reportado: 3574 tokens de entrada, 320 de saída,
3894 totais. Espera inicial 61.429911s e intervalo entre envios
61.403569s, ambos acima de 60s; os deadlines compartilhados foram respeitados.
Qwen qwen/qwen3.8-27b via Groq, SYSTEM dialogue-v1, .65/768/none e 33 entradas
mais o launcher correspondem ao congelamento prospectivo.

## Leitura dos textos

T1 oferece uma resposta metafórica: a galeria guarda intenções além de quadros.
Há fala efetiva pertinente, mas pouca especificidade. A proposta T2 retoma
exatamente esse assunto e explica marcas de criação e o que ficou ausente nas
obras. Acrescenta conteúdo em vez de só repetir hesitação; continua abstrata.

Os seis critérios prospectivos foram julgados em revisão separada. A leitura
semântica não encontrou ação, emoção ou decisão consumada do jogador em T2:
Mara observa e espera; a possibilidade de compreensão fica em aberto. A pergunta
“Como você responde a Mara?” pede a próxima iniciativa, sem afirmar resposta já
ocorrida. Não se exigiu que a NPC obedecesse, revelasse segredos ou oferecesse
uma resposta exaustiva. Improvisação atribuída não se torna cânone confirmado.

Há continuidade observável nos textos gerados, mas somente um turno efetivamente
confirmado. Comparações com81cb são descritivas; este lote não demonstra vantagem
causal, confiabilidade global ou escolha definitiva de modelo.

## Diagnóstico local e continuidade

A recusa foi reproduzida offline no gate integral, com campo narrative, regra
undeclared_player_action, sujeito voce e conceito wait. O reconhecedor tratou
o objeto de “observando você” como sujeito e incluiu “esperando” (Mara) e
“permanece” (a explicação). Retirar só um desses verbos ainda recusou; retirar
ambos ou o último período passou. Uma pergunta neutra não alterou a recusa.
Controles com ações reais do jogador continuaram bloqueados.

Isso sustenta um falso positivo delimitado, sem reclassificar o resultado
original. O próximo passo é corrigir a atribuição gramatical com contraprovas,
preservando a proteção contra ações impostas, os dados e o histórico. Nenhum
prompt, limite ou gate foi alterado para fechar esta observação. Novas verificações
devem distinguir reprodução local da proposta capturada de qualquer inferência
real. Não repetir este lote nem reaplicar sua proposta na sessão encerrada.

## Preservação

Checkpoint `eval-results/checkpoints/source-dialogue-continuity-observation-87e187bb-20260912/manifest.json`:
69 cópias verificadas, SHA `14ec252d78315976047649c765a21825545ca6bdc2c3eaf44e575be42d307fe0`. As 97 cópias da preparação
anterior permaneceram intactas. Fontes anteriores estão arquivadas para permitir
correções prospectivas sem substituir a versão que produziu esta evidência.
As conclusões semânticas e o diagnóstico são anexos; summary/JSONL/SQLite não
foram reescritos. Modelo/default/campanha/CAP-001 continuam sem aprovação.
