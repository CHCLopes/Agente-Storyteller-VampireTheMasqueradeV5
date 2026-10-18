# Observação interativa B — sessão 49fffca2

Data: 2026-09-12. Sessão: `source-groq-trial.49fffca2-3d4e-4e6c-9dba-ed813c86d985`.

A execução terminou com integridade técnica aprovada e falha de responsividade conversacional. As quatro estruturas geradas foram preservadas e recuperadas corretamente, mas as quatro iniciativas de conversa não receberam de Mara uma resposta útil, recusa compreensível ou condição concreta. Esse resultado não aprova experiência narrativa, modelo definitivo, piloto, campanha completa, default ou CAP-001.

## Resultado técnico

Foram registrados quatro HTTP 200 com finish_reason=stop, quatro P, quatro K, quatro H, doze tentativas concluídas, quatro turnos e quatro eventos player_action_declared. As falas literais conferem entre USER, preparação e turno. n/q conferem entre as estruturas retornadas e sua apresentação persistida. As cápsulas contêm aliases Mara e preparação declared_action. Não houve memórias derivadas.

O alvo e os parâmetros permaneceram Groq/qwen3.8-27b, temperatura 0,65, reasoning none e teto de 768 tokens por chamada. Os quatro corpos de requisição, SYSTEM, schema e identidades conferem com a preparação. Os 45 inputs e as 50 entradas do binding permaneceram íntegros.

O uso reportado foi 9.264 tokens de entrada, 750 de saída e 10.014 totais. Cada saída respeitou 768 e a soma ficou abaixo do orçamento de 3.072. Os intervalos entre inícios HTTP foram 1076,325654s, 120,834625s e 111,685396s; todas as respostas terminaram antes do deadline. O launcher e o backend encerraram stopped/exit0, sem força, com motivo budget_completed e calls_started=4. Root confirmou ausência das portas e do PID do backend após o encerramento.

O banco encerrado ainda tinha WAL de 74.192 bytes. Para não alterar o original nem ignorar dados confirmados, DB/WAL/SHM foram copiados para TEMP e conferidos por hash. A consulta usou somente a cópia com mode=ro, query_only e BEGIN/ROLLBACK, sem immutable. O quick_check da visão incluindo WAL retornou ok; os três arquivos originais permaneceram inalterados. O contador local e os metadados capturados não são uma consulta independente ao faturamento do provedor. O instante inicial do contador monotônico não foi persistido; sua guarda permanece comprovada pela fonte congelada.

## Resultado narrativo

| Turno | Resultado observado |
| --- | --- |
|1|Mara observa o local sem responder à pergunta sobre ele. q pergunta como o jogador reage à resposta de Mara, embora n diga que a resposta ainda não foi dada.|
|2|A insistência recebe um gesto com a bolsa e a promessa de fala, sem explicação útil. q volta a pressupor uma resposta inexistente.|
|3|Há avanço espacial para uma área mais escura, portanto a cena não ficou inteiramente imóvel. A conversa solicitada continua sem resposta. A fala convidando ao deslocamento é tratada como movimento já executado do jogador.|
|4|A impaciência declarada pelo jogador recebe outro gesto e uma decisão anunciada para depois. q é aberta e coerente, mas a contribuição conversacional continua adiada.|

A atmosfera é legível e vários detalhes mantêm continuidade. Água, tochas, pedra e a bolsa do NPC não são, por si, acréscimos proibidos: o preparo não fechava esses detalhes. A falha está em usá-los repetidamente para adiar a interação, sem resposta, recusa, desconhecimento ou condição que o jogador possa aproveitar.

No turno 3, “Vamos andando” pode ser entendido coloquialmente como intenção de deslocamento. A ressalva de agência decorre do contrato efetivamente retido: Digo a Mara: seguido de fala entre aspas, no recorte de diálogo/espera. Sob esse contrato, uma sugestão falada não confirma automaticamente o movimento do jogador. Mara poderia iniciar um movimento próprio ou indicar um caminho, deixando a adesão em aberto. Isso não implica que o jogador nunca mencionou andar. No turno 4, a impaciência já havia sido expressa pelo jogador; não foi uma emoção inventada pelo modelo.

## Interpretação e próximo passo

O SYSTEM enfatiza acontecimentos ambientais e desenvolve a espera, mas não explicita o que conta como contribuição útil de um NPC a uma pergunta direta. É plausível que essa ênfase e as fontes sucessivas de silêncio favoreçam adiamento atmosférico. A sessão não contém controle ou variante pareada: não separa efeito de prompt, contexto, amostragem e modelo e não estabelece causalidade.

O próximo trabalho é a preparação de um diagnóstico experimental com três casos independentes, em arquivos novos. Ele observará resposta útil de Mara, consequência da insistência, q ancorada no que n efetivamente narra e preservação da agência sob o envelope de fala. Os gates permanecem intactos. Nenhuma inferência desse novo diagnóstico integra este relatório, e resultados futuros não reclassificarão retroativamente esta execução.

## Evidência preservada

Checkpoint: `eval-results/checkpoints/source-player-interactive-observation-49fffca2-20260912/manifest.json`.

SHA256: `b4e3a5da047d42bc9bf9fc586dac63f4c673c3bd832390a80534076889042366`.

São 66 cópias e 1.786.581 bytes: 45 fontes provenientes exclusivamente do checkpoint da correção, 9 artefatos brutos desta execução, 11 provas e 1 âncora. Todas as cópias e os originais selecionados foram revalidados. A âncora da correção é `5e289f429062c8039dcc6cbb12aaafd6556cf475898bc1a11b313431d15ac10c`.

A auditoria final tem SHA `e25c033340a42a8d295ba4fc43b896fc86fb405e7a91522e373589bb8654b8f2`. O parecer narrativo independente tem SHA `d272bd5a751ad4ac5242e00aa7c005607f67b7ad8ed65353216cebdd541ada5f`. Ambos estão copiados no checkpoint. O snapshot parcial anterior continua preservado com SHA `c3755b023f81773401d20c8a04de3de8dac447fc6d95f76cd62afa176accff4a`.

A primeira comparação do helper de auditoria continha um hash de âncora digitado incorretamente e o literal declared em lugar de declared_action. A saída inicial foi preservada; audit-final.json corrige somente essas expectativas do auditor. Nenhum artefato bruto, fonte histórica, prompt ou resposta foi reparado. A observação parcial, este fechamento e qualquer correção posterior permanecem evidências distintas.
