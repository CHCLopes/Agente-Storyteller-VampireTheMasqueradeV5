# Revisão da triagem Groq — 05/09/2026

Batch: `7d7a644d-9623-42eb-aeb6-ec0646f482f9`. Corpus sintético v1,
uma repetição, mesmo prompt e teto de 768 tokens para ambos. Nenhum candidato
foi aprovado para CAP-001 ou dados de campanha. Não é uma nova consulta ao
catálogo: nomes e condições abaixo identificam somente o experimento gravado.

## Resultado observado, antes das correções desta revisão

| Medida | Qwen 3.8 27B | GPT-OSS 120B |
| --- | --- | --- |
| Diagnósticos texto/streaming | 2/2 | 2/2 |
| Chamadas narrativas | 5 de 7 previstas | 5 de 7 previstas |
| Estrutura válida nas chamadas feitas | 5/5 | 5/5 |
| Admissão original | 1/5 | 1/5 |
| Latência mediana de geração | 1,457 s | 1,803 s |
| Timeout / limite de taxa observado | nenhum | nenhum |

As pausas de 60 segundos são cadência do avaliador e não latência do modelo.
Dois turnos dependentes do galpão foram pulados em cada candidato porque o
primeiro não foi admitido. Portanto a continuidade multiturmo não foi medida
completamente; respostas rápidas e JSON válido não demonstram aptidão narrativa.

Fontes originais, preservadas em `eval-results/` (ignoradas pelo Git):

- Qwen: `20260905T204504Z-bb1d5166-91f3-4324-b783-dd9b773dfb57`.
- GPT-OSS: `20260905T205208Z-669108a1-a52e-4b3e-bcb0-5904c1275938`.

## Diagnóstico por cena

| Cena | Qwen | GPT-OSS |
| --- | --- | --- |
| Abertura | Admitida; revisão humana ainda necessária | Atribui abertura dos olhos/despertar ao personagem sem declaração |
| Investigação | Pergunta válida com `aborda` falsamente rejeitada; também repete fatos marcados `storyteller` no texto visível | Pergunta de 16 palavras viola teto de 15; narrativa ainda inventa avanço/deslocamento a partir de investigar |
| Injeção mecânica | `não cede` não reconhecido como falha; resumo com tentativa que falha confundido com sucesso; também inventa contato/força do personagem | Adiciona dois NPCs ao roster sem evento `npc_action`/`transition` |
| Separação de segredo | Marca descrições visíveis como `storyteller` e as repete ao jogador | Acrescenta descrição ao identificador textual do mesmo local sem transição |
| Agência/NPC | Marca ações/observações narradas como `storyteller` | Admitida; repetição do estado e progresso efetivo exigem revisão humana |

Os erros `scene_secret_disclosed` de Qwen nesta amostra provêm dos fatos novos
marcados pelo próprio modelo como `storyteller`, não da revelação literal do
segredo preexistente sobre câmera/Xerife. Não se deve remover a separação de
visibilidade nem converter esses fatos automaticamente para público.

## Correções locais

1. Família lexical de `abordar`, sem autorização implícita para aproximar,
   atacar ou convencer; perguntas com NPC como sujeito continuam rejeitadas.
2. Negação explícita de abertura/cessão reconhecida como falha. Uma tentativa
   declaradamente fracassada não equivale a atingir seu objetivo; um sucesso
   afirmado em outra cláusula continua proibido.
3. Controle limitado de contato físico implícito (dedos/mãos em objetos e
   força/peso aplicados a barreiras). Sensações involuntárias, ação ambiental
   e ações atribuídas a NPCs não são genericamente transformadas em microações.
4. `no_timeout_or_rate_limit` agora descreve chamadas observadas, separado da
   completude do corpus. `reliability_measurement` explicita cobertura e erros.
   A ausência de chamadas não vale como sucesso e os gates completos continuam
   reprovados quando faltam turnos ou há rejeições narrativas.
5. H6 explica visibilidade dos fatos, preservação do nome do local, eventos de
   alteração do roster e `pending` em falha. Reforça agência também implícita.
6. Replay aceita os turnos explicitamente pulados pelo executor, com corpus
   exato, ordem e predecessor rejeitado verificados. Não inventa respostas nem
   retoma a sequência ausente; preserva `not_attempted_original_run`. Entradas
   inválidas falham com mensagem segura, sem traceback com conteúdo do arquivo.

Não houve alteração de corpus, candidatos, orçamento, privacidade, esquema de
persistência, dados ou credenciais. As respostas históricas não foram reparadas
nem substituídas. Replay local avalia o texto antigo sob o validador novo; não
mede o efeito do novo prompt.

Replay executado localmente após as correções, com zero chamadas externas:

- Qwen: `20260905T211700Z-replay-df61d68a-18c7-45e0-a733-2ccf6251d2ff`.
- GPT-OSS: `20260905T211703Z-replay-1ebc83c8-92ac-464b-9e16-76c214b7419e`.

Ambos permanecem em 1/5 admitidas, 5/5 estruturas válidas e dois turnos pulados.
No Qwen, investigação passa da falsa rejeição da pergunta para incoerência de
visibilidade; a falha do cadeado passa da falsa rejeição mecânica para contato
físico não declarado. GPT-OSS mantém os mesmos motivos. A disponibilidade
observada passa a ser relatada corretamente como sem timeout/429/cota, com
cobertura de 7/9 chamadas. Os hashes SHA-256 dos JSONLs originais foram
conferidos antes/depois e permaneceram idênticos. O exit code 0 do replay
significa execução local bem-sucedida, não aprovação dos gates ou de CAP-001.

H6 revisado: 400 palavras; SHA-256 do prompt efetivo carregado:
`b943f9c644d827acb68e214e1c55b6132ffe2ffdf2c02bdb7c842a77990ce2d6`.

## Revisão do prompt e limites

Aplicação das skills `agentic-eval`, `pytest-coverage` e
`ai-prompt-engineering-safety-review` limitada a esta correção.

- **Classificação:** direção ficcional improvisada com contrato estruturado,
  alta sensibilidade a agência, continuidade e separação de segredo.
- **Segurança/privacidade:** instruções confiáveis continuam separadas do input
  não confiável; nenhum segredo pode aparecer em campos visíveis. A validação
  permanece no backend, não é delegada ao prompt ou a outro modelo.
- **Clareza/formato:** havia omissão de semântica em `v`, identidade de `l` e
  obrigação de `f[].p=true` para observação/pista em falha. H6 agora explica esses
  requisitos existentes; não cria uma história roteirizada ou privilégios novos.
- **Eficácia:** a nova versão é hipótese de melhoria, não resultado comprovado.
  Preserva português idiomático, improviso ante espera/pergunta, mundo/NPC ativo,
  agência do jogador, resultado mecânico e contrato JSON. Mantém até 400 palavras.
- **Viés:** sem nova identidade demográfica, estereótipo ou mudança de público;
  esta rodada não mede viés narrativo, e não permite alegação de ausência de viés.
- **Robustez:** testes positivos/negativos, sujeito/alvo, negação, contraposição,
  visibilidade e disponibilidade. Sem retries narrativos, autorreparo ou fallback.
- **Desempenho:** latências acima são da versão antiga. O prompt novo precisa de
  chamada real para medir tokens, latência e adesão; não se infere melhoria.

Os controles lexicais não compreendem toda a língua. Revisão contrafactual
também encontrou ambiguidade em percepção seguida de vírgula (`você não vê
estivadores, apenas a maré subindo` pode atribuir `subindo` ao jogador). Esse
parser não foi ampliado nesta correção: a resposta original já falha por
visibilidade. O caso deve ser tratado em regressão própria, sem mudar a nota
desta amostra. `rangido metálico cede sob seu peso` é uma formulação fisicamente
imprecisa, não base para criar regra específica que só reconheça essa resposta.

## Próxima evidência necessária

Verificação desta entrega: **939 testes passaram**, abrangendo adapters/contrato
LLM, admissão de cena, regressões desta revisão, avaliação/replay, pipeline,
isolamento de rede, contexto, memória, persistência, turnos, WebSocket e
`test_perf_sec.py`. Único aviso: depreciação preexistente do import `multipart`
no Starlette. Checks de whitespace dos arquivos tocados sem erro.
`pytest-cov` não está instalado: não foi gerada porcentagem de cobertura nem
instalada dependência. Não foram executadas chamadas ao provedor nesta revisão.

Executar a mesma triagem com H6 revisado, preservando todas as falhas e os mesmos
candidatos/parâmetros. Se houver candidato apto, completar o protocolo de 21
turnos e a revisão humana de improviso, continuidade, português, variedade e
agência. Uma rodada com uma repetição não escolhe sozinha o narrador nem aprova
CAP-001. Não enviar saves ou dados reais de campanha nesses perfis sintéticos.
