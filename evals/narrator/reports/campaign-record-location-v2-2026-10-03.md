# Posição canônica do registro — opção A, verificação offline

Data: 03/10/2026. Worktree `b008`, branch
`codex/planejamento-agente-storyteller-v5`. Autorização: "Aprovo a opção A".
Estado: implementação técnica verificada; não é aceite de narrador/experiência.

## Observado e corrigido

HYP-007-L2 não fornecia posição exata do documento no pacote causal. A
especificação previa bancada baixa no Arquivo e superfície seca na Galeria.
L2 teve também texto R-05 abaixo de 30 palavras; acrescentar posição não
comprova que esse outro problema foi resolvido pelo modelo.

- `api/campaign_progression_catalog.py` / `campaign_progression_service.py`:
  versão de conteúdo/política v2, `record_location=bench|dry_surface`; somente
  R-05/R-06 mudam para superfície seca. R-07 recupera conteúdo sem movimento.
- `api/campaign_source_context.py` / `campaign_source_storage.py`: versões
  explícitas no leitor, origem e snapshot coerentes, reconstrução do tipo
  retido. V1 conserva sua forma anterior sem preencher posição ou migrar saves.
- `api/campaign_source_profile.py`: projeção pública antes/depois e rótulos
  derivada do estado v2. O narrador não recebe autoridade para escrever estado.
- `evals/narrator/prompts/hybrid-campaign-source-v2.md`: prompt prospectivo
  separado, com posição e faixa já exigida de 30–150 palavras. Não está
  ativado no runner pago e não substitui o v1 congelado de L2.

Sem DDL, novo RNG, relaxamento de gates, nova dependência, mudança de default,
modificação do seed genérico B, commit ou push. Checkout original preservado.

## Verificação observável

1. Seleção focada `test_campaign*.py` e `test_hybrid_campaign*.py`, antes de
   acrescentar o preflight v2: **100 aprovados**.
2. `tests/test_campaign_v2_keyless_preflight.py`: **1 aprovado**, 17 turnos
   autorados simulados, zero chamadas externas; maior corpo HTTP 13.043 bytes
   contra teto de 20.000. Prompt SHA-256
   `4c3f88d3eff9c33863189173dfba91789fedd4e8b07d842f59d4b86beebc939a`.
3. Regressão ampliada, justificada pela mudança dos tipos retidos: seleção de
   `test_narrative_source*.py`, `test_narration_resume*.py`,
   `test_turn_execution_service.py`, `test_persistence.py`, `test_campaign*.py`
   e `test_hybrid_campaign*.py`: **1.612 aprovados / 1 falhou**, 107,31 s.
   A seleção começou antes da criação do teste de preflight v2; as contagens
   se sobrepõem, não devem ser somadas como cobertura distinta.
4. A falha é
   `test_narrative_source_observation_persistence.py::test_unavailable_or_incompatible_store_stays_unchanged[asyncio-wrong_session]`:
   criação de `-wal/-shm` no Windows. Já registrada no relatório de 29/09,
   sem mudança neste incremento. A suíte ampliada não está integralmente verde;
   não foi executada toda a coleção do repositório nem testes de frontend.

Reexecução final consolidada dos grupos focados, incluindo o preflight v2:
**101 aprovados**, 27,08 s. Inspeção das alterações e checks de whitespace dos
16 arquivos do incremento concluídos; apenas avisos Git de conversão LF/CRLF,
sem alteração de configuração. `state/PROJECT_STATE.md` não existe; estado
durável atualizado no prompt de retomada, plano, checklist e especificação.

Os novos testes demonstram as transições de posição em todas as regras,
rejeição de v2 sem posição/posição impossível/versão misturada, manutenção de
v1 sem campo adicional, rollback em falha do provedor e entrega, persistência
da cápsula/hash, retomada após reabrir SQLite, vínculo à operação original,
commit único e replay sem outra chamada ou RNG. Os oito percursos existentes
também verificam posição final. A comparação de cápsula usa payload e hash
canônicos: ordenar chaves de um dicionário durante armazenamento não é mutação.

Compatibilidade legada foi testada com seeds v1 sintéticos, não com bancos
pessoais. A regra de campo obrigatório vale para payload retido com versão v2;
a criação local de um novo estado pode usar o default inicial `bench`.

## Integridade histórica e custo

L2 continua `live_inference_authorized=false`. Seus hashes congelados não foram
atualizados; o runner recusa a implementação nova com
`campaign_luna_implementation_drifted`. Testes offline de transporte usam um
manifesto temporário exclusivo do teste, mantendo o gate real intacto, e têm
uma contraprova específica para a recusa do manifesto histórico.

SHA-256 dos registros L2 rechecado:
`23e741bfa5260363057c4058cff6a97a804b4036c6287afc9182bf40cea30e71`.
Custo de inferência deste incremento e preflight: **USD 0**, zero chamadas.
O custo histórico L2 continua **estimado USD 0,0012318**, não cobrança confirmada.
Nenhum arquivo de credencial ou `.env` foi lido; dotenv permaneceu desativado.

## Limites e próximo checkpoint

Estado correto e contexto suficiente não garantem fidelidade semântica,
role-play, progressão percebida ou qualidade narrativa. O validador conserva
suas contraprovas delimitadas; não foi promovido a verificador semântico geral.
TASK-014 concluída tecnicamente; TASK-013/CAMP-24 e admissão continuam abertos.

Proposta de próximo lote, ainda sem autorização: **HYP-007-L3**, Luna low,
oito trajetórias/até 17 chamadas, 768 tokens de saída por chamada, deadline
60 s, sem retry ou fallback, parada no primeiro gate reprovado ou uso/custo
indisponível; teto estimado adicional **USD 0,15**. É orçamento proposto, não
previsão de gasto nem garantia de limite rígido do provedor. Manter custo final
obrigatório, chave efêmera por entrada segura e dados somente sintéticos.
Após autorização, congelar manifesto próprio de v2, preparar lançador separado,
verificar offline e solicitar chave apenas se efetivamente necessária. Não
reaproveitar o lote L2, sua trava ou seu saldo de chamadas como autorização.

Configuração recomendada no checkpoint: **Sol high**, por conciliar autoridade
canônica, persistência, critérios e orçamento; operação posterior já congelada
pode usar **Sol low**. Ação humana: autorizar ou alterar o orçamento/escopo do
novo lote. Não pedir novamente a opção A de posição ou as decisões PROG.
