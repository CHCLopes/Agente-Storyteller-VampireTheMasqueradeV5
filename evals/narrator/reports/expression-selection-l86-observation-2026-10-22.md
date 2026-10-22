# L86 — comparação real A2 e seleção determinística, 22/10/2026

A2 completou 17 pares com Luna low e baseline determinística. Nenhuma divergência
de estado, efeito, plano ou replay foi observada nesta matriz. O modelo selecionou
somente IDs elegíveis; a aplicação compôs todo o texto. A avaliação editorial não
demonstrou vantagem consistente da seleção por LLM: oito escolhas acrescentaram
uma frase de posição já expressa na consequência. A2 é viável como fronteira
fechada neste experimento, mas o ganho de usar modelo para essas escolhas não foi
demonstrado. Não admitir narrador, MVP ou criatividade geral por este resultado.

## Autorização, execução e custo

Após o bloqueio inicial de revisão automática, usuário respondeu “Prossiga” à
pergunta explícita sobre os 17 payloads no destino OpenAI, gpt-5.6-luna low,
teto USD 0.15 pelo lote. Revalidados hash do arquivo aprovado, 32 hashes de fontes,
gates fechados e sessão protegida vigente. Request único aceito e executado pela
supervisora, sem extração da credencial, retry, fallback ou troca de alvo.

| Medida | Observação |
|---|---:|
| Chamadas ao provedor | 17 |
| Pares completados | 17 |
| Tokens de entrada reportados | 6.448 |
| Tokens de saída reportados | 859 |
| Custo estimado por tokens | USD 0.0023204 |
| Chamadas sem uso reportado | 0 |
| Maior request | 2.215 bytes |
| Limite efetivo de saída/request | 256 tokens |
| Replay pós-execução verificado | 34 apresentações |

Estimativa não confirma cobrança. Mesmas tarifas 0.20/1.20 USD por milhão,
verificadas em 22/10; a data 29/09 impressa pelo helper de custo é metadado
histórico. Baseline não chamou modelo. Custos de processamento local não medidos.
Modelo/rota foram registrados como solicitado/reported/observed, conforme contrato;
não se infere um snapshot de pesos além da identidade reportada pela API.

Lote: eval-results/hybrid-campaign-luna-l86-282a3849-3c62-4390-8809-e9bb95a2385c.
Gates false/false após término, trava mantida. Supervisora voltou idle, exit code0;
expira 23/10/2026 00:00 Fortaleza. Nenhum lote novo preparado ou despachado.

## Garantias conferidas no resultado real

- 17 corpos reais reconstruídos coincidem com o arquivo de payloads aprovado;
  também coincidem tamanho e SHA-256 com os requests registrados.
- Para cada par, consequência crítica e efeitos exigidos coincidem; os oito
  desfechos foram atingidos igualmente nos dois modos.
- Resposta bruta coincide com a escolha persistida. Todo segmento é da aplicação,
  com offsets/texto/referências retidos e evidência da escolha separada da autoria.
- Banco SQLite real do lote foi reaberto e as 34 apresentações foram recuperadas
  byte a byte. Durante a auditoria, RNG, builder atual e renderer atual foram
  substituídos por falhas deliberadas: nenhum foi chamado. Nenhum gateway foi
  fornecido ao replay; não houve inferência adicional.
- JSONL original permaneceu intacto. O banco retido é exclusivamente sintético;
  não houve migração ou alteração no checkout original/produto/default.

Verificação registrada em eval-results/expression-selection-l86-observation-review-2026-10-22.json.
Esta é evidência mais forte de persistência/replay neste lote que os lotes A1
anteriores, cujos bancos eram temporários. Não implica prova de navegador/UI,
que não fizeram parte deste recorte.

## Comparação editorial

| Escolha | Contagem |
|---|---:|
| Fala original | 5 |
| Fala alternativa autorada | 12 |
| Sem frase adicional de posição | 9 |
| Com frase adicional de posição | 8 |
| Parágrafo único | 15 |
| Separação em parágrafos | 2 |
| Texto exatamente igual à baseline | 2 |

As outras 15 apresentações diferem da baseline; diferença não equivale a melhora.
As 12 alternativas de fala são paráfrases disponíveis no catálogo. O mérito de
sua redação pertence à curadoria; a escolha do modelo precisa demonstrar ganho
separado. As duas escolhas de parágrafo podem melhorar a leitura, mas a mesma
formatação também pode ser feita deterministicamente sem invocação.

As oito frases de posição repetem informação da consequência: bancada/Arquivo ou
superfície seca/Galeria. Estão fundamentadas e são permitidas pelo contrato, mas
acrescentam redundância. A escolha pela LLM não cumpriu de forma consistente a
instrução editorial de evitar repetição. Não houve falha de admissibilidade ou
parada técnica; o lote tecnicamente completo recebe avaliação editorial
insuficiente para justificar adoção do seletor por modelo.

Exemplo CAMP-EVAL-07/2: a consequência já diz que o registro foi colocado na
superfície seca da Galeria; a opção de atmosfera repete essa posição depois da
fala de Mara. Isso aumenta texto sem nova informação. A baseline já entrega a
mesma consequência, desfecho e fala essencial sem a frase adicional.

A composição completa somou 4.242 caracteres na baseline e 4.587 na seleção Luna
(incluindo perguntas). Não usar esses totais como tokens, custo de hardware ou
medida objetiva de naturalidade. A avaliação é delimitada a 17 pares desta matriz;
não mede campanha longa, capacidade de modelos locais ou preferência de jogadores.

## Conclusão e continuidade

O experimento A2 autorizado está concluído: contrato/isolamento/persistência/
retomada e comparação real verificados. Recomenda-se conservar a baseline
sem modelo como referência neste recorte autorado. Não abrir outro lote equivalente
apenas para procurar vantagem editorial. A seleção Luna não se justifica aqui
pelos resultados observados.

O componente reaproveitável para a ferramenta original é a separação entre
resultado preparado, alternativas elegíveis, validação e proveniência. Copiar o
catálogo inteiro ou retirar a LLM de toda a experiência não foi autorizado nem
é consequência deste resultado. Em uma cena aberta, a função criativa exige outro
contrato e outras evidências; A2 reduz o espaço de escolha em troca da previsibilidade.

A verdade/elegibilidade dos textos do catálogo continua obrigação editorial.
A contraprova anterior, em que o autor introduziu uma frase falsa, permanece válida.
IDs fechados e hashes não provam a verdade da frase. Não declarar problema geral
de fidelidade resolvido.

Não há nova ação humana necessária para concluir L86. Integração no produto,
adaptação do original ou expansão de autoria são decisões futuras, com proposta
e escopo próprios. Nenhum desses passos foi realizado neste lote.

## Integridade

- records.jsonl SHA-256: 792b7df18cc297804102501714d9f100314cb91a5d5b14776d674d3860368e1c.
- sessions.sqlite3 SHA-256 após auditoria: 55bf751b08b9b609f8fd34d9d123185b49f46f2728ba98994e9a6f08fd7020f8.
- Payloads aprovados SHA-256: 3dc437e9b2cc112ecccceb92324d6780c9c99c9fbf295fb9d309af8b4d7ab038.
- Manifesto no despacho SHA-256: 2cfa7c6abc459548f90e1f16b6dda7e0f296a84bb868be068b1e2c1340c97cde.
  O manifesto final tem outro hash porque os gates foram fechados; hashes de fontes
  continuam congelados, sem reescrever a evidência da execução.

## Textos efetivamente apresentados nos 17 pares

Os textos abaixo vêm dos registros reais, sem edição de redação. Todas as frases
são autoradas pela aplicação; a LLM escolheu os IDs registrados.

### CAMP-EVAL-08 — turno 1 — R-02

Entrada: Quem é a fundadora?

Escolha Luna: `{"atmosphere": "position", "layout": "inline", "utterance": "variant"}`

Baseline determinística:

> O registro continua na bancada baixa do Arquivo, sob o risco da infiltração. A pergunta não altera a posição nem o estado do documento. Mara responde: “Não vou divulgar a identidade da fundadora.”
> 
> O que você faz agora?

Apresentação após seleção Luna:

> O registro continua na bancada baixa do Arquivo, sob o risco da infiltração. A pergunta não altera a posição nem o estado do documento. Mara diz: “Não vou revelar quem é a fundadora.” O registro está na bancada baixa do Arquivo.
> 
> O que você faz agora?

### CAMP-EVAL-08 — turno 2 — R-01

Entrada: Qual é a tarefa?

Escolha Luna: `{"atmosphere": "none", "layout": "paragraph", "utterance": "variant"}`

Baseline determinística:

> O registro permanece na bancada baixa do Arquivo, seco, ameaçado pela infiltração. A posição do documento não mudou. Mara responde: “A tarefa é preservar o registro da água. Você pode levar o documento até a superfície seca da Galeria.”
> 
> O que você faz agora?

Apresentação após seleção Luna:

> O registro permanece na bancada baixa do Arquivo, seco, ameaçado pela infiltração. A posição do documento não mudou.
> 
> Mara diz: “A tarefa é proteger o registro da água. Você pode levá-lo até a superfície seca da Galeria.”
> 
> O que você faz agora?

### CAMP-EVAL-08 — turno 3 — R-05

Entrada: Retiro o registro

Escolha Luna: `{"atmosphere": "none", "layout": "inline", "utterance": "variant"}`

Baseline determinística:

> Você retira o registro da bancada baixa do Arquivo e o protege na superfície seca da Galeria. O documento foi salvo intacto, fora do alcance da água. O resgate está concluído. Mara diz: “O registro está preservado.”

Apresentação após seleção Luna:

> Você retira o registro da bancada baixa do Arquivo e o protege na superfície seca da Galeria. O documento foi salvo intacto, fora do alcance da água. O resgate está concluído. Mara diz: “O registro foi salvo intacto.”

### CAMP-EVAL-01 — turno 1 — R-01

Entrada: Como posso ajudar?

Escolha Luna: `{"atmosphere": "none", "layout": "inline", "utterance": "variant"}`

Baseline determinística:

> O registro permanece na bancada baixa do Arquivo, seco, ameaçado pela infiltração. A posição do documento não mudou. Mara responde: “A tarefa é preservar o registro da água. Você pode levar o documento até a superfície seca da Galeria.”
> 
> O que você faz agora?

Apresentação após seleção Luna:

> O registro permanece na bancada baixa do Arquivo, seco, ameaçado pela infiltração. A posição do documento não mudou. Mara diz: “A tarefa é proteger o registro da água. Você pode levá-lo até a superfície seca da Galeria.”
> 
> O que você faz agora?

### CAMP-EVAL-01 — turno 2 — R-05

Entrada: Retiro o registro

Escolha Luna: `{"atmosphere": "none", "layout": "inline", "utterance": "variant"}`

Baseline determinística:

> Você retira o registro da bancada baixa do Arquivo e o protege na superfície seca da Galeria. O documento foi salvo intacto, fora do alcance da água. O resgate está concluído. Mara diz: “O registro está preservado.”

Apresentação após seleção Luna:

> Você retira o registro da bancada baixa do Arquivo e o protege na superfície seca da Galeria. O documento foi salvo intacto, fora do alcance da água. O resgate está concluído. Mara diz: “O registro foi salvo intacto.”

### CAMP-EVAL-02 — turno 1 — R-03

Entrada: Aguardo

Escolha Luna: `{"atmosphere": "position", "layout": "inline", "utterance": "original"}`

Baseline determinística:

> A água pinga da infiltração e se aproxima do registro sobre a bancada baixa do Arquivo. O documento permanece seco e intacto; nenhuma folha foi movida. Mara avisa: “A água está chegando perto do registro.”
> 
> O que você faz agora?

Apresentação após seleção Luna:

> A água pinga da infiltração e se aproxima do registro sobre a bancada baixa do Arquivo. O documento permanece seco e intacto; nenhuma folha foi movida. Mara avisa: “A água está chegando perto do registro.” O registro está na bancada baixa do Arquivo.
> 
> O que você faz agora?

### CAMP-EVAL-02 — turno 2 — R-03B

Entrada: Espero

Escolha Luna: `{"atmosphere": "none", "layout": "inline", "utterance": "original"}`

Baseline determinística:

> A água da infiltração atinge o registro na bancada baixa do Arquivo. As páginas ficam molhadas e parte da tinta se espalha. Ainda há trechos legíveis; o documento continua na bancada. Mara diz: “A água molhou as páginas.”
> 
> O que você faz agora?

Apresentação após seleção Luna:

> A água da infiltração atinge o registro na bancada baixa do Arquivo. As páginas ficam molhadas e parte da tinta se espalha. Ainda há trechos legíveis; o documento continua na bancada. Mara diz: “A água molhou as páginas.”
> 
> O que você faz agora?

### CAMP-EVAL-02 — turno 3 — R-01

Entrada: O que precisamos fazer?

Escolha Luna: `{"atmosphere": "none", "layout": "inline", "utterance": "variant"}`

Baseline determinística:

> O registro permanece na bancada baixa do Arquivo, molhado, com trechos ainda legíveis. A posição do documento não mudou. Mara responde: “A tarefa é preservar o registro da água. Você pode levar o documento até a superfície seca da Galeria.”
> 
> O que você faz agora?

Apresentação após seleção Luna:

> O registro permanece na bancada baixa do Arquivo, molhado, com trechos ainda legíveis. A posição do documento não mudou. Mara diz: “A tarefa é proteger o registro da água. Você pode levá-lo até a superfície seca da Galeria.”
> 
> O que você faz agora?

### CAMP-EVAL-02 — turno 4 — R-06

Entrada: Retiro o registro

Escolha Luna: `{"atmosphere": "position", "layout": "inline", "utterance": "variant"}`

Baseline determinística:

> Você retira o registro molhado da bancada baixa e o coloca na superfície seca da Galeria. Apenas a parte ainda legível foi salva. O dano anterior permanece e as páginas continuam molhadas; o resgate parcial está concluído. Mara diz: “O que ainda dava para ler está preservado.”

Apresentação após seleção Luna:

> Você retira o registro molhado da bancada baixa e o coloca na superfície seca da Galeria. Apenas a parte ainda legível foi salva. O dano anterior permanece e as páginas continuam molhadas; o resgate parcial está concluído. Mara diz: “Só a parte ainda legível foi preservada.” O registro está na superfície seca da Galeria.

### CAMP-EVAL-03 — turno 1 — R-03

Entrada: Aguardo

Escolha Luna: `{"atmosphere": "position", "layout": "inline", "utterance": "original"}`

Baseline determinística:

> A água pinga da infiltração e se aproxima do registro sobre a bancada baixa do Arquivo. O documento permanece seco e intacto; nenhuma folha foi movida. Mara avisa: “A água está chegando perto do registro.”
> 
> O que você faz agora?

Apresentação após seleção Luna:

> A água pinga da infiltração e se aproxima do registro sobre a bancada baixa do Arquivo. O documento permanece seco e intacto; nenhuma folha foi movida. Mara avisa: “A água está chegando perto do registro.” O registro está na bancada baixa do Arquivo.
> 
> O que você faz agora?

### CAMP-EVAL-03 — turno 2 — R-03B

Entrada: Espero

Escolha Luna: `{"atmosphere": "none", "layout": "inline", "utterance": "variant"}`

Baseline determinística:

> A água da infiltração atinge o registro na bancada baixa do Arquivo. As páginas ficam molhadas e parte da tinta se espalha. Ainda há trechos legíveis; o documento continua na bancada. Mara diz: “A água molhou as páginas.”
> 
> O que você faz agora?

Apresentação após seleção Luna:

> A água da infiltração atinge o registro na bancada baixa do Arquivo. As páginas ficam molhadas e parte da tinta se espalha. Ainda há trechos legíveis; o documento continua na bancada. Mara diz: “As páginas ficaram molhadas.”
> 
> O que você faz agora?

### CAMP-EVAL-03 — turno 3 — R-04

Entrada: Aguardo

Escolha Luna: `{"atmosphere": "position", "layout": "inline", "utterance": "variant"}`

Baseline determinística:

> A água continua caindo sobre o registro na bancada baixa do Arquivo. O texto se torna irrecuperável e o documento está perdido. As folhas permanecem na bancada, sem conteúdo legível para recuperar. Mara diz: “O conteúdo se perdeu.”

Apresentação após seleção Luna:

> A água continua caindo sobre o registro na bancada baixa do Arquivo. O texto se torna irrecuperável e o documento está perdido. As folhas permanecem na bancada, sem conteúdo legível para recuperar. Mara diz: “O conteúdo do registro se tornou irrecuperável.” O registro está na bancada baixa do Arquivo.

### CAMP-EVAL-04 — turno 1 — R-09

Entrada: Desisto

Escolha Luna: `{"atmosphere": "none", "layout": "inline", "utterance": "original"}`

Baseline determinística:

> A tentativa termina com a desistência declarada. O registro permanece na bancada baixa do Arquivo, seco, ainda ameaçado pela infiltração. O documento continua no mesmo lugar, sem ter sido resgatado. Mara reconhece a desistência: “Entendido. Não haverá ajuda no resgate.”

Apresentação após seleção Luna:

> A tentativa termina com a desistência declarada. O registro permanece na bancada baixa do Arquivo, seco, ainda ameaçado pela infiltração. O documento continua no mesmo lugar, sem ter sido resgatado. Mara reconhece a desistência: “Entendido. Não haverá ajuda no resgate.”

### CAMP-EVAL-05 — turno 1 — R-05

Entrada: Levo o registro até a superfície seca

Escolha Luna: `{"atmosphere": "none", "layout": "inline", "utterance": "variant"}`

Baseline determinística:

> Você retira o registro da bancada baixa do Arquivo e o protege na superfície seca da Galeria. O documento foi salvo intacto, fora do alcance da água. O resgate está concluído. Mara diz: “O registro está preservado.”

Apresentação após seleção Luna:

> Você retira o registro da bancada baixa do Arquivo e o protege na superfície seca da Galeria. O documento foi salvo intacto, fora do alcance da água. O resgate está concluído. Mara diz: “O registro foi salvo intacto.”

### CAMP-EVAL-06 — turno 1 — R-07

Entrada: Examino o registro

Escolha Luna: `{"atmosphere": "position", "layout": "paragraph", "utterance": "variant"}`

Baseline determinística:

> Durante o exame do registro, você consegue recuperar um trecho ainda legível. A informação obtida é parcial; outras linhas permanecem ilegíveis. O documento continua na bancada baixa do Arquivo. A investigação termina sem restaurar o registro inteiro. Mara diz: “Parte do conteúdo foi recuperada.”

Apresentação após seleção Luna:

> Durante o exame do registro, você consegue recuperar um trecho ainda legível. A informação obtida é parcial; outras linhas permanecem ilegíveis. O documento continua na bancada baixa do Arquivo. A investigação termina sem restaurar o registro inteiro.
> 
> Mara diz: “Foi possível recuperar parte do conteúdo.”
> 
> O registro está na bancada baixa do Arquivo.

### CAMP-EVAL-07 — turno 1 — R-08

Entrada: Examino o registro

Escolha Luna: `{"atmosphere": "position", "layout": "inline", "utterance": "original"}`

Baseline determinística:

> O exame falha: você não consegue ler o registro nem recuperar seu conteúdo. A água molha as páginas sobre a bancada baixa do Arquivo; ainda há trechos legíveis. O documento permanece na bancada, e o resgate parcial continua possível. Mara diz: “Não foi possível ler o registro.”
> 
> O que você faz agora?

Apresentação após seleção Luna:

> O exame falha: você não consegue ler o registro nem recuperar seu conteúdo. A água molha as páginas sobre a bancada baixa do Arquivo; ainda há trechos legíveis. O documento permanece na bancada, e o resgate parcial continua possível. Mara diz: “Não foi possível ler o registro.” O registro está na bancada baixa do Arquivo.
> 
> O que você faz agora?

### CAMP-EVAL-07 — turno 2 — R-06

Entrada: Retiro o registro

Escolha Luna: `{"atmosphere": "position", "layout": "inline", "utterance": "variant"}`

Baseline determinística:

> Você retira o registro molhado da bancada baixa e o coloca na superfície seca da Galeria. Apenas a parte ainda legível foi salva. O dano anterior permanece e as páginas continuam molhadas; o resgate parcial está concluído. Mara diz: “O que ainda dava para ler está preservado.”

Apresentação após seleção Luna:

> Você retira o registro molhado da bancada baixa e o coloca na superfície seca da Galeria. Apenas a parte ainda legível foi salva. O dano anterior permanece e as páginas continuam molhadas; o resgate parcial está concluído. Mara diz: “Só a parte ainda legível foi preservada.” O registro está na superfície seca da Galeria.
