# L27 — teste unitário da supervisora corrigida

## Escopo e autorização

Em 19/10/2026, após entrada protegida, humano pediu explicitamente uma chamada
de teste. Teto padrão USD 0.15; exatamente uma chamada, sem retry, fallback,
troca de modelo ou admissão automática. Nova identidade preserva evidência L26.
Manifesto novo fixa 22 arquivos atuais. Envelope legado max_calls=17 não amplia
authorized_calls=1, MAX_CALLS=1 nem o schedule unitário CAMP-EVAL-05/R-05.

## Verificação e resultado

- Preflight sem rede: uma chamada planejada, zero envios, request de 10348 bytes.
- 35 testes focados aprovados; um aviso preexistente python_multipart.
- Diff L26/L27 inspecionado: alterações restritas à identidade do novo lote.
- Batch: e3c7c9ae-201c-4fbe-8ef0-a2c6eb926cb1.
- Diretório: eval-results/hybrid-campaign-luna-l27-e3c7c9ae-201c-4fbe-8ef0-a2c6eb926cb1.
- planned_calls=1; attempted_calls=1; completed_turns=1; stop_reason=null.
- Provedor observado OpenAI; modelo reportado gpt-5.6-luna; esforço low.
- Geração 4388 ms; turno 4538 ms; desfecho preserved.
- Uso reportado: 2512 tokens de entrada, 163 de saída.
- Custo estimado USD 0.000698. Não confirma cobrança, impostos ou ajustes.
- SHA256 records: 38af0c9eb74e355aef011bd8355d80e216103d5c690e88d23bccfb618bc7748f.

## Encerramento e limites

Gate fechado após execução; latch preservado, sem nova chamada. Supervisor
20604 voltou a idle/last_lot=27/last_exit_code=0, deadline original mantido.
Chave, clipboard, ambiente e memória do processo não foram lidos pelo agente.
O teste comprova autenticação e execução neste momento, não a causa da falha
histórica L26. Não comprova satisfação narrativa nem admite narrador do MVP.
