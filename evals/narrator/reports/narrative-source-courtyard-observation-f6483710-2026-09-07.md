# Pátio — passagem de fonte observada, segunda resposta recusada

O lote `f6483710-ae78-4024-a2c5-25bbcd5e9cf0` terminou com **duas chamadas HTTP200, dois schemas válidos e uma única proposta admitida como fonte experimental**. A primeira fonte entrou integralmente, com sua atribuição e avaliação, no USER seguinte. A segunda resposta excedeu o limite de150 palavras e foi recusada. Exit1, sem skip/retry/fallback; lote encerrado.

## Observações medidas

| Turno | Palavras n | Palavras q | Total | Política | Projeção |
|---|---:|---:|---:|---|---|
| observe |100|4|104|Admitida|Fonte integral criada|
| wait |151|4|155|scene_narrative_too_long|Não criada|

As duas rotas Groq/qwen/qwen3.8-27b foram verificadas, finish_reason stop. A espera inicial observada foi60.467s e o intervalo entre inícios foi60.220s, respeitando60s. Uso informado:2.062 tokens de entrada+400 de saída=2.462. Raciocínio permanece null, não zero; custo indisponível.

A auditoria reconstruiu os artefatos com o código e o preflight congelados. O objeto source_projection do primeiro registro é exatamente a única fonte no segundo USER, incluindo n integral, identidades, hashes, audiência, binding e assessment. q não integra essa fonte. Isso demonstra uma passagem de fonte real e delimitada; **não demonstra uma cadeia de dois turnos admitidos**. Não houve gravação em campanha ou memória de produto.

## Leitura autorada, separada dos gates

O segundo texto conserva colunas de pedra lisa, madeira marcada no teto, ladrilhos, poeira/madeira velha, frestas, sombras imóveis e a gota fora de vista. Há continuidade referencial clara, com pouca progressão concreta: predominam repetição e intensificação retórica. A gota passa a soar de tempos em tempos, extensão temporal pequena e compatível.

Não identificamos nova ação, decisão, fala, pensamento ou emoção imposta ao jogador, deslocamento ou NPC novo. “O que você faz?” é uma pergunta aberta adequada nos dois turnos. O português é compreensível, mas a segunda resposta é redundante e artificial, incluindo “absoluto, absoluto”, “suspense suspenso” e repetição quase integral do encerramento.

Não identificamos contradição inequívoca entre os turnos. Há tensão retórica entre silêncio absoluto/imobilidade de cada partícula e a gota que cai; essa leitura não transforma a prosa em afirmação canônica. A rejeição de comprimento é correta:155 palavras no texto ao jogador, conforme a contagem usada pelo gate. Não ajustar limite nem aparar a resposta para admiti-la.

## Encerramento e próximo incremento

Lifecycle finished em `2026-09-08T00:17:39.8680031Z`, exit1; wrapper descarta a chave antes desse estado. A janela NoExit PID4080 pode permanecer aberta; não foi comprovado o término do processo. Não relançar. Summary/JSONL e prepared_* ficaram intactos; revisão autorada permanece neste relatório, sem alterar not_performed/approval:null no bruto. A verificação prova consistência local, não autenticação criptográfica do provedor.

Avançar a ponte **local e optativa** de fonte/turno/persistência/recuperação com FakeLLMAdapter e SQLite temporário, conforme o desenho revisado, preservando o ramo legado e sem ativar default/saves/CAP. A passagem real observada informa esse incremento; sua prova local de três turnos será separada de confiabilidade ao vivo. Nenhum novo prompt, lote, repetição ou chave está agendado.

[Registro completo, outputs, hashes e prova](narrative-source-courtyard-observation-f6483710-2026-09-07.json). [Preparação congelada](narrative-source-courtyard-preparation-2026-09-07.json). [Desenho de integração](../reviews/narrative-source-integration-design-2026-09-07.md).
