# Checkpoint de desenvolvimento público — 20/10/2026

## Escopo autorizado

Sincronizar o trabalho local publicável com o repositório
`CHCLopes/Agente-Storyteller-VampireTheMasqueradeV5` e adaptar sua apresentação
ao estado real do projeto. A publicação é da branch de implementação
`codex/planejamento-agente-storyteller-v5`, sem merge, force-push ou promoção
automática para `main`. O checkout original de comparação é preservado.

O snapshot anterior remoto era `2e84c55f6f93ec2c7e6b00f3622054ef99c61ece`
tanto em `main` quanto na branch de implementação. A diferença local abrangia
correções e experimentos posteriores à publicação de 18/10.

## Apresentação pública

- README reescrito para apresentar propósito, recursos, arquitetura, estágio,
  reprodução, limites e processo de construção, com o Portfolio do autor como
  principal referência editorial. Não é uma cópia de claims de outros projetos.
- Conteúdo técnico anterior preservado em `DEVELOPMENT.md`, com aviso de exemplos
  datados e correção da URL/branch de clonagem.
- Mantida a âncora `README.md#arquitetura-do-turno` referenciada pela documentação.
- Removida a afirmação de licença MIT: não existe arquivo `LICENSE` neste snapshot.
  Nenhuma licença nova foi escolhida por esta publicação.
- MVP aberto, campanha experimental, nenhum narrador admitido e gate
  DEC-NARR-VALID-001 pendente explicitamente apresentados. Não há release,
  implantação de demonstração pública nem afirmação de suíte integral verde.

## Arquivos elegíveis e exclusões

Incluídos: fontes, testes, prompts sintéticos, protocolos, manifestos e relatórios
técnicos de avaliação, planos aprovados e auditoria da entrada de credencial.
Os manifestos históricos e seus hashes são preservados, inclusive quando o
runtime atual deve ser recusado por divergência de implementação.

Excluídos: arquivos de ambiente, credenciais, memória/ambiente/entrada de terminal,
filas e status operacionais, `eval-results`, bancos SQLite, saves, logs,
dependências, builds e prévias regeneráveis da auditoria. A regra de exclusão
de `previews` passou a cobrir também subdiretórios de `docs/security-audit`.

As duas alterações locais em `.env.example` e `api/.env.example` permanecem
fora do commit. Seus conteúdos não foram lidos, comparados, copiados ou
sobrescritos. Exemplos já existentes no histórico não são reintroduzidos nem
alterados por esta publicação.

## Segurança da publicação

Varredura local redigida nos textos candidatos, sem abrir qualquer `.env*`:
padrões de tokens de provedores, chaves privadas, JWTs e URLs com credencial.
O resultado inicial foi zero indicadores em 561 arquivos textuais candidatos.
Os cinco arquivos do commit documental também são verificados no índice antes
do commit, sem incluir os exemplos de ambiente.

O PDF da auditoria de 19/10 foi examinado por extração de texto: sete páginas,
13.043 caracteres e zero indicadores pelos mesmos padrões. SHA256 preservado:
`620f317d49a03615f0815e56e3e7526362683513693cd5099fdba368b3912cc5`.
Prévias rasterizadas ficam ignoradas e não foram apagadas.

Limites: scanner local por padrões, não análise universal de segredos, nova
auditoria de segurança integral, pentest, varredura de CVEs ou autenticação no
provedor. Gitleaks e o plugin de varredura recomendado pela skill não estavam
disponíveis. Não foram instalados, nem houve alteração de configurações globais,
relaxamento de gates ou bypass de proteção do GitHub.

Nenhuma chamada paga ou chave de API de narração foi utilizada nesta atividade;
não houve acesso à entrada, ambiente ou memória da sessão de terminal.
A supervisora não é necessária para Git/testes offline.

## Verificação deste snapshot

- Backend focado: 89 testes aprovados; campanha e supervisora/entrada protegida.
- Backend relacionado ampliado: 1.003 testes aprovados em 3min26s, com um aviso
  preexistente de `python_multipart`; inclui regressões de campanha/cena,
  preparação L5/L83 e entrada protegida/supervisora.
- Frontend: 13 arquivos, 258 testes aprovados.
- TypeScript: verificação de tipos aprovada.
- Build Vite de produção: aprovado; saída regenerável permanece fora do Git.
- Lint de `src`: mesmos três erros e um aviso em `useCharacterState.ts` e
  `useInitializationLog.ts`, não alterados; dívida anterior preservada.
- Sintaxe dos candidatos: 285 arquivos Python aprovados por AST e 80 arquivos
  PowerShell sem erro de parser, sem executar os lançadores.
- README: todos os links relativos resolvem para arquivos existentes.
- Índice técnico: 558 arquivos; 557 textos examinados novamente diretamente dos
  blobs staged, zero indicadores pelos padrões registrados; um PDF já verificado.
- `git diff --cached --check`: 16 linhas com espaços finais em oito prompts
  históricos v16–v23. Bytes preservados para não invalidar hashes; checagem global
  de whitespace não está verde. Não houve limpeza cosmética dos experimentos.

Resultados Python locais (ignorados pelo Git):
`eval-results/repository-checkpoint-focused-2026-10-20.xml` e
`eval-results/repository-checkpoint-expanded-2026-10-20.xml`.
Os recortes se sobrepõem; não somar contagens como testes únicos.

A suíte integral não foi repetida: esta atividade de publicação não acrescenta
mudança de runtime e a execução integral anterior durou 1h41min, com falhas
históricas já classificadas. O checkpoint inclui as correções de runtime
desenvolvidas anteriormente e revalidadas nos recortes acima. Veja
`docs/repository-promotion.md`. Não extrapolar o resultado dos recortes atuais
para os 9.399 casos daquele snapshot, nem converter correção lexical em prova
geral de fidelidade semântica.

## Estado da publicação

Checkpoint técnico publicado no commit
`45d4a37e6e9d7bad316065b437a6d2bed5344eca`: 558 arquivos, incluindo código,
regressões, protocolos, planos e relatório da entrada protegida. Push normal
concluído; `git ls-remote` confirmou igualdade com o HEAD técnico local.

README, guia técnico, instruções e este registro acompanham um segundo commit
documental na mesma branch. A confirmação do HEAD final é realizada após esse
envio; não se usa `push --dry-run` como prova de publicação.

`main` permanece em `2e84c55f6f93ec2c7e6b00f3622054ef99c61ece`;
nenhum merge, troca de branch padrão, exclusão ou force-push nesta atividade.
O README atualizado deve ser consultado na branch de implementação; a página
inicial de `main` continua mostrando sua versão anterior. Isso não é um merge
pendente oculto nem aceite do gate narrativo.

O estado local esperado após a publicação documental contém somente as duas
alterações de exemplos de ambiente excluídas. Dados operacionais ignorados
permanecem locais. Portanto, o GitHub guarda o checkpoint publicável, não uma
cópia de credenciais, sessões ou bancos privados do computador.

## Continuidade

A fonte de verdade continua `PROMPT_RETOMADA_2026-09-06.md`; não há
`state/PROJECT_STATE.md` neste worktree. Próxima intervenção de produto continua
DEC-NARR-VALID-001, opção A/B ainda não escolhida. L83 permanece preparado e não
executado. Publicar o snapshot não aprova nova arquitetura, lote ou narrador.
