# HYP-007-L82 — equivalência parcial e lacunas semânticas

Batch 48aa3ea7-5087-41d6-b800-142c0e7faf58: 9 chamadas/8 turnos, primeira
rejeição R-06/CAMP-EVAL-02. USD 0.0091548 estimado, 35868 tokens entrada/1651
saída, uso nas nove chamadas, não cobrança confirmada. SHA256 records
e64756396521762a5961b8a0cf319177334a3babdc9a3f1fe95d546c82c5fac0.
Fonte: eval-results/hybrid-campaign-luna-l82-48aa3ea7-5087-41d6-b800-142c0e7faf58.
Gate fechado, saídas preservadas; sem retry/fallback/admissão.

Rejeição técnica: O que ainda é legível foi salvo não era reconhecido como
preservação parcial. Texto também pedia precisamos tratar essas páginas com
cuidado após o desfecho, contrariando o contrato de encerramento. Reprodução:
versão fiel sem novo pedido falhou antes do fix (1 falha/8 passam). Equivalência
passada delimitada adicionada e pedido terminal bloqueado; original permanece
rejeitada. 33 focados/integração passam, XML hyp-007-l82-fix-2026-10-20.xml.

Auditoria das nove saídas encontrou duas violações anteriormente ACEITAS:
- CAMP-EVAL-08/R-01: A tarefa é examinar o documento e descobrir o que ele
  registra substitui o objetivo de preservar pelo método opcional de inspeção.
- CAMP-EVAL-08/R-05: Coloque-o com cuidado sobre a superfície seca pede novamente
  ação que a narração acabou de realizar após desfecho preserved.

Duas falhas offline antes da correção comprovam que essas respostas completavam
o turno; quatro versões fiéis/contraprovas já passavam. Correções delimitadas
em _realizes_rule bloqueiam os enunciados observados sem mudar catálogo, RNG,
persistência ou objetivo. 91 focados passam, incluindo os seis novos casos,
reconstrução/replay e rejeição atômica. XML hyp-007-l82-final-audit-2026-10-20.xml.
Snapshot final ampliado: 987 testes passam, XML
hyp-007-l82-final-expanded-2026-10-20.xml. Isso NÃO prova cobertura de todas as
paráfrases; ver checkpoint de estratégia.

L83/v23 preparado, 32 testes de preparação passam antes do último ajuste local;
hash do perfil atualizado porque manifesto nunca executado. Gate false/false,
sem request/latch/summary de execução nem custo real de L83. Não é bloqueio de
orçamento: autorização contínua <= USD 0.15 segue vigente. Nenhum novo lote foi
enviado após a auditoria revelar falsos negativos semânticos e falsos positivos
recorrentes. Não ampliar silenciosamente o contrato de validação.

L41–L82: 396 chamadas/356 turnos/USD 0.3919904 estimados. Versões variaram;
não inferir taxa comparável de estabilidade. Modelo/default/CAMP-24/MVP não admitidos.
