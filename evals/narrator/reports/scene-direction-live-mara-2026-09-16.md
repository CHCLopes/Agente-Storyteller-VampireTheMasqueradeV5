# Observação ao vivo do catálogo mínimo de Mara — 16/09/2026

## Escopo

Uma única ação foi executada no jogo completo atual, em banco isolado e cena
controlada: `Mara, me fale sobre este lugar.`. A Galeria continha somente Mara,
uma descrição curta de estantes/índices e o fio aberto de compreender a história
do lugar. O alvo explícito foi Qwen 3.8 27B via Groq. Não houve retry, fallback,
rolagem ou segunda ação narrativa.

Antes da chamada, a auditoria de falhas foi ampliada para persistir evidência
estrutural fechada de `scene_player_agency_violation`. O texto rejeitado e nomes
livres continuam ausentes do registro. Passaram 53 testes focados e 213 testes do
pipeline transacional/WebSocket.

## Resultado observado

O turno foi concluído e persistido uma vez. O provedor reportou 1.602 tokens de
entrada, 278 de saída e 1.880 no total. O modelo efetivo foi
`qwen/qwen3.8-27b`; a chamada durou aproximadamente 1,47 segundo.

O resolvedor escolheu `mara.place_history`, com efeito
`mara.answers.place_context`. A orientação mínima continha o núcleo protetor,
observador e reservado; os objetivos de avaliar o visitante e proteger o índice;
as reações de resposta cautelosa, pista parcial e ajuda condicional; e avanço por
ajuda. O modelo não recebeu fala pronta nem sequência roteirizada.

A resposta realizou esses sinais sem copiá-los: Mara descreveu o local como um
arquivo do que a cidade tenta esquecer, ofereceu contexto parcial e condicionou
informação adicional à explicação do visitante. A pergunta final devolveu agência
ao jogador. A proposta preservou Mara e Galeria, não revelou a identidade da
fundadora e não atribuiu ação, emoção ou passado ao jogador.

O modelo criou livremente gesto, voz, metáforas e atmosfera. `Pólvora` apareceu
como detalhe sensorial sem apoio explícito na cena inicial. Não contradiz o estado
e não foi promovida a fato separado, mas delimita uma questão futura de produto:
quanto detalhe ambiental novo deve ser admitido como cor narrativa. Esta amostra
não justifica ampliar o catálogo nem proibir autoria ambiental.

## Integridade transacional

- operação: `mara-live-45423af4-892f-4962-b75d-840d720c71f3`;
- turno: `d60e9130-fd52-5200-bbad-ebac2c41156f`, número 1;
- status: `completed`, narrativa completa e nenhum erro;
- hash do resultado/payload: `e453bc64a4bd20876d0b0301e64f10403298a9943634714f1250d3e59e52a42e`;
- o fato reservado `world.scene.beat_resolution` preservou opção, efeito e
  orientações; os fatos públicos vieram da proposta admitida;
- nenhum recibo mecânico foi produzido, como esperado para diálogo sem rolagem.

## Limites e conclusão

Esta observação confirma que o catálogo mínimo foi ativado no caminho padrão e
pode orientar uma resposta autoral coerente sem impor prosa. É uma única amostra
Qwen/Groq e não escolhe modelo padrão, não valida toda a campanha, não aprova
qualidade narrativa global, runtime comercial ou CAP-001.

