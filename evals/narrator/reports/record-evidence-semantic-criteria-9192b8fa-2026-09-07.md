# Critérios semânticos prévios à observação medium

Registrados antes de qualquer chamada medium, sob autorização contínua. Esta matriz orienta revisão autônoma de todos os registros; não altera o prompt, o USER, o corpus ou os validadores. Os exemplos abaixo são independentes da opening e não são enviados ao modelo. Não há novo juiz LLM nem uma resposta literal obrigatória.

| Critério | Fonte independente | Exemplo compatível | Contraexemplo a recusar |
|---|---|---|---|
| Existência sugerida não pode virar pressuposição | “Talvez o sino tenha tocado.” | “O sino chegou a tocar?” | “Quem tocou o sino?” pressupõe o toque. |
| Resumo misto exige suporte e modalidade por afirmação | “A vela está acesa; a sombra talvez seja de um animal.” | Citar a vela com established e a hipótese completa com suggested. | Citar a frase inteira com established ou suggested; ambos apagam uma distinção. |
| Relação sensorial não prova presença física da causa | “Há cheiro de café no corredor.” | “O corredor tem cheiro de café.” | “Há café derramado no corredor.” |
| Convite livre ao jogador | Narrador convida uma ação, sem ação já executada. | “O que você quer fazer agora?” | “O que faço agora?” muda o ponto de vista; “Como você esconde o objeto?” pressupõe uma decisão. |
| Citação é referência literal, não fidelidade | Fonte sugere um acontecimento; registro afirma que ocorreu. | Citação única com registro que mantém a sugestão. | Citação exata de uma afirmação mais forte: o match pode passar e o conteúdo deve falhar. |

Na opening, revisar cada afirmação explícita e pressuposta em o/l/s/p/f/t/r/q e cada suporte. Preservar origem, agente, objeto, negação, relação sensorial e certeza. Questões podem manter a existência em aberto ou ser omitidas se dispensáveis; não exigir uma pergunta pronta. Listas vazias corretas não são falhas de cobertura. Um convite livre sem fato não precisa suporte inventado.

Uma citação completa não prova que cada afirmação está sustentada. Se o resumo mistura fatos estabelecidos e hipótese, exigir citações que preservem o modalizador e distingam as modalidades. Várias afirmações da mesma modalidade podem ser avaliadas em conjunto quando a citação as inclui integralmente; não impor uma granularidade lexical arbitrária. Excesso de certeza na redação não é reparado pelo rótulo do suporte.

A revisão classifica cada ponto como compatível, falha material, ressalva ou não avaliável. Só considerar esta abertura semanticamente satisfatória se não houver falha material em registros, pressuposições ou cobertura/modalidade. Ressalvas devem ser descritas, sem convertê-las retroativamente em um novo gate. Schema, envelope e admissão continuam sendo resultados independentes.

Depois da única chamada, encerrar este teste em qualquer resultado. Se os critérios falharem, encerrar esta linha de variações de prompt/esforço na opening; não aumentar automaticamente para high, elevar tokens ou acrescentar instruções. Se passarem, registrar apenas êxito neste caso e preparar casos independentes antes de qualquer generalização. Erro ou truncamento significa semântica não avaliável, sem retry. Próximas hipóteses podem ser desenhadas sob a autorização contínua, preservando os limites de produto e credenciais.
