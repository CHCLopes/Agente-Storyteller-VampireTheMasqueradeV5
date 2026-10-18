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

- Frontend: 13 arquivos e 258 testes passaram.
- TypeScript: verificação de tipos passou.
- Build de produção Vite: passou.
- Lint dos fontes (`eslint src`): três erros e um aviso, em
  `useCharacterState.ts` e `useInitializationLog.ts`. Os trechos apontados não
  foram introduzidos por esta promoção. Não foram corrigidos fora do escopo.
- Backend integral canônico: em execução (9.399 testes coletados). O resultado
  será reconciliado antes do merge; o snapshot pode ser publicado em PR draft
  enquanto a verificação termina. A execução anterior foi interrompida, não
  conta como aprovação.
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

Neste checkpoint, login e permissões GitHub foram verificados; publicação,
PR, merge e troca de default ainda não foram concluídos. Confirmar o estado
remoto e o PR em vez de inferir conclusão deste documento.
