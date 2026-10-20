# HYP-007-L6 — correção local e prontidão sem autorização de gasto

Data: 18/10/2026. Branch: `codex/planejamento-agente-storyteller-v5`.
Worktree: `C:/Users/skate/.codex/worktrees/b008/AgenteStoryteller`.
Estado: correção offline verificada; L6 paid/live false; nenhum narrador admitido.

Atualização posterior à preparação: o usuário confirmou explicitamente "L5
foi aceito, assim como o teto de L6" e esclareceu que "continue"/"prossiga"
aprovam a proposta anterior. Aceite delimitado L5 e orçamento L6 atendidos.
Somente os flags paid/live L6 foram ativados nos limites propostos abaixo,
preservando prompt, parâmetros e 22 hashes. As pendências e o SHA com flags
false abaixo são históricos da preparação, não o estado após autorização.
Próxima dependência: entrada protegida da chave no terminal L6 identificado;
depois executar uma vez, reportar custo/gates/resultado e fechar live.

## Conclusão delimitada L5 e preservação

O usuário respondeu "continue", autorizando continuidade técnica. A revisão
automática de segurança recusou interpretar essa resposta como aceite formal
narrativo/produtual; essa inferência foi removida do estado. A conclusão proposta
L5 permanece inconclusiva por falso positivo de atribuição NPC, nenhum narrador
admitido; aceite explícito pendente, sem aprovação integral ou novo orçamento.
L5 segue encerrado com três chamadas, dois turnos completos e estimativa
USD 0,0022452, não cobrança confirmada. [Resultado original](hybrid-campaign-luna-hyp-007-l5-2026-10-18.md).

Records e summary do batch `7b94103b-f600-4f25-a370-0efb761429cf` intactos.
SHA-256 de records:
`1c1d5a03b7225fe2310ffcd5e787e87d4fe7f79872f66c4bfd914f88e936d90c`.
SHA-256 do manifesto L5 fechado de 18/10:
`bd9e07b289e78f98bb9a7c21fbd8059eae2a947aaa9c4d5ed6fc2852efa2c57d`.
Os manifestos L4/L5 de 03/10 também não foram alterados. Trava L5 preservada.

## Correção mínima

O detector lia o destinatário de "Ela ergue os olhos para você e fala em voz
baixa:" como sujeito de uma fala não declarada pelo jogador. A correção em
`api/scene_director_service.py::_mask_known_npc_gaze_report` fornece prova local
somente dessa construção antes do scan de ações. Não altera o texto original
ou a autoridade do pacote causal.

- Exige NPC conhecido que não colida com referência/alias do jogador.
- Exige gesto de erguer/levantar os olhos, destinatário identificado,
  coordenação imediata, verbo `fala`, adjunto de voz limitado e dois-pontos.
- Para `ele/ela`, exige o antecedente explícito e quadro de objeto não pessoal
  delimitado observado em L5; menção, ator intermediário ou alias pessoal no
  lugar do objeto não estabelecem sujeito. Não é correferência geral.
- Aspas balanceadas servem apenas para provar que o relato está fora de fala.
  Somente as posições do verbo de relato comprovado são mascaradas no scan;
  aspas/conteúdo, outras ações, offsets e gates continuam verificados.
- Não autoriza fala/ação do jogador, coerção, relativa, troca de sujeito,
  promessa ou ação posterior. Não amplia a frente lexical geral.

Nenhuma mudança em RNG, persistência, catálogo, esquema, protocolo ou prompt.
O efeito de campanha continua preparado pelo resolvedor e confirmado somente
depois dos gates. O resultado live L5 continua rejeitado historicamente.

## Evidência de testes

Antes do ajuste: quatro positivos falharam por agência e 17 negativos passaram.
Depois, a seleção nova final tem **31 testes aprovados**, cobrindo a resposta
exata observada, variantes locais e contraprovas. Dois testes de integração
com adaptador falso verificam:

1. Aviso admitido, commit único, reconstrução após reinício e replay terminal
   sem nova geração ou RNG; uma entrega, uma requisição falsa.
2. A mesma prosa com promessa indevida do jogador é recusada; revisão zero,
   registro ameaçado, nenhuma fonte ou entrega parcial.

Uma seleção intermediária de 711 passou; após completar controles e L6, a
seleção relacionada final aprovou **754 testes**, um aviso de depreciação
preexistente, sem falhas. Inclui política de cena/agência/aliases/visibilidade,
campanha, persistência/replay, integração B, custo e segurança local.
JUnit: `eval-results/hyp-007-l6-readiness-2026-10-18.xml`.

Checagem adicional final: **59 aprovados** em
`tests/test_hybrid_campaign_luna_l5_preparation.py`,
`tests/test_hybrid_campaign_luna_l6_preparation.py` e
`tests/test_scene_npc_gaze_speech_regressions.py` (16 + 12 + 31).
As contagens são sobrepostas; não somar como evidência independente.

Os testes L5 foram isolados num manifesto temporário com hashes atuais,
seguindo L2/L3, sem reescrever evidência executada. Um teste dedicado exige
hash original preservado e rejeição do runtime corrigido pelo gate histórico.
Não relaxar essa rejeição para fazer o lote antigo passar.

Diff inspecionado, whitespace do incremento e links locais verificados. A
suíte integral e frontend/build não foram repetidos: não há mudança UI e a
seleção de consumidores da política foi ampliada após os focados passarem.
As falhas históricas da consolidação Git continuam documentadas; não se afirma
suíte integral verde ou proteção semântica universal.

## L6 prospectivo

[Manifesto próprio](hybrid-campaign-luna-l6-live-gate-2026-10-18.json), runner,
preflight e lançador separados. Os três scripts preservam o comportamento L5
fora da identidade de lote, paths, trava e variável de entrada protegida;
essa equivalência é testada. Não reutilizam a credencial ou autorização L5.

Target `gpt-5.6-luna`, esforço `low`, mesmo prompt v3 e oito casos/17 turnos,
até 768 tokens de saída/chamada, 20.000 bytes/requisição e prazo existente 60 s.
Sem retry, fallback, dados de save ou admissão automática.
Teto estimado adicional **proposto, não autorizado: USD 0,15**.
O teto é guard local estimado, não garantia de bloqueio financeiro da conta.
Preços-base e ressalvas continuam os da preparação de 18/10; saldo,
autenticação, impostos, tarifas e cobrança efetiva não foram consultados.

Congelamento de 22 arquivos, incluindo segurança Host/Origin e detector
corrigido. SHA-256 do manifesto com flags false:
`b0e582b28d46cb015f8e11aa7a6e0f37b26458168704a139963297fce1eb1c49`.
Prompt v3 inalterado:
`250f2fa0fd043a74c953b2ceb22ed8ada947e60d113820118d60ab8f61755362`.

Preflight CLI executado sem credencial: 17 turnos sintéticos, zero chamadas,
maior corpo 13.415 bytes, nenhuma trava live L6 criada. Parser AST do lançador
PowerShell válido; lançador não executado, nenhuma janela de chave aberta.
Os testes demonstram negação antes de credencial/adaptador/saída, rejeição de
drift, lote fake completo, trava contra concorrência/repetição e histórico L5
intacto. Testes fake não são inferência real nem custo faturado.

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
.venv\Scripts\python.exe -m scripts.evaluate_hybrid_campaign_luna_l6_live --preflight
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short tests/test_hybrid_campaign_luna_l5_preparation.py tests/test_hybrid_campaign_luna_l6_preparation.py tests/test_scene_npc_gaze_speech_regressions.py
```

**CUSTO FINAL LUNA DESTA CORREÇÃO/PREPARAÇÃO: USD 0 (nenhuma chamada iniciada).**

## Próximo checkpoint

Aceitar ou contestar explicitamente a conclusão delimitada L5; autorizar ou
ajustar especificamente L6 nos limites acima. Depois: ativar
somente os flags L6, conferir hashes/preflight, abrir Windows Terminal via
`wt.exe` com título identificável, confirmar prontidão do novo processo e
solicitar entrada protegida fora do chat. Executar uma vez, observar custo e
resultado, fechar live e apresentar experiência para julgamento humano.
Nenhum slot L5 é transferido. Não consultar ambiente/memória de terminal,
`.env*`, saves ou chaves. Nenhum narrador/default admitido; TASK-013/CAMP-24 e
MVP continuam abertos. TASK-017/018 fecham correção e preparação, não produto.
Mudanças locais sem commit/push, checkout original preservado.
