# Continuidade dos guardas no uso teste — 09/09/2026

A cena narrada já introduzia guardas e o usuário manifestou que essa adição
enriquece a experiência. A correção conserva essa improvisação: a projeção atual
agora registra Príncipe, Xerife e Guardas. A entrada não foi removida, reencenada
nem transformada em prisão mecânica consumada.

## Evidência e limites do diagnóstico

Após a retomada, a campanha avançou de cinco para nove turnos. A leitura local
encontrou 18 tentativas, nove turnos e zero pendentes. As tentativas 16–18 foram
recusadas por `scene_npc_roster_changed_without_event`; a tentativa 14 foi recusada
por `scene_secret_disclosed`. As estruturas rejeitadas não foram retidas, portanto
não é possível reconstruir seus nomes ou afirmar falso positivo histórico.

O turno 9 (`4ef4a158-a2cb-5070-8761-1130b890f64b`) e o fato público admitido
`96b03412-83cf-50f8-8879-c5a873da7635` já registravam a chegada dos guardas.
As duas projeções de cena, porém, continham apenas Príncipe e Xerife. Essa é uma
inconsistência confirmada, independente das estruturas perdidas das recusas.
O usuário confirmou resolvidos os problemas anteriores de interface.

## Correção e verificação

- A comparação de elenco considera membros, ignorando ordem e capitalização.
  Adições e remoções reais continuam sujeitas ao contrato de evento existente.
- H6 pede o elenco completo, inclusive grupos, e seu registro quando entradas ou
  saídas acontecem na narrativa. O pacote USER e o contrato de atores não mudaram.
- Recusas de elenco/sigilo persistem apenas diagnóstico estrutural fechado em
  metadata local; não armazenam texto rejeitado nem segredos. As mensagens de
  erro para o jogador agora distinguem essas duas situações.
- Reparo autorado, revisado independentemente e testado em cópia: somente
  `context.scene.npcs_present` e `player_sheet.scene.npcs_present` receberam
  Guardas. Metadata registra base pública, autorização e IDs de origem.
- Aplicação com o servidor escritor parado, backup SQLite consistente e CAS
  turno 9/revisão 10. Resultado: turno 9/revisão 11. Narrativas, tentativas, eventos,
  fatos, memórias, relações e demais campos foram preservados; hashes dos ledgers
  históricos conferidos antes e depois. Nenhuma ação, RNG ou chamada LLM.
- **284 testes distintos passaram**: 219 integrados, 53 diagnósticos/sigilo e 13
  de elenco, com um teste sobreposto. São 55 testes novos. Zero falhas; um aviso
  preexistente de `python_multipart`. Diff check passou.
- O carregador real recuperou as duas projeções corrigidas e nove narrativas no
  dry-run. Uma proposta sintética com o mesmo elenco e somente `observation`
  passou sem exigir nova entrada. Todas as linhas das tabelas ficaram iguais;
  os bytes físicos desse SQLite mudaram durante a inicialização do carregador.

Isso verifica o defeito local e o reparo, sem provar qualidade narrativa geral ou
melhoria ao vivo do prompt. A direção B permanece fora do jogo atual.

## Retomada preservada

Servidor antigo raiz PID17040/filho18208 parado após conferência de propriedade;
porta livre confirmada antes do reparo. A janela antiga PID4848 pode permanecer
com texto histórico. Preparação offline da nova retomada passou sem chamadas.

Run: `04e0a3ce-8112-4b58-8919-ea8f7e681221`; janela protegida PID23100.
Estado verificado: **ready**. Não duplicar essa janela.
Status: `C:\Users\skate\AppData\Local\Temp\storyteller-manual-game-04e0a3ce-8112-4b58-8919-ea8f7e681221\status.json`.
Banco: `C:\Users\skate\AppData\Local\Temp\storyteller-manual-game-4cfd5337-1c84-487e-bd77-8fe8e4d78a29\storyteller.sqlite3`.
Sessão: `local.4cfd5337-1c84-487e-bd77-8fe8e4d78a29`.
URL: `http://127.0.0.1:8000/play/local.4cfd5337-1c84-487e-bd77-8fe8e4d78a29`.

Próximo passo: Usuário continua a mesma campanha; analisar novo feedback sem reenviar ações automaticamente ou avançar a fase B.

Alvo explícito Groq `qwen/qwen3.8-27b`, contexto768, dotenv desativado,
mesmo perfil operacional do teste. Credencial inserida pelo usuário no prompt
protegido; nenhuma credencial anterior recuperada. Servidor novo PID30516,
propriedade do listener conferida. Os três probes novos (texto, structured e
streaming) passaram. Página da campanha respondeu HTTP200 com entrada frontend.
A aba CUA anterior deixou de estar disponível; reabertura no Codex enfileirada.
Não foi realizada nova inspeção visual nem enviada ação. As evidências completas
e hashes constam no JSON homônimo.
