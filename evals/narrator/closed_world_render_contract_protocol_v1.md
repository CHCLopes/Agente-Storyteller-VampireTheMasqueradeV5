# Protocolo prospectivo — plano de renderização de mundo fechado v1

Data: 25/09/2026. HYP-002-L2 foi aprovada pelo usuário antes da preparação e de
qualquer chamada deste lote. O protocolo permanece prospectivo até o freeze
offline concluir.

## Pergunta

Um plano fechado, autorado pelo servidor, permite que GPT-OSS low e Qwen none
realizem somente proposições autorizadas, preservando progressão, espera, agência,
segredo, mecânica e próxima escolha nos oito tipos de caso do MVP?

HYP-001 permitia prosa sensorial ao redor de fatos e transições. HYP-002 muda uma
única variável: toda afirmação factual ou sensorial deve corresponder a uma unidade
fornecida. Modelo, reasoning, temperatura, teto, deadline e schema n/q permanecem
iguais aos alvos observados em HYP-001.

## Alvos e orçamento

- `openai/gpt-oss-120b`, Groq oficial, reasoning `low`;
- `qwen/qwen3.8-27b`, Groq oficial, reasoning `none`;
- oito casos novos por alvo, máximo absoluto de 16 chamadas;
- temperatura 0,65, teto 768 tokens, deadline 60 segundos;
- intervalo mínimo global de 60 segundos entre inícios;
- zero retry, reparo, fallback, troca de alvo ou repetição de slot.

## Casos e ordem

O corpus executável é `closed_world_render_contract_v1.json`. Ele contém oito
casos sintéticos novos, isomórficos às classes de risco de HYP-001, sem reutilizar
seus objetos ou textos: espera sem transição, espera com uma transição, objeto
conhecido, objeto desconhecido, resultado mecânico favorável, resultado mecânico
desfavorável, segredo de NPC com pista e ação ambígua.

Os dois casos de sino formam uma cadeia por alvo. Os demais são independentes.
Cada alvo recebe os mesmos casos, parâmetros e orçamento. O agendamento alterna
os alvos e não permite que texto de um alvo entre no contexto do outro.

## Contrato fechado

Cada caso fornece required_units, optional_units, no máximo uma
authorized_transition, player_action_boundary, unknowns, forbidden_claims,
sensory_palette, next_choice_boundary e protected_secrets. Toda required_unit deve
ser realizada. Prosa não vinculada a uma unidade é violação fatal, inclusive
detalhe atmosférico aparentemente inocente.

O modelo controla somente n e q. Regras, RNG, resultado, fatos, transições,
segredos, estado e commit continuam fora de sua autoridade.

## Gates

Cada alvo precisa aprovar 8/8. São fatais: afirmação não listada, agência do
jogador, segredo revelado, ampliação/reversão mecânica, unidade obrigatória
omitida, transição indevida, schema ou cápsula inválidos, alvo/proveniência
divergentes e retry/reparo/fallback/troca/repetição ocultos.

Também são obrigatórios: 30 a 150 palavras, pergunta aberta, próxima escolha
preservada, progressão somente quando autorizada e espera coerente nos casos sem
transição. Marcadores automáticos são contraprovas mínimas; revisão semântica
independente continua obrigatória.

## Parada fail-closed

Falha de freeze, hash, teste ou preflight encerra antes da rede. Falha de
autenticação, rota, alvo, transporte, schema ou integridade encerra os slots
restantes. O décimo sexto início encerra o orçamento. Nenhum slot é repetido ou
reparado. Resultado sem candidato elegível permanece válido.

Após a execução, artefatos e revisões são verificados e o processo para para
aceitação humana. HYP-002-L2 não autoriza admissão, default, provedor produtivo,
custo pago, campanha híbrida ou relaxamento de gate.
