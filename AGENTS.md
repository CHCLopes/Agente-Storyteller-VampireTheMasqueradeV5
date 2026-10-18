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

## Produto e limites

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

Configuração, instalação, servidor e build estão no `README.md` e em
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
