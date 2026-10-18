# HYP-007-L2 — prontidão antes de credencial

O usuário aprovou em 03/10/2026 um lote novo de até 17 chamadas ao
`gpt-5.6-luna` em esforço `low`, com teto estimado adicional de USD 0,15.
É autorização distinta de L1, que parou após HTTP 400 e permanece inconclusivo.

Hipótese e critérios permanecem os do protocolo HYP-007: oito percursos
sintéticos CAMP-EVAL-01–08, consequência determinística preparada antes da
narração, pertinência de Mara, agência, segredo, mecânica e desfecho. Não há
retry, fallback, troca de alvo, admissão automática ou uso de dados reais de
campanha. Prompt, caso, 768 tokens máximos por chamada, corpo HTTP máximo
20.000 bytes, deadline de 60 s e regra de parada na primeira falha foram
mantidos. O schema de transporte corrigido torna `protocol` obrigatório para
Structured Outputs; a validação Pydantic local não foi afrouxada.

O gate registra `lot_id: HYP-007-L2` e hashes dos 16 arquivos congelados.
O runner grava em pasta `hybrid-campaign-luna-l2-<UUID>` e adquire uma pasta
atômica `hybrid-campaign-luna-l2-once` antes de qualquer despacho em produção.
Uma segunda execução L2 é recusada mesmo com novo UUID. O artefato L1 não
é modificado ou agregado.

Verificação antes da chave: 14 testes focados aprovados; parser PowerShell
sem erros; `_gate()` e autorização L2 válidos; preflight keyless com 17 turnos,
zero chamadas ao provedor, maior corpo de 12.019 bytes e hash do prompt
`10b64256b36fcae1a80432361e9e4883129d8b78084a855b03515ab26742f4cf`.
Nenhuma credencial foi consultada nem houve gasto em L2 nesta preparação.

Próximo passo humano: executar o lançador em PowerShell visível e inserir a
chave somente no prompt mascarado. O resultado deverá informar custo estimado
por uso ou `indisponível`; nunca converter ausência de uso em zero. O teto é
uma guarda local estimada, não confirmação da fatura da conta.
