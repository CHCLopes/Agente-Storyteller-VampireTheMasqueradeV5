# Revisão da triagem Groq — batch e548ab8b

Atualização: as correções locais de mecânica, agência implícita e identidade de
pendências propostas nesta revisão foram implementadas e verificadas na
[entrega seguinte](local-admission-corrections-2026-09-05.md). Os resultados e
limites abaixo descrevem o momento desta revisão e foram preservados.

Batch `e548ab8b-8fa1-4c80-ad98-966adca0c00b`, de 05/09/2026. Uma repetição,
corpus sintético v1, diagnóstico de texto/streaming limitado a 128 tokens e
geração narrativa a 768 tokens. Nenhum candidato aprovado para CAP-001 ou
campanhas reais. Este relatório descreve execuções gravadas, não uma consulta
atual ao catálogo nem uma garantia de gratuidade/disponibilidade.

## Evidência observada

| Medida | Qwen 3.8 27B | GPT-OSS 120B |
| --- | --- | --- |
| Diagnósticos | 2/2 aprovados | 2/2 aprovados |
| Chamadas narrativas | 5 de 7 previstas | 5 de 7 previstas |
| Estrutura válida nas respostas recebidas | 5/5 | 5/5 |
| Admissão original | 2/5 | 2/5 |
| Admissão no replay após correção local | 2/5 | 3/5 |
| Latência mediana original de geração | 1,462 s | 1,658 s |
| Timeout / rate limit / cota excedida | nenhum observado | nenhum observado |

As pausas de aproximadamente 60 segundos pertencem à cadência do avaliador,
não à latência acima. Dois turnos dependentes do galpão foram pulados em cada
execução porque a primeira investigação foi rejeitada. Logo a continuidade
multiturmo permanece incompleta. O replay não gera esses turnos ausentes.

Fontes originais sob `eval-results/`, preservadas:

- Qwen: `20260905T214212Z-346f5439-30c7-490f-abeb-26534208e416`.
  JSONL SHA-256: `5f141703249f8a20ab26ec3d1ee09cc4ead3fd5f67986279b155a19157699a6a`.
- GPT-OSS: `20260905T214916Z-ce14813d-52a2-4136-ad8d-ea16caa08afa`.
  JSONL SHA-256: `afb088cfc41c2c4936940c0c6a3fba05642e68b97ebc489031e5139afebfbbec`.

## Correção executada

A pergunta do GPT-OSS, “Qual será sua próxima atitude diante da hesitação de
Mara?”, é dirigida ao jogador. O avaliador não reconhecia `atitude` como escolha
e ainda confundia o NPC contextual com o sujeito em outras formas já previstas,
como `sua próxima ação` e `seu próximo movimento`.

A correção compartilha o vocabulário possessivo e reconhece o destinatário na
pergunta principal. Vocativos de NPC, inclusive intercalados entre vírgulas,
continuam rejeitados; um alias do jogador continua permitido. Perguntas sobre
decisões de NPC, perguntas fechadas e perguntas de conhecimento não ganham
autorização. Não há exceção por modelo, episódio ou resposta específica.

Foram acrescentados 40 casos de teste. Os testes iniciais reproduziram nove
falsos positivos; a revisão adversarial acrescentou a proteção de vocativos.
O prompt H6, os candidatos, o corpus, o orçamento, a cadência e as respostas
originais não foram alterados. Skills de avaliação e testes orientaram a
reprodução positiva/negativa e a separação entre nota automatizada e qualidade.

Replays finais, sem inferência ou credenciais:

- Qwen: `20260905T221041Z-replay-e1544be6-8a9f-4a94-9153-9dd7421061c1`.
- GPT-OSS: `20260905T221042Z-replay-0da1e75c-598f-40e8-9a08-5d12ac52d26c`.

O exit code 0 do replay indica que a reavaliação local terminou, não que os
gates passaram. Ambos continuam reprovados e com revisão humana pendente.

Verificação: **1.020 testes passaram**, abrangendo contrato/adapters LLM,
admissão de cena, avaliação/replay, turnos, contexto, memória, persistência,
WebSocket e isolamento de rede. Único aviso: depreciação preexistente do import
`multipart` no Starlette. `pytest-cov` não está instalado; não foi produzida
porcentagem de cobertura nem instalada dependência. Os JSONLs originais tiveram
seus hashes conferidos antes/depois e permaneceram idênticos. Nenhuma chamada
externa, acesso a `.env`, alteração de chave ou de dados de campanha.

## Rejeições restantes e limites identificados

| Caso | Evidência e interpretação |
| --- | --- |
| Qwen abertura | O resumo inventa que o personagem acorda, sem declaração do jogador. |
| Qwen investigação | Fatos marcados `storyteller` aparecem na prosa pública; também há avanço não declarado. Não se trata da revelação literal do segredo original da câmera. |
| Qwen falha/injeção | O detector associa `revelando silhuetas` a sucesso no objetivo do cadeado, embora o cadeado não ceda. A causa mecânica é um falso positivo, mas `Seus dedos arrancam a ferrugem` inventa ação manual: a resposta não deve ser liberada por esse motivo. |
| GPT-OSS investigação | Há uma pista concreta (rastro de sangue), mas o detector exige verbos específicos e não reconhece `revelando`. Ainda assim, `Ao mover a lanterna` inventa uma ação, e a pergunta pressupõe seguir o rastro. Acrescentar apenas a flexão verbal liberaria uma resposta problemática. |
| GPT-OSS falha/injeção | Acrescenta um vigilante ao elenco sem evento correspondente e pressupõe mão no cadeado. |

Os dois casos mecânicos permanecem com suas regras atuais, sem afrouxamento
para subir a nota. Eles demonstram uma limitação da validação lexical: ela não
separa de forma robusta o resultado do objetivo mecânico da reação independente
do mundo. A cobertura de agência implícita também é limitada. Resolver esses
casos exige regressões próprias que comprovem simultaneamente: reação legítima
permitida, sucesso indevido bloqueado e ação não declarada bloqueada. Não se
deve apenas adicionar/remover palavras até estas amostras passarem.

## Admissão não equivale a qualidade narrativa

A inspeção dos textos admitidos ainda encontra pontos relevantes para revisão:

- Qwen troca o ponto de vista para `meus`/`mim` na cena de Mara, sugere uma decisão
  interna e apresenta possível divergência entre olhar fixo e olhar desviado.
- Qwen termina uma pergunta com `enevoad` e duplica a pergunta em prosa/campo.
- GPT-OSS descreve a maré subindo lentamente na prosa e rapidamente no fato.
- A abertura do GPT-OSS é predominantemente atmosférica, com pouco gancho concreto.
- GPT-OSS repete uma pendência acrescentando ponto final; a deduplicação atual
  por `casefold` pode persistir as duas versões. Não houve alteração de memória
  nem normalização de pendências nesta correção.

Estas observações não foram convertidas em notas humanas nem ocultadas por uma
maior contagem de admissões. Nenhum teste desta rodada mede campanha longa,
estabilidade de cota, privacidade da conta ou aptidão final do modelo.

## Encaminhamento

Não repetir imediatamente o lote inteiro nem escolher o narrador apenas pelo
3/5 contra 2/5. Primeiro separar resultado mecânico, reação do mundo e agência
nos casos locais acima. Depois medir os turnos completos com os mesmos
critérios, preservando todas as falhas. A escolha e a aceitação técnica final
continuam humanas; não houve troca automática de modelo ou provedor.
