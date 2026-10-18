# Projeções públicas B — contrato interno concluído

O módulo inativo api/narrative_source_transport.py projeta somente os campos
públicos necessários à futura interface. Nenhuma rota, handler, frontend ou
seleção de modelo foi ativada. O fluxo atual permanece intacto.

## Comportamento

- Briefing reapresenta o texto autorado após validar manifesto e sessão.
- Preparação distingue pending, ready e recusa; ready não autoriza execução.
- Narrativa distingue retida ainda não iniciada de geração pending.
- Texto completo exige snapshot completed e envelope coerentes em sessão,
  operação e turno confirmado. n e q ficam separados, preservados literalmente;
  replay histórico não recebe o contador atual de outra cena/turno.
- Falhas conhecidas viram categorias públicas fechadas; causa segura ausente
  vira unavailable. Forma ou identidade incompatível falha fechada, sem ocultação.
- Claims, cápsulas, estado, target, SYSTEM, evidência, hashes internos e campos
  de retry não são serializados. Projeção não faz I/O, RNG, reserva ou chamada.

Modelos são estritos, congelados e versionados. A reconstrução recursiva preserva
campos extras forjados para rejeitá-los, inclusive em fontes/projeções aninhadas.
Essa validação confere consistência, não autentica o cliente nem prova um commit;
o futuro chamador deve consumir os leitores confiáveis antes da projeção.

## Verificação e correção encontrada na revisão

A rodada inicial teve202 testes verdes. Root e revisor independente identificaram
pares de falha reais que os modelos sintéticos iniciais não representavam:
provider_failure com timeout/cancelled e delivery_failed com cancelled. A primeira
versão recusava indevidamente essas observações por inferir status somente do código.

Três contraprovas pelo executor real, SQLite temporário e leitor após reinício
reproduziram a falha antes da correção:3failed/202deselected. A correção acrescentou
somente os três pares explícitos. Status e estágio permanecem preservados, sem
publicar categoria ou evidência bruta do provedor. Contratos internos existentes
não foram alterados.

Rodada final: **215 testes passaram**, sendo205 próprios e10 regressões existentes
do leitor, incluindo terminais, turnos completos e replay histórico; zero falha,
erro ou skip,7,10s. Um aviso preexistente de python_multipart. Rodadas não foram
somadas como casos distintos. Logs/JUnit anteriores foram preservados; hashes no JSON.

## Limites e continuidade

TASK-002 do plano de transporte está concluída. TASK-003 está concluída apenas
para projeções; cobertura de despacho anterior ao legado depende da seleção e
do handler futuros. Transporte completo continua In progress. Os28 arquivos
congelados e os artefatos do ensaio source-player permaneceram idênticos.

O ensaio de diálogo e espera continua experiência parcial, apesar do êxito técnico.
Este incremento não transforma esse resultado em aprovação narrativa, runtime ou
CAP-001. A seleção local optativa e o vínculo da sessão precisam ser fechados
antes de integrar uma rota. Acesso direto remoto exigiria decisão de identidade;
controle remoto do desktop não implica essa exposição.
