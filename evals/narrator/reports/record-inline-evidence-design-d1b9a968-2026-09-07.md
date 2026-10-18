# Evidência junto ao texto — prova de contrato experimental

Decisão técnica local sob autorização contínua, após o lote d1b9a968. Primeiro concluir uma prova offline de representação; nenhuma alteração no produto ou promoção de capacidade. A entrada da oficina permanece não observada, e o lote independente está encerrado.

O experimento anterior exige escrever um campo e depois copiar sua afirmação em outro local. A falha observada copiou a fonte em vez do destino. Campo integral p/s/m elimina essa duplicação, mas perde precisão dentro de um resumo misto. Seleção de evidência em outra chamada acrescenta dependências e não assegura uma derivação fiel. A prova escolhida escreve cada segmento uma vez, junto de seus IDs de origem e modalidade.

## Escopo da prova local

Protocolo novo `record-inline-evidence-v1`, somente summary e open_questions. Segmentos têm exatamente text, sources e modality. O campo final é concatenação literal na ordem declarada: nenhum trim, normalização, espaço automático, interpretação ou reparo. Os intervalos Unicode são calculados pelo código para auditoria. O modelo não fornece caminhos, citações duplicadas ou offsets.

Summary tem de um a oito segmentos. Há até duas questões, cada uma com um a quatro segmentos. O total é no máximo doze. Cada segmento tem texto não vazio, de um a três IDs distintos existentes nas unidades fornecidas pelo chamador e modalidade established/suggested/unresolved. Campos desconhecidos, tipos inválidos, fontes inexistentes e instâncias forjadas são recusados. Após concatenação, resumo entre 8 e 600 caracteres; cada questão entre 1 e 200. A concisão de 25 palavras permanece critério de instrução, sem inventar um novo gate semântico.

A projeção é parte explícita deste novo contrato, sem converter ou corrigir respostas antigas. Os contratos de quotes/offsets e os oito campos anteriores permanecem iguais. Esta prova não produz proposta de ator, admissão de cena ou dados válidos para CAP-001. Não é um novo sistema de memória nem aprovação de arquitetura produtiva.

## Critérios antes da execução

Reconstruir texto e intervalos exatamente com Unicode, repetições, espaços e pontuação. Representar modalidades diferentes em segmentos distintos do mesmo resumo. Recusar referências e tipos inválidos sem incluir texto sensível nos erros. Demonstrar também o limite: um segmento com ID válido pode ser semanticamente falso; aprovação estrutural não significa cobertura, implicação, fidelidade ou agência. Esses estados devem permanecer não avaliados.

Encerrar a prova offline se ela exigir interpretar/reparar texto, alterar regra do produto ou perder distinção de modalidades. Havendo contrato coerente e testes/revisão concluídos, preparar uma observação própria com caso sintético novo, parâmetros e critérios congelados antes da chamada. Essa observação terá no máximo uma chamada low/3.072, espera e deadline de 60 s, sem retry/fallback ou juiz LLM. Não usar a oficina como reposição, não reutilizar a abertura, não alegar comparação causal. Qualquer observação termina após a única chamada e sua análise.
