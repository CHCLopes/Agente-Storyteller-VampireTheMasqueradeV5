# Registro determinístico de catálogos — implementação inicial

## Resultado

As decisões `DEC-001` a `DEC-005` foram aprovadas. A implementação adicionou
contratos Pydantic fechados para domínio, ID, aliases, referências, suporte,
matriz e proveniência; criou um registro local único; registrou as 66 entradas na
matriz; e adicionou um manifesto sidecar com hash dos sete arquivos legados.

Os serviços de clã, armas, poderes, fisiologia, NPCs e progressão deixaram de abrir
JSON diretamente e passaram a consultar o registro validado. As APIs públicas e
os modelos de compatibilidade foram preservados. O registro rejeita hash divergente,
entrada desconhecida requerida, alias ambíguo, linha ausente e referência explícita
inválida. Nenhuma chamada LLM ou dependência nova foi introduzida.

## Proveniência editorial

O histórico Git identifica somente commits de criação, sem fonte editorial. Busca
nos documentos não encontrou título, edição, página/seção ou fundamento de uso dos
catálogos. Esses valores não foram inferidos. O manifesto usa
`verification_status: unverified`, campos de fonte nulos e nota explícita. Assim,
TASK-008 ainda não satisfaz seu aceite, e TASK-009 aguarda essa dependência embora
a migração técnica esteja pronta.

## Verificação

- 6 testes próprios do registro: aprovados;
- 39 testes focados de consumidores: aprovados;
- regressão ampliada: 200 aprovados e uma falha fora do incremento;
- falha externa: `test_narrator_uses_compact_projection_instead_of_full_sheet`
  exige frase literal antiga no SYSTEM; nenhum prompt foi alterado;
- três ou quatro avisos de ambiente, conforme o conjunto, sem falha adicional.
- `py_compile` não pôde criar bytecode em `api/__pycache__` por permissão do
  worktree; a importação dos oito módulos com bytecode desativado passou.

## Limite

Não foram alterados conteúdos dos sete catálogos, prompts, provedor, modelo,
topologia de chamadas ou regras mecânicas. A ontologia de poderes não deve receber
família, nível ou pré-requisito inventado enquanto a fonte não estiver disponível.
