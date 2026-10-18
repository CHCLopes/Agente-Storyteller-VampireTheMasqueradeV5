# Promoção da evolução para a branch principal

## Autorização e fronteiras

Em 18/10/2026 foi retomada a promoção ao GitHub já autorizada pelo usuário:
`CHCLopes/Agente-Storyteller-VampireTheMasqueradeV5`.

- Origem preservada: checkout original em `master`.
- Implementação: worktree `b008`, branch `codex/planejamento-agente-storyteller-v5`.
- Base remota observada: `master`, commit `5e563824fcba4c53cc37b5084a8ce65f3fa30356`.
- `main` não existia no remoto na verificação; referências locais antigas não
  foram tratadas como prova de existência remota.
- Rota aprovada: consolidar o snapshot de desenvolvimento, criar `main` a partir
  da base preservada, integrar por PR e depois alterar a branch padrão.
- Não apagar `master`, reescrever histórico, usar force-push, contornar proteções
  ou modificar o checkout original.

Esta promoção não é release nem conclusão do MVP. Não admite narrador, não
aceita o lote L4, não libera o lote L5 e não autoriza inferência ou novo gasto.

## Conteúdo e segurança da publicação

Publicar fontes, testes, catálogos, planos, especificações, protocolos, fixtures
sintéticas, relatórios técnicos e o PDF/fontes da auditoria de segurança.
Não publicar bancos, saves, logs, resultados locais, dependências, builds ou
prévias PNG regeneráveis. Os artefatos locais continuam preservados.

As modificações preexistentes nos dois arquivos `.env.example` ficam fora da
consolidação, sem leitura, cópia, sobrescrita ou descarte. O README documenta a
configuração do runtime. A exclusão não remove os exemplos já versionados na
base histórica; simplesmente não inclui suas alterações locais.

O scanner dos candidatos à publicação encontrou 14 indicadores, todos
classificados como fixtures/placeholders em testes; nenhum candidato exigindo
revisão adicional pelos padrões utilizados. É uma verificação heurística,
não garantia universal de ausência de segredos. Arquivos `.env*` e caminhos de
credenciais não foram abertos.

`.gitattributes` preserva bytes sem conversão automática de finais de linha.
Os manifestos avaliam bytes de prompts/implementação: normalização silenciosa
na publicação ou no clone poderia invalidar a proveniência. Manifestos
históricos não foram recalculados nem reescritos para fazê-los passar.

## Verificação e estado

- Núcleo crítico backend: 252 testes passaram novamente em 18/10/2026,
  cobrindo segurança, HTTP/WS, transações, retomada, memória e ensaio offline.
- Frontend: 13 arquivos e 258 testes passaram.
- TypeScript: verificação de tipos passou.
- Build de produção Vite: passou.
- Lint dos fontes (`eslint src`): três erros e um aviso, em
  `useCharacterState.ts` e `useInitializationLog.ts`. Os trechos apontados não
  foram introduzidos por esta promoção. Não foram corrigidos fora do escopo.
- Backend integral canônico: 9.399 casos; 8.719 aprovados, 333 ignorados,
  286 falhas e 61 erros; oito avisos. Duração CLI: 1h41min19s. A suíte integral
  não está verde. A execução anterior interrompida não conta como aprovação.
- Reprodução focada de L4/L5: quatro falhas e dois testes aprovados. Os quatro
  testes falham em `campaign_luna_implementation_drifted`, pois consultam
  manifestos anteriores à correção de segurança. Não houve chamada de provedor;
  os manifestos históricos continuam intactos e o bloqueio permanece fechado.
- `pytest.ini` limita a descoberta à pasta canônica `tests`. Sem isso, cópias
  históricas em `eval-results` eram coletadas, gerando 33 erros de importação;
  nenhum teste canônico foi removido ou desativado.
- Inspeção do diff: 285 ocorrências de whitespace em 56 arquivos do snapshot,
  incluindo arquivos históricos e desenvolvimento preexistente. A checagem não
  está verde; sem limpeza oportunista ou normalização de evidência.
- Auditoria de segurança anterior: SEC-001/SEC-002 corrigidos; relatório em
  [security-audit/README.md](security-audit/README.md). É evidência datada, não
  uma alegação de suíte integral verde ou de nova auditoria após cada commit.

Os hashes dos lotes narrativos que incluem o ensaio offline foram invalidados
pela correção de segurança anterior. Gates devem continuar falhando fechados;
ao retomar avaliação paga, preparar novo preflight e congelamento prospectivo.
Não alterar a evidência histórica para obter verde artificial.

O conflito `Final actor schema differs` e os problemas de lint já constavam em
`evals/narrator/reports/narrator-pause-resume-technical-audit-2026-09-22.md`.
O problema de sidecars Windows e o schema congelado também estão registrados
em `evals/narrator/reports/hybrid-campaign-source-offline-2026-09-29.md`.
Não interpretar reprodução de dívida histórica como autorização para reescrever
os experimentos ou como certificação de release.

### Reconciliação das falhas e erros

| Causa | Falhas | Erros | Evidência e limite |
| --- | ---: | ---: | --- |
| Schema congelado dos experimentos históricos | 281 | 61 | 314 ocorrências exibem `Final actor schema differs`; 28 são cascatas de preflight com retorno 3, artefato não criado ou mensagem diferente da esperada. Os nove preparadores foram reproduzidos separadamente, sem live ou credenciais, e todos param nesse mesmo schema. |
| Manifestos anteriores à correção de segurança | 4 | 0 | Dois testes L4 e dois L5 param em `campaign_luna_implementation_drifted`. Gates e manifestos não foram reescritos; a proteção permanece fechada. |
| Sidecars SQLite Windows | 1 | 0 | `test_unavailable_or_incompatible_store_stays_unchanged[asyncio-wrong_session]` em `test_narrative_source_observation_persistence.py`; divergência de arquivos `-wal`/`-shm`, já registrada anteriormente. |

Total: 347 ocorrências classificadas, nenhuma sem categoria. Os 333 skips são
38 casos com política/módulo impedindo execução e 295 em que o host não carrega
o módulo de execution policy. Nenhuma política foi contornada ou novo skip
adicionado. A coleção confirmou não haver teste Python versionado fora de
`tests/`; a configuração de descoberta não elimina testes canônicos.

Essas pendências ficam preservadas e explícitas: não impedem reproduzir/publicar
o snapshot de desenvolvimento solicitado, mas impedem alegar suíte integral
verde ou release aprovado. Não foi identificada causa nova introduzida pela
publicação Git. Os bytes da aplicação não mudaram durante a verificação.

Resultados locais, ignorados pelo Git: `eval-results/repository-promotion-backend.xml`,
`eval-results/repository-promotion-critical.xml` e
`eval-results/repository-promotion-frontend.json`. As contagens dos grupos
focados se sobrepõem à suíte ampla, não são testes únicos adicionais.

Reprodução da suíte canônica, na raiz do projeto:

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
& .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short
```

## Conclusão verificada

- Snapshot: `e31f679`; reconciliação antes do merge: `2a02d6f`.
- [PR #1](https://github.com/CHCLopes/Agente-Storyteller-VampireTheMasqueradeV5/pull/1)
  integrado em 18/10/2026, às 10:37:14 no fuso America/Fortaleza.
- Merge de integração: `73f1f2a1c4bf22195a8ce84f49a857c74267bab0`.
- API GitHub confirmou `default_branch: main`; `ls-remote --symref` confirmou
  `HEAD -> refs/heads/main` com o commit de integração antes deste registro.
- `master` preservada em `5e563824fcba4c53cc37b5084a8ce65f3fa30356`, sem
  force-push, exclusão ou alteração do checkout original.
- Branch do worktree de implementação preservada e alinhada por fast-forward.
  Os dois exemplos de ambiente modificados localmente continuam fora dos commits.
- Este registro final altera somente documentação; os bytes da aplicação e os
  artefatos da auditoria permanecem os mesmos verificados nos testes.

A versão atual passa a ser a principal no GitHub, mas não é release nem aceite
do MVP. O próximo checkpoint narrativo permanece L4; L5 continua sem autorização
de gasto e exige preparação prospectiva atualizada antes de qualquer execução.
Nenhuma inferência real de provedor foi executada nesta promoção.
