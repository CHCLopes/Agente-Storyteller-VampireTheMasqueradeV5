# HYP-002 — plano de renderização de mundo fechado

**Data:** 2026-09-25

**Status:** encerrada; nenhum candidato elegível; nenhum narrador admitido

**Objetivo do documento:** referência para decidir se uma nova observação viva
deve ser preparada e executada. Este documento não admite narrador, não altera o
runtime e não autoriza campanha híbrida.

## Evidência que motiva a hipótese

HYP-001 terminou com nenhum candidato elegível. O GPT-OSS foi o candidato mais
próximo do limiar, com 5/8 casos aprovados. Suas três reprovações pertencem à
mesma fronteira: acrescentar conteúdo não autorizado durante a realização da
prosa.

- na espera, fez a água avançar sem transição autorizada;
- no objeto conhecido, atribuiu aproximação não declarada ao jogador;
- na ação ambígua, inventou tipos de instrumentos e reação ambiental.

O Qwen aprovou apenas 2/8, teve cinco narrativas sem pontuação terminal e falhou
em múltiplas classes. Repeti-lo na opção mínima não é proporcional ao custo.

Uma sonda independente, limitada a uma chamada sintética, confirmou em
25/09/2026 que a autenticação Groq estava funcional. Isso não integra HYP-002 e
não comprova quota ou disponibilidade futura. Evidência:
`groq-authentication-check-2026-09-25.md` e `.json`.

## Pergunta discriminante

Um plano de renderização de mundo fechado, produzido pelo servidor antes da
narração, permite que o alvo exato `openai/gpt-oss-120b` com reasoning `low`
realize somente proposições autorizadas, sem adicionar ação do jogador, estado,
transição ou detalhe sensorial não listado, e ainda preserve progressão ou espera
coerente nos oito tipos de caso do MVP?

Essa variável é distinta de HYP-001. O contrato anterior informava fatos,
transições, desconhecidos e proibições, mas ainda permitia ao modelo criar prosa
sensorial ao redor deles. HYP-002 fecharia também essa superfície criativa: cada
afirmação factual da narrativa teria de corresponder a uma unidade de renderização
explicitamente fornecida pelo servidor.

## Intervenção única proposta

O USER prospectivo receberia um `closed_world_render_plan` com:

- `required_units`: proposições que precisam aparecer;
- `optional_units`: proposições que podem aparecer, sem obrigação;
- `authorized_transition`: no máximo uma mudança canônica já resolvida;
- `player_action_boundary`: ação já declarada e limite além do qual a prosa não
  pode avançar;
- `unknowns`: conteúdos que devem continuar desconhecidos;
- `forbidden_claims`: afirmações e classes de inferência proibidas;
- `sensory_palette`: conjunto finito de detalhes sensoriais autorizados;
- `next_choice_boundary`: escolhas que precisam permanecer com o jogador.

Nenhuma afirmação factual ou sensorial fora dessas listas seria permitida. O
modelo continuaria responsável pela fluidez, ordem e voz narrativa, mas não por
criar novos fatos. Regras, RNG, cânone, transições e commit permaneceriam sob
autoridade determinística.

O contrato, corpus, prompt, schema, templates, ordem, hashes, verificador e
runner seriam congelados antes da primeira chamada. A preparação offline teria
zero acesso à credencial e zero rede.

## Alvo e parâmetros exatos

### `HYP-002-L1` — recomendado

| Campo | Valor congelado proposto |
|---|---|
| Provedor | `Groq` pela URL oficial já imposta pelo adaptador |
| Modelo | `openai/gpt-oss-120b` |
| Reasoning | `low` |
| Temperatura | `0.65` |
| Teto por resposta | `768` tokens |
| Deadline por chamada | `60` segundos |
| Intervalo mínimo entre inícios | `60` segundos |
| Casos | 8 casos sintéticos novos e isomórficos |
| Máximo absoluto | 8 chamadas |
| Retry / reparo / fallback | nenhum |
| Troca de alvo | proibida |

Manter os parâmetros de HYP-001 isola o efeito do novo plano fechado. Não usar
reasoning `medium`: a linha histórica medium terminou em erro de schema e foi
formalmente encerrada sem evidência semântica. Não mudar simultaneamente esforço,
temperatura ou teto.

### Alternativa `HYP-002-L2` — não recomendada

Aplicar os mesmos oito casos também a `qwen/qwen3.8-27b`, reasoning `none`, para
um máximo de 16 chamadas. A simetria comparativa custa o dobro e reinclui um alvo
que falhou seis classes em HYP-001, inclusive truncamentos. L2 só deve ser usada
se a comparação entre modelos for mais importante que a busca econômica de um
candidato elegível.

## Corpus prospectivo

Os oito casos manteriam as classes de risco, mas usariam objetos, locais,
transições e formulações novos. Nenhum texto de HYP-001 entraria no request.

1. espera sem transição autorizada;
2. espera com uma transição ambiental autorizada;
3. inspeção de objeto com estado conhecido;
4. inspeção de objeto com estado deliberadamente desconhecido;
5. tentativa com resultado mecânico favorável já resolvido;
6. tentativa com resultado mecânico desfavorável já resolvido;
7. diálogo com segredo protegido e pista autorizada;
8. ação ambígua que precisa preservar a próxima escolha.

Um caso de sucesso conhecido funcionaria como controle de não regressão. Os
casos seriam novos para reduzir adaptação às reprovações já observadas.

## Critérios e regra de parada

Um candidato só será elegível se aprovar 8/8. Em todos os casos são fatais:

- qualquer fato, detalhe sensorial, estado ou transição fora do plano;
- qualquer ação, fala, decisão, percepção voluntária ou emoção nova atribuída ao
  jogador;
- vazamento de segredo ou violação de identidade do ator;
- omissão de unidade obrigatória ou realização de unidade proibida;
- reversão ou ampliação de resultado mecânico;
- schema, cápsula, alvo ou proveniência inválidos;
- retry, reparo, fallback, troca de alvo ou repetição oculta.

Também são obrigatórios: 30 a 150 palavras, pergunta aberta que devolva a escolha,
progressão perceptível somente quando autorizada e espera coerente quando não
autorizada. Revisão semântica independente continua necessária; marcadores
automáticos não substituem julgamento humano.

Paradas fail-closed:

1. falha de freeze, hash, template, teste ou preflight encerra antes da rede;
2. falha de autenticação, rota, alvo, schema de transporte ou integridade encerra
   os slots restantes;
3. limite de oito chamadas encerra o lote em qualquer estado;
4. nenhum slot é repetido e nenhuma reprovação é reparada;
5. resultado sem candidato elegível permanece válido;
6. após revisão e verificação, parar para aceitação humana do resultado antes de
   qualquer admissão ou default.

## Escopo da decisão humana

Responder `Aprovo HYP-002-L1` autoriza:

1. preparar offline o contrato, oito casos novos, prompt, templates, verificador,
   runner e testes;
2. executar a opção L1 somente se toda a preparação conferir com esta proposta;
3. realizar no máximo oito chamadas no alvo e parâmetros exatos acima, usando
   apenas a credencial protegida da sessão dedicada;
4. verificar e revisar os artefatos e então parar no checkpoint de aceitação do
   resultado.

A aprovação não autoriza L2, novo provedor, custo pago, aliases, reasoning
`medium`/`high`, retry, relaxamento de gate, default, campanha híbrida ou
configuração produtiva. Qualquer divergência material durante a preparação exige
novo gate antes da rede.

Responder `Aprovo HYP-002-L2` amplia somente o alvo e o teto para os 16 slots
descritos em L2. Responder `Recuso HYP-002` mantém nenhum narrador admitido e o
checklist bloqueado na escolha do Narrador.

## Decisão registrada

Em 25/09/2026, o usuário respondeu `Aprovo HYP-002-L2`. O corpus, protocolo,
prompt, verificador, runner e launcher foram preparados e verificados offline.
A prontidão e os hashes estão em `closed-world-render-live-readiness-2026-09-25.md`
e `.json`.

O lote `4f13b856-6bf8-4eab-8639-188fc32b05b3` executou os 16 slots uma única vez:
16 concluídos, zero falha, skip, retry, reparo, fallback ou troca de alvo. A
revisão independente, ligada byte a byte aos brutos, resultou em Qwen 0/8 e
GPT-OSS 0/8. Nenhum candidato atingiu 8/8; nenhum narrador foi admitido e nenhum
default foi criado. Em 25/09/2026, o usuário aceitou a classificação com o texto
`Aceito HYP-002-L2: nenhum candidato elegível; nenhum narrador admitido.`
Evidência: `closed-world-render-live-observation-4f13b856-2026-09-25.md` e `.json`.
