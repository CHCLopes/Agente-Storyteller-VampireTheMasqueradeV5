# Produtor interno B — 11/09/2026

Concluído o percurso interno da intenção do jogador até a cápsula com recibo:
contratos, reserva anterior à produção, adaptador local e finalização atômica.
A integração com o coordenador narrativo existente foi verificada com FakeLLM.
Nenhum transporte público ou comportamento do jogo v1 foi ativado por esta entrega.

## Comportamento entregue

- `claim_source_input` captura pedido, contexto, estado e configuração na reserva.
  Somente o retorno novo permite ao serviço chamar o produtor. Reentrada observa
  o original; outro produtor ativo na sessão impede nova produção.
- `finalize_source_input` grava a cápsula K e a conclusão P em uma transação.
  Recusa divergência, verifica história/identidade/hashes e usa CAS no primeiro
  sucesso. Base obsoleta pode encerrar P como falha segura, sem K ou efeitos.
- Repetição terminal é verificada antes do CAS atual. Registros históricos de
  process_interrupted são validados no seu formato original, sem reescrita.
  Prefixo histórico é validado mesmo fora da janela das duas últimas fontes.
- `produce_source_player_action` reconhece espera, conversa enquadrada com NPC
  conhecido e investigação ordinária do ambiente/local. Usa Wits + Investigation,
  dificuldade servidor 3 e o motor real uma vez. Não aceita números do cliente.
- `prepare_source_player_action` recebe intenção pública e configuração servidor,
  reserva P, fornece cópia ao adaptador e conclui K/P. Transações locais são
  concluídas sob cancelamentos repetidos antes de propagar interrupção. O serviço
  não despacha H6; o coordenador retido conserva essa responsabilidade.

## Provas executadas

| Rodada congelada | Aprovados | Novos no componente | Tempo do log |
|---|---:|---:|---:|
| Entrada + contexto | 161 | 72 | 2,91 s |
| Modelos + cápsula + entrada | 167 | 57 | 4,14 s |
| Persistência + regressões pertinentes | 272 | 44 | 46,23 s |
| Adaptador + preparação | 137 | 97 | 3,49 s |
| Serviço e encadeamento | 18 | 18 | 8,84 s |

As cinco rodadas passaram na primeira execução após revisão e congelamento.
Zero falhas/erros/skips; cada rodada exibiu o mesmo aviso preexistente sobre
python_multipart. São **683 casos distintos incluindo a entrada**, sendo 288 novos;
o incremento do produtor reúne 594 casos distintos, dos quais 216 novos.
Os totais são união de classname/name dos JUnits, sem somar casos repetidos.

As contraprovas incluem: pedido duplicado e sessão ocupada; rollback entre K e P;
base/configuração divergentes; corrupção; recuperação antiga sem reescrita; replay
após avanço histórico; fala citada sem comando mecânico; recusas sem RNG; pool
servidor; sucesso/falha/crítico normal; falha parcial de RNG sem retry; cancelamento
durante claim/finalize e crash incerto; entrega do recibo ao H6 e continuidade em
dois turnos com fonte anterior íntegra. Testes usam bancos temporários, dados
controlados, conftest ativo, dotenv desabilitado e rede bloqueada.

Revisões independentes de modelo, persistência, adaptador, serviço e evidências
encerradas sem bloqueadores. Uma correção preventiva na persistência manteve a
revalidação da cápsula bruta antes de serialização, evitando ocultar campos forjados;
foi aplicada antes da rodada. As **96 funções anteriores da persistência** ficaram
textualmente idênticas; constantes de schema preservadas por AST. Os demais
arquivos existentes monitorados permaneceram intactos; hashes no JSON acompanhante.

## Limites observados

O perfil inicial exige ficha sintética elegível e Fome zero; Wits1..5 e
Investigation0..5 limitam o pool a 1..10 dados. Não altera estado/relacionamentos
genericamente. Observação/vigília/escuta, ações especiais e texto fora da gramática
são recusados. Colisão de nomes normalizados de NPCs recusa todo o perfil nesta
versão. As guardas cobrem campos de condição conhecidos, não extensões arbitrárias.

Crash após RNG e antes de K pode perder um recibo em memória. A garantia é impedir
reexecução da mesma operação, não recuperar esse resultado incerto. Deadline é
conferido antes/depois do adaptador síncrono e não interrompe CPU preemptivamente.
Nenhum retry, takeover ou política nova de pausa foi implementado.

Os resultados provam funcionamento técnico com corpus e narrativas autorados.
Não demonstram qualidade live, campanha longa, progressão geral, uso do Groq ou
CAP-001. Saves reais, credenciais, UI e default permanecem fora desta entrega.

## Continuidade preparada

Plano separado de setup/introdução revisado, ainda Planned: campanha nova B,
briefing claramente autorado, objetivo em ação realmente escolhida, manifesto
durável ainda por desenhar e seleção de transporte anterior ao fluxo legado.
As perguntas de campanha híbrida continuam abertas. O próximo passo concreto
é TASK-001/002 desse plano: contrato puro de setup e testes.

- [Plano do produtor concluído](../../../plan/feature-narrative-source-input-producer-1.md)
- [Próximo plano de setup](../../../plan/feature-narrative-source-setup-1.md)
- [Evidência estruturada](narrative-source-input-producer-2026-09-11.json)

## Pendência preexistente encontrada na auditoria final

README.md:8 aponta para LICENSE, ausente no worktree. O mesmo link foi confirmado
na cópia anterior a esta retomada. Não bloqueia código/testes do produtor; arquivo
de licença e link não foram alterados como parte deste escopo.
