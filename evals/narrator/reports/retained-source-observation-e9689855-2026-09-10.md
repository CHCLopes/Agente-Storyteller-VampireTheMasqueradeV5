# Observação B retida — Galeria — 10/09/2026

O lote `e9689855-aef3-4765-8213-704aaaeff4f0` terminou com **sucesso operacional**: duas respostas admitidas,
duas fontes persistidas e dois replays sem nova chamada. A primeira fonte foi
transportada integralmente para o segundo USER. A qualidade de progressão ficou
aquém do desejado: a segunda resposta repete o cenário sem novo acontecimento.

## Evidência técnica

| Item | Observar | Aguardar |
|---|---:|---:|
| HTTP / término | 200 / stop | 200 / stop |
| Tokens de entrada reportados | 842 | 1851 |
| Tokens de saída reportados | 162 | 165 |
| Caracteres de n | 616 | 657 |
| Schema, rota, commit e replay | válidos | válidos |

Groq observado, modelo reportado `qwen/qwen3.8-27b`, alvo fixo do manifesto.
Total reportado: 2693 tokens de entrada e 327 de saída, 3020 no total. Reasoning
não informado (`null`); custo indisponível. Nenhum desses valores é custo zero.

Primeiro despacho 61,055 s após início do lote; intervalo entre despachos 61,188 s.
Duração observada das invocações: 1,637 s e 1,997 s. O código congelado configura
prazo de 60 s após espera/conferência; o prazo absoluto não está persistido.
Não houve skip, retry, reparo, diagnóstico, fallback ou chamada de controle.

A segunda cápsula contém o envelope anterior completo, e o segundo USER contém
a projeção anterior completa. Ambas as fontes ultrapassam 600 caracteres e
permanecem integrais; q fica separada. A fonte continua `source_only/not_assessed`.
Isso demonstra transporte e recuperação nesta amostra, sem confirmar a narrativa
como verdade canônica ou comprovar confiabilidade de campanha longa.

O wrapper terminou `finished/0` após executar seu verificador offline sobre cópia.
Esta revisão conferiu também o hash do banco selado, sem abri-lo com SQLite;
metadados, fingerprints e hashes dos artefatos originais permaneceram intactos.

## Leitura narrativa autorada

A revisão independente concorda com estes achados, separados dos gates:

- Continuidade: galeria, obras, iluminação, ventilação e odores mantidos;
  nenhuma contradição material inequívoca identificada.
- Agência e escopo: nenhuma ação, escolha, fala ou emoção nova imposta ao jogador;
  sem novos NPCs, troca de local ou resolução mecânica inventada.
- Incerteza: “O ar parece parado” passa a “O ar permanece parado”, um endurecimento
  lexical leve sem novo suporte. Não foi demonstrada falha de gate por isso.
- Progressão: a segunda resposta redescreve quase todos os detalhes da primeira.
  O tempo passa, mas não surge um acontecimento relevante ou nova abertura para agir.
- Pergunta: “O que você faz agora?” é aberta e válida, porém idêntica nos dois turnos.
- Estilo: ambientação sensorial legível; expressões sobre não exigir interação ou
  alteração expõem a contenção do prompt e reforçam a cena parada.

## Próxima hipótese registrada

Preparar `narrative-source-progress-v1`, preservando o SYSTEM anterior e adicionando
um parágrafo para desenvolver um elemento existente em acontecimento observável.
Mesmos gates, cenário, ações, modelo e parâmetros; novo lote isolado, sem reexecutar
ou importar este resultado como controle. [Plano com critérios anteriores ao envio](../../../plan/feature-progressing-source-observation-1.md).
O SYSTEM é o fator configurado alterado; IDs/tempos e o segundo USER dependente
variam entre lotes. A comparação será descritiva, sem alegação A/B causal.

## Textos observados

### Turno 1: observe

> A luz difusa da galeria desliza sobre as superfícies expostas, criando sombras suaves que se alongam pelo piso. O silêncio predomina, quebrado apenas pelo zumbido baixo e constante dos sistemas de ventilação. As obras permanecem em suas posições, intactas, refletindo a imobilidade do espaço. O ar parece parado, carregado com o cheiro sutil de tinta fresca e madeira tratada. Nada se move, exceto a leve vibração das lâmpadas fluorescentes. A atmosfera convida à contemplação, mantendo uma distância respeitosa entre o observador e os objetos à sua frente, sem exigir interação física ou alteração do cenário atual.

> O que você faz agora?

### Turno 2: wait

> O tempo parece diluir-se na galeria. O zumbido dos ventiladores mantém seu ritmo constante, quase hipnótico, enquanto a luz difusa continua a deslizar pelas superfícies expostas. As sombras no piso se alongam de forma imperceptível, marcando a passagem dos segundos sem alterar a imobilidade das obras. O ar permanece parado, carregado com o cheiro sutil de tinta fresca e madeira tratada. Nenhuma nova vibração ou som rompe o silêncio; a atmosfera mantém a mesma distância respeitosa, convidando à contemplação silenciosa. O espaço ao redor não exige interação, apenas observa a quietude compartilhada entre o observador e os objetos intactos à sua frente.

> O que você faz agora?

[Artefatos, auditoria, hashes e limites em JSON](retained-source-observation-e9689855-2026-09-10.json).
Nenhuma aprovação de CAP-001, runtime ou qualidade geral deriva deste lote.
