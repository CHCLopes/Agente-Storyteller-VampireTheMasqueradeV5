# Chamada única Luna — transporte/resposta inconclusivos

Data: 19/10/2026. Probe L26, batch 6c5f11c5-b2e7-4d1e-9c6b-b2422b407abf.

## Autorização e escopo

Humano restringiu o pedido inicial de teste a UMA chamada paga, manteve USD 0,15
e confirmou Está autorizado. Fixou também USD 0,15 como teto padrão previamente
aprovado por teste enquanto outro valor não for proposto; quantidade/escopo
continuam dependentes de autorização. Não interpretar como gasto automático.

Pedido de bateria L25 interrompido antes de publicar: gate fechado, nenhuma
requisição/latch/artefato L25, supervisora idle. L25 não foi executado.
Probe separado: CAMP-EVAL-05/R-05, um cenário/um turno, MAX_CALLS=1 e
authorized_calls=1 obrigatórios antes da credencial e em cada dispatch.
O envelope max_calls=17 do manifesto é compatibilidade com o protocolo da
supervisora já carregada, não autorização para 17: o limite efetivo e o schedule
são um. Mantidos Luna low/prompt v6/768 tokens/20.000 bytes/60s/USD 0,15,
sem retry/fallback/admissão. Manifesto e 22 arquivos verificados.

## Observado

Supervisora recebeu o pedido sem credencial e executou preflight sem chave,
revalidou e iniciou exatamente uma tentativa. Summary: planned_calls=1,
attempted_calls=1, completed_turns=0, status stopped,
stop_reason campaign_source_provider_failure. Registro:
transport_or_response_invalid, response null, geração 485 ms/turno 580 ms.
Não há HTTP status, subtipo seguro da exceção ou resposta do modelo.
Não afirmar que o pedido chegou ao servidor ou que houve cobrança: o marcador
call_made comprova entrada na tentativa do adapter, não recebimento no provedor.

O adapter agrupa httpx.HTTPError e ValueError (inclui transporte/protocolo ou JSON)
nesse código. Não é diagnóstico de chave inválida, TLS, rede ou saldo. Não
inspecionar a chave/clipboard/ambiente/memória para adivinhar a causa.
Autenticação do provedor e qualidade narrativa permanecem inconclusivas.

## Custo final

Indisponível, não USD zero: uma tentativa sem usage, zero precificadas,
estimated_total_usd null. Reporter --settled reproduzido. Não há cobrança
confirmada. Limite local USD 0,15 não é garantia de faturamento do provedor.

## Integridade e verificações

Diretório eval-results/hybrid-campaign-luna-l26-6c5f11c5-b2e7-4d1e-9c6b-b2422b407abf/:

- records.jsonl SHA256: 2cbbcfe6d2d5835807e6de18d7e02d9d309d4c849cd11f6e376ade7946b55052
- summary.json SHA256: 38af2d0ab13e39e4c170a95fbfd04c16badf01446fba8f688ee9361dcb7125c5
- Manifesto fechado SHA256: 0fd1bff7e5da88a2c6974b3a7a5e5dff9ec91167889fdf5a248b01eeec62f249

46 testes focados aprovados antes e depois: probe de uma chamada, teto/gate,
hashes, recusa de outro authorized_calls, fake com uma requisição/turno,
preflight sem chave/rede, supervisora e custo; um aviso preexistente multipart.
XML eval-results/luna-single-call-readiness-2026-10-19.xml e
eval-results/luna-single-call-closure-2026-10-19.xml. Suíte integral não repetida:
teste operacional isolado sem mudança no runtime do jogo.

Gate probe paid/live fechado, latch/artefatos preservados. Supervisora idle,
last_lot=26/exit 2, prazo inalterado (20/10 00:00 Fortaleza), sem nova chave.
L25 permanece fechado. Sem retry, fallback ou segunda tentativa.
Nenhum narrador admitido/MVP aberto.

## Limites e próximo passo

A sessão de credencial está disponível; a autenticação na API não foi confirmada.
Não solicitar nova chave sem evidência de necessidade. Antes de uma próxima
tentativa, melhorar a discriminação segura de erros (somente categoria/código,
sem mensagem de exceção/headers/body/credencial) e verificar offline. Nova
inferência requer autorização da quantidade, não nova aprovação do teto padrão.
Não repetir este lote. O envelope antigo da supervisora é limitação operacional;
não interpretá-lo como quantidade aprovada nem alterar o processo vivo para
inspecionar a chave.
