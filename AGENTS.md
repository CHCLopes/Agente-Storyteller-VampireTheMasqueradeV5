# Agente Storyteller — instruções locais

## Autonomia autorizada pelo usuário

Em 07/09/2026, o usuário ampliou explicitamente a autorização: “Prossiga,
daqui por diante, como se tivesse autorização plena, inclusive para novas
observações necessárias à continuidade. As restrições mantidas são sobre
chaves, credenciais ou ações diretas de intervenção que exigem minha atuação”.

Trabalhar em AUTONOMOUS_TASK. Investigar, planejar, implementar, corrigir,
verificar, documentar e executar novas observações necessárias à continuidade,
sem solicitar nova aprovação de cada hipótese, variante, lote ou escolha
reversível. A autorização cobre o próximo experimento target-spans e os passos
técnicos subsequentes necessários. Ao terminar uma etapa, avançar à seguinte.
Não encerrar apenas recomendando trabalho que já pode ser executado.

Chaves, credenciais e intervenções que efetivamente exigem atuação do usuário
continuam dependências humanas. Completar todo o trabalho independente delas
antes de interromper. Não pedir confirmação adicional usando uma restrição
histórica de autorização por lote: ela foi superada por esta instrução.

Manter cada observação delimitada, com hipótese, fontes, parâmetros, critérios,
proveniência e regra de parada registrados antes do envio. Encerrar cada lote
no limite definido, analisar seu resultado e definir o próximo experimento de
forma autônoma; não transformar nova autorização em retry silencioso, repetição
para elevar taxa, alteração retroativa de evidência ou aprovação automática do
produto. Os critérios de fidelidade, agência, visibilidade e integridade seguem
válidos; autorização de execução não comprova que foram satisfeitos.

Preservar o checkout original de comparação; trabalhar neste worktree. Não
modificar configurações globais ou arquivos fora do projeto por esta autorização.
Não abrir, copiar, imprimir ou registrar `.env` ou credenciais. Solicitar inserção
de chave por mecanismo seguro, não pelo chat; nunca usar chave antiga da conversa.

## Continuidade e formato de resposta — 22/10/2026

Humano reforçou: quando não houver intervenção humana necessária, continuar todas
as tarefas autorizadas até o próximo gate decisório real. Não encerrar apenas
por terminar uma subtarefa nem criar aceite intermediário já delegado.

Em TODA resposta final, incluir ao final este bloco, priorizando economia de
recursos e indicando expressamente quando nenhuma ação humana for necessária:

Configuração recomendada:

- Modelo:
- Esforço:
- Motivo:
- Ação humana necessária:
- O que continuará autonomamente depois da ação:

O bloco não amplia escopo, não troca o modelo automaticamente e não transforma
recomendação em decisão aprovada. Preservar os limites de arquitetura e aceite
final humano descritos abaixo.

## Publicação antes de gate humano — 22/10/2026

Humano determinou: entre a última atividade que não exige sua interação e a
apresentação do gate decisório humano, fazer commit e push do projeto no GitHub.
Esta instrução autoriza publicação do trabalho relacionado e verificado na branch
atual de implementação. Não implica merge, promoção à main, alteração do checkout
original, publicação de credenciais/saves/dados locais ou inclusão de mudanças
alheias. Inspecionar diff/arquivos, executar verificações pertinentes e confirmar
ref remoto após push. Se houver bloqueio concreto, relatar sem afirmar publicação.

Ao final de toda resposta que exige interação humana, incluir obrigatoriamente
“Configuração recomendada”, com Modelo, Esforço, Motivo, Ação humana necessária e
O que continuará autonomamente depois da ação. Priorizar economia de recursos.
A regra anterior de incluir o bloco em toda resposta final permanece vigente.

## Produto e limites

### Naturalidade e experiência — 20/10/2026

Em seguida, humano autorizou abrir a sessão diária de API e delegou ao agente
as avaliações de resultados de L41 e testes futuros necessários até o próximo
gate humano real, como na bateria anterior. Não parar por aceite intermediário
de lote/variante/naturalidade quando os critérios já estiverem definidos.
Conservar teto <= USD 0.15 por lote, registros prospectivos, parada na primeira
falha, sem retry silencioso/fallback ou nova arquitetura por arrasto. Credencial,
novo cânone/produto/arquitetura fora das decisões aprovadas, destruição e aceite
final que efetivamente dependa do humano continuam gates humanos.

Humano aprovou resultados L40 com ressalva de linguagem não natural. Recusa
contextual já cumpre segredo; não anunciar estado interno de informação protegida
ao jogador nem repetir a recusa em tarefa/conclusão fora de contexto. Preservar
agência e autoridade canônica. Não inventar motivos ou lore para recusar.
Mundo/NPCs podem resistir e ajudar; narrador não pode trapacear, punir curiosidade
arbitrariamente ou garantir roteiro/vitória. Diálogo colateral e por quê contextual
são visão de experiência registrada, não ramos implementados no catálogo atual.
Limites/correção: plan/observation-campaign-state-language-1.md. Não converter
essa visão em expansão silenciosa do MVP nem em poderes canônicos da LLM.

### Autorização contínua de testes — 19/10/2026 (vigente)

Humano autorizou explicitamente L30 e todos os testes futuros necessários no
escopo aprovado, com tetos planejados de no máximo USD 0.15 por lote/teste.
Não pedir aprovação individual adicional de quantidade ou desse teto dentro
desses limites. Esta decisão supera as restrições históricas abaixo de uma
chamada ou aprovação por lote; não transforma artefatos antigos em reexecutáveis.
Antes de cada lote registrar hipótese, quantidade, teto, hashes e parada;
primeira falha encerra, analisar antes de qualquer teste novo. Sem retry
silencioso/best-of/fallback/admissão automática. Custear cada teste e distinguir
estimativa de cobrança. Acima de USD 0.15, credenciais, nova arquitetura,
expansão de escopo ou aceitação humana de produto continuam exigindo intervenção.
Manter expiração da supervisora à meia-noite e não renovar automaticamente.

### Sessão temporária de credencial — semana de 19 a 25/10/2026

Humano autorizou explicitamente supervisora local que guarda a chave apenas
em memória até meia-noite de Fortaleza e executa somente baterias aprovadas
individualmente dentro dos tetos. Esta será a forma de trabalho nesta semana.
Uma entrada protegida por sessão diária; sem renovação automática, arquivo de
chave, ambiente permanente, rede/listener ou nova autorização de gasto inferida.
Na expiração/interrupção, encerrar também avaliador ativo. Não ler chave,
entrada/ambiente/memória do terminal. Requests/status são não secretos.
Procedimento e limites: plan/process-luna-credential-lease-1.md.
Esta autorização operacional não aceita L24 nem aprova orçamento L25 por arrasto.

### Convenção explícita de aprovação — 18/10/2026

Em 19/10, humano fixou USD 0,15 estimados como teto padrão previamente aprovado
por teste enquanto outro valor não for proposto. Não pedir novamente aprovação
desse mesmo teto. Quantidade/escopo do teste continuam exigindo autorização:
pedido atual foi reduzido a UMA chamada paga, explicitamente autorizada em voz.
Não converter esse limite unitário em autorização para executar a bateria inteira.

O usuário esclareceu: quando responder "continue" ou "prossiga", considera
aprovada a proposta delimitada imediatamente anterior e autoriza seguir o
trabalho. Não exigir uma frase ritual adicional para esse mesmo aceite.
A aprovação conserva o escopo, limites e exclusões apresentados; não autoriza
gasto ainda não proposto, decisão não apresentada ou admissão não submetida.
Credenciais e ações que só o usuário pode executar continuam dependências
humanas. Especificamente: L5 foi aceito e o teto proposto de L6 foi autorizado.

Monólito modular local-first: React/TypeScript e FastAPI/Python. Regras, RNG,
estado e commits transacionais são determinísticos; a LLM propõe improvisação
e continuidade sem controlar o jogador ou sobrescrever mecânica/cânone.
Memória deriva de eventos validados. Local-first não exige inferência local.

Não promover experimento, provedor, modelo ou CAP-001 por uma resposta aceita.
Preservar alvos explícitos, proveniência, visibilidade, limites e ausência de
fallback/retry narrativo silencioso. APIs pagas e decisões de produto pendentes
não são aprovadas por arrasto. Avaliações de modelo usam somente fixtures
sintéticas, nunca dados de campanha.

## Inspeção, execução e estado

- Ler a cadeia de instruções e `state/PROJECT_STATE.md` se existir; inspecionar
  `git status`, arquivos afetados e testes antes de editar. Preservar alterações
  preexistentes; evitar refatoração, dependência ou migração oportunista.
- O README descreve comportamento atual. `SESSION_LOG.md` é histórico, com
  propostas explicitamente não aprovadas; não tratá-las como autorização.
- Usar a skill mais específica aplicável, alterações mínimas coerentes,
  contraprovas e inspeção final. Separar observação, inferência e implementação.
- Registrar resultados duráveis em documentação pertinente, sem reescrever
  artefatos de avaliações anteriores para fazê-los passar.

## Verificação e navegação

Apresentação e limites estão no `README.md`; configuração, instalação, servidor
e build detalhados estão em `DEVELOPMENT.md` e em
`client/package.json`; executar apenas o necessário ao escopo, sem iniciar
serviços ou instalar dependências como parte automática do preflight.

PowerShell na raiz, usando o ambiente já disponível:

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
& .\.venv\Scripts\python.exe -m pytest -q
```

Para testes focados, informar os arquivos `tests/test_*.py`. O `conftest.py`
isola persistência e bloqueia rede externa; não desativar esses controles.
Não contornar a política do PowerShell 5 para fazer testes operacionais passarem.
Os scripts de avaliação ao vivo ficam fora do pytest; preparação deve terminar
antes de depender da chave. Guias e relatórios em `evals/narrator/README.md`.

Este arquivo usa o [formato AGENTS.md](https://agents.md/) para tornar a
autorização e os limites locais recuperáveis em próximas sessões.
