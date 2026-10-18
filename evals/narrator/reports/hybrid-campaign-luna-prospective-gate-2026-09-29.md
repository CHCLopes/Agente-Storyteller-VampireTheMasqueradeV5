# Gate prospectivo — Luna low na campanha B opt-in

Estado: desenho, preflight e runner simulado; autorização de até 17 chamadas e
teto estimado USD 0,15 concedida explicitamente em 30/09/2026. Aguardando
entrada segura da chave e execução. Nenhuma chave foi consultada, nenhuma
chamada foi feita e nenhum narrador/default foi admitido.

## Pergunta e dependência

HYP-007 (nova hipótese, não repetição do HYP-006): com consequência
determinística preparada e histórico B atribuído, `gpt-5.6-luna` em esforço
`low` consegue realizar no texto a progressão, responder a Mara de modo
pertinente e encerrar a aventura sem usurpar agência, mecânica ou segredos?

O usuário aceitou o objetivo técnico/causal da microcena autorada, confirmou
os desfechos CAMP-EVAL-02–04 e avaliou 05/08; 01 já havia sido executado.
O feedback de UX reforça a preferência por fala direta de Mara, sem transformar
o corpus autorado em saída do Luna ou alterar retroativamente esta rubrica.
Houve avaliação qualitativa de UX: a mediação impessoal de Mara prejudica a
imersão, sem uma nota global de satisfação ou aceite integral do MVP. Os
percursos 06/07 têm recibos fixos apenas no teste offline. A observação sobre
diálogo direto de NPC está em
[observação separada](../../../plan/observation-npc-direct-dialogue-1.md):
não é gate retroativo deste experimento. O objetivo causal do recorte autorado
foi observado; o lote Luna é a próxima medição separada. Antes de qualquer
live, conferir prompt, casos, código, hashes e autorização financeira. O
corpus usa apenas dados sintéticos da campanha de teste.

## Desenho técnico congelado; autorização paga concedida

- Alvo único: OpenAI Responses API, `gpt-5.6-luna`, reasoning `low`, saída
  estruturada `CampaignSourceProposal` (`n`, `q`, `realized_effects`),
  `store: false`; sem ferramentas. Nenhum default de runtime é alterado.
- Mesmos oito percursos `CAMP-EVAL-01–08` e contraprovas do
  [protocolo](../hybrid_campaign_progression_protocol_v1.md). São 17 turnos
  teóricos (2+4+3+1+1+1+2+3), máximo absoluto de 17 chamadas concluídas ou
  tentadas. Cada trajetória começa em sessão sintética independente; falha
  de uma predecessora impede continuação daquela trajetória.
- Uma resposta por operação, sem retry, reparo, fallback, seleção da melhor
  resposta ou troca de alvo. Falha crítica de autoridade, agência, segredo ou
  efeito encerra o lote; transporte/uso incerto o torna inconclusivo. Não
  agregar resultados de HYP-006 nem de eventual execução parcial.
- Teto candidato por resposta: 768 tokens de saída, prazo de 60 s, zero
  espera artificial entre chamadas Luna. Preflight deve medir e limitar o
  corpo UTF-8 de cada request antes do dispatch; proposta inicial: 20.000
  bytes por chamada. Se o pacote real exceder, parar sem chamada e revisar o
  desenho prospectivamente, nunca truncar consequência obrigatória.
- Estimativa de planejamento: aproximadamente USD 0,10 pelos 17 requests
  nos limites acima, antes de impostos e variações de cobrança. Propor
  autorização máxima de USD 0,15 para a bateria, com bloqueio local por
  orçamento restante e limite de gastos da conta como proteção separada.
  O cálculo não é fatura nem autorização. Preço de referência em 29/09/2026:
  USD 0,20/M tokens de entrada e USD 1,20/M de saída, segundo a
  [página oficial do modelo](https://developers.openai.com/api/docs/models/gpt-5.6-luna).
  Revalidar tarifa e capacidade imediatamente antes da execução.
- Registrar por slot: operação, caso, alvo solicitado/efetivo, hash do
  pacote/contrato, duração de preparo, geração e commit, status, uso reportado,
  custo estimado e resultado da validação. O encerramento deve mostrar custo
  final `estimated`, `unavailable` ou `no_dispatch`; uso faltante nunca vira
  zero. Nenhum token de chave ou conteúdo de credencial nos artefatos.

## Rubrica e parada

Separar transporte/schema, admissão mecânica/canônica, realização do efeito,
resposta à intenção, continuidade e julgamento humano da experiência. Gates
críticos não podem ser compensados por média de estilo. Pontuar apenas os bytes
originais da resposta; não usar outro LLM como juiz nem otimizar/repetir o
mesmo lote após observar falha. A fala direta de NPC pode constar como nota
qualitativa não-gating, preservando a escolha futura de produto.

## Preflight keyless realizado

O prompt candidato está em `evals/narrator/prompts/hybrid-campaign-source-v1.md`
(SHA-256 atualizado em 30/09: `10b64256b36fcae1a80432361e9e4883129d8b78084a855b03515ab26742f4cf`).
Após o feedback humano sobre imersão, ele passou a pedir fala direta de Mara
quando responde, sem alterar o schema, os gates ou a prosa autorada. Trata-se
de instrução prospectiva, não de requisito retroativo ou critério eliminatório.
`scripts/preflight_hybrid_campaign_luna.py` percorreu os 17 turnos das oito
trajetórias com adaptador falso e corpo Responses API montado localmente.
Maior corpo HTTP UTF-8 observado após essa revisão: **12.049 bytes**, abaixo dos 20.000 propostos;
máximo de 768 tokens de saída por request e `store: false`. Não há autorização
de inferência, runner live nem credencial nessa etapa. O preflight deve ser
refeito após qualquer alteração do prompt, schema, corpus ou código de
construção do pacote: hashes de requests sintéticos incluem dados temporais
e não são manifestos estáveis para congelamento. Testes focados do preflight,
trajetórias e perfil: **16 aprovados**, 1 aviso de dependência preexistente.
Nenhum custo ou tempo de resposta do Luna foi medido.

Em 30/09, `scripts/evaluate_hybrid_campaign_luna_live.py` e
`scripts/run_hybrid_campaign_luna_live.ps1` foram preparados. O manifesto
`hybrid-campaign-luna-live-gate-2026-09-30.json` contém alvo, prompt e 16
hashes de implementação; **ambos os flags de gasto e inferência permanecem
false**. O lançador recusou a execução antes de pedir chave e mostrou
`CUSTO FINAL LUNA: USD 0 (nenhuma chamada iniciada)`. O runner limita 17
chamadas, 768 tokens de saída, 20.000 bytes reais por corpo HTTP, prazo de 60 s,
modelo/rota fixos, uma tentativa por turno e interrupção na primeira falha.
Registra operação, hash da cápsula e requisição, durações, uso e estimativa;
uso ausente interrompe o lote sem converter custo desconhecido em zero. O
limite local de USD 0,15 é estimativo por tokens e não substitui limite da
conta nem confirma cobrança. A chave só será pedida pelo terminal seguro após
autorização explícita; nunca em chat ou `.env`.

Com transporte falso, 17/17 turnos fecharam; contraprovas adicionais mostraram
parada após uso indisponível, rejeição semântica e orçamento insuficiente antes
do dispatch. Três exemplos de fala direta de Mara passaram no contrato atual,
sem alterar o verificador. Ele é lexical e pode rejeitar uma formulação
ambígua de segredo; tal resultado precisa de leitura humana antes de atribuir
falha narrativa ao modelo. A matriz focada final de campanha, preflight,
adaptador Luna, custo e diálogo aprovou **98 testes** (um aviso de dependência
preexistente); o parser PowerShell teve zero erros. Nenhuma dessas simulações
qualifica Luna.

## Trabalho restante antes de live

1. CAMP-EVAL-01–05/08 têm relato humano de execução e objetivo causal; 06/07
   têm cobertura determinística offline, mas não devem ser repetidos
   manualmente até obter o dado desejado. A avaliação de UX encontrou a
   apresentação impessoal de Mara. Não inferir aceite integral da experiência
   nem qualificação do Luna a partir da prosa autorada.
2. Antes de live, revalidar preço e disponibilidade na documentação oficial,
   conferir os hashes congelados e o limite de gastos da conta. Obter aprovação
   humana explícita do teto estimado USD 0,15 para no máximo 17 chamadas e
   inserir a chave apenas no prompt seguro do lançador. Sem esses gates não
   despachar. O manifesto técnico está congelado, mas os flags pagos continuam
   desativados.
3. Depois do lote, verificar artefatos e custo final e submeter a realização
   narrativa à avaliação humana. Não admitir Luna/default automaticamente.

Este arquivo é uma proposta técnica reversível. Não promove `HYP-007` a lote
aprovado ou executado, nem qualifica Luna antes de evidência semântica humana.
