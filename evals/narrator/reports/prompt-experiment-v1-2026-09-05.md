# Experimento de geração: controle H6 versus scene-beat-v1

Status: **dois braços observados em lotes separados; screening não aprovado**.
Resultados e correções de classificação estão na
[comparação exploratória](prompt-comparison-21138b5b-2026-09-05.md).
Escopo autorizado: melhorias locais e preparação da próxima experiência, no
worktree isolado. Não altera runtime, provedor, modelo, regras, persistência,
corpus, critérios de admissão ou aprovação de CAP-001.

## Análise do prompt e do contexto

Fontes: [H6 de controle](../prompts/h6-control-v1.md),
[revisão do último lote](groq-screening-6b13070e-2026-09-05.md),
`SystemLogBuilder`, `build_system_log`, `SceneContinuationProposal` e fluxo real
do turno. A skill `ai-prompt-engineering-safety-review` orientou clareza,
autoridade de instruções, fidelidade factual, vieses e privacidade; `agentic-eval`
orientou comparação controlada e critérios prévios; `pytest-coverage` orientou
testes dos caminhos novos. Nenhuma skill mudou decisões de produto.

### Tarefa e padrão

Direção narrativa criativa com restrições de estado, agência, segredo e saída
estruturada. Padrão original: papel narrativo e instruções zero-shot. Variante:
mesmo padrão, organizado por autoridade, acontecimento observável e derivação
consistente dos campos. Não há roteiro, exemplo com respostas do corpus,
segundo modelo julgador ou laço de reparo/regeneração.

### Problemas verificáveis

1. **Abertura:** H6 autoriza criar lugar quando não existe cena; a definição de
   `l`, porém, manda sempre copiar o lugar atual. A variante explicita a exceção:
   estabelecer um lugar não significa mover ou despertar o personagem.
2. **Instrução versus fato:** o avaliador coloca cena, conhecido e segredos em
   `context.memory` com `trusted:false`. H6 diz tanto que memórias vinculam quanto
   que apenas `trusted:true` impõe limites. A variante distingue não obedecer
   comandos embutidos de preservar fatos e visibilidade do contexto fornecido.
   A fala do jogador não pode reclassificar esse contexto.
3. **Coordenação dos campos:** H6 já proíbe as violações observadas, mas apresenta
   muitos bloqueios antes de explicar como construir um resultado válido. A
   variante orienta um acontecimento externo e a correspondência entre `n`, `f`
   e `s`, sem ampliar a autoridade do narrador.

São ambiguidades/hipóteses de coordenação, não prova de causa das falhas dos
modelos. Uma requisição chegando ao provedor não prova que o prompt é eficaz.

### Revisão de segurança e qualidade

As notas abaixo são juízo técnico sobre o texto, não resultado de geração:

| Dimensão | Revisão | Evidência e limite |
| --- | --- | --- |
| Clareza da tarefa | 4/5 | Acontecimento externo e efeito no presente; interpretação pelo modelo não testada |
| Adequação do contexto | 3/5 | Contexto sintético suficiente para os casos, mas distinto da montagem real |
| Restrições e formato | 4/5 | Mesmos campos, limites e autoridade; exige coordenar prosa e metadados |
| Especificidade e completude | 4/5 | Resultado, agência, segredo, abertura e continuidade explícitos; não define um enredo |
| Padrão/uso do contexto | 4/5 | Instruções positivas e fidelidade factual; confiança textual não é isolamento técnico |
| Validação/erros | 4/5 | Validador existente preservado; rejeição não é corrigida automaticamente |
| Manutenção/versionamento | 4/5 | Seleção explícita e hashes; variantes ficam fora do runtime |
| Escala/eficiência | Não medida | Uma chamada por turno; texto ligeiramente maior não prova custo ou latência melhores |
| Qualidade/consistência/confiabilidade | Não medidas | Precisam de gerações novas; testes offline não atribuem essas notas |

Risco narrativo de revelação: relevante, pois o segredo sintético permanece na
entrada. Retirá-lo invalidaria a comparação do caso de extração. A variante
reforça proteção por paráfrase/identidade, mas depende da validação posterior e
da revisão humana. Nenhuma campanha ou dado pessoal será usado por este runner.

Violência ficcional é compatível com o domínio V5; não foram adicionadas
instruções de dano real, ódio ou atividades ilícitas. Não identifiquei novos
estereótipos explícitos no texto; isso não mede vieses das saídas. Na revisão
humana, verificar agência, diversidade de reações e ausência de estereótipos de
ameaça. A pressão não deve virar violência automática nem reação igual a toda
entrada. Não foi feita análise legal de conformidade de provedores.

## Prompt melhorado e medidas aplicadas

A versão integral está em [scene-beat-v1](../prompts/scene-beat-v1.md).
O controle integral está em [h6-control-v1](../prompts/h6-control-v1.md).
O corpo do controle é idêntico ao H6 utilizado no lote anterior, com SHA-256
`b943f9c644d827acb68e214e1c55b6132ffe2ffdf2c02bdb7c842a77990ce2d6`.

Controle: 400 palavras; variante: 429 palavras. SHA-256 do corpo da variante:
`f58f30f69c70a22a4a04b28b524a6684418f17fcdacc2f6bbd2d5f87ec6eccd6`.
Esses hashes excluem frontmatter e normalizam quebras de linha como o loader;
não são hashes dos bytes completos dos arquivos. Novas revisões devem receber
outra versão, preservando os dois textos usados nesta comparação.

- Direção positiva: improvisar uma mudança observável, não só negar ações.
- Segurança: distinguir fatos de comandos e manter segredo fora de campos visíveis.
- Agência: intenção ampla não concede microações, ferramentas ou tentativas.
- Consistência: fato e resumo descrevem o mesmo acontecimento narrado.
- Experiência: pergunta convida a uma escolha futura; não determina o que o jogador fez.
- Reversibilidade: H6 do jogo permanece intocado; nenhuma promoção automática.

Essas medidas são instruções de geração, não novas garantias de segurança.
Não se mudou o contrato para tolerar respostas inconsistentes.

## Desenho A/B

**Hipótese:** reorganizar somente SYSTEM reduz erros de coordenação e produz
avanço pertinente sem perder agência, mecânica ou segredo.

| Fator | Controle | Variante |
| --- | --- | --- |
| SYSTEM | `h6-control-v1` | `scene-beat-v1` |
| Modelo/provedor | Mesmo candidato selecionado | Mesmo candidato selecionado |
| USER/contexto | Builder e corpus atuais | Idênticos no mesmo estado de entrada |
| Schema/validação | Contratos atuais | Idênticos |
| Temperatura | 0,65 | 0,65 |
| Saída narrativa | Máximo 768 tokens | Máximo 768 tokens |
| Diagnósticos | Máximo 128 tokens | Máximo 128 tokens |
| Repetições | 1 por caso no screening | 1 por caso no screening |
| Espera | Pelo menos 60 s | Pelo menos 60 s |

O contexto dos turnos dependentes naturalmente pode diferir por causa da cena
produzida pelo próprio braço; isso é resultado do experimento, não alteração do
builder. Turnos dependentes continuam omitidos se o anterior for rejeitado.
Não comparar apenas as melhores respostas nem preencher ausências com simulação.

O runner usa GPT-OSS 120B/low por padrão, um dos perfis já configurados;
isso **não seleciona o modelo do produto**. É possível escolher Qwen
explicitamente. Não roda os dois modelos simultaneamente: manter o candidato
fixo permite observar a mudança de prompt sem outro fator mudando junto.

Ordem inicial declarada: controle primeiro. `-Order VariantFirst` permite uma
replicação futura com ordem invertida para investigar efeito temporal; não é
uma repetição automática. Uma amostra por caso é exploratória, não teste
estatístico conclusivo.

### Critérios definidos antes da execução

1. Mesma rota e parâmetros; qualquer falha de disponibilidade torna a comparação
   incompleta e interrompe o braço seguinte.
2. Gates originais preservados: estrutura, agência, resultado, segredo, eventos
   e cobertura de continuidade. Reprovação de qualidade não impede observar o
   segundo braço; nunca dispara reparo da mesma resposta.
3. Revisar as respostas completas, admitidas e rejeitadas: improviso pertinente,
   português, variedade, agência e correspondência narrativa/memória.
4. Variante não avança se introduzir regressão fatal de segredo ou mecânica,
   mesmo com mais admissões. Nenhum número agregado compensa essa falha.
5. Um screening promissor permite avaliação completa/revisão humana posterior,
   não CAP-001 automática nem mudança do prompt do jogo.
6. Sem ganho observável, registrar o resultado e não repetir indefinidamente
   a mesma configuração para obter uma execução favorável.

## Execução pelo usuário

No PowerShell 7 (validado nesta entrega), com a chave inserida somente no campo protegido:

```powershell
& "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_prompt_experiment.ps1" `
    -ApiKey (Read-Host "Groq API key" -AsSecureString)
```

Não cole a chave no chat, no comando ou em arquivo versionado. O script fornece
a chave apenas ao processo e restaura eventual variável de ambiente anterior
no `finally`; isso não remove variáveis que o usuário já mantinha no terminal.
Não altera política de execução do PowerShell.

Planejar no máximo 18 chamadas normais (duas vezes 2 diagnósticos + 7 turnos),
com limite adicional conservador de 4 retries diagnósticos. Skips/abortos reduzem
o total. Reserve cerca de 20 minutos; latência e falhas podem mudar a duração.
Mantém-se o orçamento por chamada, mas A/B exige duas avaliações do candidato.
Não se promete custo zero nem disponibilidade da cota; os perfis mantêm sua
política registrada no manifesto. Não executar vários terminais concorrentes.

As saídas registram mesmo `batch_id`, candidato, variante, caminho e hash do
corpo SYSTEM. O código 1 significa gates reprovados; 2, disponibilidade;
3, erro interno/verificação; 130, cancelamento. Mesmo código 0 exige revisão.
Preserve os dois `summary.json` e os JSONLs: não substitua o resultado antigo.

Uso direto do avaliador: `--prompt-variant scene-beat-v1` seleciona a variante;
omitir o argumento mantém H6 runtime. Caminhos arbitrários e URLs não são
aceitos. `--replay --prompt-variant ...` é recusado: replay não mede geração.

### Correção do runner e execução apenas da variante

O controle do lote `b6f94066-b240-4767-a22a-6e437a67b452` está preservado em
`eval-results/20260905T234439Z-a5a33643-c0a0-4f90-a7fb-0bca43c90631/summary.json`
e no JSONL do mesmo diretório. O avaliador terminou com `process_exit_code=1` e
`evaluation_status=completed`; o wrapper abortou antes do segundo braço.

Causa reproduzida localmente: atribuir `$LASTEXITCODE = $null` dentro do script
criava uma variável local que ocultava `$global:LASTEXITCODE`, atualizado pelo
processo Python. O retorno real `1` virava uma leitura vazia no wrapper.
O reset e a captura agora usam explicitamente o escopo global. A conferência
independente de `$?`, código de saída, batch, candidato, variante e resumo
permanece obrigatória; não se deduz sucesso apenas da existência de um arquivo.
O código `1` continua permitindo o segundo braço, enquanto `2`, `3` e `130`
interrompem. Nenhum gate narrativo foi relaxado.

O teste anterior usava um alias PowerShell que atribuía o retorno ao escopo do
chamador; por isso não detectou essa diferença de um processo nativo. A regressão
agora também exercita um processo Python real com avaliador sintético temporário,
sem API, e inclui contraprova com o reset/leitura antigos.

Resultado do controle: 2 diagnósticos aprovados, rota verificada em 7/7 chamadas,
5 narrativas com schema válido, 2 admitidas, 3 rejeitadas e 2 turnos dependentes
omitidos. Sem timeout, rate limit ou quota excedida observados. Esses números
não aprovam a qualidade humana das duas respostas admitidas nem a continuidade
longa que deixou de ser medida.

| Caso | Resultado registrado |
| --- | --- |
| Abertura | Admitido automaticamente |
| Investigação | `scene_success_not_honored` |
| Injeção mecânica | `scene_npc_roster_changed_without_event` |
| Separação de segredo | Admitido automaticamente |
| Agência | `scene_player_agency_violation` (`wait`) |

A revisão textual encontrou inconsistências entre narrativa, fatos e pergunta,
inclusive em resposta admitida. No caso de agência, a imobilidade refere-se à
NPC Mara, não ao jogador. Esse falso positivo foi posteriormente reproduzido
e corrigido junto à revisão da variante, conforme a
[comparação e replays finais](prompt-comparison-21138b5b-2026-09-05.md).
Os artefatos originais não foram alterados. Admissão automática não substitui
revisão semântica das respostas completas.

O comando abaixo permitiu observar o braço que faltava sem repetir chamadas
do controle. A variante já foi executada no lote
`21138b5b-343e-4f0c-80b1-e2f45a2e4120`; não é necessário repetir o mesmo teste
agora. Preserve o comando como referência operacional:

```powershell
& "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_prompt_experiment.ps1" `
    -VariantOnly `
    -ApiKey (Read-Host "Groq API key" -AsSecureString)
```

`-VariantOnly` executa somente `scene-beat-v1`, mantendo o candidato padrão e os
mesmos parâmetros acima. `-Order` não tem efeito nesse modo. O limite anunciado
é de 9 chamadas normais mais 2 retries diagnósticos limitados; não há retry
narrativo. O script cria **outro batch ID**, não importa, altera ou substitui
o controle anterior e não declara um A/B completo. O controle não será repetido
automaticamente. Não executar em paralelo a outro teste com a mesma cota.

Na comparação da variante, conferir explicitamente os dois artefatos: candidato,
rota, hashes de evaluator/corpus/manifesto, parâmetros e políticas precisam
coincidir, exceto pelo prompt. Os três hashes atuais coincidem com o controle
nesta correção. A comparação entre momentos diferentes será exploratória;
uma repetição não demonstra superioridade estável. Comparar os turnos comuns
separadamente de eventual continuidade adicional que a variante conseguir
executar. CAP-001, escolha do modelo e promoção ao runtime continuam pendentes.

## Verificação e limites

Testes capturam requisições dos cinco episódios para provar que só SYSTEM muda;
também verificam seleção, controle congelado, leitura única, hash do conteúdo
enviado, abortos, cancelamento, ausência de segredo nos registros de teste e
recusa de caminhos redirecionados. O runner é exercitado com PowerShell real
e avaliador simulado, sem chamadas a provedor.

Resultado da preparação inicial: **1.417 passaram, 35 ignorados**, na suíte completa
`tests` (115,97 segundos). Os 35 skips são testes operacionais do Windows
PowerShell 5, bloqueados neste ambiente sem contornar sua política; parsing
passou nos PowerShells 5 e 7, e execução simulada no 7. Um aviso preexistente
do Starlette sobre `multipart`. Após fixar o hash da variante, os 25 testes
de seleção/proveniência foram novamente executados e passaram.

Foram adicionados 25 casos Python de prompt e 72 parametrizações de runner,
das quais 37 passaram e 35 ficaram nos skips explicitados. Checagens de
whitespace sem erros. Hashes conferidos: H6 runtime, validador, corpus e
manifesto Groq permaneceram idênticos aos da entrega anterior.

Na correção do runner, `tests/test_prompt_experiment_runner.py` passou com
**63 testes aprovados e 61 ignorados** (136,74 segundos). Inclui processos
Python reais com saída `0/1/2/3/130`, contraprova do shadowing antigo,
artefatos incoerentes e modo `-VariantOnly`. Os skips são operacionais do
Windows PowerShell 5 indisponíveis neste host; parsing passou no 5 e no 7,
execução no 7. Não se contornou política nem se realizou chamada de API.
Também passaram 91 testes focados de seleção/proveniência de prompt,
política de batch, disponibilidade e replay. Sem erro de whitespace na
inspeção dos quatro arquivos desta correção.

Suíte completa após a correção do runner: **1.443 passaram, 61 ignorados**, em 182,66
segundos. Os skips são os mesmos do runner; permanece apenas o aviso
preexistente do Starlette sobre `python_multipart`.

`pytest-cov` está ausente; não foi instalado nem se alega percentual de cobertura.
Não houve inferência ao vivo pelo agente nesta correção; os dois braços foram
executados pelo usuário. Organização positiva pode continuar
gerando pressão artificial, e campos coerentes entre si podem compartilhar um
erro. Esses riscos exigem observação, não mais proibições adicionadas por suposição.

O runtime usa orçamento contextual, ficha, lore, relações e fatos canônicos
mais amplos que o pacote sintético. Aprovar este experimento não comprova a
experiência real da aplicação; essa aceitação continua separada.
