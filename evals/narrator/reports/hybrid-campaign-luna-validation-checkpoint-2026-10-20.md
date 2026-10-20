# Checkpoint — fronteira de validação do narrador

Status: decisão proposta, não aprovada. Nenhum narrador admitido/default alterado.
Escopo continua campanha sintética Registro em risco, perfil B opt-in.

## Resultado e evidência

L76–L82 preservados, primeira falha encerra, sem retry/fallback/best-of:

| Lote | Chamadas | Turnos completos | USD estimado |
|---|---:|---:|---:|
| L76 | 4 | 3 | 0.0039206 |
| L77 | 15 | 14 | 0.0148322 |
| L78 | 10 | 9 | 0.0099626 |
| L79 | 12 | 11 | 0.0122374 |
| L80 | 17 | 16 | 0.0168512 |
| L81 | 16 | 15 | 0.0158616 |
| L82 | 9 | 8 | 0.0091548 |
| Total desta sequência | 83 | 76 | 0.0828204 |

Estimativas por uso observado e snapshot de preços, não cobrança confirmada.
Todos abaixo do teto de USD 0.15 TOTAL por lote; teto não é cumulativo da conversa.
L41–L82: 396 chamadas/356 turnos/USD 0.3919904 estimados. Versões e guards
mudaram; não calcular taxa de estabilidade a partir desses lotes.

Falsos positivos reproduzidos/corrigidos: em mente como mentir; das partes
legíveis como partir; gotas que avançam e água atravessar registro atribuídas
ao jogador; falha negativa sem conteúdo algum; equivalências de preservação.
Lacunas de fidelidade corrigidas: secagem instantânea, novos cuidados após
desfecho, tarefa de examinar substituindo preservar e repetição de transporte.
Não houve relaxamento de limites, concessão de autoridade à LLM ou nova lore.

L75 havia completado 17/17 tecnicamente, mas auditoria descobriu secagem indevida.
L82 comprova o outro lado: além de rejeitar frases válidas, o sistema aceitou
desvios do objetivo e pedidos posteriores ao epílogo. Duas falhas offline
pré-fix reproduzem esses falsos negativos. As correções são verificadas localmente,
não prova de que linguagem não vista esteja coberta. Fontes: relatórios L75–L82,
records imutáveis de cada batch e testes de regressão vinculados nesses relatórios.

## Verificação

- 91 focados do snapshot final passam, hyp-007-l82-final-audit-2026-10-20.xml.
- 966 ampliados passaram no snapshot L81 antes das últimas correções; não
  atribuir cobertura retroativa. Snapshot final ampliado: 987 passam,
  hyp-007-l82-final-expanded-2026-10-20.xml (161.19s, um aviso python_multipart).
- Regressores incluem agência, segredo, objetivo, consequência, desfecho,
  persistência/reconstrução/replay sem RNG/chamada adicional e rollback.
- Nenhuma medição atual de UX em navegador, estabilidade estatística ou release.
- Chave nunca lida/exibida; supervisora ociosa, expiração automática preservada.
- L83/v23 preparado e fechado; não executado, sem custo de inferência.
- Conferência final: 22 hashes reais de L83 válidos, gates L76–L82 false/false,
  nenhuma execução pendente; diff focado sem erros de whitespace. Os 987 testes
  incluem preparação L83 no perfil final; não somar com execuções sobrepostas.

## Decisão humana proposta — DEC-NARR-VALID-001

O diagnóstico é insuficiência de evidência para admitir o modelo no MVP, não
prova de impossibilidade da arquitetura ou de que outro modelo resolverá tudo.
O problema não pode ser atribuído apenas à capacidade narrativa de Luna:
validadores locais também falham em ambos os sentidos.

**A — recomendada: revisar a arquitetura desta fronteira antes de mais lotes.**
Definir um contrato com vínculos explícitos entre atores, referentes, efeitos
preparados e trechos de narração; avaliar composição determinística dos fatos
críticos e liberdade da voz do NPC sem transferir autoridade canônica à LLM.
Planejar compatibilidade/persistência e contraprovas do corpus completo antes
de implementar. Esta é uma DIREÇÃO PROPOSTA, não contrato decidido; campos,
renderização e grau de liberdade dependem da decisão/arquitetura revisada.
Consequência: investigação/desenho local sem chamadas pagas inicialmente;
mudanças de schema/runtime somente após aprovação explícita da proposta final.
Não prometer validação semântica perfeita de prosa livre.

**B — manter o contrato atual e continuar correções incrementais delimitadas.**
Preserva arquitetura e liberdade existentes, com novos testes prospectivos
quando necessários sob autorização contínua <= USD 0.15 por lote. Consequência:
continua risco observável de rejeitar frases válidas/aceitar desvios novos;
nenhum lote verde sozinho admite modelo, default ou produto. Não é recomendado
prolongar essa estratégia como se bastasse acumular exemplos para garantir UX.

Não falta aprovação financeira para L83; o gate é escolher conscientemente
a estratégia de qualidade/arquitetura e risco do MVP. A escolha não admite
Luna nem fecha CAMP-24. Nenhuma das duas opções foi convertida em decisão.

Configuração recomendada:
- Modelo: Astra (gpt-6-astra).
- Esforço: high.
- Motivo: conflito de adequação entre liberdade narrativa, validação determinística
  de significado e autoridade canônica, com falhas observadas nas duas direções.
- Ação humana necessária: escolher A ou B; A autoriza o desenho/auditoria da
  fronteira, não implementação de um schema ainda não especificado.
- O que continuará autonomamente depois da ação: em A, inventariar corpus,
  comparar contratos e preparar proposta/provas offline; em B, retomar L83
  somente após preparação/hashes finais, dentro dos tetos e sem admissão automática.

## Próximo item do MVP

Fechar desenho/progressão da campanha híbrida mínima e a fronteira do narrador
(PROG-ROUTE-B, DEC-PROG-001/002). CAMP-24 continua aberto; não saltar para bandeja
de dados, ficha/criação de jogador, merge ou entrega do MVP.
