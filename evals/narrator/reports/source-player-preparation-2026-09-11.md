# Preparação da observação com ação do jogador — 11/09/2026

Preparação concluída e revisada, com **50 casos distintos aprovados** e preflight
real sem chave aprovado. Nenhuma inferência realizada. O próximo passo é executar
o lote na janela PowerShell que já possui a credencial do Groq.

## Hipótese e percurso

Cena sintética nova na Galeria com Mara presente, objetivo declarado na preparação
e na pergunta escolhida pela fixture. O segundo turno espera a reação de Mara.
Ambos passam pelo produtor real, após reserva P; preparação K e narrativa H ficam
ligadas ao pedido original. O briefing autorado permanece separado das fontes.
Não houve nova paráfrase de SYSTEM ou repetição de lote histórico.

Qwen/Groq explícito, candidate qwen-3.8-27b-groq-free-synthetic-nonthink,
SYSTEM narrative-source-progress-v1 preservado, reasoning none, temperatura0.65.
Máximo2 chamadas,768 tokens cada/1536 totais, espera inicial60s, intervalo60s e
deadline60s por chamada. Primeira falha encerra a cadeia; sem diagnóstico,
retry, reparo ou fallback. Avaliar reação concreta, continuidade, agência e
incerteza separadamente dos gates técnicos. Não é A/B causal.

## Verificação e revisão

- Executor: **43 passed em178,60s**, primeira rodada, HTTPX MockTransport,
  bancos temporários, conftest e dotenv desativado.
- Launcher: **7 cenários distintos**. A primeira rodada teve5pass/2fail;
  o stub precisava criar seu diretório pai e usar contadores no escopo correto
  do PowerShell isolado. Corrigida somente fixture; os dois casos afetados
  passaram em11,68s. Logs originais preservados, launcher inalterado.
- Parser PowerShell sem erros. Testes do launcher em PowerShell7 cobrem variável
  do processo, entrada SecureString, ausência de chave, PreflightOnly, limpeza
  e supressão da saída sensível sintética do filho.
- Revisão antes do freeze corrigiu captura de P/K no cancelamento depois da
  persistência e reforçou vínculo ao recibo declarado e diagnósticos fechados.
  Contraprovas vedam reprodução, recibo trocado e adulteração coordenada de hashes.
- Reuso do observador, captura e fechamento SQLite existentes, sem alterar
  scripts históricos, gates ou prompt. A verificação usa cópia descartável
  e confirma hashes dos artefatos originais ao terminar.

Preflight real `70034cd6-b60c-4565-a8de-2fce835315da`: saída0,
`preflight_only_completed`,28 arquivos de implementação conferidos. Nenhuma
chave solicitada ou chamada realizada. Hash SHA256 do preflight:
`587d44eb4459a09d64e2bf6a5670bb94bd279ee1a68ef27f21ba5549b32db62c`.
Esse batch é somente preflight encerrado; o launcher criará UUID novo para live.

Evidências e hashes completos no [JSON](source-player-preparation-2026-09-11.json).
Um aviso preexistente de python_multipart em cada rodada; nenhuma falha aberta.

## Próxima ação concreta

Na janela que já tem `GROQ_API_KEY`, executar:

```powershell
& 'C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_source_player_probe.ps1' -UseProcessCredential
```

O switch usa somente a variável dessa janela, sem exibi-la e preservando-a após
o processo. Se a chave não estiver nessa variável, executar o mesmo script sem
o switch: ele solicita entrada protegida. Nenhum valor deve ser enviado pelo chat.
O processo desta sessão não herdou a credencial, inclusive na verificação de
presença sob execução autorizada; não houve inspeção de outra janela ou .env.

Após término, conferir lifecycle, summary, JSONL, banco e horários; revisar as duas
respostas contra os critérios autorados e continuar conforme o resultado.
Timestamps são gravados e checados quanto ao fuso; o verificador não certifica
o intervalo a partir deles. Pacing/hook impõem a cadência, e a cronologia live
deve ser examinada no fechamento do lote.

UI/default/save seguem preservados. Nenhuma evidência desta preparação aprova
qualidade narrativa, campanha completa ou CAP-001. O contrato de acesso do futuro
transporte permanece no [plano separado](../../../plan/feature-narrative-source-transport-1.md).
