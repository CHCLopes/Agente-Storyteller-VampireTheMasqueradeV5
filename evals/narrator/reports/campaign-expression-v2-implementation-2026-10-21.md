# A1 — perfil experimental v2 e fronteira de fidelidade

> Atualização de 21/10 após entrada protegida: L84 e L85 foram executados e fechados.
> 29 chamadas, USD 0.0175598 estimado. L85 completou a matriz técnica, mas deixou
> 14/17 turnos sem expressão opcional e introduziu silêncio não estabelecido.
> O texto abaixo preserva o checkpoint da implementação **anterior à inferência**;
> seus trechos “aguardando chave”, “sem inferência” e “próximo passo” são históricos.
> Resultado vigente e apresentações: [avaliação L84/L85](campaign-expression-v2-l84-l85-review-2026-10-21.md).


Data: 21/10/2026. A1 aprovada pelo humano com “Prossiga” após a proposta de
composição crítica e expressão livre delimitada. Implementação opt-in no worktree
b008; nenhuma migração, alteração de RNG, default, commit, push ou admissão.

## Resultado implementado

Novo perfil `campaign-source-local-v2`, somente em sessões novas, com configuração,
origem, snapshot, cápsula, preparação, entrada, execução, projeção e turno versionados.
Os leitores v1 permanecem separados. Dois pontos compartilhados foram alterados:
`narrative_source_preparation.py` admite o tipo exato de snapshot v2;
`persistence.py` adiciona 21 linhas para validar obrigação v2 dentro da transação
e impedir mutação genérica do snapshot. Quebras de linha anteriores preservadas.
Sem DDL novo, migração de save ou mudança da ordem entrega/commit.

A aplicação compila `campaign-realization-plan-v2` com versão
`campaign-expression-renderer.v1`, operação, revisão, hash da preparação,
atores/referentes, referências de fatos/efeitos, falas essenciais e pergunta final.
Matriz R-01–R-09, incluindo tarefa repetida/pedido a Mara e R-08 sobre wet.
A LLM retorna apenas `campaign-source-expression-v2`, hash do plano e dois slots
ordenados (`atmosphere`, `mara.reaction`), opcionais, <=240 caracteres cada.
O texto crítico, efeitos declarados e pergunta final não vêm da LLM.

`ComposedProjection` mantém spans exatos e autoria por segmento. Prefixo do locutor
e aspas acrescentados pela aplicação são segmentos da aplicação; só o conteúdo
do slot recebe a invocação da LLM. Normalização NFC e espaços preserva offsets
sobre o texto final. Contexto posterior conserva atribuição; memória/fatos canônicos
continuam derivados dos eventos preparados. `semantic_truth_assessed` fica false.

Replay devolve o texto persistido, sem nova chamada ou sorteio. A validação usa
plano retido e compilador registrado por versão, sem chamar o construtor editorial
atual. A integridade dos efeitos continua usando a verificação mecânica existente.
Manter implementações antigas ao introduzir futuras versões do renderizador.

## Verificação

269 testes distintos selecionados passam no estado final:

- 28 em `tests/test_campaign_expression_v2.py`: oito percursos/17 turnos, retomada,
  identidade/revisão/referências, proveniência e Unicode, cancelamento em três
  momentos, pedido/repetição, histórico atribuído e isolamento de sessão antiga.
- 10 em `tests/test_campaign_expression_persistence.py`: claims concorrentes,
  bloqueio de commit genérico, gate anterior ao RNG, provedor/entrega/SQLite,
  reinício, resume concorrente, encadeamento de falhas e adulteração de histórico.
- 25 de integração/storage/trajetórias v1, na mesma rodada de 61 testes
  (a versão inicial da suíte v2 nessa rodada tinha 26 testes; os dois adicionais
  passaram depois na rodada final de 28).
- 206 de regressão compartilhada e preparação de L84, incluindo transporte falso
  integral, nenhum acesso a chave/rede no preflight, gate fechado, drift de hashes
  adicionais e parada após a primeira proposta inválida.

XMLs em `eval-results/a1-v2-persistence-verified-2026-10-21.xml`,
`a1-v2-regression-2026-10-21.xml` e `a1-v2-boundary-final-2026-10-21.xml`.
Aviso preexistente de `python_multipart`. Falhas intermediárias ficaram registradas;
não são contabilizadas como testes aprovados. Corpus crítico ajustado por dois
falsos positivos dos guards existentes; nenhuma flexibilização dos guards v1.

## Limite comprovado: o texto livre ainda pode contradizer o plano

Observação offline prospectiva, 23 composições autoradas: 13 válidas aceitas;
9 de 10 inválidas aceitas; ação explícita de abrir porta rejeitada.
Provas congeladas em `evals/narrator/spikes/expression-v2-2026-10-21/`.
Não é amostra de respostas Luna nem medição estatística de estabilidade.

Exemplos inválidos ainda aceitos em slots: “As folhas já secaram por completo”,
“Fiz um juramento de silêncio à fundadora” e “Falta embrulhar as folhas antes de
terminarmos”. A composição garante presença do núcleo correto, mas um slot pode
contradizê-lo. Autoria marcada não elimina impacto da afirmação no jogador.
Não corrigimos isso por novas regex oportunistas nem restringimos silenciosamente
os slots a catálogo fechado. Alterar essa fronteira requer decisão de produto.

A1 experimental está implementada e verificada offline; fidelidade integral,
naturalidade, navegador, admissão do narrador, CAMP-24 e MVP não foram aprovados.
O efeito canônico não muda com um slot falso. A entrega anterior ao commit,
herdada, continua provisória se persistência falhar; redesenhar isso está fora de A1.

## L84 preparado, ainda sem inferência real

Avaliador e preflight próprios: `scripts/evaluate_hybrid_campaign_luna_l84_live.py`
e `scripts/preflight_hybrid_campaign_luna_l84.py`. L83 preservado fechado;
seus hashes históricos agora divergem dos pontos compartilhados e não devem
ser atualizados para viabilizar reexecução.

L84 guarda plano, antes/depois, resposta bruta quando disponível, resposta
estruturada, texto final, autoria, proveniência, uso e custo. O novo manifesto
conserva os 22 hashes esperados pela supervisora e adiciona 10 hashes de apoio
validados pelo avaliador. Nenhuma mudança no processo supervisor ou no leitor
de credenciais. Gates false/false até o despacho autorizado, chave disponível
e revalidação final. Nenhum request de lote foi enviado.

Preflight keyless: 17 turnos simulados, zero chamadas; máximo observado 8.779 bytes
por request sob limite de 20.000. Schema e prompt SHA256 no manifesto/preflight.
Teto conservador por bytes para 17 requests máximos: USD 0.0836672,
abaixo de USD 0.15; isso não comprova cobrança. Tarifas verificadas em 21/10:
USD 0.20 entrada e USD 1.20 saída por milhão de tokens, conforme
[documentação oficial](https://developers.openai.com/api/docs/models/gpt-5.6-luna).

Custo novo de inferência desta implementação/validação: **USD 0** (zero chamadas).
Sessão anterior 42a67e70... ficou com status idle obsoleto; PID 2152 ausente.
Supervisora reaberta a pedido já autorizado, mesma expiração 22/10/2026 00:00
Fortaleza, sessão fa6f0ca5-2cc1-4dd3-9821-34946243c0c7, PID observado 12548,
aguardando entrada protegida. Não usar status antigo como disponibilidade.

## Próximo passo

Receber a chave exclusivamente na janela protegida; conferir PID/status/expiração;
revalidar manifesto/preflight; executar L84 uma vez sob autorização contínua;
fechar gates, analisar conteúdo e relatar custo. Primeira falha técnica encerra;
avaliação qualitativa pode reprovar um lote tecnicamente completo. Sem retry,
fallback, agregação best-of ou admissão automática.

Sol high é adequado à continuidade da integração; Astra high à decisão final
sobre liberdade narrativa e risco residual. Nenhuma troca automática de modelo.
