# Preparação offline — contrato de progressão fundamentada v1

**Data:** 2026-09-22

**Status:** preparação offline verificada; L1 autorizada posteriormente em gate separado

## Resultado

A aprovação humana original de `HYP-001` foi aplicada somente à preparação
offline. O protocolo prospectivo, corpus de oito casos, extensão de prompt, oito
templates target-neutral, matriz de adulterações e verificador fail-closed estão
prontos. Naquele estágio, nenhum candidato, alvo, provedor ou default foi
selecionado. A autorização posterior de `LIVE-HYP-001-L1` está registrada no
gate próprio e não altera o caráter não operacional deste preparador.

O preparador declara `provider_calls: 0`, `live_inference_authorized: false`,
`target_selected: false` e `runtime_default_eligible: false`. Cada template tem
`is_live_request: false`, alvo nulo e hash de body próprio.

## Freeze observado

| Artefato | SHA-256 |
|---|---|
| `evals/narrator/grounded_progression_contract_v1.json` | `e3d9252090f7c1208039c74f01bdf4bf2c9940d5560fbd43a003a9c3a7e939e4` |
| `evals/narrator/grounded_progression_contract_protocol_v1.md` | `da938d4380c6cb73036522d407583aa26aec1ef78a05e253efef9a396ee79fb3` |
| `evals/narrator/grounded_progression_verifier_fixtures_v1.json` | `a3b3d2619118c77a775612fd9e1d2896019d986835dd662a714e53f4c56e0bea` |
| `evals/narrator/prompts/narrative-source-progress-v1.md` | `87b9cbcd67a67b9d25b97c2b25276e83af56d48c09f53843a64b8e77303b1a0e` |
| `evals/narrator/prompts/grounded-progression-contract-v1.md` | `011dfc767490c718e99824bb636a4262674bafa802dbbdb29d1078556888f012` |
| `scripts/evaluate_grounded_progression_contract.py` | `38d2f3ce74ebd292846176463471b8620b3dffdb08fa6e67cad18ad8db04e81a` |
| `tests/test_grounded_progression_contract.py` | `25962f83da3dbb2e76263f0a69b335a941f2694394637834868cc811a41ecc98` |

O preflight também congelou os hashes atuais de
`api/scene_director_service.py`, `api/scene_resolution_service.py` e
`api/turn_models.py`. Qualquer mudança nesses contratos altera o manifesto
reconstruído e impede comparar um futuro lote contra este freeze sem revisão.

## Verificação

- 18 testes próprios do HYP-001 passaram dentro da matriz final.
- A regressão focada atual, incluindo resolvedor, diretor de cena, contrato de
  atores, runner L1 e adaptador Groq, passou: **421 testes aprovados**.
- JSON estrito rejeita chaves duplicadas e números não finitos.
- Target divergente, retry, fallback e hash divergente falham como erro de
  integridade.
- Violação semântica fatal, estado desconhecido afirmado, marcador proibido,
  transição ausente e orçamento excedido reprovam o caso.
- O preparador não importa cliente de rede e não consulta ambiente de credencial.
- A tentativa adicional de `py_compile` não pôde gravar `__pycache__` no worktree
  por permissão do sandbox; os mesmos módulos foram importados e executados pela
  suíte aprovada. Não há lacuna funcional decorrente desse aviso.

Avisos não bloqueantes: depreciação já conhecida do Starlette e impossibilidade
do sandbox gravar `.pytest_cache` nesse worktree externo.

## Limites

- Marcadores lexicais são apenas contraprova mínima; revisão semântica humana
  continua obrigatória em todo caso.
- O verificador não transforma revisão humana em verdade canônica nem qualifica
  automaticamente um modelo para o produto.
- A continuidade possui uma cadeia dependente de dois turnos; os seis casos
  restantes são deliberadamente independentes.
- O runner vivo foi criado somente após autorização humana separada. Ele não faz
  parte da autorização offline original e continua bloqueado por credencial
  pendente antes do primeiro request.
- A suíte backend integral não foi repetida: a matriz relacionada atual de 421
  testes passou, e a suíte ampla anterior já possui falhas históricas congeladas
  documentadas.

## Gate subsequente

A decisão humana separada aprovou `L1` com alvos, parâmetros, ordem, máximo de
chamadas e parada congelados. O estado corrente está em
`grounded-progression-live-gate-2026-09-22.*` e
`grounded-progression-live-readiness-2026-09-22.*`: nenhuma chamada ocorreu e a
credencial protegida é o único gate restante antes da execução.
