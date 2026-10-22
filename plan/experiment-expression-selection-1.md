# Experimento A2 — seleção de expressão v1

Autorizado por “Prossiga” após a proposta delimitada de experimento isolado,
contrato próprio, persistência/retomada e comparação determinística. Original,
defaults e admissão permanecem fora do recorte. Autonomia: AUTONOMOUS_TASK.

- [x] Contrato versionado, catálogo congelado por variante e composição autorada.
- [x] Armazenamento SQLite dedicado somente ao experimento, recusando bancos de
      produto; claim antes de RNG, preparação retida, CAS e histórico validado.
- [x] Execução com seleção determinística explícita ou alvo de modelo explícito;
      parsing JSON estrito local, sem retry/fallback. Resposta por IDs apenas.
- [x] Pausa/falha/reinício e retomada explícita; escolha validada retida para
      recuperação sem nova inferência; apresentação retornada após commit.
- [x] Oito percursos e variantes R01 ajuda/repetição, R08 perda e R09 molhado;
      igualdade de efeitos entre políticas e evidência da contribuição editorial.
- [x] Contraprovas de versão/escopo/schema/parsing, concorrência, rollback,
      cancelamento e replay; regressão dos leitores A1 e fronteira comum intactos.
- [x] Documentar resultado e próximo gate real, atualizar checkpoint.

Escolhas locais: pacote opt-in api/experiments/expression_selection. SQLite da
biblioteca padrão, arquivo dedicado e marcador de aplicação, sem DDL/migração no
banco de produto. Reutilizar resolvedor e renderer crítico congelado A1 sem editar
seus módulos. Nenhuma chamada é necessária para validar o núcleo offline. Alvos
reais somente após protocolo próprio, freeze/limites e entrada protegida vigente.
A avaliação editorial intermediária já está delegada. O catálogo é autorado e
limitado; fidelidade geral do autor e utilidade de um modelo continuam questões
separadas. Este recorte não implementa criação livre de mundo ou adaptação do
checkout original.


## Estado em 22/10/2026

Implementação e verificações offline concluídas: 142 testes selecionados (75
novos), preflight de 17 pares sem API/max2.215 bytes. A comparação com modelo real
L86 está preparada e bloqueada por revisão automática: falta confirmação explícita
de envio dos payloads específicos à OpenAI até USD0.15. Nenhum envio/custo/latch;
gates false/false. Não tratar seleções simuladas como resultado Luna.
Relatório: evals/narrator/reports/expression-selection-a2-implementation-2026-10-22.md.


## Encerramento do experimento, 22/10/2026

Envio explicitamente autorizado; L86 completou17 pares/17 chamadas, USD0.0023204
estimado. Estados/efeitos iguais;34 replays reais conferidos no SQLite retido.
Oito frases de posição redundantes; ganho editorial consistente não demonstrado.
Gates fechados/trava mantida; nenhum lote adicional. Experimento aprovado concluído;
nenhuma ação humana pendente para L86. Produto/MVP/adaptação do original não admitidos.
Relatório: evals/narrator/reports/expression-selection-l86-observation-2026-10-22.md.
