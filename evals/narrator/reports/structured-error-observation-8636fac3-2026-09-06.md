# Sondagem estruturada 8636fac3 — análise e próxima observação

Data: 06/09/2026. Lote `8636fac3-d5a7-4a23-90e4-f2cadd2dba98`.
Análise offline do resultado fornecido pelo usuário, correção de perguntas e
preparação da próxima observação. Nenhuma chamada real foi feita pelo agente.
Os artefatos originais e os resultados anteriores permanecem preservados.

## Resultado e alcance

| Dimensão | Observação |
| --- | --- |
| Chamadas | Uma abertura faithful; nenhum diagnóstico de texto/streaming, outro turno ou retry |
| Transporte e rota | Resposta recebida; Groq e `openai/gpt-oss-120b` verificados |
| Schema | Uma proposta válida no contrato com atores |
| Admissão histórica | Recusada em `player_prompt`, `does_not_invite_player_action` |
| Pergunta | “O que deseja fazer agora?”: pergunta aberta válida, cinco palavras |
| Disponibilidade | Sem HTTP 400, HTTP 429, timeout ou evento de rate limit |
| Latência | 2,400136 segundos para esta única chamada |
| Uso | 2.703 tokens de entrada, 659 de saída, total reportado de 3.362 |
| Custo | Indisponível, não convertido em zero |
| Resultado original | Exit 1; operacional não aprovado; qualidade e CAP-001 não avaliados |

O caminho novo de `groq_json_validate_failed` não foi exercitado por esta
resposta. A ausência de HTTP 400 nesta chamada não determina a causa dos erros
anteriores, nem demonstra que desapareceram. Não repetir a sondagem até conseguir
um erro. O [relatório anterior](scene-faithful-observation-aa2ea81c-2026-09-06.md)
continua descrevendo a evidência histórica disponível.

## Proveniência

Os seis hashes registrados de implementação coincidiram com os arquivos antes
desta correção: avaliador, contexto/foco, atores, validador, serviço de cena e
adaptador Groq. Manifesto, corpus, SYSTEM e schema também coincidiram.

O pacote USER da abertura foi reconstruído exatamente, sem omissões de fundo:
`729575cdb2ad329d1bc93769389ba78f421824cd1b1773b2927fce58903a0dd1`.
É o mesmo pedido da abertura faithful que recebeu HTTP 400. A nova proposta
não substitui a abertura daquele lote nem pode ser importada como predecessor.

SYSTEM faithful:
`76a9ffdb37296be672e94e1a8c741d90cb5c44164c8dcf888107d308865218d2`.
Schema:
`bdbda5ab60a1d9c4af44bcadf3be3d09b333b566b61cad9f68cfa7e8a9065bd2`.

A [auditoria JSON](structured-error-observation-8636fac3-2026-09-06.json) registra
hashes das fontes, classificação antes/depois, limites e verificação corrente.
Uma observação isolada não é comparação causal A/B.

## Proposta integral

A narrativa começa com **“Você abre os olhos”**, mas a única ação fornecida
foi **“Onde estou?”**. É uma ação não declarada do jogador. Não é necessário
inferir despertar ou amnésia para reconhecer essa violação; esses estados não
estão demonstrados pela frase.

Depois da correção da pergunta, a resposta original continua recusada:
`scene_player_agency_violation`, campo `narrative`, regra
`undeclared_player_action`, sujeito `voce`, conceito `interact`.
Essa regra já existia e não foi relaxada. Nenhuma palavra da resposta original
foi alterada para revalidá-la.

A narrativa tem **91 palavras**, acima das 35–70 pedidas pelo SYSTEM. O limite
geral de runtime continua 150; essa diferença não foi convertida em um novo
gate nem em falha de schema. Resumo (15 palavras), pergunta (5), dois fatos e
duas pendências respeitam os limites solicitados.

A ambientação é compatível com a abertura urbana e gótico-punk. O cartaz do
“Coração de Aço” fornece um gancho observável e os dois fatos preservam os
detalhes principais da narrativa. Não há NPC visível, coerentemente com a lista
vazia. O episódio não contém segredos protegidos: ausência de divulgação aqui
não mede a capacidade de separação confidencial.

Duas ressalvas permanecem qualitativas: “Alameda das Sombras” é nomeado somente
em `location`, e o vínculo entre cheiro de óleo/cigarro e contrabandistas tem
sustentação fraca nos sinais apresentados. Não há local anterior contradito;
criação de elementos ficcionais compatíveis continua permitida. Esses achados
não justificam fabricar regras lexicais de fidelidade.

## Correção e auditoria offline

A pergunta observada expôs uma lacuna nas construções com sujeito omitido.
A primeira correção foi submetida a uma matriz independente de 50 casos:
25 perguntas válidas e 25 contraprovas, avaliadas tanto pelo reconhecimento
específico quanto por uma proposta sintética integral.

Nesse primeiro estado (`c7cd1fdd…`), 43 casos foram classificados corretamente.
Seis perguntas válidas continuavam recusadas:

- “O que quer fazer agora?”
- “O que você quer fazer agora?”
- “O que gostaria de fazer agora?”
- “Como gostaria de prosseguir?”
- “O que deseja fazer diante de Mara?”
- “O que deseja fazer em relação ao cadeado?”

Um caso inválido passava: “O que você faz agora? Quem Mara obedece?”.
A segunda pergunta transferia uma resposta sobre NPC/mundo ao jogador.

A revisão independente ainda demonstrou que reconhecer apenas a cauda após
ponto ou dois-pontos permitia ignorar uma ação anterior, como “Você abre a
porta. O que deseja fazer agora?”. A correção final considera a pergunta
integral na nova família, conserva os aliases do jogador e limita os
complementos admitidos. Perguntas compostas indevidas, NPCs como destinatários,
pedidos de criação da história, sigilo, agência e mecânica permanecem cobertos
pelas contraprovas. A revisão posterior também verificou aspas simples
tipográficas e abertura de barreira pressuposta em subordinadas. Perguntar sobre uma ação
não concede autorização para executá-la; ações já declaradas e ações de NPCs
precisam continuar distintas. O caso relativo com “que você acaba de abrir”
era uma lacuna anterior, corrigida de modo delimitado a barreiras nesta fronteira e sem atribuí-la
à nova forma modal. Não houve mudança de schema ou concessão de novas ações.

Os mesmos 50 casos, com textos e expectativas preservados, terminaram com
**50 classificações integrais corretas, zero falsos positivos e zero falsos
negativos** no hash final. Exatamente sete classificações mudaram; as outras
43 permaneceram iguais. A revisão independente fechou os achados delimitados.
As 187 regressões novas incluem as construções de agência e citações, além
da matriz de formas de pergunta.

A matriz é sintética e limitada. Não representa cobertura de toda a língua
portuguesa nem substitui revisão semântica das narrativas. Foram corrigidos os
defeitos demonstrados nesta superfície, sem parser geral ou novo modelo julgador.

Validador anterior: `14aff1c58d2fcaf766694dac6d55f5c7e0bc532342fdf89f6fcdaa86e868b66a`.
Validador final: `3c963e608942919361444ec9d07504a38b62ebcbbceebbca2c6ec4368911bdfb`.

## Verificação corrente

A execução final usou três grupos disjuntos, com código congelado:

| Grupo | Aprovados | Duração | Saída |
| --- | ---: | ---: | ---: |
| Sete arquivos focados de perguntas/agência/validação de cena | 703 | 9,77 s | 0 |
| Demais testes Python, excluídos esses sete e os dois arquivos de wrappers | 1.840 | 93,45 s | 0 |
| Integração Python de `test_narrator_structured_error_probe.py` (`-k 'not wrapper'`) | 38 | 2,11 s | 0 |
| Total corrente | **2.581** | Grupos paralelos | **0** |

Nenhuma falha ou skip nos grupos executados. Cada grupo apresentou apenas
o aviso preexistente de `python_multipart`. Os 187 testes novos estão incluídos
nos 703 focados, não somados novamente. A matriz independente de 50 casos
também não foi somada ao total do pytest.

Os dois runners PowerShell e seus arquivos de testes permaneceram byte a byte
inalterados. `tests/test_prompt_experiment_runner.py` não foi reexecutado.
Os 78 testes operacionais/parser do módulo da sondagem foram deselecionados;
seus 38 testes Python foram executados. A verificação anterior do PowerShell 7
permanece histórica e não está incluída nos 2.581. Não houve contorno de política
do PowerShell 5 nem alegação de nova execução dos wrappers.

A revisão independente e os deltas finais foram conferidos antes da rodada
ampla definitiva. Revalidação integral do JSONL preservado confirmou a rejeição
por agência; os originais continuam com os hashes registrados na auditoria.

Testes usaram o venv existente, `STORYTELLER_DISABLE_DOTENV=1`,
`PYTHONDONTWRITEBYTECODE=1` e `-p no:cacheprovider`, com persistência isolada
e bloqueio de rede do pytest. Nenhuma dependência instalada, chave real lida ou
resposta original reescrita. O checkout original foi preservado.

## Próxima observação delimitada antes da execução

O diagnóstico de erro terminou com uma resposta estruturada disponível.
A próxima chamada não será outra sondagem para perseguir HTTP 400.
O runner existente permite **uma única observação completa faithful**, agora
com os validadores corrigidos, para observar recorrência de falhas e cobertura:

1. A nova abertura preserva a agência, sem inserir ações do jogador?
2. Os problemas de método físico e fidelidade narrativa→memória reaparecem?
3. Um predecessor naturalmente admitido no galpão permite avaliar suas duas
   continuações? Se ele for recusado, os turnos dependentes continuam omitidos.

SYSTEM, USER, schema/atores, corpus, candidato e parâmetros permanecem iguais.
Nenhuma melhora da geração é presumida: a alteração foi nos validadores.
O lote antigo mantém seus próprios resultados e hash de implementação.
A correção local pode mudar o primeiro motivo de rejeição; isso não conta como
melhora da prosa nem estabelece comparação causal.

Executar uma vez em **PowerShell 7**, em um único terminal. Pressionar Enter
após a linha; inserir uma chave válida não exposta somente no prompt protegido:

```powershell
& "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_prompt_experiment.ps1" -FaithfulOnly -ApiKey (Read-Host "Groq API key" -AsSecureString)
```

Limites: um braço, uma repetição, até nove chamadas normais e dois retries
exclusivamente diagnósticos; 768 tokens narrativos, 128 diagnósticos,
temperatura 0,65, deadline de 60 segundos após pacing e intervalo mínimo de
60 segundos. Sem retry narrativo, fallback, baseline, importação de predecessor
ou mudança de modelo. A chave temporária é removida/restaurada em `finally`.

O critério de parada desta observação é seu término, inclusive falhas. Não
executar outra rodada automaticamente para buscar admissão. Depois, analisar
o resultado e continuar apenas a investigação e as correções locais justificadas
pela evidência; não acrescentar outra variante SYSTEM por arrasto. Mesmo se
todas as propostas forem admitidas, revisar agência, memória, sigilo e qualidade;
não promover runtime, CAP-001 ou aceitação de produto automaticamente.

A entrada protegida da chave é a próxima dependência humana. Não é necessário
aguardar avaliação intermediária das correções locais.
