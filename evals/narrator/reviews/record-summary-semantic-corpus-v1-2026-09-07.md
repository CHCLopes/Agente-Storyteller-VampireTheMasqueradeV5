# Corpus autorado de relações em resumos — 07/09/2026

Seis respostas históricas SummaryOnly, quatro lotes encerrados. A finalidade é registrar quais afirmações o resumo permite recuperar e quais ficaram alteradas, ausentes ou indeterminadas. Não houve nova chamada, correção de resposta, mudança de contrato ou admissão em memória.

Esta é uma revisão autorada de relações selecionadas, com trechos literais e proveniência. Os rótulos não são um classificador executável nem novo gate de produto. Omissão permitida é não informativa; ambiguidade permanece indeterminada. Os metadados semânticos brutos continuam `not_performed`/`approval: null`.

Qwen/Groq com raciocínio `none` e temperatura 0,65 em todos. O teto original de 21cf era 3.072; os demais usaram 768. Fontes/SYSTEM/tarefa e lote variam historicamente. Somente os dois braços faad compartilham o USER inteiro, com SYSTEM diferente e uma saída por braço, em ordem fixa. Não inferir causalidade, superioridade ou taxa de confiabilidade.

| Observação | Palavras | Caracteres | Leitura autorada |
| --- | ---: | ---: | --- |
| 21cf-archive-vibration | 21 | 134 | Atribuição de vermelho à luz sem suporte; hipótese modal do motor preservada. |
| 95dd-station-clock | 23 | 120 | Afirmações retidas compatíveis; omissões não informativas. Não contém hipótese modal para avaliá-la. |
| 0e7b-reading-room-a | 20 | 129 | Cor, escopo da iluminação e vínculo com a porta ambíguos. |
| 0e7b-reading-room-b | 20 | 121 | Cor, relação luz/luminária sobre o mapa e vínculo com a porta ambíguos. |
| faad-control | 19 | 128 | Reflexão preservada; posição da tapeçaria diante da janela menos explícita. |
| faad-relational | 23 | 156 | Apoio das molduras acrescentado com suporte; repete a ambiguidade do controle. |

## 21cf-archive-vibration

**Fonte literal:** No arquivo municipal, a luz de uma lanterna vermelha ilumina uma mesa coberta de pastas. Perto da porta fechada, uma vibração leve sugere que talvez exista um motor funcionando do outro lado.

**Resposta literal:** No arquivo municipal, luz vermelha ilumina mesa com pastas. Perto da porta fechada, vibração leve sugere possível motor do outro lado.

Brutos: [summary](../../../eval-results/20260907T190328Z-33c26c5a-59ef-4ef7-a40e-178fe3a65a16/summary.json) e [JSONL, linha 1](../../../eval-results/20260907T190328Z-33c26c5a-59ef-4ef7-a40e-178fe3a65a16/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl). Hashes, offsets e parâmetros no JSON associado.

| Relação | Fonte → resumo | Classificação | Conteúdo recuperável ou limite |
| --- | --- | --- | --- |
| local | No arquivo municipal → No arquivo municipal | preservado | A cena ocorre no arquivo municipal. |
| cor | a luz de uma lanterna vermelha → luz vermelha | alterado | A fonte atribui vermelho à lanterna. O resumo atribui à luz; essa afirmação não tem suporte e a cor da lanterna deixa de ser recuperável do resumo. |
| iluminação | ilumina uma mesa coberta de pastas → ilumina mesa com pastas | preservado | A iluminação da mesa e a presença de pastas permanecem; o grau de cobertura da mesa não é recuperável. |
| sensação | Perto da porta fechada, uma vibração leve → Perto da porta fechada, vibração leve | preservado | Vibração leve perto da porta fechada. |
| hipótese | sugere que talvez exista um motor funcionando do outro lado → sugere possível motor do outro lado | preservado | A existência/posição do motor continua possível, sugerida pela vibração; não recuperar motor confirmado. |
| funcionamento | talvez exista um motor funcionando do outro lado → ∅ | omitido | O funcionamento pertencia à hipótese; sua ausência não o confirma nem o nega. |

## 95dd-station-clock

**Fonte literal:** Na estação vazia, um relógio parado marca seis horas. Um envelope lacrado repousa sobre o banco; perto da janela aberta, a cortina se move com a brisa.

**Resposta literal:** Na estação vazia, um relógio parado marca seis horas. Um envelope lacrado está no banco e a cortina se move com a brisa.

Brutos: [summary](../../../eval-results/20260907T204016Z-b929bf2c-302d-4b26-b36b-abb0eec249d9/summary.json) e [JSONL, linha 1](../../../eval-results/20260907T204016Z-b929bf2c-302d-4b26-b36b-abb0eec249d9/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl). Hashes, offsets e parâmetros no JSON associado.

| Relação | Fonte → resumo | Classificação | Conteúdo recuperável ou limite |
| --- | --- | --- | --- |
| local | Na estação vazia → Na estação vazia | preservado | Estação vazia. |
| relógio | um relógio parado marca seis horas → um relógio parado marca seis horas | preservado | O relógio está parado e marca seis horas; não recuperar seis horas como horário atual. |
| envelope | Um envelope lacrado repousa sobre o banco → Um envelope lacrado está no banco | preservado | Envelope lacrado no banco. A formulação é menos precisa, compatível com a fonte. |
| cortina | a cortina se move com a brisa → a cortina se move com a brisa | preservado | Movimento da cortina com a brisa. |
| janela | janela aberta → ∅ | omitido | O estado aberto da janela não é recuperável. |
| proximidade | perto da janela aberta, a cortina → ∅ | omitido | A proximidade da cortina com a janela não é recuperável. |

## 0e7b-reading-room-a

**Fonte literal:** Na sala de leitura vazia, uma luminária de base azul ilumina um mapa dobrado. Um estojo fechado repousa junto ao marcador de páginas sobre a mesa; perto da porta, uma poltrona está afastada da estante.

**Resposta literal:** Sala de leitura vazia com luminária azul iluminando mapa, estojo fechado, marcador e poltrona afastada da estante perto da porta.

Brutos: [summary](../../../eval-results/20260907T211537Z-dd5ca339-6fe5-4f8d-8aeb-81abaf5c26b0/summary.json) e [JSONL, linha 1](../../../eval-results/20260907T211537Z-dd5ca339-6fe5-4f8d-8aeb-81abaf5c26b0/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl). Hashes, offsets e parâmetros no JSON associado.

| Relação | Fonte → resumo | Classificação | Conteúdo recuperável ou limite |
| --- | --- | --- | --- |
| local | Na sala de leitura vazia → Sala de leitura vazia | preservado | Sala de leitura vazia. |
| cor | uma luminária de base azul → luminária azul | ambíguo | Não recuperar inequivocamente a base azul. Luminária azul também não demonstra por si só uma transferência explícita para a luz. |
| mapa-iluminado | uma luminária de base azul ilumina um mapa dobrado → luminária azul iluminando mapa | preservado | A relação de iluminação do mapa permanece, independentemente da atribuição ambígua da cor. |
| escopo-iluminação | ilumina um mapa dobrado. Um estojo fechado repousa junto ao marcador de páginas sobre a mesa; perto da porta, uma poltrona → iluminando mapa, estojo fechado, marcador e poltrona | ambíguo | A lista pode ser inventário sob com ou objetos de iluminando. A fonte só explicita iluminação do mapa; não afirmar iluminação dos demais nem erro categórico. |
| estojo | Um estojo fechado → estojo fechado | preservado | Estojo fechado. |
| poltrona-estante | uma poltrona está afastada da estante → poltrona afastada da estante | preservado | Poltrona afastada da estante. |
| porta | perto da porta, uma poltrona está afastada da estante → poltrona afastada da estante perto da porta | ambíguo | O resumo permite vincular perto da porta à poltrona ou à estante; a localização da poltrona perde explicitação. |
| mapa-dobrado | mapa dobrado → ∅ | omitido | O estado dobrado não é recuperável. |
| estojo-marcador-mesa | repousa junto ao marcador de páginas sobre a mesa → ∅ | omitido | Proximidade, apoio na mesa e função do marcador deixam de ser explícitos; omissão não demonstra falsidade. |

## 0e7b-reading-room-b

**Fonte literal:** Na sala de leitura vazia, uma luminária emite luz azul sobre um mapa dobrado. Um estojo fechado repousa junto ao marcador de páginas sobre a mesa; perto da porta, uma poltrona está afastada da estante.

**Resposta literal:** Sala de leitura vazia: luminária azul sobre mapa, estojo e marcador na mesa; poltrona afastada da estante perto da porta.

Brutos: [summary](../../../eval-results/20260907T211537Z-dd5ca339-6fe5-4f8d-8aeb-81abaf5c26b0/summary.json) e [JSONL, linha 2](../../../eval-results/20260907T211537Z-dd5ca339-6fe5-4f8d-8aeb-81abaf5c26b0/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl). Hashes, offsets e parâmetros no JSON associado.

| Relação | Fonte → resumo | Classificação | Conteúdo recuperável ou limite |
| --- | --- | --- | --- |
| local | Na sala de leitura vazia → Sala de leitura vazia | preservado | Sala de leitura vazia. |
| cor | uma luminária emite luz azul → luminária azul | ambíguo | A fonte atribui azul à luz. O resumo não preserva inequivocamente essa atribuição; não concluir cor explícita da base. |
| posição-iluminação | uma luminária emite luz azul sobre um mapa dobrado → luminária azul sobre mapa | ambíguo | A fonte situa a luz sobre o mapa. O resumo pode descrever luminária acima do mapa; não recuperar posição física da luminária como fato confirmado. |
| estojo-mesa | Um estojo fechado repousa junto ao marcador de páginas sobre a mesa → estojo e marcador na mesa | preservado | A enumeração mantém estojo/marcador na mesa de modo compatível; proximidade e função do marcador não ficam explícitas. |
| poltrona-estante | uma poltrona está afastada da estante → poltrona afastada da estante | preservado | Poltrona afastada da estante. |
| porta | perto da porta, uma poltrona está afastada da estante → poltrona afastada da estante perto da porta | ambíguo | A ligação de perto da porta à poltrona ou à estante fica ambígua. |
| mapa-dobrado | mapa dobrado → ∅ | omitido | O estado dobrado não é recuperável. |
| estojo-fechado | estojo fechado → ∅ | omitido | O estado fechado não é recuperável. |
| proximidade | repousa junto ao marcador de páginas → ∅ | omitido | A proximidade e a função do marcador deixam de ser explícitas. |

## faad-control

**Fonte literal:** Na galeria vazia, um espelho reflete uma tapeçaria pendurada diante de uma janela fechada. Um catálogo permanece sobre o banco; à direita da entrada, duas molduras vazias estão apoiadas contra a parede.

**Resposta literal:** Galeria vazia: espelho reflete tapeçaria diante de janela fechada; catálogo no banco; duas molduras vazias à direita da entrada.

Brutos: [summary](../../../eval-results/20260907T214523Z-c8bd771b-741e-4c06-97ff-085c9882bdf2/summary.json) e [JSONL, linha 1](../../../eval-results/20260907T214523Z-c8bd771b-741e-4c06-97ff-085c9882bdf2/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl). Hashes, offsets e parâmetros no JSON associado.

| Relação | Fonte → resumo | Classificação | Conteúdo recuperável ou limite |
| --- | --- | --- | --- |
| local | Na galeria vazia → Galeria vazia | preservado | Galeria vazia. |
| reflexão | um espelho reflete uma tapeçaria → espelho reflete tapeçaria | preservado | O espelho reflete a tapeçaria. |
| janela-fechada | uma janela fechada → janela fechada | preservado | Janela fechada. |
| posição-tapeçaria | uma tapeçaria pendurada diante de uma janela fechada → espelho reflete tapeçaria diante de janela fechada | ambíguo | A retirada de pendurada torna menos explícito o vínculo de diante da janela à tapeçaria ou à situação de reflexão. Não recuperar posição do espelho; não afirmar transferência inequívoca. |
| suspensão | tapeçaria pendurada → ∅ | omitido | A condição pendurada não é recuperável. |
| catálogo | Um catálogo permanece sobre o banco → catálogo no banco | preservado | Catálogo no banco, menos específico e compatível. |
| molduras | à direita da entrada, duas molduras vazias → duas molduras vazias à direita da entrada | preservado | Duas molduras vazias à direita da entrada. |
| apoio | duas molduras vazias estão apoiadas contra a parede → ∅ | omitido | O apoio contra a parede não é recuperável. |

## faad-relational

**Fonte literal:** Na galeria vazia, um espelho reflete uma tapeçaria pendurada diante de uma janela fechada. Um catálogo permanece sobre o banco; à direita da entrada, duas molduras vazias estão apoiadas contra a parede.

**Resposta literal:** Galeria vazia: espelho reflete tapeçaria diante de janela fechada. Catálogo sobre banco; duas molduras vazias apoiadas contra a parede à direita da entrada.

Brutos: [summary](../../../eval-results/20260907T214523Z-c8bd771b-741e-4c06-97ff-085c9882bdf2/summary.json) e [JSONL, linha 2](../../../eval-results/20260907T214523Z-c8bd771b-741e-4c06-97ff-085c9882bdf2/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl). Hashes, offsets e parâmetros no JSON associado.

| Relação | Fonte → resumo | Classificação | Conteúdo recuperável ou limite |
| --- | --- | --- | --- |
| local | Na galeria vazia → Galeria vazia | preservado | Galeria vazia. |
| reflexão | um espelho reflete uma tapeçaria → espelho reflete tapeçaria | preservado | O espelho reflete a tapeçaria. |
| janela-fechada | uma janela fechada → janela fechada | preservado | Janela fechada. |
| posição-tapeçaria | uma tapeçaria pendurada diante de uma janela fechada → espelho reflete tapeçaria diante de janela fechada | ambíguo | A retirada de pendurada torna menos explícito o vínculo de diante da janela à tapeçaria ou à situação de reflexão. Não recuperar posição do espelho; não afirmar transferência inequívoca. |
| suspensão | tapeçaria pendurada → ∅ | omitido | A condição pendurada não é recuperável. |
| catálogo | Um catálogo permanece sobre o banco → Catálogo sobre banco | preservado | Catálogo sobre o banco. |
| molduras | à direita da entrada, duas molduras vazias → duas molduras vazias apoiadas contra a parede à direita da entrada | preservado | Quantidade, estado e localização das molduras permanecem em leitura compatível. Não derivar localização autônoma da parede a partir desse adjunto. |
| apoio | duas molduras vazias estão apoiadas contra a parede → duas molduras vazias apoiadas contra a parede | preservado | O apoio das molduras contra a parede é retido adicionalmente. |

## Conclusões e fronteira

- Cumprir schema e 25 palavras não garante preservar os participantes e vínculos das afirmações.
- O conjunto registra um erro explícito de atribuição, ambiguidades e afirmações preservadas. Não estima frequência, estabilidade ou efeito causal.
- A variante relacional recuperou apoio contra a parede, mas repetiu o trecho ambíguo do controle. Não foi selecionado vencedor.
- Não há defeito local demonstrado de transporte, retenção literal ou medição que explique os problemas semânticos observados. Isso não prova inexistência de outros defeitos.
- Encerrada esta sequência de reformulações SYSTEM e repetições das fontes; o corpus é documentação auditável para avaliações futuras, não critério novo de produto nem dados de campanha.

## Verificação

Auditoria independente concluída: oito brutos intactos, seis linhas/medições/restrições de schema, 46 relações e 81 trechos literais exatos. O Markdown corresponde ao JSON. Uma leitura independente dos 46 rótulos não encontrou contradição material; esse julgamento é autorado, separado da auditoria de integridade. Provas completas e hashes da versão auditada estão incorporados no JSON. A finalização preserva literalmente todos os registros. Nenhuma chamada externa ou novo teste foi necessário para consolidar este pacote.

Próximo trabalho local: auditar uma vez proposta/narrativa → evento → memória → contexto, contra REQ-015 e AC-IMP-005, e corrigir somente defeitos locais demonstrados. Não há novo prompt, lote ou credencial agendado.

[Estrutura auditável em JSON](record-summary-semantic-corpus-v1-2026-09-07.json).
