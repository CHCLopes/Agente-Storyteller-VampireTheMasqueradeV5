--- ISSUE 1 ---
# [Segurança] Fronteira local sem validação Host/Origin
Labels sugeridas: security, alta
Estado: corrigido localmente; rascunho de rastreabilidade, não publicado.

## Problema
Origin/Host de requisição de navegador; sessão conhecida ou padrão local_player. POST de retry não exige corpo. Site não confiável aberto pelo operador em navegador/ambiente que permita acesso site externo -> loopback; DNS rebinding depende do ambiente. Reprodução local ASGI, não exploração real.

## Evidência
Antes da correção: api/main.py:873 (WebSocket) e scripts/run_campaign_source_offline_trial.py:188 (bootstrap). Posições do estado local observado, não de um commit histórico.
- api/main.py:331 (correção atual)
- api/local_request_security.py:34 (correção atual)
- scripts/run_campaign_source_offline_trial.py:152 (correção atual)
```python
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
# Sem gate Host/Origin antes do accept no baseline.
```

## Impacto
Possível leitura/mutação de sessão conhecida ou disparo de operações locais/runtime. Host forjado também alcançava o bootstrap que distribui o token efêmero do ensaio. Uma causa única, não contada novamente como IDOR.

## Correção recomendada / executada
LocalRequestBoundary antes de todos os handlers principais e offline: exige Host loopback, recusa origem estrangeira/null e metadados duplicados. HTTP 403 e WebSocket 1008 antes do accept. Mantém mesma origem, desenvolvimento local explícito e automação nativa sem Origin.

## Verificação
Quatro regressões de fronteira falharam antes. Depois: seis POSTs, origens e headers ambíguos, bootstrap, fluxo nativo e HTTP/WebSocket legítimos.

## Critérios de aceite
- [x] Origem estrangeira recusada antes de efeitos/accept.
- [x] Host de rebinding não lê bootstrap.
- [x] Fluxos locais legítimos preservados.
- [x] Nenhuma exceção testserver no servidor.

## Limitações
Não autentica pessoas nem contém processo local malicioso. O listener deve permanecer em loopback; headers não provam a interface de escuta. Sem autorização para publicar LAN/Internet.
--- FIM ISSUE 1 ---

--- ISSUE 2 ---
# [Segurança] Consolidação do jogador incluía fontes privadas
Labels sugeridas: security, média
Estado: corrigido localmente; rascunho de rastreabilidade, não publicado.

## Problema
POST /session/{session_id}/memory/consolidate/{scope}, sem IDs ou com ID privado. Sessão com fontes storyteller/system. A factory conservava a classificação privada, mas a rota retornava o resumo inteiro ao jogador. Não requer quebrar SQLite ou credencial.

## Evidência
Antes da correção: api/main.py:1971 (seleção de fontes). Reprodução com fontes sintéticas; dados reais de campanha não foram usados.
- api/main.py:1976 (correção atual)
- api/main.py:2016 (correção atual)
```python
rows = await store.list_episodic_memories(session_id)
# ... linhas intermediárias omitidas ...
memories.append(EpisodicMemory.model_validate(payload))
# ... resposta do endpoint ...
"consolidation": consolidation.model_dump(mode="json"),
```

## Impacto
Divulgação de resumo/referências privados e segredos narrativos. A rota também podia suceder uma cadeia privada pelo caminho do jogador.

## Correção recomendada / executada
Filtrar public/player antes da validação de IDs e do resumo. IDs privados se comportam como ausentes. Cadeia anterior privada causa recusa controlada sem expor ID/versão ou sobrescrever fontes. Sem migração/bifurcação do versionamento.

## Verificação
Três regressões falharam antes e passaram depois: seleção implícita, ID privado e cadeia privada. Resumo fundamentado e idempotência existentes preservados.

## Critérios de aceite
- [x] Somente public/player no resumo entregue.
- [x] ID privado não concede acesso nem grava consolidação.
- [x] Cadeia privada preservada, sem vazamento de ID.
- [x] Resumo livre continua não canônico.

## Limitações
Uma cadeia privada existente não pode ser atualizada por essa rota do jogador. Recusa deliberada para preservar a cadeia canônica única; sem API administrativa nova.
--- FIM ISSUE 2 ---
