# A1 v2 — avaliação dos lotes L84 e L85, 21/10/2026

Resultado: A1 preservou os trechos críticos nas 29 apresentações técnicas completas.
L84 falhou no formato da fala opcional; L85 completou 17 turnos sem repetir esse erro,
mas o texto livre ainda acrescentou uma descrição ambiental não fundamentada.
O experimento não autoriza fidelidade integral, naturalidade geral ou admissão.

## Execução e custo

| Lote | Chamadas | Turnos completos | Custo estimado USD | Resultado |
|---|---:|---:|---:|---|
| L84 | 12 | 12 | 0.0075790 | Fechado durante revisão de descrições apresentadas como fala |
| L85 | 17 | 17 | 0.0099808 | Matriz técnica completa; ressalvas qualitativas abaixo |
| Total desta continuidade | 29 | 29 | 0.0175598 | Cobrança não confirmada |

L84: 24.587 tokens de entrada/2.218 de saída. L85: 35.234/2.445.
Nenhuma chamada sem uso reportado; limites por lote <= USD 0.15 respeitados.
Tarifas 0.20/1.20 por milhão de tokens verificadas em 21/10; o helper imprime
sua data histórica 29/09, sem mudar a tarifa. Nenhuma inferência adicional foi
feita para gerar este relatório. Não somar lotes como estimativa de estabilidade:
prompt, número de turnos e cobertura diferem.

## Comparação controlada

L85 altera somente a instrução de mara.reaction no prompt, agora explicitamente
discurso direto. Runner/preflight novos diferem apenas em identidade e caminho
do prompt. A aplicação e o renderizador não mudaram. Ambos os manifestos tiveram
32 hashes conferidos, gates fechados ao final e travas mantidas.

L84: três reações não vazias, todas descrições de Mara apresentadas como fala;
quatro atmosferas não vazias e sete turnos com os dois campos vazios. Parada
local antes da chamada 13; erro genérico no registro 13 não é erro do provedor.
O silêncio ambiental também aparece no L84, sem estar estabelecido no cenário.

L85: uma reação não vazia, em discurso direto; duas atmosferas; 14/17 turnos com
os dois campos vazios. A fala da recusa é contextual, mas parcialmente redundante
com a fala essencial. Uma amostra de fala correta não comprova correção geral.
Os vazios são permitidos; evidenciam contribuição pequena do modelo nesta matriz,
não um erro estrutural. A resposta final continua majoritariamente autorada.

CAMP-EVAL-03/1: “O Arquivo permanece silencioso, com a bancada baixa ao alcance
da vista.” O silêncio não está estabelecido: esse é o primeiro turno do percurso,
sem fontes atribuídas anteriores; create_campaign_expression_session cria cena
apenas com Arquivo e Mara, e build_campaign_expression_context envia localização,
NPCs, pacote causal e plano. Esses dados não definem silêncio. Trata-se de um
acréscimo não fundamentado, não de prova de alteração do estado canônico nem de
contradição física comprovada. O prompt exigia ambiente já estabelecido; guard
aceitou. Não acrescentar silêncio ao cânone para legitimar retroativamente a saída.

Também há redundância editorial no núcleo autorado, como “A posição do documento
não mudou”, e repetição do nome Mara quando existe reação extra. As formulações
fazem parte do renderer congelado v1; não foram mudadas para melhorar esta amostra.

## Verificação e limites

Seis testes offline L85 passaram (XML a1-v2-l85-offline-2026-10-21.xml), incluindo
preflight keyless/17 turnos, lote falso completo, falha de hash, gate fechado,
schema estrito e drift. Somam-se aos 269 testes distintos da implementação A1
já registrados; não houve nova mudança de aplicação nesta continuidade.

Inspeção programática dos registros reais verificou integridade SHA-256, offsets,
reconstrução do texto, autoria/IDs, preservação dos trechos críticos e suas
referências. Em L85, bruta e normalizada coincidem, a pergunta final corresponde
ao plano e os oito desfechos esperados foram atingidos. O avaliador validou a
persistência durante execução; bancos SQLite do lote eram temporários e já foram
removidos pelo próprio runner. Permanecem registros JSONL/summary, não os saves
reais para teste posterior de reinício. Reinício/replay têm testes offline já
registrados; não apresentar isso como prova de navegador ou replay real deste lote.

Continuam válidas as contraprovas autoradas: 9/10 acréscimos inválidos aceitos,
13 válidos aceitos. São casos de diagnóstico, não taxa probabilística. Nenhuma
validação lexical ou lote tecnicamente completo certifica significado livre.

## Próxima decisão, ainda não aprovada

O ciclo experimental A1 previsto está concluído com limites medidos. Não abrir
L86 apenas para procurar um lote sem falhas. Garantir que nenhum acréscimo livre
seja não fundamentado exige mudar a fronteira de autoria/admissão, ou aceitar
explicitamente uma garantia mais estreita no produto. A aprovação experimental
de A1 não representa esse aceite final. CAMP-24/default/MVP continuam abertos.

Proposta para decisão de produto: manter A1 como experimento de autoria mista;
para uma apresentação que prometa somente fatos validados, estudar um contrato
em que a aplicação componha também a expressão a partir de opções autoradas e
referências verificáveis. A LLM poderia propor escolhas entre opções válidas,
sem prosa livre exibida diretamente. Isso reduz liberdade, aumenta curadoria e
pode tornar o modelo dispensável nesta matriz — tradeoff que cabe ao humano.
É proposta, não decisão nem implementação. Se a intenção for manter prosa livre,
a aceitação deve declarar que a garantia cobre núcleo/estado/proveniência e que
o texto opcional continua sujeito a erro semântico. Não promover essa condição
a aceite por conta própria. Não se pede autorização financeira de novo lote.

## Evidências

- L84: eval-results/hybrid-campaign-luna-l84-c9cd77f6-8e5b-42e0-b6ad-c77fcaba2e02.
- L84 records SHA-256: 3d2606a84818ab046ec592cc9ee5681338ce7267a63f5e712d1db1d46be2cffc.
- L85: eval-results/hybrid-campaign-luna-l85-a60bde9c-5fff-46d6-95a0-f50c120a1761.
- L85 records SHA-256: d55e6bfe106b5f556bc1438d835d127d0f2c070d81a6e380f6012607791281ec.
- L85 prompt SHA-256: ff8036f7fe4b4845bc75bce9382309b6af6e0f7ccb6bc707faaf0937739e01f0.
- Registros prospectivos próprios L84/L85 preservados, com resultados separados.

## Apresentações completas do L85

Abaixo, texto efetivamente produzido pelo pipeline, sem edição editorial.
Rótulos de autoria são evidência de revisão e não controles exibidos ao jogador.

### CAMP-EVAL-08 — turno 1 — R-02

Entrada: Quem é a fundadora?

> O registro continua na bancada baixa do Arquivo, sob o risco da infiltração. A pergunta não altera a posição nem o estado do documento. Mara responde: “Não vou divulgar a identidade da fundadora.” Mara diz: “Posso falar sobre o registro, não sobre a identidade dela.”
> 
> O que você faz agora?

Contribuição LLM: mara.reaction: Posso falar sobre o registro, não sobre a identidade dela.

### CAMP-EVAL-08 — turno 2 — R-01

Entrada: Qual é a tarefa?

> O registro permanece na bancada baixa do Arquivo, seco, ameaçado pela infiltração. A posição do documento não mudou. Mara responde: “A tarefa é preservar o registro da água. Você pode levar o documento até a superfície seca da Galeria.”
> 
> O que você faz agora?

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-08 — turno 3 — R-05

Entrada: Retiro o registro

> Você retira o registro da bancada baixa do Arquivo e o protege na superfície seca da Galeria. O documento foi salvo intacto, fora do alcance da água. O resgate está concluído. Mara diz: “O registro está preservado.”

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-01 — turno 1 — R-01

Entrada: Como posso ajudar?

> O registro permanece na bancada baixa do Arquivo, seco, ameaçado pela infiltração. A posição do documento não mudou. Mara responde: “A tarefa é preservar o registro da água. Você pode levar o documento até a superfície seca da Galeria.”
> 
> O que você faz agora?

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-01 — turno 2 — R-05

Entrada: Retiro o registro

> No Arquivo, a bancada baixa continua sob a infiltração; a Galeria tem uma superfície seca. Você retira o registro da bancada baixa do Arquivo e o protege na superfície seca da Galeria. O documento foi salvo intacto, fora do alcance da água. O resgate está concluído. Mara diz: “O registro está preservado.”

Contribuição LLM: atmosphere: No Arquivo, a bancada baixa continua sob a infiltração; a Galeria tem uma superfície seca.

### CAMP-EVAL-02 — turno 1 — R-03

Entrada: Aguardo

> A água pinga da infiltração e se aproxima do registro sobre a bancada baixa do Arquivo. O documento permanece seco e intacto; nenhuma folha foi movida. Mara avisa: “A água está chegando perto do registro.”
> 
> O que você faz agora?

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-02 — turno 2 — R-03B

Entrada: Espero

> A água da infiltração atinge o registro na bancada baixa do Arquivo. As páginas ficam molhadas e parte da tinta se espalha. Ainda há trechos legíveis; o documento continua na bancada. Mara diz: “A água molhou as páginas.”
> 
> O que você faz agora?

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-02 — turno 3 — R-01

Entrada: O que precisamos fazer?

> O registro permanece na bancada baixa do Arquivo, molhado, com trechos ainda legíveis. A posição do documento não mudou. Mara responde: “A tarefa é preservar o registro da água. Você pode levar o documento até a superfície seca da Galeria.”
> 
> O que você faz agora?

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-02 — turno 4 — R-06

Entrada: Retiro o registro

> Você retira o registro molhado da bancada baixa e o coloca na superfície seca da Galeria. Apenas a parte ainda legível foi salva. O dano anterior permanece e as páginas continuam molhadas; o resgate parcial está concluído. Mara diz: “O que ainda dava para ler está preservado.”

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-03 — turno 1 — R-03

Entrada: Aguardo

> O Arquivo permanece silencioso, com a bancada baixa ao alcance da vista. A água pinga da infiltração e se aproxima do registro sobre a bancada baixa do Arquivo. O documento permanece seco e intacto; nenhuma folha foi movida. Mara avisa: “A água está chegando perto do registro.”
> 
> O que você faz agora?

Contribuição LLM: atmosphere: O Arquivo permanece silencioso, com a bancada baixa ao alcance da vista.

### CAMP-EVAL-03 — turno 2 — R-03B

Entrada: Espero

> A água da infiltração atinge o registro na bancada baixa do Arquivo. As páginas ficam molhadas e parte da tinta se espalha. Ainda há trechos legíveis; o documento continua na bancada. Mara diz: “A água molhou as páginas.”
> 
> O que você faz agora?

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-03 — turno 3 — R-04

Entrada: Aguardo

> A água continua caindo sobre o registro na bancada baixa do Arquivo. O texto se torna irrecuperável e o documento está perdido. As folhas permanecem na bancada, sem conteúdo legível para recuperar. Mara diz: “O conteúdo se perdeu.”

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-04 — turno 1 — R-09

Entrada: Desisto

> A tentativa termina com a desistência declarada. O registro permanece na bancada baixa do Arquivo, seco, ainda ameaçado pela infiltração. O documento continua no mesmo lugar, sem ter sido resgatado. Mara reconhece a desistência: “Entendido. Não haverá ajuda no resgate.”

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-05 — turno 1 — R-05

Entrada: Levo o registro até a superfície seca

> Você retira o registro da bancada baixa do Arquivo e o protege na superfície seca da Galeria. O documento foi salvo intacto, fora do alcance da água. O resgate está concluído. Mara diz: “O registro está preservado.”

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-06 — turno 1 — R-07

Entrada: Examino o registro

> Durante o exame do registro, você consegue recuperar um trecho ainda legível. A informação obtida é parcial; outras linhas permanecem ilegíveis. O documento continua na bancada baixa do Arquivo. A investigação termina sem restaurar o registro inteiro. Mara diz: “Parte do conteúdo foi recuperada.”

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-07 — turno 1 — R-08

Entrada: Examino o registro

> O exame falha: você não consegue ler o registro nem recuperar seu conteúdo. A água molha as páginas sobre a bancada baixa do Arquivo; ainda há trechos legíveis. O documento permanece na bancada, e o resgate parcial continua possível. Mara diz: “Não foi possível ler o registro.”
> 
> O que você faz agora?

Contribuição LLM: nenhum texto opcional

### CAMP-EVAL-07 — turno 2 — R-06

Entrada: Retiro o registro

> Você retira o registro molhado da bancada baixa e o coloca na superfície seca da Galeria. Apenas a parte ainda legível foi salva. O dano anterior permanece e as páginas continuam molhadas; o resgate parcial está concluído. Mara diz: “O que ainda dava para ler está preservado.”

Contribuição LLM: nenhum texto opcional
