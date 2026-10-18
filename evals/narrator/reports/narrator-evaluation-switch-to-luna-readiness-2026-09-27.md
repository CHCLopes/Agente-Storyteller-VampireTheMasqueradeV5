# Switch de avaliação para Luna — prontidão offline

**Data:** 2026-09-27  
**Switch:** `NARRATOR-EVAL-SWITCH-OPENROUTER-L3-TO-LUNA-LOW-V1`  
**Estado:** preparado; não ativado

## Decisão e fronteira

O usuário revogou temporariamente a decisão “provedores pagos fora de questão”
para permitir testes e informou que a restabelecerá quando necessário. Essa
revogação abre a classe de provedor para avaliação, mas não autoriza gasto sem
limite, não admite o Luna, não muda o default do runtime e não cancela a bateria
OpenRouter L3 que aguarda nova janela gratuita.

O switch é somente entre filas de avaliação. A rota de destino permanece
`HYP-006-OPENAI-LUNA-LOW-L1`, com `gpt-5.6-luna`, esforço `low`, oito casos
sintéticos, máximo de oito chamadas, 768 tokens de saída por chamada e 6.144 no
total. Continuam proibidos retry, reparo, fallback, troca de alvo dentro do lote,
agregação com OpenRouter e best-of.

## Verificação oficial atual

A página oficial do [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
confirma o model ID, suporte a `reasoning.effort: low`, Responses API, Structured
Outputs e ausência de Free Tier. A [página oficial de preços](https://developers.openai.com/api/docs/pricing)
mantém, para processamento Standard e contexto curto, USD 0,20 por milhão de
tokens de entrada, USD 0,02 em cache, USD 0,25 para cache write e USD 1,20 por
milhão de tokens de saída. O lote não usa ferramentas pagas nem contexto longo.

O teto de conta de USD 0,05 continua sendo um guardrail humano obrigatório, não
uma estimativa nem um controle implementado pelo runner. A API cobra por uso e o
runner não consegue impor um teto monetário global da conta.

## Artefato de switch

`scripts/prepare_luna_evaluation_switch.py --preflight` valida conjuntamente:

- gate OpenRouter L3 ainda aguardando nova janela gratuita;
- gate Luna pago ainda fechado;
- política paga temporariamente aberta apenas para testes;
- runner, launcher, manifesto, limites e hashes Luna congelados;
- zero chamada, zero inspeção de credencial e zero mudança de default.

O preparador não possui modo `--live`; `--live` é recusado pelo parser. O runner
Luna continua recusando execução antes de credencial ou criação de diretório
enquanto `live_inference_authorized` e `paid_spend_authorized` estiverem falsos.

## Evidências

- 4 testes próprios do switch: aprovados.
- Regressão combinada switch, Luna, runner-base e isolamento de rede: 22 testes
  aprovados.
- Preflight do switch: exit 0.
- SHA-256 do preflight: `dca62e95c5930ff2734ca355fb5951bbcd981c7c871d308096d9b9389c58b00a`.
- Preparador: `c23758ac5a050b91c42b3be58a7e545d0d676591e0700e37cc311e346a30570e`.
- Testes: `b8ef06388a09a526055bdcd2ff432c1d5c44711652409afd8f0c0a7de58f27b4`.
- Gate do switch: `8feb2e7f58e84f5e8fdafa2dda196539dfe8046d7182a12970942a775b100ed0`.

Os avisos de cache do pytest decorrem da permissão de `.pytest_cache` no
worktree e não alteraram a execução.

## Ativação ainda necessária

Antes de qualquer chamada, o usuário precisa autorizar explicitamente o lote
pago delimitado e confirmar que configurou no painel da conta um limite de gasto
de USD 0,05. Depois disso, o gate Luna será aberto de forma rastreável e o
launcher solicitará confirmação `PAID-USD-0.05` e chave por entrada mascarada.
Nenhuma dessas ações foi realizada nesta preparação.
