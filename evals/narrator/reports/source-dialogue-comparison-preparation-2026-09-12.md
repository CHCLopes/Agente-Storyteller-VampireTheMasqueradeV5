# Comparação com diálogo: preparação concluída, inferência pendente

O consumidor e o lançador de source-dialogue-comparison-v1 foram preparados e
verificados offline. O novo experimento compara Qwen3.8-27b/none e GPT-OSS120b/low
via Groq com o SYSTEM dialogue-v1 existente. Seu fundamento é a lacuna de resposta
de NPC observada na sessão49 e o diálogo parcial observado depois em81/87.
Não se criou outro prompt nem se reclassificou a observação87 após sua correção.

Os mesmos casos Oficina/Nina e Arquivo/Rui, ordem e critérios do comparativo61b83
foram mantidos. A seção de revisão semântica/elegibilidade é idêntica em LF, SHA
f21711cb210a3461c9cbed6b027a4de2e1b7e10397c7ee14e81fe8fc5ae1582c.
Nenhuma resposta, pontuação, sessão, fonte ou banco antigo será importado.
É comparação de configurações e trajetórias próprias; não isola efeito causal
do SYSTEM ou do modelo e não demonstra campanha longa.

## Recorte fechado

Quatro blocos novos, três turnos cada: Qwen/Oficina, GPT-OSS/Oficina,
GPT-OSS/Arquivo, Qwen/Arquivo. Máximo12 HTTP,768 tokens de completion por chamada
e9216 no total, temperature0.65. Sessenta segundos iniciais e entre inícios HTTP,
com relógio global. A espera antecede P; o deadline único de60s abrange P/K/H6.
Uma recusa interrompe sua cadeia; erro operacional global encerra o restante.
Nenhum retry, reparo, fallback ou preenchimento posterior dos skips.

O consumidor próprio usa as APIs B de setup, produção declarativa, retenção,
execução e replay. Os USER posteriores contêm somente n integral de commits do
próprio bloco, até duas fontes, sem q ou briefing narrativo. O verificador
reconstrói requests, metadados, cápsulas, auditoria, tempos e bancos em cópias,
preservando os arquivos originais. O launcher separa preflight, filho live com
SecureString e verificação posterior sem chave. Nada foi ativado na interface.

## Verificação e revisão

Foram aprovados 107 casos distintos da preparação, reconciliados por
identidade nos XMLs; reexecuções não são contadas como casos novos.
São 31 casos do consumidor e76 do launcher. Os XMLs preservam as
etapas, e a última execução de cada identidade é aprovada.
A revisão confirmou duas correções restritas à auditoria: preservar um commit
recuperado após cancelamento, com parada global/exit130, e reconhecer timeout
sem HTTP quando a preparação esgota o prazo, preservando sua evidência local.
O runtime e o deadline original não foram relaxados. Vermelhos e ajustes
intermediários estão arquivados. Eventos extras com hashes recalculados já eram
recusados; não houve alteração adicional por essa hipótese.

Preflight nativo final 2b399092-bd38-42b9-839a-5a3919908950: exit0/preflight_only_completed,
SHA65b51c6042f39b396945f01c97b9947c3ae701aed38e4f84f1abfebdf0375096. Nenhuma credencial fornecida, chamada ao provedor,
banco ou diretório de inferência criado. A preparação congelada inclui os
arquivos de construção, corpus, protocolo, SYSTEM, schema e configurações;
os corpos futuros com narrativa gerada não são apresentados como já existentes.

O catálogo público foi conferido em12/09/2026: os IDs e o suporte a strict estão
listados, assim como os esforços de raciocínio escolhidos. Fontes oficiais:
[modelos](https://console.groq.com/docs/models),
[saída estruturada](https://console.groq.com/docs/structured-outputs) e
[reasoning](https://console.groq.com/docs/reasoning). Essa leitura não verifica
credencial, quota ou disponibilidade futura da conta.

## Preservação e próximo passo

Checkpoint próprio: eval-results/checkpoints/source-dialogue-comparison-preparation-20260912/manifest.json,
98 cópias verificadas, SHA59a899b352456dc47f36c7cdc7da70f866f26c6508b0de8f3b511ce0f4b03e3b. As68 cópias da correção,
69 da observação87 e97 da preparação anterior mantiveram hashes; o core e os
avaliadores/lançadores históricos continuam intactos durante esta preparação.

Próximo passo: uma execução pelo launcher scripts/run_groq_source_dialogue_comparison.ps1,
com entrada protegida de chave. Depois, fechar a auditoria e a avaliação narrativa
independente conforme a rubrica congelada. Ausência de candidato qualificado é
resultado válido; não repetir para forçar vencedor. Eventual recomendação não
muda default, ativa campanha ou aprova CAP-001. Não pedir novamente a aceitação
do recorte B já autorizada pelo usuário.
