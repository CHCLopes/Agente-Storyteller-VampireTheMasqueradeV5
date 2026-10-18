# Luna — espera interativa e custo final

Data: 2026-09-29. Estado: implementação local verificada; nenhum teste live novo.
Autorização: reduzir/adequar espera de um minuto se pertinente e mostrar custo
final em todo teste Luna. Não autoriza reabrir gates de admissão ou gasto.

## Diagnóstico observado

O ensaio Luna herdava DELAY_SECONDS=60 do controle Groq e outro cooldown de
60.000 ms na interface após conexão/resultado. Isso não é duração observada da
inferência. O prazo máximo do handler/adapter também é 60 s, mas é timeout,
não espera mínima. Não houve medição live da latência do provedor nesta etapa.

## Alterações

- TrialControl passou a usar atributo de classe de intervalo, mantendo 60 s no
  Groq; LunaTrialControl fixa zero e guarda dispatch em andamento independente do
  relógio. O handler continua serializando operações e bloqueando nova conexão.
- Protocolo do ensaio Luna versionado para source-local-luna-trial-v2; preflight,
  checagem do lançador e UI concordam em zero espera artificial. Deadline continua
  60 s, teto quatro chamadas e 768 tokens por chamada, sem retry/fallback.
- Interface Luna permite envio após briefing validado e nova ação após terminal,
  sem timer. Ação pendente, indisponibilidade e reconexão continuam protegidas.
- scripts/report_luna_test_cost.py produz relatório somente de leitura. Os dois
  lançadores Luna o invocam no finally, inclusive falha/interrupção capturável.
- Uso reportado em resposta inválida de Luna é conservado para não descartar custo
  de chamada rejeitada. Rejeição narrativa não significa chamada gratuita.

## Contrato do relatório de custo

Estados: estimated, unavailable e no_dispatch. Exibe total estimado em USD
somente com encerramento completo e uso conhecido para todas as chamadas
registradas. Com uso ausente/interrupção incerta, total=null e subtotal observado
separado. Nenhuma cobrança da conta é consultada ou declarada confirmada.

Tarifa de referência verificada em 29/09/2026: USD 0,20 por milhão de tokens de
entrada e USD 1,20 por milhão de saída. A política registra fonte/data e aplica
multiplicadores de contexto longo quando cabíveis. Não ajusta cache, tarifas
especiais ou impostos; não se apresenta como fatura ou teto financeiro.
Fontes: [modelo](https://developers.openai.com/api/docs/models/gpt-5.6-luna) e
[contagem de tokens](https://developers.openai.com/api/docs/guides/token-counting).

output_tokens já contempla tokens gerados além do texto visível; não somar
raciocínio outra vez. Não há leitura de conteúdo de raciocínio, credencial ou .env.
Artefatos antigos não foram regravados. O custo não substitui os controles de gasto.

Entradas suportadas ao operador: run_openai_luna_source_local_trial.ps1 e
run_openai_luna_low_live.ps1. Novos testes Luna devem integrar o mesmo relatório.
O avaliador HYP-006 congelado não foi reescrito para acrescentar saída cosmética.
Encerramento forçado de toda a janela/processo pode impedir qualquer impressão;
o utilitário permite leitura posterior de records.jsonl, sem transformar
artefato incompleto em custo total conhecido.

## Verificação executada

| Grupo | Resultado |
|---|---|
| Luna + custo, rodada final | 21 testes aprovados |
| Controle/ensaio Groq, executado no grupo focal inicial | 66 testes aprovados |
| Lançador Groq, handler/app B, adapter Luna e controle de fala | 137 testes aprovados |
| Interface SourcePlayerTrial | 62 testes aprovados |
| SourceTrialView, conexão e protocolo frontend | 149 testes aprovados |
| TypeScript e build isolado | Aprovados |
| Lint dos dois arquivos de UI alterados | Aprovado |
| Parser dos dois lançadores PowerShell | Aprovado |
| Preflight real do lançador Luna, sem chave | Exit 0; custo final USD 0; nenhum banco/listener/inferência |

Total distinto: **224 backend + 211 frontend**. Rodadas focais repetidas não são
somadas novamente. Avisos de depreciação preexistentes, sem falhas.
A contraprova integrada executou quatro turnos completos com HTTPX falso e SQLite
temporário mantendo clock=0, com quatro chamadas e limite final conservado.
Duas instâncias de gateway com o mesmo controle produziram apenas um dispatch
concorrente; a recusa não libera a trava pertencente à primeira chamada.

Não foi executada suíte integral do repositório: o risco é do ensaio/lançadores,
e os grupos afetados cobrem as superfícies modificadas. Não revalidar lotes
históricos congelados nem corrigir falhas históricas por arrasto.
A tentativa de executar o lançador formal com gate fechado não foi realizada:
a revisão de segurança bloqueou o comando pelo risco de iniciar execução paga.
Usaram-se testes offline, inspeção do finally e parser; execução live não é
necessária para fechar esta alteração e continua sem autorização.

## Limitações e próximo passo

Não há promessa de resposta Luna em um número específico de segundos: somente
a espera mínima local foi removida. Erro 429/transporte permanece parada segura,
sem retry automático. Outros provedores conservam seus limites até evidência
e escopo próprios. Esta correção não modifica o prompt antigo nem resolve,
por si, a progressão narrativa; campanha e novo contrato continuam em preparação.

Uma nova bateria deverá mostrar custo final e separar tempo de geração de espera
local. Não reutilizar autorização HYP-006 nem pedir chave antes de desenho/gate
do próximo ensaio. Planejamento em
[especificação](../../../spec/spec-architecture-hybrid-campaign-progression.md).
