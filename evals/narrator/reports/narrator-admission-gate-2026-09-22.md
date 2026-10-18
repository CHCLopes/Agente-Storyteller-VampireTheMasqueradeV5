# Gate de admissão do Narrador do MVP

**Data:** 2026-09-22

**Status:** concluído — opção A escolhida pelo usuário

**Escopo:** escolher se algum candidato pode ser admitido como Narrador do MVP;
não aprova campanha híbrida, custo, credencial, fallback ou capacidade paga.

## Estado observado

- A pausa/retomada foi concluída técnica e humanamente.
- O comparativo fechado não qualificou Qwen nem GPT-OSS.
- Qwen excedeu o limite de palavras em duas saídas do lote comparativo; o
  diagnóstico posterior explicou duas recusas, mas não transformou o lote
  encerrado em evidência de elegibilidade.
- GPT-OSS obteve três turnos confirmados na Oficina; a proposta recusada no
  Arquivo continua recusada, embora um falso positivo tenha sido corrigido para
  avaliações futuras.
- Ambos apresentaram fragilidade em espera/progressão e inventaram estado de
  porta no diagnóstico posterior.
- Repetir o mesmo comparativo, sem uma pergunta prospectiva diferente, seria
  apenas reamostragem. A necessidade técnica imediata de código ou inferência é
  zero.

Fontes: `source-model-choice-status-2026-09-12.md`,
`../../../plan/feature-source-model-comparison-1.md` e
`../../../spec/spec-architecture-narrative-engine-admission-policy.md`.

## Decisão solicitada

**Decisão registrada em 2026-09-22:** A — não admitir nenhum candidato agora.
Qwen e GPT-OSS permanecem não qualificados e nenhum default do MVP foi criado.

### A — não admitir candidato agora (recomendado)

Preserva o protocolo e registra que nenhum modelo é default do MVP. O próximo
passo será definir uma hipótese prospectiva realmente distinta e seu protocolo
de admissão antes de qualquer nova chamada. A campanha híbrida não começa por
arrasto enquanto o Narrador permanecer sem admissão.

### B — admitir GPT-OSS de forma provisória

Aceita explicitamente evidência incompleta e exige, antes da implementação,
definir o recorte provisório, critérios de revogação, alvo exato, `CAP-001`,
custo, segurança e política de fallback. Não é recomendada pelo parecer atual.

### C — admitir Qwen de forma provisória

Aceita explicitamente variabilidade e estouros observados, além de exigir as
mesmas definições de B. Não é recomendada pelo parecer atual.

## Limites da resposta

A escolha deste gate não autoriza silenciosamente provedor, conta, orçamento,
credencial, fallback, alteração de prompt, novas inferências ou arquitetura da
campanha. Se B ou C for escolhida, essas decisões continuam separadas e deverão
ser explicitadas antes de ativar o candidato no caminho produtivo.

## Continuação autônoma após a escolha

- Em A: registrar a não admissão e preparar somente o brief da nova hipótese de
  avaliação, sem chamadas, para aprovação humana.
- Em B ou C: registrar a escolha provisória e apresentar os parâmetros mínimos
  ainda necessários; nenhuma credencial será lida ou registrada.

O brief correspondente à opção A foi preparado em
`narrator-prospective-admission-hypothesis-2026-09-22.md` e `.json`. Sua
existência não aprova `CAP-001`, implementação ou inferência.
