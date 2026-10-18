# TASK-016 — poderes determinísticos do escopo base

Data: 2026-09-20

## Escopo

Somente `feral_weapons`, `soaring_leap` e `awe`, os três poderes
`base_reachable`. Poderes adiados não foram promovidos.

## Evidência V5

- Armas Ferais: PDF página 272 (impressa 270), nível 2, um Rouse Check, +2 de
  dano de Briga; agravado contra mortais e superficial não reduzido contra vampiros.
- Salto Ascendente: PDF página 266 (impressa 264), nível 1, passivo, sem rolagem;
  salto vertical 3 vezes Potência e horizontal 5 vezes Potência.
- Fascínio: PDF página 269 (impressa 267), nível 1, gratuito, duração de cena;
  adiciona Presença a ações sociais aplicáveis baseadas em Carisma.

## Resultado implementado

- Modificadores passaram a vir dos campos tipados do catálogo, sem ramificação
  por ID para esses três poderes.
- Armas Ferais não converte mais dano contra vampiros em agravado. O dano
  superficial não é reduzido e recebe +2.
- Ativar Salto Ascendente ou Fascínio isoladamente não fabrica uma rolagem.
  Fascínio concede o bônus somente quando há uma ação suportada de Carisma.
- Os multiplicadores de salto estão registrados, mas a distância não é aplicada
  até existir uma geometria canônica da cena.

## Limites preservados

- O tipo agravado contra mortais de Armas Ferais permanece fora do cálculo atual,
  cujo modelo de dano mortal ainda não diferencia esse tipo.
- A resistência a Fascínio e outras perícias sociais dependem de expansão futura
  da intenção e dos pools determinísticos.
