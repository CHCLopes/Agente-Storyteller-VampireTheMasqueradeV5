# Observação inline Qwen — desenho prévio em 07/09/2026

Status: autorizada pela autonomia contínua; preparação técnica em andamento. Nenhuma chamada deste perfil foi feita nesta preparação.

## Pergunta e alcance

O lote GPT-OSS 6876955e foi estruturalmente aceito, mas mostrou resumo de 32 palavras, junção sem espaço, mistura de modalidades e pergunta que pressupõe a existência do motor. A projeção foi literal e correta. Uma observação do outro candidato já declarado, Qwen 3.8 27B sem raciocínio, examinará se essas dimensões são preservadas sob o mesmo pedido de dois campos. A hipótese pode falhar. Não é uma busca repetida por uma resposta aprovada.

Perfil fixo: `qwen-3.8-27b-groq-free-synthetic-nonthink`; alvo `inline-evidence-qwen-3.8-27b-groq-free-synthetic-nonthink`, Groq direta, `qwen/qwen3.8-27b`, `reasoning_effort:none`. Manifesto e adaptador existentes não serão alterados. Somente fixture sintética, sem dados de campanha.

## Pedido e comparação

Usar literalmente o SYSTEM record-inline-evidence-v1, USER archive-vibration, source_units n0/n1, schema InlineEvidenceProposal, projeção sem separador, temperatura 0,65 e teto 3.072 do lote 687. O dossiê JSON associado congela o corpo inteiro e seus hashes. Diferenças no corpo: model, reasoning_effort e omissão de include_reasoning, parâmetro que o adaptador aplica somente ao GPT-OSS. Não igualar perfis de raciocínio diferentes nem apresentar a comparação histórica como A/B causal. Nenhum controle será chamado ou importado para os contadores do novo lote.

O caso permanece o arquivo municipal: lanterna vermelha ilumina mesa/pastas; vibração perto da porta fechada sugere que talvez exista motor funcionando do outro lado. Nenhum ajuste na fonte, nos critérios ou no prompt é permitido após a observação.

## Critérios prévios

1. Transporte/proveniência: exatamente Groq e qwen/qwen3.8-27b reportado. Modelos alternativos, ausentes ou identidades incoerentes não passam. Strict schema e projeção são critérios estruturais separados da revisão textual.
2. Revisar integralmente todos os segmentos e questões contra ambas as unidades. Conferir participante, cor atribuída à lanterna, iluminação, posição da vibração e hipótese de motor. Preservar incerteza na redação e separar afirmações estabelecidas e sugeridas; IDs/rótulos não provam entailment.
3. Perguntas não podem transformar a existência ou posição hipotética do motor em fato definido. Uma questão fundamentada sobre a vibração é possível; a ausência de questão pode ser legítima. Não atribuir ações ou estados internos ao jogador/NPCs.
4. Resumo em português brasileiro com até 25 palavras, contadas por unidades Unicode com apóstrofos/hífens internos; espaços e pontuação de junção devem vir do modelo. Projeção não repara o texto.
5. Omissão fundamentada é permitida. Se o modelo omitir a dimensão de incerteza, registrar como não informativa para essa dimensão, sem afirmar sucesso nela. Não exigir reprodução integral da fonte nem premiar omissão como fidelidade demonstrada.
6. Resultado estrutural e revisão semântica serão registrados separadamente. Uma resposta integralmente satisfatória vale apenas para este caso; não prova taxa, generalização, oito campos, admissão de atores, runtime ou CAP-001.

## Orçamento, parada e credencial

Uma única chamada ao vivo, após espera local mínima de 60 segundos; deadline de 60 segundos contado após preflight/espera; teto total 3.072 tokens, uma repetição. Sem diagnóstico, geração narrativa, retry, fallback, juiz LLM, novo caso ou preenchimento de amostra. Encerrar em qualquer resultado, inclusive disponibilidade/HTTP400/schema inválido/recusa semântica. Não repetir este mesmo pedido Qwen para elevar taxa. Preservar summary/JSONL originais e revisar fora deles.

Executar somente depois de preflight, testes focados, revisão independente e integração sem chave. Nova chave apenas no prompt local protegido; nenhuma leitura de .env ou recuperação de chave anterior. Free Plan é contexto do candidato existente, não promessa de cota ou custo zero da conta. Não comprar, fazer upgrade, habilitar cobrança ou trocar de rota.

## Fontes oficiais verificadas em 07/09/2026

- [Modelos Groq](https://console.groq.com/docs/models): Qwen3.8-27B em Preview, destinado à avaliação.
- [Structured Outputs](https://console.groq.com/docs/structured-outputs): Qwen com strict:true.
- [Reasoning](https://console.groq.com/docs/reasoning): modo none disponível para Qwen3.8.
- [Rate Limits](https://console.groq.com/docs/rate-limits): modelo consta na tabela Free Plan; limites efetivos dependem da organização.

Não foi feita consulta autenticada ao catálogo nem inferência para verificar disponibilidade nesta preparação. Um erro operacional será analisado como tal. O próximo passo após o lote será definido pela evidência, sem promover produto nem reabrir silenciosamente a linha de ajustes SYSTEM/esforço na opening.
