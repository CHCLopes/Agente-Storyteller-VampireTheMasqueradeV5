# Comparativo Qwen/GPT-OSS — lote 61b83a2f

**Lote encerrado; nenhum candidato qualificado pelo protocolo prévio.** A auditoria
dos artefatos passou, mas o comparativo operacional terminou com código 1. Isso não
equivale a indisponibilidade do provedor nem demonstra superioridade geral de um modelo.

| Configuração e cena | Chamadas | Confirmados | Recusas | Dependentes não enviados |
|---|---:|---:|---|---:|
| Qwen none / Oficina | 1 | 0 | T1: 155 palavras, teto 150 | 2 |
| GPT-OSS low / Oficina | 3 | 3 | Nenhuma | 0 |
| GPT-OSS low / Arquivo | 1 | 0 | T1: agência; falso positivo delimitado em diagnóstico local | 2 |
| Qwen none / Arquivo | 2 | 1 | T2: 157 palavras, teto 150 | 1 |

As sete respostas tiveram HTTP 200, encerramento stop, schema válido e rota exata.
Foram conservados sete recibos P, sete cápsulas K, sete tentativas H, quatro commits
e seus replays. Os cinco skips respeitam a interrupção da cadeia; nenhum erro global.
Tempo: 433,347870 segundos; espera inicial 61,214159 segundos; intervalos entre
inícios HTTP de 60,842809 a 65,870295 segundos. Todos terminaram antes do prazo.
Consumo reportado: 11.066 tokens de entrada e 1.582 de saída. Nenhuma saída excedeu
768; raciocínio agregado e custo permanecem desconhecidos. GPT-OSS reportou 221
tokens de raciocínio; Qwen não informou essa medida. Não houve retry/fallback.

## Experiência narrativa

Revisão principal e independente aplicaram o protocolo congelado. O revisor recebeu
rótulos A/B sem consultar o mapa; o contexto herdado impede alegar cegamento completo.
Todos os textos disponíveis foram lidos. Propostas recusadas recebem avaliação
descritiva separada; os cinco skips não recebem notas.

| Texto | Situação | Utilidade | Avanço | Clareza |
|---|---|---:|---:|---:|
| Qwen / Oficina T1 | Proposta recusada | 2 | 2 | 1 |
| GPT-OSS / Oficina T1 | Confirmado | 2 | 2 | 2 |
| GPT-OSS / Oficina T2 | Confirmado | 1 | 1 | 1 |
| GPT-OSS / Oficina T3 | Confirmado | 2 | 1 | 1 |
| GPT-OSS / Arquivo T1 | Proposta recusada | 2 | 2 | 1 |
| Qwen / Arquivo T1 | Confirmado | 2 | 2 | 1 |
| Qwen / Arquivo T2 | Proposta recusada | 1 | 1 | 1 |

GPT-OSS sustenta três turnos na Oficina, responde com objetos e possibilidades
úteis e preserva agência/continuidade. Na espera, porém, lâmpada, cheiro e reflexo
mudam pouco a próxima escolha. O terceiro turno retoma as mesmas oportunidades.
Mesmo descontando a recusa incorreta no Arquivo, a espera não satisfaz avanço 2.

A proposta Qwen/Oficina contém um acontecimento concreto interessante: Nina aponta
uma mancha que cresce. O gesto responde ao objetivo sem impor ação ao jogador.
Ultrapassar o teto em cinco palavras é falha de conformidade; não torna a cena
inerentemente ruim. Qwen/Arquivo T1 oferece destino e motivo utilizáveis, mas tem
o defeito lexical “papel veloz”. Na espera recusada, o texto reforça a cena suspensa.

As avaliações originais de ambos os revisores foram preservadas. A reconciliação
corrige a leitura inicial excessivamente verbal da resposta de Nina e reconhece
microgestos na espera de Rui. Divergências menores de clareza ficaram registradas.
Nenhuma alteração nos textos, no protocolo, nos artefatos ou nos resultados live.

## Diagnóstico e próximo incremento

Em GPT-OSS/Arquivo, Rui diz “se houver algo específico que você procura, talvez seja
melhor seguir o índice”. A reprodução local mostrou que o detector atribui procura
e seguir ao jogador como ações realizadas. Trata-se de interesse hipotético e
sugestão na fala do NPC; a revisão independente não identificou violação de agência.
O diagnóstico separa esse falso positivo das falhas de progressão e extensão.

Próximo incremento: corrigir esse caso local com contraprovas de ações efetivamente
realizadas e de ações posteriores, preservando os demais gates e o teto de palavras.
Não repetir o comparativo, reclassificar sua recusa nem importar um resultado novo.
O plano específico é [fix-hypothetical-interest-agency-1.md](../../../plan/fix-hypothetical-interest-agency-1.md).

O desenho do despacho local inativo também foi preparado como proposta temporária;
nenhuma rota/handler/UI foi ativada. Sua integração permanece subordinada ao plano
de transporte e à aceitação da experiência. Nenhum modelo/default/produto/CAP-001
foi aprovado. Este corpus não cobre campanha longa, combate, dados ou segredos autorados.

## Evidência preservada

Checkpoint: `eval-results/checkpoints/source-comparison-observation-61b83a2f-20260911/`.
Contém summary/JSONL/quatro bancos selados, controle do launcher, verificação,
avaliações originais e cópia de 36 arquivos da versão congelada. A auditoria foi
executada antes de qualquer correção posterior. O verificador prende o hash do
código: uma reauditoria futura deve respeitar a versão congelada, sem trocar o
resultado histórico pelo comportamento de um código corrigido.

Os JSONs deste relatório e do checkpoint registram os hashes e a reconciliação.
