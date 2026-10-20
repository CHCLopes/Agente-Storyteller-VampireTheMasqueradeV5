# HYP-007-L16 — violação terminal real; hipótese v5/L17 fechada

18/10/2026, gpt-5.6-luna/low, prompt v4.
Batch `b6fa997d-1241-4363-8d52-1aded62e4a42`.

## Resultado observado e custo final

L15 aceito e L16 autorizado por Prossiga. Após chave protegida, seis chamadas/
cinco turnos; CAMP-EVAL-01 completo, aviso/dano/ajuda CAMP-EVAL-02 confirmados,
resgate parcial R-06 rejeitado. Parada campaign_source_policy_failed. 03–08
não alcançados. Gate L16 fechado, trava mantida; sem retry/fallback/transferir
11 slots. Nenhum narrador admitido; TASK-013/CAMP-24/MVP abertos.

**USD 0,0052150 finais estimados**, não cobrança confirmada. 18.353 tokens
entrada/1.287 saída, seis chamadas com usage/zero sem. Reporter --settled com
records conferidos contra summary; sem ajustes de cache/tarifas/impostos.
Preparação/verificação offline adicional USD 0, nenhuma chamada real nova.

Originais em eval-results/hybrid-campaign-luna-l16-b6fa997d-1241-4363-8d52-1aded62e4a42/.
SHA256 records `bf040328b6a7c60b08a937a422cc3a7612629be7184074c7b4828e5fe3ba1320`.
SHA256 summary `2cf83a6a3ec23ba3a32a91ee4568e46b36289a36e1c4fbeaba15c7f72c47e30a`.
Manifesto fechado L16 `a3cb71c93d3504843b3ddccb99ba919bfa15e44cf4be1056d437acd6eb3270b3`.

## Causa comprovada — não é falso positivo

Resposta q: "Como você examina o conteúdo legível do registro preservado?"
Packet de R-06 tem state_after.outcome partial. O prompt v4 já manda string
vazia em desfecho. validate_campaign_source_proposal exige q vazio quando
outcome não é null; erro específico reproduzido campaign_source_effect_mismatch.
A continuação proposta não é autorizada pelo desfecho determinístico.

Cinco testes novos em tests/test_campaign_terminal_question_regressions.py:
rejeitam pergunta real e pergunta genérica em partial, contrafactual q vazio
admitido offline, integração com rejeição atômica da resposta exata e integração
contrafactual/replay. Rejeição mantém revisão três/registro wet/sem desfecho/
nenhuma entrega. Contrafactual confirma revisão quatro/partial; replay não gera,
entrega ou rola de novo. Não alterar/reclassificar resposta live por isso.
Nenhuma correção/relaxamento no validador, runtime, schema, RNG ou persistência.
Narrador não elegível para admissão com esta evidência no perfil v4; campanha
integral não concluída. Isso não prova incapacidade universal do modelo.

## Hipótese técnica prospectiva — v5/L17, sem gasto autorizado

L17 não é repetição idêntica: novo prompt v5, apenas o trecho q reordenado para
consultar primeiro causal_packet.state_after.outcome. Enumera desfechos e diz
explicitamente que partial encerra o objetivo; só null autoriza pergunta.
Não muda catálogo/critério de aceitação/arquitetura ou fatos. Parte anterior
do prompt v4 preservada e hash v4 intacto. É hipótese de redução da violação,
não eficácia comprovada. Sem correção pós-hoc/remoção automática de q.

Prompt v5 SHA256 `393e0e5c1078e41af20f3ff30639deea34e7cac0614385ccde3524962949bf60`.
Manifesto fechado L17 `2d6984f6741ba9a9727ca07727857779bea4b6e2ce85879ff52b7201b6823828`.
Mesmo alvo low/oito percursos/17 chamadas/768 tokens/20.000 bytes/60s,
teto adicional proposto USD 0,15, sem retry/fallback/admissão automática.
Paid/live false, 22 hashes válidos. CLI 17 sintéticos/zero chamadas, máximo
13.952 bytes; AST PowerShell sem erros. Sem chave/terminal/trava L17.

Primeira checagem de preparação tinha uma expectativa copiada de drift do
runtime histórico. Como nenhum runtime mudou, o manifesto L16 deve continuar
válido e fechado. Teste corrigido para essa propriedade, sem editar hashes
históricos ou desativar verificação. Teste novo prova delta limitado v5/v4.

Verificação final: 57 testes focados aprovados, um aviso preexistente,
34,66s; XML eval-results/hyp-007-l17-focused-2026-10-18.xml, zero errors/
failures. Cobre testes L16/L17, novo caso terminal, perfil, integração e
trajetórias. Não repetida seleção ampliada: nenhum runtime/validador mudou;
997 aprovados são evidência anterior, não nova execução. Não é suíte integral/
frontend/build/release verde. Diff inspecionado sem whitespace; sem commit/push.

Proposta: aceitar L16 como violação real de fechamento terminal, Luna não
admitido no perfil v4, e autorizar hipótese L17/v5 nos limites acima.
Continue/prossiga aprova ambos; depois chave protegida. Não prometer última
tentativa ou admissão. Fragilidade lexical/UX/fidelidade semântica continuam
registradas, sem refatoração geral/decisão arquitetural por arrasto.
