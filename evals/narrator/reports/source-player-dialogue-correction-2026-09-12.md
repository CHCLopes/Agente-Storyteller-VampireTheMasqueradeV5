# Conversa com Mara — correção da entrada em 12/09/2026

A fala informada pelo usuário, `Mara, me fale sobre este lugar`, revelou uma
falha de apresentação: o campo parecia aceitar conversa natural, mas enviava o
texto cru a uma gramática que exige `Digo a Mara: "..."`. A correção oferece
**Conversar com Mara** e **Aguardar**. No primeiro modo, o jogador escreve a fala
normalmente e clica em **Enviar fala**; no segundo, clica em **Confirmar espera**.

## Observação encerrada

A sessão6486b938-4667-418d-8bc0-57b913c104b7 iniciou e encerrou stopped/exit0,
sem força. Backend: calls_started0 e admission_unavailable; records.jsonl ausente.
Auditoria somente leitura: zero P/K/H, attempts, turnos e eventos, banco íntegro
e sem mudança dos hashes do SQLite/WAL/SHM. Os45 inputs e50 entradas do binding
foram conferidos. Isso não constitui validação da credencial no Groq nem avaliação
de narrativa: nenhuma chamada foi iniciada pelo guard local.

O texto exato vem do relato posterior do usuário, não do banco ou journal.
A contraprova reproduziu sua recusa antes de P/RNG/HTTP. Ela demonstra uma causa
suficiente, mas o status original não guardou o subtipo de admissão que permitiria
atribuir retrospectivamente todos os detalhes. Os artefatos originais permanecem
fechados, com58 cópias no checkpoint de observação e suas fontes históricas.

## Implementação e verificação

A interface compõe o envelope existente mantendo a fala literal, inclusive espaços,
acentos e aspas compatíveis. Antes de criar ID ou enviar, valida conteúdo vazio,
Unicode incompatível, NUL, conflito entre delimitadores e limite de500 pontos de
código do envelope. Erro fica local, conserva o rascunho e não encerra a sessão.
O rascunho bruto pertence apenas à view do modo diálogo para evitar o descarte
silencioso de texto longo pelo reducer. Troca de modo e reconexão conservam a fala;
somente a escolha explícita de nova ação a limpa. Reload continua sem restauração
do rascunho. Aguardar exige escolha e confirmação, sem envio ao apenas alternar.

Alterados SourceTrialView, a prop Mara em SourcePlayerTrial e seus testes.
Adicionado test_source_local_groq_speech_control.py. Parser, reducer, hook,
runner, launcher, prompts, regras e componentes do jogo padrão conservaram hashes.
Nenhum arquivo runtime novo ficou fora do freeze de45 inputs.

| Prova | Resultado |
|---|---|
| Reprodução anterior à correção | Uma falha causal: socket recebia fala crua |
| UI, primeira seleção |50 aprovados; lint encontrou regex de controles |
| UI, seleção final afetada |25 aprovados após correção; lint/TypeScript/build exit0 |
| UI reconciliada |51 casos distintos;26 não repetidos; não somar execuções |
| Backend com HTTP simulado |2 aprovados: fala crua recusada; envelope confirma um turno |
| Consulta desse turno |Mesmo resultado; zero HTTP adicional e zero RNG |
| Preflight conjunto final |exit0;45 hashes; sem chave, banco, listener ou inferência |

Preflight a8d9edb2-9ab1-4e68-981d-34ddd3c0aae2, SHA
`72a434982f44fa56965112887a8e1d458a0d279266bfcd911103d6d177c27beb`.
Revisão independente encerrada sem achado material pendente. O teste final da UI
usou DOM/socket simulado; não houve nova inspeção visual por pixels nem narrativa
real após a correção. As contraprovas, falhas iniciais e limites foram preservados.

Checkpoint da correção: `eval-results/checkpoints/source-player-dialogue-correction-20260912/manifest.json`, 108 cópias, SHA
`5e289f429062c8039dcc6cbb12aaafd6556cf475898bc1a11b313431d15ac10c`. As152 cópias da preparação anterior e58 da observação mantiveram
hashes. O checkout original continua limpo;39 modificações rastreadas preexistentes
do b008 preservadas. Nenhum commit/push/merge.

## Próximo uso

O usuário já executou o recorte apresentado. Corrigir esta entrada não exige uma
nova aceitação do mesmo recorte; qualidade narrativa, default e CAP-001 permanecem
sem aprovação. A próxima execução será uma sessão nova, sem reenviar a antiga.

Na janela PowerShell7 que detém o SecureString:

```powershell
& 'C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_source_local_trial.ps1' -Credential $StorytellerGroqKey
```

Se a variável não existir, omitir `-Credential $StorytellerGroqKey` para o prompt
protegido. O agente não lê a chave de outra janela nem usa .env. Abrir o novo
endereço mostrado pelo launcher, conectar e aguardar a liberação do envio.
Escolher Conversar com Mara e escrever a frase original normalmente.

Conservados Qwen/Groq, cena sintética Galeria/Mara, SYSTEM progress-v1,0,65,
768 tokens por chamada, até4 tentativas e intervalo mínimo60s. Sem retry/fallback.
Uma negativa operacional pode encerrar antes de quatro respostas. Manter a janela
aberta durante o uso; Enter encerra os próprios serviços. A única dependência
atual é esse lançamento protegido e a participação do jogador.
