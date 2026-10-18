# Auditoria de segurança - 16/10/2026

Auditoria solicitada e correções autorizadas. Resultado: duas causas únicas
confirmadas e corrigidas localmente (SEC-001 alta; SEC-002 média). Não é
certificação, liberação de release ou aprovação de narrador/campanha.

## Artefatos

- `relatorio-auditoria-seguranca.pdf`: relatório em pt-BR, 11 páginas.
- `dados-relatorio.json`: achados, evidências, correções, testes e limites.
- `cobertura-e-scan.json`: 20 handlers explícitos, categorias e scan mascarado.
- `issues.md`: duas issues completas para rastreabilidade, não publicadas.
- `manifesto-auditoria.json`: hashes das superfícies corrigidas e do PDF.
- `plano-auditoria.md`: plano executado e fronteiras.
- `scan_local.py`: inventário AST e scanner local reproduzível.
- `gerar_relatorio.py`: gerador PDF/gráficos/fontes/manifesto/prévias.
- `previews/pagina-01.png` até `pagina-11.png` e `visao-geral.png`: rasterização.

Inspeção visual: visão geral de todas as páginas e detalhe do apêndice de issues;
sem corte, sobreposição ou tabela ilegível observados. Texto e contagens também
validados por pypdf. Gerador usa fontes Arial do Windows e bibliotecas locais.

## Verificação executada

Baseline: sete regressões falharam antes das correções. Após correção:

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
& .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_security_audit_regressions.py tests/test_operational_contract_api.py tests/test_campaign_source_offline_trial.py tests/test_websocket_flows.py tests/test_perf_sec.py tests/test_narrative_source_local_app.py tests/test_narrative_source_local_selection.py
# 196 passed
& .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_websocket_transactional.py tests/test_narration_resume_service.py tests/test_memory_service.py
# 56 passed, grupo distinto
& 'C:\Users\skate\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' client/node_modules/vitest/vitest.mjs run --root client src/components/NarrativeLog.test.tsx src/components/SourceTrialView.test.tsx
# 24 passed
```

Sem rede/provedor real; nenhum `.env*`, arquivo de credencial ou save examinado.
Clone local não raso: 27 commits, 182 blobs textuais; código atual: 1.063 arquivos.
14 indicadores atuais são fixtures; nenhum indicador histórico pelos padrões
usados. Bundle existente examinado sem rebuild. Sem auditoria de CVEs ou pentest.

Suíte integral não repetida. Avisos de depreciação preexistentes. Checagem de
whitespace identificou quatro linhas preexistentes em main (760/800/2147/2156),
não tocadas pelas correções; sem limpeza oportunista ou alegação de diff global
verde. Alterações do usuário foram preservadas; nenhum commit/push/merge.

## Reprodução dos artefatos

Da raiz do worktree:

```powershell
& .\.venv\Scripts\python.exe docs/security-audit/scan_local.py
& 'C:\Users\skate\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' docs/security-audit/gerar_relatorio.py
```

O primeiro comando só lê fontes permitidas e grava saída mascarada nesta pasta;
o segundo usa reportlab/pypdf/pypdfium2 já presentes. Nenhuma dependência instalada.

## Limites e continuidade

Operador local único: Host/Origin não são login nem prova de binding. Manter
listener em loopback; native callers/processos locais continuam confiáveis.
Cadeias privadas existentes são recusadas no endpoint do jogador, sem migração.
Rotas públicas/compartilhadas do mesmo operador não ganharam owner_id fictício.

Mudança no ensaio offline invalida hashes de preparação narrativa que o incluam.
Não reescrever manifestos live históricos; ao retomar L5, refazer seu preflight
e congelamento prospectivo, sem inferir autorização de gasto nesta auditoria.
