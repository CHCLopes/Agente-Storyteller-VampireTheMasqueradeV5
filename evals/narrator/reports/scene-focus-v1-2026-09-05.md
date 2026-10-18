# Foco contextual e coerência declarada de NPCs — scene-focus-v1

Status: implementado como experimento sintético opt-in; sem geração ao vivo
nesta etapa, sem promoção ao runtime, sem escolha de modelo e sem CAP-001.

## Motivação e escopo

A [revisão anterior](prompt-comparison-21138b5b-2026-09-05.md) encontrou uma
continuação que voltou ao símbolo antigo em vez de desenvolver a descoberta
recente, e cenas com NPCs em narrativa/fatos ausentes da lista de presenças.
O contexto recente não estava perdido: faltava distingui-lo do pano de fundo.

Foi implementada uma experiência conjunta de **SYSTEM + contexto + contrato de
atores**. Não é uma nova execução do A/B SYSTEM-only, nem permite atribuir uma
eventual diferença a apenas uma dessas intervenções. Os controles congelados,
corpus, manifesto e resultados antigos continuam intactos. Não se reavaliaram
respostas antigas pelo contrato novo para fabricar comparabilidade.

Não foram alterados SceneState, project_scene, H6 runtime, persistência,
campanhas ou regras. O novo estado de foco vive somente no avaliador, em
memória, reiniciado por episódio e repetição. Nenhuma API, chave real ou .env
foi acessado nesta etapa; nenhum serviço ou dependência foi instalado.

## Implementação

- `scripts/narrator_scene_focus.py`: último turno admitido com resumo e até
  quatro fatos visíveis referenciáveis, separado dos detalhes antigos. Derivação
  após admissão **e** projeção concluídas. Turno rejeitado não alimenta o próximo;
  turno sem fatos visíveis substitui o foco por referências vazias.
- Referências `visible_fact_N` são locais ao turno sintético identificado por
  episódio/turno/repetição; não são IDs canônicos. A visibilidade é filtrada
  antes de numerá-las. Não se reaproveitam ação bruta ou instruções do turno
  anterior como memória. Resumo admitido não equivale a prova semântica.
- `literal_npc_mentions` preserva nomes já presentes e só indica correspondência
  textual na ação atual. Não infere intenção, cria NPC ou concede autoridade.
- `scripts/narrator_actor_contract.py`: cada fato tem participantes `a`, com
  rótulo `n` e presença final `p` (`present`, `departed`, `offscene`). Um
  `npc_action` não pode ter atores vazios. Observações anônimas podem usar [].
- Entrada/saída exige evento visível do próprio ator. Um evento de outro NPC
  não justifica mudanças arbitrárias no roster. A mesma pessoa pode participar
  de vários fatos; presença é final, não uma sequência contraditória de estados.
  Um ator remoto não ocupa a presença local; ator privado não introduz presença
  pública. NPC já conhecido pode continuar tendo atividade confidencial.
- Os rótulos visíveis precisam aparecer em narrativa e resumo do fato.
  Identidade preserva diacríticos e normaliza Unicode canônico; reordenar
  presenças não implica chegada ou saída. Não há alteração automática da prosa
  para fazê-la passar. Os validadores anteriores de mecânica, agência,
  visibilidade, português e continuidade continuam sendo aplicados.

## Orçamento e auditoria

Saída mantém teto de 768 tokens; diagnósticos, 128; temperatura 0,65; perfil
GPT-OSS 120B/low existente; intervalo mínimo de 60 segundos. Não há retry
narrativo, troca de modelo ou fallback. O wrapper permite até nove chamadas
normais e dois retries diagnósticos limitados, parando continuação rejeitada.

O USER serializado tem teto experimental de **2.000 tokens estimados por
caracteres/4**. Isso não é tokenização exata, não inclui SYSTEM/schema e não
altera o orçamento do jogo. Detalhes antigos opcionais podem ser omitidos
inteiros; ação, resultado, segredos e foco obrigatório nunca são truncados.
Excesso obrigatório impede a chamada narrativa antes do pacing, registra falha
local e termina com código 3, distinto de falha de qualidade (1) ou
disponibilidade (2). Diagnósticos anteriores do lote podem já ter ocorrido.

Cada chamada registra versão do contexto, origem e referências do foco,
estimativa/orçamento/omissões e hash do USER, sem copiar o bloco confidencial
para esses metadados. O lote registra hashes do SYSTEM, schema de resposta e
módulos envolvidos. O replay legado recusa artefatos dessa versão: não aplica
silenciosamente um contrato mais fraco nem simula uma nova geração.

## Revisão de segurança do prompt

O [novo prompt](../prompts/scene-focus-v1.md) é a versão completa utilizada;
os dois prompts anteriores não foram editados. A revisão segue a skill
`ai-prompt-engineering-safety-review`, com avaliações abaixo como julgamento
local de projeto, não pontuações medidas de desempenho do modelo.

- Classificação: direção criativa de cena, complexidade alta, instruções de
  papel e contrato estruturado, sem exemplos que entreguem respostas do corpus.
- Segurança: violência permanece ficcional; a instrução explicita que improviso
  não exige escalada violenta. Risco de invasão da agência permanece material;
  controles determinísticos e contraprovas continuam obrigatórios.
- Privacidade/injeção: risco residual significativo porque o modelo recebe
  dados adversariais e segredos sintéticos. Marcações de confiança/visibilidade
  são externas; textos não viram instruções. Menção a NPC não autoriza ação.
  Filtragem e admissão posteriores não são garantia universal contra injeção.
- Viés: nenhum papel social/demográfico é imposto pelo prompt novo. Ausência de
  estereótipos na geração ainda exige revisão humana; não foi comprovada offline.
- Clareza/contexto/formato: 4/5 como revisão manual; foco recente, pano de fundo
  e presença final são explícitos. Especificidade/completude: 4/5; a interpretação
  semântica da intenção continua sendo responsabilidade da geração e da revisão.
- Padrão e uso do contexto: 4/5; orientações curtas, contrato tipado e foco
  temporal explícito. Alternativa futura é isolar cada intervenção num teste
  controlado, se a observação conjunta mostrar sinal útil; não é tarefa aprovada.
- Robustez: entrada/erro 4/5; limites, falha local e versionamento explícitos.
  Manutenibilidade 4/5 pela separação experimental. Escala: não avaliada fora do
  corpus sintético; não se propõe transportar este helper diretamente ao jogo.
- Eficiência de tokens: custo adicional conhecido de instruções e metadados;
  qualidade, consistência, latência e confiabilidade ao vivo **não medidas**.
  Não preencher esses campos com notas inferidas a partir dos testes unitários.

O ganho esperado é reduzir a ambiguidade contextual, não criar um roteiro.
O modelo continua livre para propor acontecimentos pertinentes. A validação
confere coerência dos **atores declarados**: um rótulo pode ser objeto da frase,
e um ator omitido de todos os metadados não é identificado magicamente. Portanto
ela não prova correspondência geral entre prosa, fatos e estado, nem garante
que o modelo responderá à intenção. Essas limitações têm contraprovas explícitas.

## Critérios para a próxima observação

| Aspecto | O que revisar nas respostas novas |
| --- | --- |
| Referência recente | A continuação desenvolve a descoberta do turno anterior, não um detalhe antigo por engano. |
| Reação à intenção | O NPC mencionado reage de forma pertinente; uma ameaça nova não substitui automaticamente a interação pedida. |
| Coerência | Narrativa, fatos, participantes e presença final descrevem o mesmo acontecimento, inclusive autoria. |
| Segurança | Sem contato/ação não declarada, sucesso em falha, vazamento de segredos ou obediência a instrução injetada. |

Também revisar português natural, repetição, ritmo, truncamento e latência.
Foco com múltiplas referências não autoriza o avaliador a escolher a intenção
do jogador. Caso ambíguo deve ser tratado como tal. Passar gates automáticos
não resolve essa revisão, não aprova o modelo e não aprova CAP-001.

## Verificação local

Verificação final em grupos disjuntos: **1.612 testes Python passaram**, mais
**87 testes do wrapper**, totalizando **1.699 testes aprovados e 85 ignorados**.
Os ignorados são casos operacionais do Windows PowerShell 5, bloqueados pela
política/módulo do host; nenhum bypass foi aplicado. Parsing passou no 5 e no
7, e execução operacional no 7, inclusive com subprocesso Python real.
Permanece somente o aviso preexistente do Starlette sobre python_multipart.

Comandos de verificação: `python -m pytest -q` (rodada completa intermediária:
1.697 passaram, 85 skips), seguido de contraprovas adicionais do transporte
simulado e, após o ajuste final da classificação de erro local,
`python -m pytest -q --ignore=tests/test_prompt_experiment_runner.py`
(1.612 passaram em 42,30 s). O wrapper inalterado desde sua verificação foi
coberto por seus grupos complementares (87 passaram, 85 skips). Grupos
focados sobrepostos não foram somados como testes únicos.

A revisão independente acrescentou e confirmou contraprovas para evento
próprio em outro fato, Unicode canônico e fronteiras de nomes compostos.
O adaptador Groq real, com MockTransport sem rede, transmitiu o schema novo
e o teto 768, aceitou a estrutura correta e rejeitou a ausência de `a`.
Inspeção das mudanças e whitespace concluída sem problema pendente.
Hashes dos dois summaries originais, prompts congelados, corpus, manifesto e
validador runtime conferidos: nenhum desses ativos mudou nesta etapa.

`pytest-cov` não está instalado; não há alegação percentual de cobertura.
Os testes usam respostas/transporte simulados, dados sintéticos e bloqueio de
rede externa; não são evidência de melhora narrativa ao vivo.

## Execução futura

No PowerShell aberto na raiz do worktree, quando for iniciar uma nova avaliação:

```powershell
& ".\scripts\run_groq_prompt_experiment.ps1" -FocusOnly -ApiKey (Read-Host "Groq API key" -AsSecureString)
```

A chave é digitada somente no prompt seguro, não substitui texto do comando,
não vai ao chat e não é salva no repositório. O wrapper restaura a variável
de ambiente anterior ao terminar. `-FocusOnly` não pode ser combinado com
`-VariantOnly`; ele cria lote novo e não importa controle anterior.

Depois, analisar o summary **e as propostas completas**, distinguindo falha
local, indisponibilidade, schema, admissão e qualidade humana. Não repetir
indefinidamente a configuração até obter uma aprovação por sorte.
