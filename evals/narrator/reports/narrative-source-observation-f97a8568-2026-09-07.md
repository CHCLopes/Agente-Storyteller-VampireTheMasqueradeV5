# Fonte integral — observação f97a8568 encerrada

O piloto terminou com **uma chamada HTTP 200 e schema válido, rejeição local da pergunta e um turno dependente pulado**. O código de saída é 1. O resultado original permanece inalterado: nenhuma projeção foi criada, o segundo USER não foi enviado e a continuidade entre fontes não foi observada.

Batch `f97a8568-4b67-4f8a-b975-78f4b6e5638b`; execução `20260907T234303Z-6886c00d-1c52-4ee8-a712-42992877d6da`. Rota Groq / `qwen/qwen3.8-27b` verificada, finish_reason stop. Uso informado: 574 tokens de entrada e163 de saída, subtotal737. O agregado é parcial porque houve uma chamada das duas previstas; raciocínio null não significa zero e custo permanece indisponível.

## Resultado e leitura autorada

A pergunta literal **“O que fazes?”** tem três palavras e solicita livremente a próxima ação do jogador. A política congelada não reconhece essa flexão e retorna `scene_player_prompt_not_actionable`. Isso é um falso negativo local; não é motivo para reformular o SYSTEM ou considerar o piloto aprovado. A rejeição da pergunta impede alcançar os gates posteriores de agência, sigilo e demais políticas; eles não podem ser declarados aprovados por este registro.

A narrativa tem569 caracteres/99 palavras; com q são102 palavras. Descreve observações sensoriais compatíveis com permanecer na estufa sem tocar. Não identificamos uma nova ação positiva, decisão, fala ou emoção imposta ao jogador. “Nenhuma mão se move” acrescenta uma inferência corporal de imobilidade que não estava literalmente na entrada, sem uma violação inequívoca de escolha nesta amostra. Os detalhes ambientais são improvisação nova, não fatos previamente fornecidos pela fixture.

“Húmida” destoa da grafia brasileira esperada, e “traças de água” é lexicalmente obscuro. A conjugação “fazes” não é, por si, incompatível com português brasileiro. A evidência não foi corrigida nem reescrita. A leitura autorada fica neste relatório, separada de `not_performed/approval:null` no bruto.

## Integridade e encerramento

A reconstrução offline dos artefatos passou **antes de qualquer correção do validador**, usando o mesmo preflight da janela e os hashes históricos. O JSON associado conserva a prova completa, hashes dos dois brutos, snapshot temporário do validador520ad02b e lifecycle final. A verificação demonstra consistência local, não autenticação criptográfica do provedor. Os campos prepared_* e evidence_files da preparação foram preservados.

Lifecycle finished em `2026-09-07T23:44:08.2047125Z`, exit1. O wrapper descarta a chave antes desse estado, conforme seu finally testado. A janela PowerShell PID22460 usa NoExit; não foi comprovado o encerramento do processo da janela. Não relançar o lote nem preencher o skip.

## Continuidade autorizada

Corrigir o reconhecimento delimitado de perguntas com “fazes”, com controles de sujeito NPC, metanarrativa, múltiplas cláusulas e agência; preservar o resultado histórico. Prosseguir nas TASK-012/013 do plano de integração. A direção B permanece aprovada, mas esta amostra não demonstra continuidade, qualidade geral, verdade semântica, integração de produto ou CAP-001.

Detalhes e resposta n/q integral: [registro estruturado](narrative-source-observation-f97a8568-2026-09-07.json). [Preparação congelada](narrative-source-preparation-2026-09-07.json).
