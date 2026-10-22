# A2 — seleção de expressão v1 implementada offline, 22/10/2026

> Atualização posterior, 22/10: envio explicitamente autorizado e L86 executado.
> 17 pares, USD0.0023204 estimado; 34 replays reais conferidos. O bloqueio e a
> pendência descritos abaixo são o checkpoint anterior ao aceite específico.
> Resultado vigente: [observação L86](expression-selection-l86-observation-2026-10-22.md).


O experimento isolado aprovado foi implementado. O modelo pode selecionar somente
IDs de fala, atmosfera e layout elegíveis; todo texto exibido tem autoria da
aplicação. Preparação, escolha, estado e apresentação são versionados/retidos.
A comparação real L86 está pronta e bloqueada por revisão automática de envio;
nenhuma inferência ocorreu nesta etapa. Não há ganho editorial de modelo medido.

## Superfície e comportamento

Pacote opt-in `api/experiments/expression_selection/`:

- `contract.py`: perfil campaign-selection-local-v1, preparação/catálogo/renderizador
  v1, schemas de escolha por enums, JSON bruto estrito (sem chaves duplicadas,
  cercas, prosa extra ou reparo), referências e autoria por segmento. Catálogo
  distingue tarefa/ajuda/repetição e condições de dano/posição/desfecho.
- `store.py`: SQLite dedicado ao experimento, marcador de aplicação e formato
  próprios; recusa bancos do produto e não sobrescreve arquivo existente.
  Claim de entrada durável antes de RNG; resultado mecânico e catálogo retidos.
  Commit CAS confirma estado, apresentação e tentativa na mesma transação.
- `service.py`: política determinística ou target de modelo explicitamente escolhido;
  capabilities native/emulated respeitadas. Retém escolha validada antes do commit;
  texto só retorna depois de persistir. Sem streaming provisório neste experimento.
- `transport.py`: protocolo bruto com evidência do contrato LLM comum; adaptador
  OpenAI-compatible isolado preserva resposta bruta para o parsing estrito local.
  Não muda o parser global, que continua aceitando última chave duplicada.

Não foram editados módulos de regras, leitores A1, persistência do produto,
configurações/credenciais, endpoints da interface ou checkout original. Os bancos
A2 são arquivos novos e separados. Nenhuma migração, seleção de default, admissão,
commit/push/merge ou instalação de dependência.

Preparação chama o resolvedor determinístico existente. Investigação usa recibo
da única rolagem feita após claim; H6/replay/resume não interpretam nem rolam de
novo. Falha/crash após claim de preparação não autoriza repetir RNG. Recuperação
explícita pode encerrar claim incompleto sem reconstruir recibo ou reexecutar ação.

Falha/cancelamento do seletor conserva preparação e revisão. Nova tentativa exige
vínculo explícito à anterior; mesma tentativa não envia de novo. Se já houve escolha
válida retida, retomada a reutiliza com evidência da invocação original e não chama
modelo. Recuperação explícita invalida a tentativa velha por CAS, impedindo commit
de uma resposta tardia. Isso não prova cancelamento remoto nem custo zero de uma
chamada que já estava em andamento. Nenhuma recuperação automática no startup.

Replay valida o conteúdo persistido e sua composição pelo catálogo/versionamento
retidos, retornando os mesmos bytes. Não usa builder/renderizador atuais, modelo
ou RNG. A garantia depende da preservação dos compiladores v1 e da fonte local
confiável; hashes não tornam o banco inviolável nem provam a verdade editorial.

## Verificação concluída

**142 testes distintos selecionados passaram nesta etapa: 138 do núcleo/regressão
mais quatro do harness L86.** Desses, 75 são novos (71 do experimento e quatro do
harness). Não somar execuções intermediárias repetidas como testes distintos.

- Oito percursos nos modos determinístico e modelo simulado: 17 turnos por modo,
  mesmos desfechos/efeitos, reinício/replay sem chamadas/rolagens adicionais.
- Variantes R01 ajuda/repetição e tarefa/ajuda com páginas molhadas, R08 com perda
  após dano anterior e R09 molhado; slots nunca alteram consequências.
- JSON inválido, chave duplicada, campo extra, enum desconhecido, homógrafo,
  prosa/cercas, tipos, tamanho e contrato A1 rejeitados nos modos native/emulated.
- Falta de capability, emulação sem permissão, indisponibilidade, rota divergente,
  cancelamento antes/depois da seleção e cancelamento da task.
- Rollback SQL sem texto retornado; retomada após rollback usa escolha retida;
  single dispatch concorrente, recuperação CAS e resposta tardia recusada.
- Adulteração rehashada de plano, catálogo, ator/referências, versão/revisão e
  texto de histórico rejeitada; banco de produto recusado sem mutação.
- Regressões selecionadas A1 e adaptador comum; parser legado não foi alterado.

XMLs: `eval-results/expression-selection-offline-final-2026-10-22.xml` (138),
`eval-results/expression-selection-l86-readiness-2026-10-22.xml` (4).
A execução inicial de 63 testes é subconjunto anterior, não contagem adicional.
Aviso preexistente python_multipart; nenhuma dependência alterada.

Preflight keyless L86: 17 pares completos, zero provedor, maior request 2.215 bytes.
Arquivo `eval-results/expression-selection-l86-preflight-2026-10-22.json`.
Falha inicial do harness (capabilities ausente no adaptador Responses) foi corrigida
antes de enviar API; diagnósticos falsos preservados, sem retry de modelo.

## Comparação real preparada e bloqueio

L86 é um lote próprio de até 17 seleções com Luna low, pareado com baseline sem
modelo. Protocolo prospectivo, 32 hashes, guard de custo <=USD 0.15, requests
<=20.000 bytes e até 256 tokens efetivos por request. O manifesto compatível com
supervisora conserva limite máximo 768, com campo explícito para os 256 usados.
API Responses/store false, sem tools/temperatura/retry/fallback/admissão.
Tarifas 0.20/1.20 USD por milhão reconferidas em 22/10 na documentação oficial.

A revisão automática rejeitou o comando que ativaria gates e criaria o request
por exigir autorização explícita para os payloads específicos no destino OpenAI,
com custo. O comando inteiro não executou. Gates permanecem false/false; não há
request L86, latch ou execução real. Custo de inferência novo: USD 0.
O bloqueio foi respeitado, sem mecanismo alternativo de envio.

Arquivo completo preparado para autorização:
`eval-results/expression-selection-l86-payload-review-verified-2026-10-22/payloads-for-approval.json`.
SHA-256: 3dc437e9b2cc112ecccceb92324d6780c9c99c9fbf295fb9d309af8b4d7ab038.
Destino: https://api.openai.com/v1/responses. Contém instrução de seleção, consequência,
falas/opções autoradas da microcampanha sintética e schema. Não inclui chave,
ficha de jogador, save de campanha ou código-fonte. Contém 17 corpos de request,
que são os corpos gerados por esta versão do harness para a matriz.

O banco `sessions.sqlite3` e records/summary nessa pasta são uma execução com
seletor FALSO, não Luna. As variantes foram escolhidas programaticamente; diferenças
para baseline não medem ganho da LLM. Esse banco também conserva evidência de replay
sobre armazenamento real. Nenhuma capacidade local/gratuita/hardware foi avaliada.

## Limites e próximo passo

A2 torna a inserção de texto arbitrário uma violação estrutural rejeitável neste
contrato. A verdade/elegibilidade das frases autoradas continuam responsabilidade
da aplicação, como demonstrado no estudo pela contraprova de catálogo falso.
Não declarar solução de fidelidade para RPG aberto, improvisação ou outros H0/H1/H4.
O catálogo e o compositor são específicos do recorte de Mara; o padrão de contrato,
preparação, validação e proveniência pode ser estudado para outros modelos.

A única intervenção pendente para esta comparação é autorizar explicitamente os
17 payloads sintéticos no destino OpenAI, até USD 0.15 estimados. Após essa ação,
revalidar hashes/estado da supervisora, despachar uma vez, fechar gates e comparar
todas as apresentações com a baseline. Naturalidade intermediária está delegada;
não pedir novo aceite por turno. Se a autorização não chegar antes da expiração,
nenhum despacho; nova entrada de credencial só quando necessária e solicitada.
CAMP-24/admissão/MVP e adaptação do original permanecem abertos.
