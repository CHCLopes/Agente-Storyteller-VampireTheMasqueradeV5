--- ISSUE 1 ---
# [Segurança] Entrada sem feedback e sem validação estrutural
Labels sugeridas: security, informativa

Estado: corrigido nas fontes; rascunho não publicado.

Problema: O console usava getpass e verificava apenas se key.strip() era não vazio. O operador não via quantidade de caracteres, duplicata ou controles de colagem.
Condição: Operador cola duas vezes o mesmo token, ou o terminal entrega Ctrl+V como controle em vez do texto. A presença desse evento na entrada real não foi inspecionada.
Impacto: Falha local, tentativa desnecessária, diagnóstico ambíguo e dificuldade de correção. Nenhum vazamento de chave foi demonstrado.
Evidência atual: scripts/luna_credential_supervisor.py:31. read_credential; credential_problem em scripts/evaluate_openai_luna_low_live.py:46; bloqueio do supervisor antes de subprocess em scripts/luna_credential_supervisor.py:167.
Correção: Editor mascarado com asteriscos e contador só na tela, Backspace, Esc/Ctrl+U, cancelamento, limite de buffer e validação. Repetição integral de token sk- duas a quatro vezes é recusada; espaços, Unicode e controles são recusados. Nunca ler clipboard, revelar fragmentos ou dividir automaticamente a chave.
Critérios de aceite:
- [x] Colagem repetida rejeitada e corrigível
- [x] Nenhum valor real no output/status/log
- [x] Entrada inválida bloqueada antes do HTTP
- [x] Asteriscos/contador testados em console Windows com valor sintético
--- FIM ISSUE 1 ---

--- ISSUE 2 ---
# [Segurança] Falhas locais, rede e JSON agrupadas no mesmo código
Labels sugeridas: security, informativa

Estado: corrigido nas fontes; rascunho não publicado.

Problema: HTTPError e ValueError eram normalizados como transport_or_response_invalid, sem subtipo suficiente para diagnóstico.
Condição: Cabeçalho local inválido, falha de conexão/timeout/protocolo ou resposta JSON inválida.
Impacto: Não distinguir falha local de falha remota; risco operacional de pedir outra chave ou repetir chamada sem causa conhecida. Não constitui, isoladamente, vulnerabilidade de autorização.
Evidência atual: scripts/evaluate_openai_luna_low_live.py:61. transport_error_code:61; response_json_invalid:209; response_shape_invalid:215. Testes MockTransport fazem exceções conterem texto sintético sensível e confirmam que ele não aparece no erro normalizado.
Correção: Classificação só pelo tipo da exceção, sem texto potencialmente secreto. Separar protocolo local, conexão, timeout, protocolo remoto, requisição local, I/O e parsing/forma do JSON. Preservar códigos HTTP 401/403/429/5xx.
Critérios de aceite:
- [x] Sem mensagem bruta de exceção/headers/body
- [x] Sem retry novo
- [x] Categorias distinguíveis em testes offline
- [x] Histórico L26 preservado, sem reclassificar sua causa
--- FIM ISSUE 2 ---

--- ISSUE 3 ---
# [Segurança] Ramo de credencial vazia referenciava fase inexistente
Labels sugeridas: security, informativa

Estado: corrigido nas fontes; rascunho não publicado.

Problema: OperationPhase.AUTHENTICATION não existe no enum do contrato; o ramo de credencial vazia produzia AttributeError em vez do erro controlado.
Condição: Entrada vazia chegando diretamente ao adaptador, ou entrada malformada interceptada no novo ramo.
Impacto: Erro local sem diagnóstico contratual; nenhuma chamada necessária para reproduzir. Não comprova vazamento de credencial.
Evidência atual: scripts/evaluate_openai_luna_low_live.py:172. api/llm/contract.py:91 define as fases; scripts/evaluate_openai_luna_low_live.py:172 usa fase válida após correção.
Correção: Usar OperationPhase.VALIDATION; categoria de autenticação e códigos credential_missing/credential_input_invalid sem material secreto.
Critérios de aceite:
- [x] Entrada vazia gera erro normalizado
- [x] Sem AttributeError
- [x] Sem acesso à rede para chave inválida
--- FIM ISSUE 3 ---
