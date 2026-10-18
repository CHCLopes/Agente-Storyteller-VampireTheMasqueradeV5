# Próximo passo de escolha do narrador — parecer técnico

Proposta somente documental, em 12/09/2026. Não implementa comparador, altera gates, pede credencial ou autoriza outra inferência. Base: arquivos atuais lidos e resultados já encerrados; não incorpora respostas antigas como braços de um experimento novo.

## Recomendação

Não preparar outro comparativo apenas substituindo as cenas. O comparador existente já executa o fluxo retido e fornece aliases explícitos. A omissão encontrada no diagnóstico de extensão é específica daquele harness puro e não justifica refazer uma comparação que já tinha o contrato correto. Também não há evidência para adotar o SYSTEM B de orçamento: todos os quatro textos do diagnóstico ficaram dentro do limite original, resultado previamente definido como não discriminante.

Sob as condições propostas — mesmos alvos, SYSTEM e gates, com apenas novos contextos — não identifiquei uma hipótese nova que justifique outra observação agora. Isso seria nova amostragem da mesma pergunta, não uma correção operacional pendente ou um teste de mecanismo distinto. Renomear locais/NPCs não supera essa limitação.

O protocolo encerrado é explícito: “Não repetir para forçar vencedor” (`source_comparison_protocol_v1.md:108–109`) e “Nova investigação posterior terá hipótese e protocolo próprios” (:111). Esta recomendação preserva os critérios; não sugere reduzi-los para qualificar algum candidato.

## Matriz de evidência e pendências

| Dimensão | Evidência disponível | O que permanece sem resposta |
|---|---|---|
| Fluxo técnico B | Comparador 61b83 executou setup, produtor real, cápsula retida, H6, commit e replay. `_config` já passa os aliases do NPC. A composição técnica local foi encerrada em plano próprio. | Isso não escolhe narrador nem aceita a experiência de jogador. Não há código de aliases a corrigir nesse caminho por causa de 291b. |
| Conformidade Qwen | Em 61b83 houve excessos de 155 e 157 palavras. Em 291b houve quatro saídas abaixo de 150. As duas recusas C1 de 291b decorreram de aliases omitidos no harness, conforme diagnóstico local confirmado. | A variabilidade observada não sustenta aderência futura. Corrigir a leitura do diagnóstico não converte suas recusas em commits nem torna Qwen elegível no lote antigo. |
| Conformidade GPT-OSS | Em 61b83, três turnos da Oficina foram confirmados; a recusa no Arquivo teve falso positivo delimitado e correção local posterior. | A proposta recusada continua recusada no lote encerrado. Falta evidência suficiente para qualificação; não completar seus skips com novas respostas. |
| Reação e progressão | O comparativo registrou avanço fraco nas esperas de ambos. Em 291b, C2 intensificou a ameaça da bandeja com progresso modesto; ambos os textos atribuíram continuidade a um estado da porta não fornecido. | Gates técnicos aprovados não demonstram progressão narrativa suficiente. O diagnóstico de extensão não é uma comparação de modelos. |
| Orçamento por campo | Ambos B atenderam à margem solicitada em 291b; ambos A também atenderam ao gate original. | Não se demonstrou a necessidade ou vantagem causal da margem. Não adotar o prompt B, aumentar limite ou truncar saída. |
| Escolha de produto | Nenhum candidato satisfez a elegibilidade do protocolo 61b83. O transporte sintético possui provas técnicas próprias. | Aceitação do recorte de uso, configuração escolhida para eventual experiência e modelo default são decisões distintas; CAP-001 permanece fora desta evidência. |

## Opção local útil, sem chamadas

O próximo trabalho mínimo é concluir o quadro revisável de uso B a partir dos planos existentes, separando três decisões: recorte de jogador, contrato de acesso e configuração experimental explícita. O auditor designado pelo root já está conferindo essa fronteira; não há motivo para duplicar a composição encerrada.

Esse quadro deve explicitar o que a experiência já oferece, suas exclusões e o que significaria aceitá-la: um operador no desktop, loopback e sessão escolhida pelo servidor; ações reconhecidas e comportamento de recusa/consulta; narrativa somente após commit; limitações observadas de resposta/progressão; modelo ainda não qualificado. Acompanhamento remoto do desktop não implica publicação da API. Não adicionar identidade, contas, proxy ou acesso direto remoto como detalhe técnico.

Referências concretas: `plan/feature-narrative-source-local-handler-1.md:11–13,47–56` distingue preparação técnica concluída de aceitação do uso. `plan/feature-narrative-source-transport-1.md:158–175` apresenta as alternativas de acesso e a decisão arquitetural separada para serviço remoto direto. Preparar esse quadro é trabalho local; não exige relaxar gates nem iniciar outro lote.

## Interfaces disponíveis se surgir uma pergunta prospectiva distinta

Não é necessária nova infraestrutura. `create_source_trial_setup` (`api/narrative_source_setup_service.py:19`), `create_source_producer_config` (`api/narrative_source_input.py:153`), `prepare_source_player_action` (`api/narrative_source_input_service.py:56`) e `execute_retained_source_turn` (`api/narrative_source_coordinator.py:84`) já formam o caminho correto. A cápsula conserva aliases, e o executor os encaminha em :106–107.

O comparador atual confirma esse uso em `scripts/evaluate_source_comparison.py:181–185,251–258,307–356`. Em eventual protocolo futuro, aliases precisam aparecer no config, cápsula e revalidação dos artefatos; não devem ser inferidos de texto. Histórias posteriores pertencem somente ao bloco que as confirmou. Bancos/sessões novos, replays sem gateway e contagem global limitada são padrões reutilizáveis.

O comparador fechado, porém, não é um runner genérico: `prepare_experiment` (:114) prende hashes, casos, ordem, três turnos e constantes globais. Seus métodos de execução e verificação dependem desse freeze. Não passar um corpus novo por monkeypatch nem mudar o arquivo histórico. Um consumidor futuro real precisaria de protocolo/corpus próprios e um adaptador experimental pequeno sobre as APIs existentes, com teste offline e freeze próprios. As guardas de observação/tempo/tokens do diagnóstico recente também não podem ser importadas cegamente, pois parte delas prende Qwen e o formato de quatro slots puros.

Hoje a necessidade de código é zero. Não extrair uma plataforma comum, refatorar os harnesses encerrados ou fabricar uma mudança de prompt para justificar nova inferência. Uma pergunta de cobertura realmente diferente poderia fundamentar outra avaliação no futuro; nenhuma foi estabelecida neste parecer. A evidência atual permite relatar limites e preparar uma decisão concreta de uso, sem declarar vencedor ou tornar essa decisão aprovação automática de narrador/produto.
