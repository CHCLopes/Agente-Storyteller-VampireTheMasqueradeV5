# Preparação da observação B com fonte retida — 10/09/2026

Preparação concluída. A entrada completa do coordenador pode ser observada por
um novo lote sintético de dois turnos dependentes. **Nenhuma chamada ao provedor
ocorreu nesta preparação**; o resultado ao vivo permanece desconhecido.

## Entrega e verificação

- `scripts/evaluate_retained_source.py`: cenário Galeria, retenção antes da H6,
  corpo conferido antes do envio, primeira fonte integral no segundo contexto,
  registro de admissão/falha e replay após recriar a persistência, sem gateway.
- `scripts/run_groq_retained_source_probe.ps1`: preflight antes da chave,
  ambiente isolado dos filhos, chave em prompt protegido, encerramento do filho
  próprio em falha e verificação offline dos artefatos.
- **72 testes distintos passaram** numa rodada integrada final: 36 do avaliador e 36 do
  wrapper; zero falhas, erros ou skips; 220.110s pelo JUnit.
  Hashes estáveis antes/depois. Somente o aviso preexistente de python_multipart.
- As 575 regressões do coordenador constam no [relatório anterior](narrative-source-coordinator-2026-09-10.md).
  Os hashes da aplicação continuam iguais; essa rodada não foi repetida nem somada como teste novo.
- Preflight real `-PreflightOnly`: saída 0, lote `b5acc987-5489-4f8f-a2da-63a4878d9f1d`,
  lifecycle `preflight_only_completed`; sem chave e sem diretório live.
  Esse lote é somente prova offline: o lançador cria outro lote ao executar.

O verificador abre apenas uma cópia descartável do SQLite selado. Confere
integridade referencial, origem/cápsula, cadeia, request e pareamento de resultado,
provenance, uso e custo disponíveis no audit. Campos não persistidos integralmente
pela aplicação são validados pelo contrato/observador; não se afirma autenticação
externa ou verdade semântica. JSONL duplicado ou com número não finito é recusado.

Um cancelamento posterior ao commit preserva o turno já gravado, recuperado por
replay sem H6. A execução continua cancelada, com código 130, e o segundo turno é
pulado. Isso não constitui retry nem garantia de execução única após crash.

As 12 falhas da primeira rodada do avaliador foram corrigidas e verificadas;
envolviam fechamento de conexões no Windows e evidência após bloqueio de eco da
credencial. A revisão também corrigiu pareamento de audit, JSONL, etapa delivery,
referências órfãs e cancelamento após commit. Evidências intermediárias permanecem
preservadas; revisão encerrada sem achado material aberto.

## Observação delimitada pronta

Alvo do manifesto existente: `qwen-3.8-27b-groq-free-synthetic-nonthink`, Groq
direto, modelo `qwen/qwen3.8-27b`, reasoning none. Mesmo prompt narrative-source-v1.
Até 2 chamadas, 768 tokens cada, total de 1536, temperatura 0,65; espera inicial de 60 s, intervalo
mínimo de 60 s e prazo de 60 s por chamada. A primeira falha interrompe a cadeia.
Sem diagnósticos, reparo, retry, fallback ou baseline. Um novo lote não é A/B causal.

```powershell
pwsh -NoProfile -File "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_retained_source_probe.ps1"
```

A chave deve ser inserida somente no `Read-Host -AsSecureString` desse processo.
Não recuperar chave de .env, processo do jogo ou variáveis existentes. O lançador
retira a variável privada após uso/finalização. Encerramento forçado pelo sistema
operacional não garante execução de finally.

Default, UI e save real não foram alterados. CAP-001, qualidade narrativa geral,
progressão de campanha e ativação no produto continuam sem aprovação derivada
deste teste. O próximo passo é a observação protegida e a análise de seus artefatos.

Provas e hashes completos: [registro estruturado](retained-source-probe-preparation-2026-09-10.json).
JUnit, saída e inventário final: `C:\Users\skate\AppData\Local\Temp\storyteller-retained-probe-20260910`.
Preflight congelado: `C:\Users\skate\AppData\Local\Temp\storyteller-retained-source-window-b5acc987-5489-4f8f-a2da-63a4878d9f1d\preflight.json`.

## Janela preparada para a credencial

Em `2026-09-10T23:51:34.3098765Z`, a janela própria PID `15836`
estava em `awaiting_secure_credential`, lote `e9689855-aef3-4765-8213-704aaaeff4f0`.
A entrada protegida da chave é a dependência humana. Não abrir outra janela
sem conferir esse lifecycle: `C:\Users\skate\AppData\Local\Temp\storyteller-retained-source-window-e9689855-aef3-4765-8213-704aaaeff4f0\lifecycle.json`.
Esse registro é uma fotografia do lançamento, não um resultado ao vivo.
