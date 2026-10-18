# Decisão prospectiva após HYP-005 L2-B

Data: 2026-09-27  
Estado: proposta; zero chamada autorizada por este documento

## Fatos bloqueados

- L2-B alterou somente o teto de saída e foi executado uma vez.
- O mesmo caso Nemotron truncado em L1 concluiu em L2-B.
- Esse caso falhou o gate fatal de alegação não listada.
- A segunda chamada recebeu `provider_unavailable/openrouter_provider_overloaded`.
- Liquid e DeepSeek não foram despachados em L2-B.
- Nenhum candidato foi admitido e nenhum default mudou.

## Opções

### A — encerrar HYP-005 sem narrador

Aceitar a classificação e não realizar novas chamadas. Mantém custo e risco em
zero, mas o checklist do MVP continua sem narrador admitido.

### B — HYP-005-L3, réplica com retry estrito de sobrecarga — recomendada se a busca gratuita continuar

Repetir o protocolo L2-B em novo lote, mantendo 2048 tokens e todos os demais
campos. A única mudança seria permitir no máximo um retry da mesma requisição,
mesmo alvo e mesmo corpo exclusivamente quando a categoria normalizada for
`provider_unavailable` e o código for `openrouter_provider_overloaded`.

- máximo teórico: 48 chamadas;
- nenhum retry para rate limit, 404/model unavailable, truncamento, schema,
  semântica, custo, autenticação ou erro desconhecido;
- respeitar `Retry-After` quando reportado; sem ele, backoff único congelado;
- segunda falha idêntica aciona o mesmo fail-closed global;
- sem agregar L1/L2, best-of, troca de alvo ou fallback;
- executar somente em uma nova janela diária gratuita confirmada;
- custo reportado exatamente zero continua obrigatório.

Vantagem: testa a única causa operacional que impediu observar 22 slots.  
Limitação: mesmo que conclua, o Nemotron já demonstrou uma falha semântica fatal;
todos os oito casos de cada candidato ainda precisam passar no novo lote.

### C — selecionar candidatos gratuitos novos

Fazer uma nova triagem do catálogo e um protocolo prospectivo separado. Requer
aprovação dos slugs e não reutiliza resultados HYP-005 para admissão.

### D — alterar raciocínio, prompt ou contrato

Não recomendada neste ponto. Mistura variáveis e pode enfraquecer o gate de mundo
fechado. Qualquer uma dessas mudanças exige hipótese própria e justificativa de
produto.

## Recomendação

Primeiro aceitar formalmente L2-B. Se a intenção continuar sendo esgotar os três
candidatos gratuitos atuais, escolher B e executar apenas após uma nova janela
gratuita. Se não houver disposição para outra bateria potencialmente longa,
escolher A e tratar a ausência de narrador como decisão explícita antes de avançar
no checklist.

