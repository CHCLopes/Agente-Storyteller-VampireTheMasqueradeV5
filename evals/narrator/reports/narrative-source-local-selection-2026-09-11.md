# Seleção local B — contrato inativo concluído

O vínculo criado pelo servidor e o seletor local foram implementados em
`api/narrative_source_local_selection.py`, com **73 testes aprovados**, sem
falhas, erros ou casos ignorados. A revisão independente fechou sem bloqueadores.
O componente está inativo: nenhuma rota ou interface o chama.

O servidor escolhe destino, habilitação, sessão, store, manifesto, configuração
e Host/Origin de loopback exatos. A factory não faz I/O. Destino B recusado nunca
retorna legado. Sessão e cabeçalhos incompatíveis são recusados antes da consulta;
somente a entrada compatível lê o manifesto pelo leitor B existente, uma vez,
em modo somente leitura, e o compara ao vínculo revalidado.

Foram verificadas cópias inconsistentes, campos internos extras, identidade/path
do store, cabeçalhos duplicados, origens incompatíveis, banco ausente ou corrompido
e falhas de leitura. Erros tipados de SQLite/OSError retornam causa fechada sem
diagnóstico bruto. Cancelamento propaga após uma consulta, sem retry ou fallback.
No SQLite sintético real, a seleção preservou os bytes do banco, com uma campanha
de setup e zero tentativas, turnos, eventos ou memórias. Banco ausente não foi criado.

Na revisão, identificou-se que rollback/close do leitor pode lançar sqlite3.Error
fora da normalização do corpo. A captura específica e contraprovas foram incluídas
antes da primeira suíte, que passou integralmente. Hashes dos dois arquivos antes
e depois da execução são iguais. O revisor não repetiu testes nem fez inferências.

## Limites e continuidade

O checksum e a identidade Python detectam inconsistências; não autenticam jogador
ou processo local hostil. O caminho é lexical absoluto, sem garantia de identidade
física do arquivo. Os handles internos não são payloads públicos nem permissões
serializáveis de execução. O chamador futuro ainda precisa vincular o banco sintético
isolado e o listener; a factory não inspeciona rede ou filesystem.

Não houve montagem de handler, accept, bootstrap, reserva, migração, produtor,
gateway ou RNG. `main.py`, `state_service.py`, rotas e UI não foram modificados
por este incremento. Os testes comprovam o componente isolado, não ordenação no
endpoint real ou no lifespan. TASK-001/003 do transporte permanecem parciais quanto
à integração; TASK-004/005/006 não são entregas deste fechamento.

A comparação 61b83a2f e sua revisão estão preservadas; nenhum candidato qualificado,
modelo default ou CAP-001 aprovado. A correção anterior de agência permanece com
suas 1.097 verificações próprias, sem repetir essa suíte. Não houve chamada real
adicional. Integração/ativação seguem os requisitos de experiência e aceitação do
recorte do plano de transporte, separados desta preparação local.

[Plano de transporte](../../../plan/feature-narrative-source-transport-1.md) ·
[Desenho do despacho](../../../plan/source-local-dispatch-design-2026-09-11.md).
Evidências: `eval-results/checkpoints/narrative-source-local-selection-20260911/`; o JSON acompanha os hashes.
