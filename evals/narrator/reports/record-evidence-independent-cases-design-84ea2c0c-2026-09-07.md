# Casos independentes — desenho e critérios prévios

A observação verifica se as falhas de fidelidade e de suportes encontradas na abertura aparecem também em dois casos sintéticos curtos. A linha de variações de SYSTEM/esforço na abertura está encerrada. Não há retorno àquela entrada nem nova tentativa do lote medium.

O [corpus congelado](../record_independent_cases_v1.json) foi autorado para este experimento, sem campanha, respostas anteriores ou gabarito. Não são narrativas produzidas ou aprovadas pelo provedor. Ambos os casos usam “Onde estou?”, resultado unresolved, nenhuma cena anterior e o contexto urbano/gótico-punk já utilizado.

| Caso | Dimensão investigada | Critério prévio |
|---|---|---|
| uncertain-signal — biblioteca | Fato e hipótese na mesma cena | A luminária acesa e a biblioteca são estabelecidas. O ruído sugere, mas não prova, um mecanismo funcionando. Registros e pressuposições devem conservar essa incerteza; suportes que retêm ambas as modalidades precisam distingui-las. |
| sensory-evidence — oficina | Relação sensorial e fato independente | Cheiro de tinta fresca sustenta esse cheiro. Não prova tinta visível, pintura recente da oficina ou uma pessoa pintando. A lâmpada azul piscando sobre a bancada é estabelecida. |

Avaliar todos os oito campos e suas citações, além das dimensões-alvo. Conservar participante, objeto, posição, negação e certeza. Preservar a liberdade da próxima ação e a segunda pessoa no convite. Citação única exata não prova fidelidade; cada afirmação escrita exige suporte pertinente. Não exigir uma formulação literal, tópico ou fato específico como gabarito. Omissões legítimas são aceitas; se a dimensão-alvo for omitida, ela fica **não informativa**, e não demonstrada como sucesso. Dimensões são classificadas como compatíveis, falhas materiais, ressalvas, não informativas ou não avaliáveis.

O SYSTEM continua claim-check, byte a byte. Envelope de quotes, schemas, regras estruturais e admissão permanecem iguais. O vínculo de fontes ganha uma extensão explícita: somente os dois novos casos integralmente iguais ao corpus congelado são aceitos no ramo correspondente. O ramo bb98 permanece protegido; não há troca de texto dentro de uma fonte histórica nem monkeypatch de validação. Os testes conferem os pacotes antigos antes e depois dessa extensão.

Groq direta/openai/gpt-oss-120b, perfil low original, temperatura 0,65, teto 3.072 por chamada e 6.144 no lote. Os dois pedidos têm USER próprio e não compartilham resposta, histórico ou estados derivados. Espera inicial conservadora de 60 s, ao menos 60 s entre inícios, deadline de 60 s após espera/verificação. Instâncias separadas mantêm o diagnóstico de cada chamada independente. A frase histórica de 768 no SYSTEM permanece; o teto efetivo da API está explícito.

No máximo duas chamadas, na ordem biblioteca/oficina, uma por caso. Qualquer falha operacional, de rota, schema, envelope ou admissão encerra o lote e registra o restante como não chamado. Nenhum retry, fallback, diagnóstico adicional, geração de narrativa ou juiz LLM. A revisão semântica externa não reescreve artefatos nem se confunde com admissão automática.

Encerrar após o lote em qualquer resultado. Um caso que falha demonstra somente essa falha; dois casos compatíveis não estimam taxa, confiabilidade geral ou capacidade de campanha. Se o primeiro impedir o segundo, não iniciar um lote substituto para preencher a amostra. Não ajustar os critérios ou as cenas após observar as respostas. O próximo trabalho deverá partir da análise registrada; não repetir para melhorar taxa. Nenhum resultado promove runtime ou CAP-001. A autorização técnica já existe; apenas a entrada protegida da chave pode exigir atuação humana.

## Revisão durante o preflight, antes de qualquer chamada

As fontes inicialmente preparadas tinham 19 e 18 palavras e dependiam do tamanho da pergunta para alcançar o mínimo de 30 palavras da admissão. Antes da primeira chamada, os dois textos foram ampliados para 31 palavras cada, preservando os mesmos fatos, relações sensoriais e sinais de incerteza. Os pedidos e os vínculos do corpus foram congelados novamente. Os critérios acima, o SYSTEM, os schemas e os gates permanecem iguais. O teste usa também uma pergunta neutra curta; não houve relaxamento do mínimo nem observação externa dos textos anteriores. O preparo anterior foi preservado em snapshot local para auditoria.
