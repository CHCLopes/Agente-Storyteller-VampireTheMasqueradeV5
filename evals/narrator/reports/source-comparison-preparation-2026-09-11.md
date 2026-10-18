# Preparação do comparativo Qwen/GPT-OSS — 11/09/2026

Preparação offline concluída, revisada e verificada: **106 testes distintos
nas duas suítes finais**, sem falhas, erros ou skips. Nenhuma inferência real foi
executada nesta preparação. A única dependência imediata é inserir a chave no
lançador protegido; a credencial não está disponível no processo desta tarefa.

O [protocolo prévio](../source_comparison_protocol_v1.md) e o
[corpus](../source_comparison_v1.json) definem duas cenas novas, três turnos de
conversa/espera/continuidade por candidato e quatro blocos Q/Oficina, G/Oficina,
G/Arquivo, Q/Arquivo. Máximo de 12 chamadas, 768 tokens de saída por chamada,
60 segundos de espera inicial, intervalo global de 60 segundos no lote e prazo
de 60 segundos por chamada.
Nenhum retry, reparo, diagnóstico ou fallback. Resultado pode ser inconclusivo
ou não qualificar nenhum candidato; integridade técnica não aprova a narrativa.

## Implementação e verificação

Novos evaluate_source_comparison.py/run_groq_source_comparison.ps1 mantêm alvos
e reasoning explícitos, schema/corpo aprovados, setup→produtor→retenção→executor,
quatro bancos separados, histórico próprio de até duas fontes e replays sem
produção/chamada. O orçamento é consumido no hook HTTP do lote. A auditoria
reconstrói P/K/H e rejeita adulterações, inclusive observação de resposta sem HTTP
e cronologia incompatível entre evidência, envio e prazo. Uso ausente fica desconhecido.
O launcher verifica os arquivos congelados e entrega a credencial só ao filho live.

| Rodada preservada | Passaram | Falhas | Erros | Skips |
|------------------|----------|--------|-------|-------|
| evaluator-round1 | 38 | 1 | 0 | 0 |
| evaluator-regression | 2 | 1 | 0 | 0 |
| evaluator-chronology-regression | 2 | 0 | 0 | 0 |
| evaluator-final | 48 | 0 | 0 | 0 |
| launcher-round1 | 42 | 16 | 0 | 0 |
| launcher-final | 58 | 0 | 0 | 0 |

Rodadas repetidas não entram novamente na contagem de casos distintos. Falhas
iniciais e contraprovas ficam preservadas; as correções não alteraram o runtime.
No launcher, os 16 casos iniciais que não criavam resumo usavam caminhos de 268
caracteres na fixture Windows; pastas temporárias foram encurtadas. Os achados
de revisão e correções específicas do evaluator constam no JSON e nas evidências.
Permanece o aviso preexistente de python_multipart, sem falha de teste associada.

Revisão documental independente encerrada. Revisão técnica confirmou as correções
dos achados, os limites e a ausência de mudanças nos componentes anteriores.
Os 28 arquivos do preflight source-player e os artefatos históricos conferem por hash.
Checkpoint durável: `eval-results/checkpoints/source-comparison-preparation-20260911`; JSON deste relatório
lista cada origem, cópia e SHA256. Preflight real sem chave encerrou com código 0,
lote somente-preflight `9d5cb11e-75bf-4676-acea-6b95b4f149e1`; não usar esse UUID como lote live.

## Execução pronta

Em PowerShell 7, executar uma vez:

```powershell
pwsh -NoProfile -File "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_source_comparison.ps1"
```

O script faz novo preflight e solicita a chave por Read-Host -AsSecureString. Não
colocar chave em comando/chat/arquivo. Manter a janela aberta até o resumo final.
O launcher cria um novo lote, preserva artefatos e executa o verificador offline
sem chave. Depois analisar a matriz completa e propostas recusadas separadamente,
com revisão narrativa independente pelos critérios congelados. Se houver falha
global, encerrar o lote e analisar; não executar novamente para obter aprovação.

Este recorte não demonstra campanha longa, investigação, combate, interface ou
segredos autorados. Não altera default, transporte, save, CAP-001 ou decisão de
modelo. Falha de filesystem/setup/seal pode deixar evidência parcial não certificada;
isso exige diagnóstico local, sem retomar chamadas do lote como retry.
