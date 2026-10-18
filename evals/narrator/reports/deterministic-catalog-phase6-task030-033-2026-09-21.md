# Catálogos determinísticos — fechamento técnico TASK-030 a TASK-033

Data: 2026-09-21

## Resultado

Os testes dedicados TEST-001 a TEST-010 foram implementados e cobrem integridade
do registro e da matriz, referências, aliases, poderes suportados, falha fechada
de armas, ficha, progressão, seleção de lore e ausência de resolução LLM nos
caminhos determinísticos. A progressão recebeu provas positivas e negativas para
todas as categorias implementadas; `specialty` permanece explicitamente sem
mutação implementada.

A suíte focal consolidada no worktree real aprovou 184 testes. Depois de duas
correções de compatibilidade no Markdown H6, os grupos de prompt e integração
relacionados aprovaram 101 testes e o grupo final de contratos de prompt aprovou
37 testes.

## Suíte offline ampla

A execução usou `STORYTELLER_DISABLE_DOTENV=1`, rede externa apontada para destino
local inválido, `NO_PROXY` restrito a localhost, bytecode desativado e nenhuma
instalação de dependência.

O primeiro diagnóstico aprovou 3.198 testes antes de encontrar a perda de uma
frase contratual no Markdown H6. A frase foi restaurada e verificada. A continuação
aprovou mais 287 testes antes de parar em um runner histórico de derivação cujo
`FINAL_SCHEMA_SHA256` congelado já não corresponde ao contrato de ator atual.
Esse runner, o contrato e seu teste são artefatos anteriores e não foram alterados
por este lote; atualizar a impressão digital reescreveria a evidência histórica.

Há ainda uma falha preexistente reproduzida no worktree antes da aplicação do
lote: em Windows, a leitura SQLite de uma sessão inexistente cria os sidecars
`-wal` e `-shm`, contrariando a asserção de que nenhum caminho novo aparece. O
arquivo principal permanece byte a byte igual. A coleta a partir da raiz também
não é válida porque inclui cópias históricas de testes sob
`eval-results/checkpoints`; a suíte oficial deve ser coletada em `tests/`.

Assim, não se declara a suíte histórica integral verde. As falhas externas ao
incremento estão preservadas e descritas, sem alteração oportunista.

## Auditoria

`git diff --check` passou. A inspeção do lote não encontrou `.env`, credencial,
segredo, conteúdo integral de livro, alteração de provedor/modelo, aumento de
limite de saída ou nova chamada LLM. As novas ocorrências de fallback são apenas
texto técnico local de carregamento de prompt e a resposta fundamentada local de
H4; não constituem fallback de provedor.

A matriz `v5_support_matrix.json` foi atualizada apenas onde os testes fornecem
evidência. Atributo, perícia, três classes de disciplina e potência de sangue têm
provas positivas e negativas. As limitações de classificação por clã/Caitiff
continuam explícitas, e especialidade está marcada `unsupported` para mutação.

## Decisões preservadas

- catálogos são orientação mínima e determinística, não roteiro textual;
- H6 conserva improviso coerente e autoridade ficcional limitada;
- H4 não preenche lacunas de lore;
- H2 permanece descontinuado como skill cognitiva e a relação é determinística;
- nenhuma decisão de provedor, modelo, CAP-001, custo ou fallback foi ampliada.

## Aceitação humana

Em 2026-09-21, após a apresentação do inventário, limitações, resultados e
decisões preservadas, o usuário respondeu “prossiga”. A resposta foi aplicada ao
gate corrente TASK-034 e encerra este plano como `Completed`. Ela não escolhe as
alternativas ainda abertas de acesso ao transporte B nem de pausa/retomada.
