# Próxima hipótese — intervalos no campo derivado

Data: 07/09/2026. Status: **proposta documental concreta; sem modo executável, registro de prompt ou nova chamada autorizada**.

A [análise b129ceaa](record-evidence-budget-observation-b129ceaa-2026-09-07.md) mostrou JSON/schema concluídos e cinco suportes fora dos campos. O validador implementa corretamente a instrução existente. A proposta testa uma formulação mais explícita do mesmo contrato; não corrige artefatos nem pressupõe defeito local.

## Delta exato a avaliar

Preservar o SYSTEM record-evidence-v1 integralmente e inserir, logo depois da regra b/e, somente este parágrafo:

> Os índices b/e pertencem sempre ao valor de records apontado por p, nunca ao texto de source_units. Os start/end de uma unidade de origem não são índices do registro. Para cada suporte, confira 0 <= b < e <= comprimento da string de records[p]; a contagem recomeça em zero em cada campo. Não reutilize o comprimento da narrativa como fim de campos derivados. Exemplo apenas de coordenadas, sem acrescentar esses fatos à resposta: se a fonte for “Há uma rua vazia à frente.” e records.l for “rua vazia”, o suporte para /l usa [0,9), não [7,16). Os IDs de origem continuam em s e identificam unidades completas. Esse exemplo não muda os campos obrigatórios nem permite agrupar modalidades distintas.

Nome proposto: `record-evidence-target-spans-v1`. O [corpo completo para revisão](record-evidence-target-spans-draft-b129ceaa-2026-09-07.json) contém a reconstrução sintética, sem headers, credencial ou resposta. Não é runner nem request enviado.

A comparação local confirmou somente `/messages/0/content` diferente. USER, narrativa, source_units, schema, temperatura, reasoning, provider e teto 1.536 permanecem iguais ao lote b129ceaa. Hash canônico anterior `90a5fffba8a57247439dfa1f9cfba202aeb2dff0182ba9e2235f95673ea6429f`; proposto `8138c098ec49cdc768e7c5d9fe19cc952001939f1c54af11bdb1241762526a09`. Hash do SYSTEM proposto `fdba32bb00dd20144ec5553d72635c3a2388fee9c4621486f3bddd6f3b1721cb`.

O exemplo de coordenadas foi conferido localmente: “rua vazia” tem nove pontos de código; está em [7,16) na fonte demonstrativa e [0,9) no valor derivado. É exemplo didático novo, não gabarito do caso nem conteúdo para incorporar à narrativa. O SYSTEM conserva sua menção histórica a 768 para que este delta tenha apenas o esclarecimento dos índices; isso continua limitação conhecida do desenho.

## Desenho proposto para uma decisão

Uma chamada total, somente a mesma abertura bb98, Groq direta / openai/gpt-oss-120b, raciocínio low, include_reasoning false, saída estruturada sem streaming, temperatura 0,65 e teto de 1.536. Espera inicial conservadora de 60 segundos e deadline de 60 após a espera, um único terminal. Mesmos metadados limitados do observador de orçamento. Sem Mara, narrativa nova, diagnósticos, retry, fallback ou aumento posterior de teto.

Em qualquer resultado, encerrar. IDs/ranges corretos apenas permitem continuar os checks existentes; não provam fidelidade ou cobertura. Repetição histórica com SYSTEM diferente não será A/B causal.

Antes de eventual chamada, preparar um runner exclusivo e contraprovas que fixem esse novo hash, preservem USER/schema/parâmetros e rejeitem replay CAP. Os scripts do diagnóstico encerrado permanecem congelados e recusam este corpo diferente. Não ampliar o allowlist deles para reaproveitar o lote.

## Critérios de leitura

- Se os intervalos estiverem todos dentro dos campos, registrar viabilidade estrutural apenas desta realização; aplicar schema final e admissão existentes sem reparos.
- Revisar separadamente cada afirmação, sua origem, modalidade e pressuposições de perguntas. “Quem ou o que está observando?” continua falha de certeza mesmo com índices válidos.
- Se persistir uso de offsets da fonte, registrar que o esclarecimento não bastou nesta realização. Não substituir por offsets calculados e não repetir automaticamente.
- Qualquer falha de provedor/rota/schema continua falha observada; a cobertura semântica não vira zero quando a etapa não é alcançada.

Não se propõe aqui trocar o contrato por citações, segmentar afirmações no backend, reduzir critérios, aumentar orçamento ou integrar ao jogo. Essas seriam decisões separadas. Esta proposta também não resolve por si a certeza indevida da pendência; ela conserva esse problema como observação independente.

## Limite atual

O [desenho anterior](record-evidence-budget-hypothesis-2c1cafde-2026-09-07.md) autorizou uma chamada e determinou encerramento após qualquer resultado. Essa chamada já terminou. Esta proposta não se autoriza sozinha: alterar o SYSTEM congelado e fazer outra inferência requer a decisão específica sobre este novo desenho e entrada protegida da chave. A análise, o corpo revisável e o próximo passo local já estão preparados, sem solicitar avaliação semântica intermediária do usuário.
